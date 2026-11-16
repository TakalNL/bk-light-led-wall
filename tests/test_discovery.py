import asyncio
import json

import pytest

from conftest import advertisement
from led_matrix_hacker.discovery import resolve_device, scan


def test_scan_keeps_unnamed_devices_and_uses_advertisement_rssi(ble):
    ble.advertisements["MOCK-B"] = advertisement("MOCK-B", None, rssi=None)
    report = asyncio.run(scan(0.1))
    assert len(report["devices"]) == 2
    assert report["devices"][0]["rssi_dbm"] == -42
    assert report["devices"][1]["name"] is None
    assert report["devices"][1]["rssi_dbm"] is None
    assert report["devices"][0]["service_uuids"] == ["mock-service"]
    assert "manufacturer_data_hex" not in report["devices"][0]
    assert ble.scan_calls == [{"timeout": 0.1, "return_adv": True}]
    assert not ble.clients
    json.dumps(report)


def test_scan_name_filter_uses_local_name_and_payloads_are_opt_in(ble):
    ble.advertisements = {"MOCK-A": advertisement(name=None, local_name="LED_BLE_mock")}
    report = asyncio.run(scan(0.1, name_filter="led_ble", include_payloads=True))
    assert report["devices"][0]["manufacturer_data_hex"] == {"123": "0102"}
    assert report["devices"][0]["service_data_hex"] == {"mock-service": "03"}
    assert asyncio.run(scan(0.1, name_filter="other"))["devices"] == []


def test_resolve_identifier_has_priority_over_names(ble):
    ble.advertisements["MOCK-B"] = advertisement("MOCK-B", "mock-a")
    assert asyncio.run(resolve_device("mock-a", 0.1)).address == "MOCK-A"


def test_resolve_unique_advertised_name(ble):
    ble.advertisements = {"MOCK-A": advertisement(name=None, local_name="Mock panel")}
    assert asyncio.run(resolve_device("Mock panel", 0.1)).address == "MOCK-A"


def test_resolve_duplicate_name_refuses_to_choose(ble):
    ble.advertisements["MOCK-B"] = advertisement("MOCK-B", "Mock panel")
    with pytest.raises(ValueError, match="Multiple devices"):
        asyncio.run(resolve_device("Mock panel", 0.1))
    assert not ble.clients
    assert ble.scan_calls == [{"timeout": 0.1, "return_adv": True}]
    assert not ble.address_find_calls


def test_resolve_missing_device_and_empty_identifier(ble):
    with pytest.raises(ValueError, match="Device not found"):
        asyncio.run(resolve_device("missing", 0.1))
    with pytest.raises(ValueError, match="empty"):
        asyncio.run(resolve_device("  ", 0.1))


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_scan_duration_does_not_touch_bluetooth(ble, timeout):
    with pytest.raises(ValueError):
        asyncio.run(scan(timeout))
    assert not ble.scan_calls


@pytest.mark.parametrize("identifier", ["aa:bb:cc:dd:ee:ff", "12AB34CD-5678-9ABC-DEF0-123456789ABC"])
def test_platform_identifier_uses_early_lookup_and_ignores_name_collision(ble, identifier):
    target = advertisement(identifier.upper(), "Panel")
    ble.advertisements = {"other": advertisement("OTHER", identifier), "target": target}
    assert asyncio.run(resolve_device(identifier, 15)) is target[0]
    assert ble.address_find_calls == [{"device_identifier": identifier, "timeout": 15}]
    assert not ble.scan_calls
    assert not ble.clients


def test_missing_address_reports_not_found_without_rescanning_or_using_a_name(ble):
    identifier = "AA:BB:CC:DD:EE:FF"
    ble.advertisements = {"other": advertisement("OTHER", identifier)}
    with pytest.raises(ValueError, match="Device not found"):
        asyncio.run(resolve_device(identifier, 15))
    assert len(ble.address_find_calls) == 1
    assert not ble.scan_calls and not ble.clients


@pytest.mark.parametrize("identifier", ["aa:bb:cc:dd:ee", "Office panel", "mock-a"])
def test_non_address_names_keep_full_scan_and_ambiguity_check(ble, identifier):
    ble.advertisements = {"a": advertisement("A", identifier),
                          "b": advertisement("B", None, local_name=identifier)}
    with pytest.raises(ValueError, match="Multiple devices"):
        asyncio.run(resolve_device(identifier, 15))
    assert ble.scan_calls == [{"timeout": 15, "return_adv": True}]
    assert not ble.address_find_calls


def test_cancelling_address_discovery_does_not_attempt_a_connection(ble, monkeypatch):
    from led_matrix_hacker import discovery, transport
    entered = asyncio.Event()
    async def pending(*args, **kwargs):
        entered.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(discovery.BleakScanner, "find_device_by_address", pending)
    async def connect():
        async with transport.connection("AA:BB:CC:DD:EE:FF"):
            pytest.fail("Cancelled discovery must not connect")
    async def run():
        task = asyncio.create_task(connect())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(run())
    assert not ble.clients


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_resolve_duration_does_not_start_either_scan(ble, timeout):
    with pytest.raises(ValueError):
        asyncio.run(resolve_device("AA:BB:CC:DD:EE:FF", timeout))
    assert not ble.address_find_calls and not ble.scan_calls
