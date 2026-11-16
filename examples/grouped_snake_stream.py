"""Test upstream PR #88 grouped pixels using acknowledged writes only.

The probe waits on a control file so its picture can be checked while connected.
Motion uses a deterministic Snake pilot, latest-state selection, and either
grouped coordinate changes or full PNG uploads. Saved slots are never written.
Select .research/ipixel-set-pixels/src with PYTHONPATH for grouped modes.
"""

import argparse
import asyncio
from collections import defaultdict
import hashlib
from io import BytesIO
import logging
from pathlib import Path
import random

from PIL import Image
import pypixelcolor

from games.snake.game import DIRECTIONS, HEIGHT, Snake, WIDTH, render_board
from games.starfall.game import text
from led_matrix_hacker.experiments import Recorder
from led_matrix_hacker.library_link import library_connection

if __package__:
    from .corner_test import markers
    from .pixel_session import wait_command
    from .public_game_stream import timing_summary
else:
    from corner_test import markers
    from pixel_session import wait_command
    from public_game_stream import timing_summary

PR_COMMIT = 'fff5cc7ff44e318eb40d114a387574dca7de8d1d'


def pixel_groups(before, after):
    """Group actual display changes by RGB colour, respecting the upstream cap."""
    if after.mode != 'RGB' or after.size != (64, 16):
        raise ValueError('Expected native 64x16 RGB images.')
    if before is not None and (before.mode != 'RGB' or before.size != after.size):
        raise ValueError('Previous framebuffer must match the next image.')
    groups = defaultdict(list)
    for y in range(16):
        for x in range(64):
            colour = after.getpixel((x, y))
            if before is None or before.getpixel((x, y)) != colour:
                groups[colour].append((x, y))
    return [(colour, points[offset:offset + 123])
            for colour, points in sorted(groups.items())
            for offset in range(0, len(points), 123)]


def snake_frames(count):
    """Follow an adjacent cycle using normal rules, turns, growth and food."""
    cycle = [(x, 0) for x in range(WIDTH)]
    for y in range(1, HEIGHT):
        cycle.extend((x, y) for x in (range(WIDTH - 1, 0, -1) if y % 2 else range(1, WIDTH)))
    cycle.extend((0, y) for y in range(HEIGHT - 1, 0, -1))
    game = Snake(rng=random.Random(42))
    game.toggle_pause()
    initial = render_board(game.snapshot())
    frames = []
    position = cycle.index(game.body[0])
    for _ in range(count):
        position = (position + 1) % len(cycle)
        target = cycle[position]
        delta = (target[0] - game.body[0][0], target[1] - game.body[0][1])
        game.turn(next(name for name, vector in DIRECTIONS.items() if vector == delta))
        game.tick()
        board = game.snapshot()
        if board.phase != 'running':
            raise ValueError('Pilot stopped following ordinary Snake rules.')
        frames.append((render_board(board), board))
    return initial, frames


def probe_image():
    image = Image.new('RGB', (64, 16), 'black')
    for _, colour, points in markers(64, 16):
        for point in points:
            image.putpixel(point, colour)
    for x in range(8, 56, 6):
        image.putpixel((x, 7), (255, 255, 255))
    return image


def png_bytes(image):
    output = BytesIO()
    image.save(output, format='PNG', optimize=True)
    return output.getvalue()


def pack_pixel_commands(packets, limit):
    """Keep complete upstream paint commands together within one GATT write.

    Concatenation is an experimental firmware capability, not an upstream API
    guarantee. Never split a command or accept commands with other semantics.
    """
    if not 1 <= limit <= 512:
        raise ValueError('Invalid write budget.')
    batches = []
    current = b''
    for packet in packets:
        if (len(packet) < 10 or packet[2:4] != b'\x05\x01'
                or int.from_bytes(packet[:2], 'little') != len(packet)
                or (len(packet) - 8) % 2 or len(packet) > limit):
            raise ValueError('Expected a complete paint command that fits one write.')
        if current and len(current) + len(packet) > limit:
            batches.append(current)
            current = b''
        current += packet
    if current:
        batches.append(current)
    return batches


def batch_probe_image():
    image = Image.new('RGB', (64, 16), 'black')
    for left, colour in ((8, (255, 0, 0)), (28, (0, 255, 0)), (48, (0, 0, 255))):
        for y in range(6, 10):
            for x in range(left, left + 4):
                image.putpixel((x, y), colour)
    return image


async def paint(link, info, before, after, *, batch=False):
    # The upstream PR owns all command framing. Keep this an optional import so
    # ordinary app/test imports still work with the unchanged pinned dependency.
    from pypixelcolor.commands.set_fun_mode import set_pixels
    groups = pixel_groups(before, after)
    plans = [set_pixels(points, bytes(colour).hex(), device_info=info)
             for colour, points in groups]
    if batch:
        from pypixelcolor.lib.transport.send_plan import single_window_plan
        packets = []
        for plan in plans:
            windows = list(plan.windows)
            if (len(windows) != 1 or plan.ack_policy.ack_per_window
                    or plan.ack_policy.ack_final or plan.response_handler is not None):
                raise ValueError('Only reply-free upstream paint plans may be batched.')
            packets.append(windows[0].data)
        batches = pack_pixel_commands(packets, link.client.chunk_size)
        for payload in batches:
            await link.send(single_window_plan('batch_native_pixels', payload, requires_ack=False),
                            response=True, timeout=4)
        link.record('pixel_batch_completed', native_commands=len(plans), writes=len(batches),
                    bytes=sum(map(len, packets)))
        writes = len(batches)
    else:
        for plan in plans:
            await link.send(plan, response=True, timeout=4)
        writes = len(plans)
    return writes, sum(len(points) for _, points in groups)


