"""Isolated bounded PNG pipeline experiment; production transport is unchanged.

Upstream builds every packet and performs each acknowledged GATT write. A FIFO
ledger owns image completion replies instead of upstream's shared ACK events.
Replies have no image IDs: FIFO attribution is a hypothesis, not a guarantee.
"""

import argparse
import asyncio
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import replace
import hashlib
from io import BytesIO
import logging
from pathlib import Path

from PIL import Image
import pypixelcolor
from pypixelcolor.commands.send_image import send_image_hex
from pypixelcolor.lib.constants import NOTIFY_UUID
from pypixelcolor.lib.transport.ack_manager import AckManager, AckPolicy
from pypixelcolor.lib.transport.send_plan import send_plan

from games.starfall.game import text
from led_matrix_hacker.experiments import Recorder
from led_matrix_hacker.library_link import library_connection

if __package__:
    from .public_game_stream import build_frames, timing_summary
else:
    from public_game_stream import build_frames, timing_summary

PNG_REPLY = bytes.fromhex('0500020003')


class ReplyLedger:
    def __init__(self, depth, record, *, clock=None, timeout=4):
        if depth not in (1, 2) or timeout <= 0:
            raise ValueError('Expected depth 1 or 2 and a positive timeout.')
        self.depth, self.record = depth, record
        self.clock = clock or asyncio.get_running_loop().time
        self.timeout = timeout
        self.pending = deque()
        self.changed = asyncio.Event()
        self.error = None
        self.submitted = self.received = self.high_water = 0
        self.latencies = []

    def check(self):
        if self.error is not None:
            raise self.error
        if self.pending and self.clock() - self.pending[0][1] >= self.timeout:
            raise TimeoutError('Oldest outstanding PNG completion reply exceeded its deadline.')

    def reserve(self, frame):
        self.check()
        if len(self.pending) >= self.depth:
            raise RuntimeError('PNG pipeline capacity exceeded.')
        self.pending.append((frame, self.clock()))
        self.submitted += 1
        self.high_water = max(self.high_water, len(self.pending))
        self.record('image_reserved', frame=frame, outstanding=len(self.pending))

    def notify(self, _, data):
        # Latch callback errors for the sender; never throw into the BLE backend.
        try:
            self.check()
            if bytes(data) != PNG_REPLY:
                raise ValueError('Unexpected notification in PNG pipeline: ' + bytes(data).hex())
            if not self.pending:
                raise ValueError('Unsolicited or extra PNG completion reply.')
            frame, began = self.pending.popleft()
            latency = self.clock() - began
            self.latencies.append(latency)
            self.received += 1
            self.record('png_reply_received', fifo_frame=frame, received=self.received,
                        outstanding=len(self.pending), reply_ms=round(latency * 1000, 3))
        except Exception as error:
            if self.error is None:
                self.error = error
        self.changed.set()

    async def wait(self, *, empty=False):
        while True:
            self.check()
            if not self.pending or (not empty and len(self.pending) < self.depth):
                return
            remaining = self.timeout - (self.clock() - self.pending[0][1])
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), remaining)
            except TimeoutError:
                raise TimeoutError('Timed out waiting for PNG pipeline completion.') from None


def transport_only(plan, limit):
    """Copy a small non-saving PNG plan, leaving reply waits to the ledger."""
    windows = list(plan.windows)
    if len(windows) != 1 or plan.response_handler is not None:
        raise ValueError('Pipeline requires one-window PNG plans.')
    packet = windows[0].data
    if (not 15 < len(packet) <= limit or packet[2:5] != b'\x02\x00\x00'
            or packet[13:15] != b'\x00\x00' or not packet[15:].startswith(b'\x89PNG\r\n\x1a\n')):
        raise ValueError('Pipeline requires a complete slot-0 PNG fitting one write.')
    return replace(plan, windows=[replace(windows[0], requires_ack=False)],
                   chunk_size=limit, ack_policy=AckPolicy(False, False))


@asynccontextmanager
async def pipeline_sender(link, depth, *, observe_nonfinal=False):
    if link._sending:
        raise RuntimeError('A library command is already pending.')
    ledger = ReplyLedger(depth, link.record)
    link._sending = True
    link.client.notification_filter = None
    try:
        await link.client.stop_notify(NOTIFY_UUID)
        def notified(sender, data):
            if observe_nonfinal and bytes(data) == bytes.fromhex('0500020000'):
                link.record('nonfinal_status_observed', payload_hex=bytes(data).hex(),
                            outstanding=len(ledger.pending), counted_as_completion=False)
                return  # Do not release capacity or extend a completion deadline.
            ledger.notify(sender, data)
        await link.client.start_notify(NOTIFY_UUID, notified)
        transport_ack = AckManager()  # No shared ACK events are used for image replies.
        async def write(plan, frame):
            bare = transport_only(plan, link.client.chunk_size)
            ledger.reserve(frame)  # A reply can arrive before write completion.
            began = asyncio.get_running_loop().time()
            remaining = ledger.timeout - (ledger.clock() - ledger.pending[0][1])
            async with asyncio.timeout(remaining):
                result = await send_plan(link.client, bare, transport_ack, write_with_response=True)
            if not result.success:
                raise ValueError('Upstream PNG transport did not succeed.')
            ledger.check()
            return asyncio.get_running_loop().time() - began
        yield ledger, write
    except Exception as error:
        link.record('pipeline_aborted', submitted=ledger.submitted, replies=ledger.received,
                    outstanding=len(ledger.pending), error_type=type(error).__name__)
        raise
    finally:
        try:
            if link.client.is_connected:
                await link.client.stop_notify(NOTIFY_UUID)
                link.ack.reset()
                await link.client.start_notify(NOTIFY_UUID, link.ack.make_notify_handler())
        finally:
            link._sending = False


