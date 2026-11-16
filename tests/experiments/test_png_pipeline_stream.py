import asyncio
from dataclasses import replace

import pytest

from tools.experiments.png_pipeline_stream import (
    PNG_REPLY, ReplyLedger, marker_png, pair_probe, pipeline_sender, stream, transport_only,
)
from led_matrix_hacker.library_link import LibraryLink, TracedClient
from pypixelcolor.commands.send_image import send_image_hex
from pypixelcolor.lib.transport.ack_manager import AckManager
from pypixelcolor.lib.transport.send_plan import single_window_plan


def image_plan(count=1):
    return send_image_hex(marker_png('END', count).hex(), '.png', save_slot=0)


def test_transport_copy_preserves_packet_and_original_ack_policy():
    original = image_plan()
    copied = transport_only(original, 500)
    assert copied.windows[0].data == original.windows[0].data
    assert original.windows[0].requires_ack and original.ack_policy.ack_per_window
    assert original.ack_policy.ack_final
    assert not copied.windows[0].requires_ack
    assert not copied.ack_policy.ack_per_window and not copied.ack_policy.ack_final
    with pytest.raises(ValueError):
        transport_only(original, len(original.windows[0].data) - 1)
    with pytest.raises(ValueError):
        transport_only(replace(original, windows=original.windows * 2), 500)
    saved = send_image_hex(marker_png('END', 1).hex(), '.png', save_slot=1)
    with pytest.raises(ValueError):
        transport_only(saved, 500)
    with pytest.raises(ValueError):
        transport_only(single_window_plan('not_an_image', b'\x05\x00\x04\x01\x01'), 500)


def test_ledger_preserves_multiple_replies_without_event_coalescing():
    async def run():
        records = []
        ledger = ReplyLedger(2, lambda kind, **fields: records.append((kind, fields)))
        ledger.reserve(4)
        ledger.reserve(8)
        with pytest.raises(RuntimeError, match='capacity'):
            ledger.reserve(9)
        waiter = asyncio.create_task(ledger.wait(empty=True))
        await asyncio.sleep(0)
        ledger.notify(None, PNG_REPLY)
        ledger.notify(None, PNG_REPLY)
        await waiter
        assert ledger.received == ledger.submitted == ledger.high_water == 2
        assert [fields['fifo_frame'] for kind, fields in records if kind == 'png_reply_received'] == [4, 8]
        assert not ledger.pending
    asyncio.run(run())


@pytest.mark.parametrize('payload', [b'\x05\x00\x02\x00\x01', b'\x05\x00\x03\x00\x03', b'', b'garbage'])
def test_unexpected_replies_latch_an_error_and_wake_waiter(payload):
    async def run():
        ledger = ReplyLedger(1, lambda *a, **kw: None)
        ledger.reserve(1)
        waiter = asyncio.create_task(ledger.wait(empty=True))
        await asyncio.sleep(0)
        ledger.notify(None, payload)
        with pytest.raises(ValueError, match='Unexpected notification'):
            await waiter
        with pytest.raises(ValueError):
            ledger.reserve(2)
    asyncio.run(run())


def test_extra_reply_is_rejected_after_drain():
    async def run():
        ledger = ReplyLedger(2, lambda *a, **kw: None)
        ledger.reserve(1)
        ledger.notify(None, PNG_REPLY)
        await ledger.wait(empty=True)
        ledger.notify(None, PNG_REPLY)
        with pytest.raises(ValueError, match='extra'):
            ledger.check()
    asyncio.run(run())


def test_missing_reply_expires_even_without_filling_pipeline():
    async def run():
        ledger = ReplyLedger(2, lambda *a, **kw: None, timeout=.01)
        ledger.reserve(1)
        with pytest.raises(TimeoutError):
            await ledger.wait(empty=True)
    asyncio.run(run())


def test_oldest_reply_deadline_is_not_extended_by_new_submissions():
    async def run():
        now = [0.0]
        ledger = ReplyLedger(2, lambda *a, **kw: None, clock=lambda: now[0], timeout=4)
        ledger.reserve(1)
        now[0] = 3.9
        ledger.reserve(2)
        now[0] = 4.01
        ledger.notify(None, PNG_REPLY)
        with pytest.raises(TimeoutError):
            ledger.check()
        assert ledger.received == 0
    asyncio.run(run())


