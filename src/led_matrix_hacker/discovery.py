"""Collect BLE metadata without assuming a device name or protocol."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from bleak import BleakScanner


_PLATFORM_IDENTIFIER = re.compile(
    r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def positive_seconds(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Time must be a finite number greater than zero.")
    return value


def advertisement_record(device: Any, advertisement: Any, *, include_payloads: bool = False) -> dict:
    record = {
        "identifier": device.address,
        "name": device.name,
        "advertised_name": advertisement.local_name,
        "rssi_dbm": advertisement.rssi,
        "service_uuids": sorted(advertisement.service_uuids),
    }
    if include_payloads:
        record["manufacturer_data_hex"] = {
            str(company_id): bytes(value).hex()
            for company_id, value in advertisement.manufacturer_data.items()
        }
        record["service_data_hex"] = {
            uuid: bytes(value).hex() for uuid, value in advertisement.service_data.items()
        }
    return record


async def scan(
    timeout: float = 10.0, *, name_filter: str | None = None, include_payloads: bool = False
) -> dict:
    positive_seconds(timeout)
    started_at = utc_now()
    results = await BleakScanner.discover(timeout=timeout, return_adv=True)
    devices = []
    for device, advertisement in results.values():
        names = (device.name or "", advertisement.local_name or "")
        if name_filter is not None and not any(name_filter.casefold() in n.casefold() for n in names):
            continue
        devices.append(advertisement_record(device, advertisement, include_payloads=include_payloads))
    return {
        "schema_version": 1,
        "kind": "scan",
        "started_at": started_at,
        "finished_at": utc_now(),
        "timeout_seconds": timeout,
        "devices": sorted(devices, key=lambda d: d["identifier"]),
    }


async def resolve_device(identifier: str, timeout: float = 10.0) -> Any:
    """Find addresses immediately; scan fully to reject ambiguous exact names."""
    positive_seconds(timeout)
    if not identifier.strip():
        raise ValueError("Device identifier must not be empty.")
    if _PLATFORM_IDENTIFIER.fullmatch(identifier):
        # Bleak stops the scan on the first exact address/UUID advertisement.
        # A missing address must not fall back to a different device's name.
        device = await BleakScanner.find_device_by_address(identifier, timeout=timeout)
        matches = [device] if device is not None else []
    else:
        results = await BleakScanner.discover(timeout=timeout, return_adv=True)
        for device, _ in results.values():
            if device.address.casefold() == identifier.casefold():
                return device
        matches = [
            device for device, advertisement in results.values()
            if identifier in (device.name, advertisement.local_name)
        ]
    if len(matches) > 1:
        raise ValueError("Multiple devices have that name. Use an identifier from 'led-matrix scan'.")
    if not matches:
        raise ValueError(
            "Device not found. Use the current identifier or exact name from 'led-matrix scan'; "
            "check power, Bluetooth, and that the phone app is disconnected. "
            "BLE scans do not find Bluetooth Classic-only devices."
        )
    return matches[0]


def service_records(services: Any) -> list[dict]:
    result = []
    for service in services:
        characteristics = []
        for characteristic in service.characteristics:
            properties = sorted(characteristic.properties)
            characteristics.append({
                "uuid": characteristic.uuid,
                "handle": characteristic.handle,
                "description": characteristic.description,
                "properties": properties,
                "writable": bool({"write", "write-without-response"}.intersection(properties)),
                "notifiable": bool({"notify", "indicate"}.intersection(properties)),
                "descriptors": [
                    {"uuid": descriptor.uuid, "handle": descriptor.handle}
                    for descriptor in characteristic.descriptors
                ],
            })
        result.append({
            "uuid": service.uuid,
            "handle": service.handle,
            "description": service.description,
            "characteristics": characteristics,
        })
    return result
