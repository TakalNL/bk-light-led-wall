"""Compare scripted Starfall streaming through AsyncClient and the app adapter.

Uses normal game controls and rules, no invulnerability, one upload in flight,
and latest-state selection when Bluetooth falls behind the requested schedule.
Only non-saving slot 0 is used. Debug logs contain private device information.
"""

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict
import hashlib
import logging
import math
from pathlib import Path
import statistics

from PIL import Image
import pypixelcolor
from pypixelcolor import AsyncClient
from pypixelcolor.__version__ import VERSION

from games.starfall.game import DT, SPRITES, Shooter, flight_png, text
from led_matrix_hacker.recording import Recorder

from tools.diagnostics.public_client_test import step

FPS = 10


def build_frames(seconds, fps=FPS):
    game = Shooter()
    game.toggle_pause()
    terminal_ticks = 0
    frames = []
    for tick in range(round(seconds / DT)):
        if game.phase in ('over', 'won'):
            terminal_ticks += 1
            if terminal_ticks >= round(1 / DT):
                game.restart()
                game.toggle_pause()
                terminal_ticks = 0
        if game.pickups:
            desired_y = min(game.pickups, key=lambda p: p.x).y - 1
        elif game.boss:
            desired_y = game.boss.y + 2
        elif game.enemies:
            target = min(game.enemies, key=lambda e: e.x)
            desired_y = target.y + len(SPRITES[target.kind]) / 2 - 2
        else:
            desired_y = 5
        dy = 1 if desired_y > game.y + .3 else -1 if desired_y < game.y - .3 else 0
        game.controls(0, dy, True)
        game.tick()
        # Keep the normal 20-Hz simulation at every output rate. At the default
        # 10 fps this selects exactly the same ticks as the original runner.
        if int((tick + 1) * DT * fps + 1e-7) > len(frames):
            board = game.snapshot()
            frames.append((flight_png(board), board))
    return frames


class PngReplies(logging.Handler):
    """Observe upstream debug messages without changing its BLE/ACK handling."""

    def __init__(self):
        super().__init__()
        self.replies = []

    def emit(self, record):
        message = record.getMessage()
        if message.startswith('Notify frame: '):
            self.replies.append(message.removeprefix('Notify frame: '))


def timing_summary(values):
    ordered = sorted(values)
    if not ordered:
        return None
    return dict(min=round(ordered[0] * 1000, 3), median=round(statistics.median(ordered) * 1000, 3),
                p95=round(ordered[math.ceil(len(ordered) * .95) - 1] * 1000, 3),
                max=round(ordered[-1] * 1000, 3))


async def stream(send_png, frames, record, acks, *, fps=FPS, clock=None, sleep=asyncio.sleep):
    clock = clock or asyncio.get_running_loop().time
    start = clock()
    duration = len(frames) / fps
    sent, starts, latencies = [], [], []
    index = 0
    record('stream_started', expected_frames=len(frames), fps=fps, seconds=duration,
           one_upload_in_flight=True, queue_policy='select latest state; never catch up with stale frames')
    while index < len(frames):
        await sleep(max(0, start + index / fps - clock()))
        index = max(index, int((clock() - start) * fps + 1e-7))
        if index >= len(frames):
            break
        png, board = frames[index]
        previous_replies = len(acks.replies)
        began = clock()
        async with asyncio.timeout(4):
            await send_png(png)
        latency = clock() - began
        if acks.replies[previous_replies:] != ['0500020003']:
            raise ValueError('Public upload did not produce exactly one strict PNG completion reply.')
        skipped = index - (sent[-1] + 1 if sent else 0)
        sent.append(index)
        starts.append(began - start)
        latencies.append(latency)
        record('frame_completed', frame=index+1, completed=len(sent), start_seconds=round(began-start, 6),
               reply_ms=round(latency*1000, 3), skipped_before=skipped,
               png_bytes=len(png), phase=board.phase, score=board.score, lives=board.lives)
        index += 1
    await sleep(max(0, start + duration - clock()))
    elapsed = clock() - start
    result = dict(expected_frames=len(frames), completed=len(sent), skipped=len(frames)-len(sent),
                  seconds=round(elapsed, 6), achieved_fps=round(len(sent)/elapsed, 5),
                  all_scheduled_frames_completed=len(sent) == len(frames),
                  reply_ms=timing_summary(latencies),
                  start_interval_ms=timing_summary([b-a for a, b in zip(starts, starts[1:])]))
    record('stream_completed', **result)
    return result