class FakeRaw:
    is_connected = True

    def __init__(self, *, immediate=False, fail_write=False):
        self.callback = None
        self.writes = []
        self.immediate, self.fail_write = immediate, fail_write
        self.writing = False
        self.replies = []

    async def stop_notify(self, char):
        self.callback = None

    async def start_notify(self, char, callback):
        self.callback = callback

    async def write_gatt_char(self, char, data, *, response):
        assert response and not self.writing
        self.writing = True
        self.writes.append(bytes(data))
        try:
            if self.fail_write:
                raise OSError('simulated write failure')
            if self.immediate:
                self.callback(None, PNG_REPLY)
            else:
                async def complete(callback):
                    await asyncio.sleep(.09)
                    callback(None, PNG_REPLY)
                self.replies.append(asyncio.create_task(complete(self.callback)))
            await asyncio.sleep(0 if self.immediate else .005)
        finally:
            self.writing = False


def fake_link(raw, records):
    record = lambda kind, **fields: records.append((kind, fields))
    client = TracedClient(raw, record)
    client.chunk_size = 500
    client.without_response_limit = 244
    return LibraryLink(client, AckManager(), record)


def test_reply_before_write_returns_is_retained_and_normal_handler_restored():
    async def run():
        records = []
        raw = FakeRaw(immediate=True)
        link = fake_link(raw, records)
        plan = image_plan()
        async with pipeline_sender(link, 2) as (ledger, write):
            await write(plan, 1)
            await ledger.wait(empty=True)
            assert ledger.received == 1 and not ledger.pending
            assert link._sending
            with pytest.raises(RuntimeError):
                await link.send(plan)
        assert not link._sending
        await link.send(image_plan(2))
        assert raw.writes[0] == plan.windows[0].data
        assert any(kind == 'library_plan_completed' for kind, fields in records)
    asyncio.run(run())


@pytest.mark.parametrize('depth', [1, 2])
def test_pipeline_serializes_writes_drains_replies_and_bounds_inflight(depth):
    async def run():
        records = []
        raw = FakeRaw()
        link = fake_link(raw, records)
        plans = [image_plan(count) for count in range(15)]
        result = await stream(link, plans, fps=15, depth=depth)
        await asyncio.gather(*raw.replies)
        assert result['submitted'] == result['replies'] == len(raw.writes)
        assert result['submitted'] + result['skipped'] == len(plans)
        assert result['max_outstanding'] == depth
        if depth == 2:
            assert result['submitted'] == len(plans)
        else:
            assert result['skipped'] > 0
        reserved = [fields['frame'] for kind, fields in records if kind == 'image_reserved']
        assert raw.writes == [plans[index - 1].windows[0].data for index in reserved]
        assert not link._sending
    asyncio.run(run())


def test_write_failure_stops_without_retry_and_releases_command_guard():
    async def run():
        raw = FakeRaw(fail_write=True)
        link = fake_link(raw, [])
        with pytest.raises(OSError, match='simulated'):
            async with pipeline_sender(link, 2) as (ledger, write):
                await write(image_plan(), 1)
        assert len(raw.writes) == 1 and not link._sending
    asyncio.run(run())


def test_pair_probe_records_status_zero_but_requires_two_final_replies():
    async def run():
        records = []
        class Raw(FakeRaw):
            async def write_gatt_char(self, *args, **kwargs):
                await super().write_gatt_char(*args, **kwargs)
                if len(self.writes) == 2:
                    self.callback(None, bytes.fromhex('0500020000'))
        raw = Raw()
        result = await pair_probe(fake_link(raw, records), [image_plan(1), image_plan(2)])
        await asyncio.gather(*raw.replies)
        assert result['submitted'] == result['replies'] == result['max_outstanding'] == 2
        status = [fields for kind, fields in records if kind == 'nonfinal_status_observed']
        assert len(status) == 1 and not status[0]['counted_as_completion']
    asyncio.run(run())


def test_observed_status_zero_does_not_complete_an_image_or_extend_deadline():
    async def run():
        class Raw(FakeRaw):
            async def write_gatt_char(self, char, data, *, response):
                self.writes.append(bytes(data))
                self.callback(None, bytes.fromhex('0500020000'))
        link = fake_link(Raw(), [])
        with pytest.raises(TimeoutError):
            async with pipeline_sender(link, 2, observe_nonfinal=True) as (ledger, write):
                ledger.timeout = .01
                await write(image_plan(), 1)
                assert ledger.received == 0 and len(ledger.pending) == 1
                await ledger.wait(empty=True)
        assert not link._sending
    asyncio.run(run())


def test_hung_write_is_bounded_by_oldest_completion_deadline():
    async def run():
        class Raw(FakeRaw):
            async def write_gatt_char(self, char, data, *, response):
                await asyncio.sleep(10)
        link = fake_link(Raw(), [])
        with pytest.raises(TimeoutError):
            async with pipeline_sender(link, 2) as (ledger, write):
                ledger.timeout = .01
                await write(image_plan(), 1)
        assert not link._sending
    asyncio.run(run())