async def stream(link, plans, *, fps, depth):
    clock = asyncio.get_running_loop().time
    start = clock()
    starts, write_times = [], []
    index = 0
    async with pipeline_sender(link, depth) as (ledger, write):
        # Notification setup is excluded from measured streaming time.
        start = clock()
        link.record('stream_started', expected_frames=len(plans), fps=fps, depth=depth,
                    gatt_writes_serialized=True, image_reply_attribution='FIFO; no image IDs')
        while index < len(plans):
            await asyncio.sleep(max(0, start + index / fps - clock()))
            await ledger.wait()
            index = max(index, int((clock() - start) * fps + 1e-7))
            if index >= len(plans):
                break
            began = clock()
            starts.append(began - start)
            write_ms = await write(plans[index], index + 1)
            write_times.append(write_ms)
            link.record('image_write_completed', frame=index + 1, start_seconds=round(began - start, 6),
                        write_ms=round(write_ms * 1000, 3), outstanding=len(ledger.pending))
            index += 1
        await ledger.wait(empty=True)
        await asyncio.sleep(max(0, start + len(plans) / fps - clock()))
        elapsed = clock() - start
        # Keep the ledger installed to detect extra replies after the final drain.
        await asyncio.sleep(.25)
        ledger.check()
        if ledger.submitted != ledger.received:
            raise ValueError('PNG submission and completion counts differ.')
        result = dict(expected_frames=len(plans), submitted=ledger.submitted, replies=ledger.received,
                      skipped=len(plans) - ledger.submitted, seconds=round(elapsed, 6),
                      achieved_fps=round(ledger.received / elapsed, 5), max_outstanding=ledger.high_water,
                      reply_ms=timing_summary(ledger.latencies), write_ms=timing_summary(write_times),
                      start_interval_ms=timing_summary([b - a for a, b in zip(starts, starts[1:])]))
        link.record('stream_completed', **result)
    return result


async def pair_probe(link, plans):
    async with pipeline_sender(link, 2, observe_nonfinal=True) as (ledger, write):
        link.record('pair_probe_started', expected_images=2,
                    spacing='second image immediately after first GATT write returns')
        await write(plans[0], 1)
        if not ledger.pending:
            raise ValueError('First image completed before the second; no overlap was tested.')
        await write(plans[1], 2)
        await ledger.wait(empty=True)
        await asyncio.sleep(.25)
        ledger.check()
        if ledger.submitted != 2 or ledger.received != 2 or ledger.high_water != 2:
            raise ValueError('Pair probe did not overlap two images with two final replies.')
        result = dict(submitted=ledger.submitted, replies=ledger.received,
                      max_outstanding=ledger.high_water, reply_ms=timing_summary(ledger.latencies))
        link.record('pair_probe_completed', **result)
        return result


def marker_png(label, count):
    image = Image.new('RGB', (64, 16), 'black')
    text(image, label, 2, 1)
    text(image, str(count), 2, 9)
    buffer = BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


async def marker(link, label, count):
    await link.send(send_image_hex(marker_png(label, count).hex(), '.png', save_slot=0), timeout=4)


async def experiment(args, frames, record):
    record('experiment', name='bounded-png-pipeline', depth=args.depth, fps=args.fps,
           seconds=args.seconds, pair_probe=args.pair_probe, game='Starfall', write_with_response=True, save_slot=0,
           library_source=str(Path(pypixelcolor.__file__).resolve()),
           input_sha256=hashlib.sha256(b''.join(png for png, _ in frames)).hexdigest(),
           limitation='Completion replies have no IDs; counts do not prove unique image presentation.')
    plans = [send_image_hex(png.hex(), '.png', save_slot=0) for png, _ in frames]
    try:
        async with library_connection(args.device, record, chunk_size=500) as link:
            info = await link.initialize()
            if (info.device_type, info.width, info.height) != (0x83, 64, 16):
                raise ValueError('Unexpected panel profile.')
            for plan in plans:
                transport_only(plan, link.client.chunk_size)
            await asyncio.sleep(.25)
            async with asyncio.timeout(args.seconds + 10):
                if args.pair_probe:
                    result = await pair_probe(link, plans)
                else:
                    result = await stream(link, plans, fps=args.fps, depth=args.depth)
            await link.initialize(versions=False)
            await marker(link, 'END', result['replies'])
            record('end_marker', count=result['replies'])
        record('finished', visual_result='awaiting_owner_observation')
    except Exception as error:
        record('error', error_type=type(error).__name__, message=str(error))
        # Never reuse an ambiguous pipeline connection for recovery.
        try:
            async with library_connection(args.device, record, chunk_size=500) as link:
                await link.initialize()
                await marker(link, 'STOP', 0)
            record('recovery_completed', method='fresh connection; acknowledged slot-0 PNG')
        except Exception as recovery_error:
            record('recovery_failed', error_type=type(recovery_error).__name__, message=str(recovery_error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device')
    parser.add_argument('--depth', type=int, choices=(1, 2), required=True)
    parser.add_argument('--fps', type=int, choices=(10, 15, 20), default=15)
    parser.add_argument('--seconds', type=int, choices=(10, 30, 60, 120), default=30)
    parser.add_argument('--pair-probe', action='store_true', help='Only two overlapping images; record status 0 without counting it')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.pair_probe and args.depth != 2:
        parser.error('--pair-probe requires --depth 2')
    frames = build_frames(args.seconds, fps=args.fps)
    with args.output.open('x', encoding='utf-8') as output:
        logging.basicConfig(filename=args.output.with_suffix('.debug.log'), filemode='x', level=logging.DEBUG)
        asyncio.run(experiment(args, frames, Recorder(output, echo=False)))


if __name__ == '__main__':
    main()
