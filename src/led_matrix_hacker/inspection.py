"""GATT enumeration and explicitly requested, bounded notification capture."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable

from bleak.exc import BleakError

from .discovery import positive_seconds, service_records, utc_now
from .transport import connection

logger = logging.getLogger(__name__)


async def inspect_device(identifier: str, **connection_options) -> dict:
    started_at = utc_now()
    async with connection(identifier, **connection_options) as (device, client):
        return {
            "schema_version": 1,
            "kind": "inspection",
            "started_at": started_at,
            "finished_at": utc_now(),
            "device": {"identifier": device.address, "name": device.name},
            "services": service_records(client.services),
        }


async def listen(
    identifier: str,
    characteristic_selector: str | int,
    emit: Callable[[dict], None],
    *,
    duration: float = 30.0,
    max_events: int = 1000,
    **connection_options,
) -> int:
    """Subscribe to one selected characteristic; stream events without retaining a list.

    Subscribing can write the CCCD through the OS. No application commands are sent.
    The synchronous sink should be fast (for example a local JSONL file).
    """
    positive_seconds(duration)
    if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events <= 0:
        raise ValueError("max_events must be a positive integer.")
    done = asyncio.Event()
    count = 0
    sink_error: Exception | None = None
    disconnected = False

    def on_disconnect(_client):
        nonlocal disconnected
        disconnected = True
        done.set()

    async with connection(
        identifier, disconnected_callback=on_disconnect, **connection_options
    ) as (_device, client):
        characteristic = client.services.get_characteristic(characteristic_selector)
        if characteristic is None:
            raise ValueError("Characteristic not found. Choose a UUID or handle from 'led-matrix inspect'.")
        if not {"notify", "indicate"}.intersection(characteristic.properties):
            raise ValueError("Selected characteristic does not support notify or indicate.")
        started = time.monotonic()

        def on_notification(sender, payload):
            nonlocal count, sink_error
            if done.is_set():
                return
            try:
                emit({
                    "schema_version": 1,
                    "kind": "notification",
                    "timestamp": utc_now(),
                    "elapsed_seconds": round(time.monotonic() - started, 6),
                    "characteristic_uuid": sender.uuid,
                    "characteristic_handle": sender.handle,
                    "length": len(payload),
                    "payload_hex": bytes(payload).hex(),
                })
                count += 1
                if count >= max_events:
                    done.set()
            except Exception as error:
                sink_error = error
                done.set()

        subscribed = False
        try:
            async with asyncio.timeout(10.0):
                await client.start_notify(characteristic, on_notification)
            subscribed = True
            try:
                await asyncio.wait_for(done.wait(), timeout=duration)
            except TimeoutError:
                pass
            if sink_error is not None:
                raise sink_error
            if disconnected:
                raise ConnectionError("Device disconnected during notification capture; partial JSONL was retained.")
        finally:
            if subscribed and client.is_connected:
                try:
                    async with asyncio.timeout(5.0):
                        await client.stop_notify(characteristic)
                except (BleakError, OSError, TimeoutError):
                    logger.warning("Could not stop notifications; disconnecting the BLE link.")
    return count
