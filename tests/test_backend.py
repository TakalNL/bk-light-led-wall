"""Exercise our adapter with real upstream plans and a synthetic GATT client."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from pypixelcolor.commands.send_image import send_image_hex
from pypixelcolor.lib.transport.ack_manager import AckManager
from pypixelcolor.lib.transport.send_plan import single_window_plan

from led_matrix_hacker import library_link
from led_matrix_hacker.library_link import LibraryLink, TracedClient
from led_matrix_hacker.protocol import NOTIFY_UUID, WRITE_UUID


class Device:
    mtu_size = 23
    is_connected = True

    def __init__(self, on_write=lambda device, data: None):
        self.on_write = on_write
        self.writes = []
        self.callback = None
        self.write = SimpleNamespace(properties=['write'], max_write_without_response_size=0)
        self.notify = SimpleNamespace(properties=['notify'])
        self.services = SimpleNamespace(
            get_service=lambda _: object(),
            get_characteristic=lambda uuid: self.write if uuid == WRITE_UUID else self.notify,
        )

    def emit(self, data):
        self.callback(SimpleNamespace(uuid=NOTIFY_UUID), data)

    async def start_notify(self, _, callback):
        self.callback = callback

    async def stop_notify(self, _):
        self.callback = None

    async def write_gatt_char(self, _, data, *, response):
        assert response is True
        self.writes.append(bytes(data))
        self.on_write(self, data)


async def link_for(device, *, chunk_size=20):
    records = []
    record = lambda kind, **fields: records.append((kind, fields))
    client = TracedClient(device, record)
    client.chunk_size = chunk_size
    client.without_response_limit = 0
    ack = AckManager()
    await client.start_notify(NOTIFY_UUID, ack.make_notify_handler())
    return LibraryLink(client, ack, record), records


def test_query_captures_immediate_reply_and_filters_unrelated_notifications():
    async def run():
        def respond(device, _):
            device.emit(bytes.fromhex('0500020003'))
            device.emit(bytes.fromhex('0500018083'))
        link, _ = await link_for(Device(respond))
        assert await link.query(b'query', opcode=b'\x01\x80', label='info') == bytes.fromhex('0500018083')
        assert link.client.notification_filter is None
        # The upstream response path must restore its normal ACK subscription.
        assert link.client.client.callback is not None
    asyncio.run(run())


def test_query_timeout_restores_subscription_and_allows_next_command_without_retry():
    async def run():
        device = Device()
        link, _ = await link_for(device)
        with pytest.raises(TimeoutError):
            await link.query(b'query', opcode=b'\x01\x80', label='info', timeout=.001)
        assert device.writes == [b'query']
        assert device.callback is not None and link.client.notification_filter is None
        await link.send(single_window_plan('next', b'next', requires_ack=False))
        assert device.writes == [b'query', b'next']
    asyncio.run(run())


def test_upstream_chunking_stops_at_failed_write_without_replaying_partial_message():
    async def run():
        def fail_second(device, _):
            if len(device.writes) == 2:
                raise OSError('failed chunk')
        device = Device(fail_second)
        link, _ = await link_for(device)
        with pytest.raises(OSError, match='failed chunk'):
            await link.send(single_window_plan('raw', bytes(range(60)), requires_ack=False))
        assert device.writes == [bytes(range(20)), bytes(range(20, 40))]
        assert not link._sending
    asyncio.run(run())


def test_fragmented_image_captures_reply_during_last_write():
    async def run():
        plan = send_image_hex((b'\x89PNG\r\n\x1a\n' + bytes(range(100))).hex(), '.png')
        expected = plan.windows[0].data
        def respond(device, _):
            if sum(map(len, device.writes)) == len(expected):
                device.emit(bytes.fromhex('0500020003'))
        device = Device(respond)
        link, _ = await link_for(device)
        _, _, replies = await link.send(plan, timeout=.1)
        assert replies == [bytes.fromhex('0500020003')]
        assert b''.join(device.writes) == expected
        assert max(map(len, device.writes)) == 20
    asyncio.run(run())


def test_notification_capture_failure_aborts_without_more_writes():
    async def run():
        device = Device(lambda device, _: device.emit(bytes.fromhex('0500018083')))
        link, _ = await link_for(device)
        def broken_record(kind, **fields):
            if kind == 'library_notification':
                raise OSError('capture disk full')
        link.client.record = broken_record
        with pytest.raises(OSError, match='disk full'):
            await link.query(b'query', opcode=b'\x01\x80', label='info')
        assert device.writes == [b'query']
        assert not link._sending and link.client.notification_filter is None
    asyncio.run(run())


def test_multi_window_gif_uses_upstream_intermediate_and_final_acknowledgments():
    async def run():
        plan = send_image_hex((b'GIF89a' + bytes(range(256))*100).hex(), '.gif')
        windows = [window.data for window in plan.windows]
        boundaries = [sum(map(len, windows[:index+1])) for index in range(len(windows))]
        def respond(device, _):
            total = sum(map(len, device.writes))
            if total in boundaries:
                device.emit(bytes((5, 0, 3, 0, 3 if total == boundaries[-1] else 1)))
        device = Device(respond)
        link, _ = await link_for(device, chunk_size=244)
        _, _, replies = await link.send(plan, timeout=.5)
        assert [p[4] for p in replies] == [1, 1, 3]
        assert b''.join(device.writes) == b''.join(windows)
    asyncio.run(run())


@pytest.mark.parametrize('reply', ['0500030003', '0500020001'])
def test_wrong_opcode_or_nonfinal_status_cannot_complete_png_upload(reply):
    async def run():
        device = Device(lambda device, _: device.emit(bytes.fromhex(reply)))
        link, _ = await link_for(device)
        with pytest.raises(TimeoutError):
            await link.send(send_image_hex('89504e470d0a1a0a00', '.png'), timeout=.001)
        assert not link._sending and link.client.notification_filter is None
    asyncio.run(run())


@pytest.mark.parametrize('reply', ['05000180ff', '0500018081', '0600018083'])
def test_initialize_rejects_unknown_wrong_size_and_malformed_profiles(reply):
    async def run():
        device = Device(lambda device, _: device.emit(bytes.fromhex(reply)))
        link, _ = await link_for(device)
        with pytest.raises(ValueError):
            await link.initialize(versions=False)
        assert len(device.writes) == 1
    asyncio.run(run())


def test_initialize_returns_upstream_info_and_keeps_raw_version_evidence():
    async def run():
        def respond(device, data):
            device.emit(bytes.fromhex('0b00018083212a00000100' if data[2:4] == b'\x01\x80' else '080005800e020704'))
        link, records = await link_for(Device(respond))
        info = await link.initialize()
        assert (info.width, info.height, info.device_type) == (64, 16, 0x83)
        versions = next(fields for kind, fields in records if kind == 'firmware_versions')
        assert versions['mcu_version_bytes'] == [14, 2]
        assert versions['secondary_version_bytes'] == [7, 4]
    asyncio.run(run())


def test_commands_cannot_overlap_and_cancellation_releases_the_link():
    async def run():
        link, _ = await link_for(Device())
        task = asyncio.create_task(link.query(b'query', opcode=b'\x01\x80', label='info'))
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError, match='one panel command'):
            await link.send(single_window_plan('other', b'other', requires_ack=False))
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await link.send(single_window_plan('next', b'next', requires_ack=False))
        assert link.client.client.writes == [b'query', b'next']
    asyncio.run(run())


def test_connection_uses_negotiated_mtu_and_allows_write_with_response_only(monkeypatch):
    device = Device()
    options = []
    @asynccontextmanager
    async def connect(_, **kwargs):
        options.append(kwargs)
        yield object(), device
    monkeypatch.setattr(library_link, 'connection', connect)
    async def run():
        async with library_link.library_connection('mock', lambda *a, **k: None,
                                                   windows_cached_services=False, chunk_size=500) as link:
            assert link.client.chunk_size == 20
            await link.send(single_window_plan('raw', bytes(range(45)), requires_ack=False))
            with pytest.raises(ValueError):
                await link.send(single_window_plan('fast', b'fast', requires_ack=False), response=False)
        assert device.callback is None
    asyncio.run(run())
    assert max(map(len, device.writes)) == 20
    assert 'winrt_options' not in options[0]


@pytest.mark.parametrize('size', [0, -1, 513, True, 20.5])
def test_invalid_chunk_size_is_rejected_before_discovery(size, ble):
    async def run():
        async with library_link.library_connection('mock', lambda *a, **k: None, chunk_size=size):
            pytest.fail('Invalid chunk size must not connect')
    with pytest.raises(ValueError):
        asyncio.run(run())
    assert not ble.scan_calls