async def play(send, initial, frames, record, *, fps, clock=None, sleep=asyncio.sleep):
    clock = clock or asyncio.get_running_loop().time
    previous = initial
    start = clock()
    index, completed, skipped, writes = 0, 0, 0, 0
    durations = []
    record('motion_started', fps=fps, expected_frames=len(frames),
           one_frame_in_flight=True, policy='latest state; diff against last completed image')
    while index < len(frames):
        await sleep(max(0, start + index / fps - clock()))
        selected = max(index, int((clock() - start) * fps + 1e-7))
        skipped += min(selected, len(frames)) - index
        index = selected
        if index >= len(frames):
            break
        image, board = frames[index]
        began = clock()
        async with asyncio.timeout(4):
            commands, points = await send(previous, image)
        duration = clock() - began
        durations.append(duration)
        previous = image
        completed += 1
        writes += commands
        record('frame_completed', frame=index + 1, completed=completed,
               update_ms=round(duration * 1000, 3), commands=commands,
               changed_pixels=points, score=board.score, body_cells=len(board.body))
        index += 1
    await sleep(max(0, start + len(frames) / fps - clock()))
    elapsed = clock() - start
    result = dict(expected_frames=len(frames), completed=completed, skipped=skipped,
                  seconds=round(elapsed, 6), achieved_fps=round(completed / elapsed, 5),
                  commands=writes, update_ms=timing_summary(durations))
    record('motion_completed', **result)
    return result


async def experiment(args, initial, frames, record):
    from pypixelcolor.commands.send_image import send_image_hex
    from pypixelcolor.commands.set_fun_mode import set_fun_mode
    if args.mode != 'png':
        from pypixelcolor.commands.set_fun_mode import set_pixels  # noqa: F401
    record('experiment', name='grouped-snake', mode=args.mode, fps=args.fps,
           seconds=args.seconds, write_with_response=True, save_slot=0,
           library_source=str(Path(pypixelcolor.__file__).resolve()),
           upstream_pr=88, library_commit=PR_COMMIT,
           input_sha256=hashlib.sha256(initial.tobytes() + b''.join(image.tobytes() for image, _ in frames)).hexdigest(),
           pilot='normal rules; one move per requested update; no human controls')
    try:
        async with library_connection(args.device, record, chunk_size=500) as link:
            info = await link.initialize()
            if (info.device_type, info.width, info.height) != (0x83, 64, 16):
                raise ValueError('Unexpected panel profile.')
            if args.mode != 'png':
                await link.send(set_fun_mode(True), response=True, timeout=4)
            if args.mode in ('probe', 'batch-probe'):
                expected = batch_probe_image() if args.mode == 'batch-probe' else probe_image()
                expected.save(args.output.with_suffix('.expected.png'))
                before = None
                if args.mode == 'batch-probe':
                    before = Image.new('RGB', (64, 16), 'black')
                    await paint(link, info, None, before)
                commands, points = await paint(link, info, before, expected,
                                               batch=args.mode == 'batch-probe')
                record('probe_drawn', commands=commands, points=points,
                       expected=('black background; three 4x4 blocks: red left, green middle, blue right'
                                 if args.mode == 'batch-probe' else
                                 'black background; red TL, green TR, blue BL, yellow BR L markers; eight white dots across middle'))
                await wait_command(args.control, 'finish', record)
                if args.mode == 'batch-probe':
                    await link.send(send_image_hex(png_bytes(expected).hex(), '.png', save_slot=0), timeout=4)
                    record('probe_recovered_with_acknowledged_png')
            else:
                if args.mode == 'grouped':
                    await paint(link, info, None, initial)
                    async def send(before, after):
                        return await paint(link, info, before, after)
                else:
                    await link.send(send_image_hex(png_bytes(initial).hex(), '.png', save_slot=0), timeout=4)
                    async def send(before, after):
                        await link.send(send_image_hex(png_bytes(after).hex(), '.png', save_slot=0), timeout=4)
                        return 1, 1024
                result = await play(send, initial, frames, record, fps=args.fps)
                # This ordered query exposes queued transport work, not the
                # instant the panel physically finished drawing a frame.
                began = asyncio.get_running_loop().time()
                await link.initialize(versions=False)
                record('ordered_query_completed', seconds=round(asyncio.get_running_loop().time() - began, 6))
                marker = Image.new('RGB', (64, 16), 'black')
                text(marker, 'END', 2, 1)
                text(marker, str(result['completed']), 2, 9)
                await link.send(send_image_hex(png_bytes(marker).hex(), '.png', save_slot=0), timeout=4)
                record('end_marker', count=result['completed'], mode='acknowledged PNG')
        record('finished', visual_result='awaiting_owner_observation')
    except BaseException as error:
        record('error', error_type=type(error).__name__, message=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device')
    parser.add_argument('--mode', choices=('probe', 'grouped', 'png', 'batch-probe'), default='probe')
    parser.add_argument('--fps', type=int, choices=(10, 15, 20), default=15)
    parser.add_argument('--seconds', type=int, choices=(30, 60, 120), default=60)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--control', type=Path)
    args = parser.parse_args()
    if args.mode in ('probe', 'batch-probe') and (args.control is None or args.control.exists()):
        parser.error('Probe requires a fresh --control path.')
    initial, frames = snake_frames(args.fps * args.seconds)
    with args.output.open('x', encoding='utf-8') as output:
        logging.basicConfig(filename=args.output.with_suffix('.debug.log'), filemode='x', level=logging.DEBUG)
        asyncio.run(experiment(args, initial, frames, Recorder(output, echo=False)))


if __name__ == '__main__':
    main()
