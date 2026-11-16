import asyncio
from datetime import datetime

import pytest
from bleak.exc import BleakError

from led_matrix_hacker.inspection import inspect_device, listen
from led_matrix_hacker.transport import connection


def test_inspection_only_enumerates_metadata_and_disconnects(ble):
    report = asyncio.run(inspect_device("MOCK-A"))
    char = report["services"][0]["characteristics"][0]
    assert char["writable"] is True
    assert char["notifiable"] is True
    assert char["descriptors"] == [{"uuid": "mock-cccd", "handle": 8}]
    assert report["device"]["identifier"] == "MOCK-A"
    assert ble.clients[0].device.address == "MOCK-A"
    assert ble.clients[0].calls == ["connect", "disconnect"]


def test_connection_failure_still_attempts_cleanup(ble):
    ble.connect_error = BleakError("mock connect failure")
    with pytest.raises(BleakError, match="mock connect failure"):
        asyncio.run(inspect_device("MOCK-A"))
    assert ble.clients[0].calls == ["connect", "disconnect"]


def test_connect_timeout_is_bounded_and_disconnects(ble):
    ble.connect_delay = 60
    with pytest.raises(TimeoutError):
        asyncio.run(inspect_device("MOCK-A", connect_timeout=0.001))
    assert ble.clients[0].calls == ["connect", "disconnect"]


def test_cancellation_disconnects(ble):
    async def work():
        async with connection("MOCK-A"):
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(work())
    assert ble.clients[0].calls == ["connect", "disconnect"]


def test_windows_cache_and_service_filter_are_opt_in(ble):
    async def work():
        async with connection("MOCK-A", winrt_options={"use_cached_services": True}, service_uuids=["mock-service"]):
            pass
        async with connection("MOCK-A"):
            pass

    asyncio.run(work())
    assert ble.clients[0].options == {"winrt": {"use_cached_services": True}, "services": ["mock-service"]}
    assert ble.clients[1].options == {}


def test_discovery_telemetry_precedes_connection_failure(ble):
    observations = []

    def discovered(device):
        observations.append(device.address)
        assert not ble.clients

    ble.connect_error = BleakError("mock connection failure")

    async def work():
        async with connection("MOCK-A", discovered_callback=discovered):
            pytest.fail("Failed connection must not yield")

    with pytest.raises(BleakError):
        asyncio.run(work())
    assert observations == ["MOCK-A"]


def test_notification_events_have_timestamps_bytes_and_a_hard_limit(ble):
    ble.messages = [b"\x00\xff", b"\x01", b"\x02", b"\x03"]
    events = []
    count = asyncio.run(listen("MOCK-A", 7, events.append, max_events=2, duration=1))
    assert count == len(events) == 2
    assert events[0]["payload_hex"] == "00ff"
    assert events[0]["length"] == 2
    assert events[0]["characteristic_handle"] == 7
    assert datetime.fromisoformat(events[0]["timestamp"]).utcoffset().total_seconds() == 0
    assert events[0]["elapsed_seconds"] <= events[1]["elapsed_seconds"]
    assert ble.clients[0].calls == ["connect", ("start_notify", 7), ("stop_notify", 7), "disconnect"]


def test_listen_duration_expires_without_notifications(ble):
    assert asyncio.run(listen("MOCK-A", ble.characteristic.uuid, lambda _: None, duration=0.001)) == 0
    assert ble.clients[0].calls[-2:] == [("stop_notify", 7), "disconnect"]


@pytest.mark.parametrize("selector", ["missing", 123])
def test_listen_refuses_unknown_characteristic(ble, selector):
    with pytest.raises(ValueError, match="Characteristic not found"):
        asyncio.run(listen("MOCK-A", selector, lambda _: None))
    assert ble.clients[0].calls == ["connect", "disconnect"]


def test_listen_refuses_characteristic_without_notify(ble):
    ble.characteristic.properties = ["write"]
    with pytest.raises(ValueError, match="does not support"):
        asyncio.run(listen("MOCK-A", 7, lambda _: None))
    assert ble.clients[0].calls == ["connect", "disconnect"]


def test_subscription_failure_disconnects(ble):
    ble.subscribe_error = BleakError("mock subscription failed")
    with pytest.raises(BleakError, match="subscription failed"):
        asyncio.run(listen("MOCK-A", 7, lambda _: None))
    assert ble.clients[0].calls[-1] == "disconnect"


def test_sink_failure_propagates_and_cleans_up(ble):
    ble.messages = [b"\x01"]

    def broken_sink(_event):
        raise OSError("mock disk full")

    with pytest.raises(OSError, match="disk full"):
        asyncio.run(listen("MOCK-A", 7, broken_sink))
    assert ble.clients[0].calls[-2:] == [("stop_notify", 7), "disconnect"]


def test_unexpected_disconnect_retains_partial_events_and_reports_failure(ble):
    ble.messages = [b"\x01"]
    ble.drop_link = True
    events = []
    with pytest.raises(ConnectionError, match="disconnected during"):
        asyncio.run(listen("MOCK-A", 7, events.append))
    assert len(events) == 1
    assert ble.clients[0].calls[-1] == "disconnect"


@pytest.mark.parametrize("max_events", [0, -1, True, 1.5])
def test_invalid_event_limit_does_not_touch_bluetooth(ble, max_events):
    with pytest.raises(ValueError, match="positive integer"):
        asyncio.run(listen("MOCK-A", 7, lambda _: None, max_events=max_events))
    assert not ble.scan_calls