@asynccontextmanager
async def sender(args, record):
    if args.backend == 'adapter':
        from pypixelcolor.commands.send_image import send_image_hex
        from led_matrix_hacker.library_link import library_connection
        async with library_connection(args.device, record, chunk_size=500) as link:
            await link.initialize()
            async def send_png(png):
                await link.send(send_image_hex(png.hex(), '.png', save_slot=0), timeout=4)
            yield send_png
    else:
        options = {} if args.chunk_size is None else {'chunk_size': args.chunk_size}
        if args.fast:
            options['write_with_response'] = False
        client = AsyncClient(args.device, **options)
        try:
            info = await step(record, 'connect', client.connect())
            record('device_info', **asdict(info))
            if (info.device_type, info.width, info.height) != (0x83, 64, 16):
                raise ValueError('Device does not match the tested panel profile.')
            async def send_png(png):
                await client.send_image_hex(png.hex(), '.png', save_slot=0)
            yield send_png
        finally:
            await step(record, 'disconnect', client.disconnect(), timeout=10)


async def experiment(args, frames, record, acks):
    options = []
    if args.chunk_size is not None:
        options.append(f'chunk_size={args.chunk_size}')
    if args.fast:
        options.append('write_with_response=False')
    connection_options = 'public ' + ', '.join(options) + '; other upstream defaults' if options else 'upstream defaults'
    record('experiment', api='pypixelcolor.AsyncClient' if args.backend == 'public' else 'project adapter', version=VERSION,
           library_source=str(Path(pypixelcolor.__file__).resolve()),
           game='Starfall', seconds=args.seconds, fps=args.fps, save_slot=0,
           pilot='normal controls; no invulnerability',
           chunk_size=args.chunk_size if args.backend == 'public' else 500,
           write_with_response=not args.fast,
           connection_options=connection_options if args.backend == 'public' else 'cached FA service; 500-byte chunks',
           input_sha256=hashlib.sha256(b''.join(png for png, _ in frames)).hexdigest(),
           png_bytes_min=min(len(png) for png, _ in frames),
           png_bytes_max=max(len(png) for png, _ in frames))
    try:
        async with sender(args, record) as send_png:
            result = await stream(send_png, frames, record, acks, fps=args.fps)
            marker = Image.new('RGB', (64, 16), 'black')
            text(marker, 'END', 2, 1)
            text(marker, str(result['completed']), 2, 9)
            from io import BytesIO
            buffer = BytesIO()
            marker.save(buffer, format='PNG', optimize=True)
            previous = len(acks.replies)
            await step(record, 'end_marker', send_png(buffer.getvalue()), timeout=4)
            if acks.replies[previous:] != ['0500020003']:
                raise ValueError('Missing END marker completion reply.')
        record('finished', marker_count=result['completed'], visual_result='awaiting_owner_observation')
    except BaseException as error:
        record('error', error_type=type(error).__name__, message=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', help='Previously identified panel address')
    parser.add_argument('--backend', choices=('public', 'adapter'), default='public', help='Use adapter only for a comparison run')
    parser.add_argument('--seconds', type=int, choices=(60, 120, 300), default=120)
    parser.add_argument('--fps', type=int, choices=(10, 15, 20), default=FPS)
    parser.add_argument('--chunk-size', type=int, help='Public client override; requires the patched library (1..512)')
    parser.add_argument('--fast', action='store_true', help='Public writes without response; still require PNG completion replies')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.fast and args.backend != 'public':
        parser.error('--fast requires --backend public')
    if args.chunk_size is not None:
        if args.backend != 'public' or not 1 <= args.chunk_size <= 512:
            parser.error('--chunk-size requires --backend public and a value in 1..512')
    frames = build_frames(args.seconds, args.fps)
    with args.output.open('x', encoding='utf-8') as output:
        logging.basicConfig(filename=args.output.with_suffix('.debug.log'), filemode='x',
                            level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
        acks = PngReplies()
        logger = logging.getLogger('pypixelcolor.lib.transport.ack_manager')
        logger.addHandler(acks)
        try:
            asyncio.run(experiment(args, frames, Recorder(output), acks))
        finally:
            logger.removeHandler(acks)


if __name__ == '__main__':
    main()
