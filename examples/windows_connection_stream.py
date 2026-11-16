"""Compare ordinary sequential PNG streaming with a scoped Windows BLE hint.

Optional fast PNG writes and scoped timer precision support separate controlled
comparisons. All packets, ACK handling and serialized writes use the existing
pypixelcolor adapter path. Production defaults are unchanged.
"""

import argparse
import asyncio
from contextlib import contextmanager
import hashlib
import logging
from pathlib import Path
import sys

import pypixelcolor
from pypixelcolor.commands.send_image import send_image_hex

from led_matrix_hacker.experiments import Recorder
from led_matrix_hacker.library_link import library_connection
from led_matrix_hacker.windows_connection import connection_profile, connection_snapshot

if __package__:
    from .public_game_stream import PngReplies, build_frames, stream, timing_summary
    from .png_pipeline_stream import marker_png
else:
    from public_game_stream import PngReplies, build_frames, stream, timing_summary
    from png_pipeline_stream import marker_png


@contextmanager
def timer_precision(period_ms, record, *, api=None):
    """Pair a process-scoped WinMM timer request with its matching release."""
    if period_ms is None:
        record('timer_precision_ready', requested_ms=None)
        yield
        return
    if type(period_ms) is not int or period_ms != 1:
        raise ValueError('Only the experimental 1-ms timer request is supported.')
    if api is None:
        import ctypes
        api = ctypes.WinDLL('winmm', use_last_error=True)
        for name in ('timeBeginPeriod', 'timeEndPeriod'):
            function = getattr(api, name)
            function.argtypes = [ctypes.c_uint]
            function.restype = ctypes.c_uint
    status = int(api.timeBeginPeriod(period_ms))
    if status != 0:
        raise RuntimeError(f'Windows rejected timer precision request: {status}')
    try:
        record('timer_precision_ready', requested_ms=period_ms, request_status=status)
        yield
    finally:
        status = int(api.timeEndPeriod(period_ms))
        record('timer_precision_released', requested_ms=period_ms, release_status=status)
        if status != 0:
            raise RuntimeError(f'Windows timer precision release failed: {status}')


class MeasuredSleep:
    """Measure actual scheduled waits without changing asyncio scheduling."""

    def __init__(self, record, *, clock=None, sleep=asyncio.sleep):
        self.record = record
        self.clock = clock or asyncio.get_running_loop().time
        self.sleep = sleep
        self.overshoots = []
        self.zero_waits = 0

    async def __call__(self, delay):
        began = self.clock()
        await self.sleep(delay)
        if delay > 0:
            overshoot = max(0, self.clock() - began - delay)
            self.overshoots.append(overshoot)
            self.record('scheduled_wait', requested_ms=round(delay * 1000, 3),
                        overshoot_ms=round(overshoot * 1000, 3))
        else:
            self.zero_waits += 1

    def summary(self):
        return dict(positive_waits=len(self.overshoots), zero_waits=self.zero_waits,
                    overshoot_ms=timing_summary(self.overshoots),
                    includes_final_duration_wait=True)


async def send_png(link, info, png, *, fast=False):
    plan = send_image_hex(png.hex(), '.png', device_info=info, save_slot=0)
    windows = list(plan.windows)
    limit = min(link.client.chunk_size, link.client.without_response_limit if fast else 512)
    if len(windows) != 1 or not 1 <= len(windows[0].data) <= limit:
        raise ValueError('Experiment requires a complete PNG fitting one supported write.')
    return await link.send(plan, response=not fast, timeout=4)


async def experiment(args, frames, record, acks):
    record('experiment', name='windows-connection-parameters', profile=args.profile,
           fps=args.fps, seconds=args.seconds, game='Starfall', save_slot=0,
           write_with_response=not args.fast, timer_requested_ms=args.timer_ms,
           max_images_outstanding=1,
           windows_build=sys.getwindowsversion().build,
           library_source=str(Path(pypixelcolor.__file__).resolve()),
           input_sha256=hashlib.sha256(b''.join(png for png, _ in frames)).hexdigest())
    try:
        async with library_connection(args.device, record, chunk_size=500) as link:
            info = await link.initialize()
            if (info.device_type, info.width, info.height) != (0x83, 64, 16):
                raise ValueError('Unexpected panel profile.')
            async with connection_profile(link, args.profile):
                async def send(png):
                    await send_png(link, info, png, fast=args.fast)
                sleep = MeasuredSleep(record)
                with timer_precision(args.timer_ms, record):
                    result = await stream(send, frames, record, acks, fps=args.fps, sleep=sleep)
                record('scheduler_summary', **sleep.summary())
                previous = len(acks.replies)
                # END always uses the verified acknowledged transport.
                await send_png(link, info, marker_png('END', result['completed']))
                if acks.replies[previous:] != ['0500020003']:
                    raise ValueError('Missing strict END marker completion reply.')
                record('end_marker', count=result['completed'])
        record('finished', visual_result='awaiting_owner_observation')
    except Exception as error:
        record('error', error_type=type(error).__name__, message=str(error))
        try:
            # Close any ambiguous connection before a conventional recovery.
            async with library_connection(args.device, record, chunk_size=500) as link:
                info = await link.initialize()
                await send_png(link, info, marker_png('STOP', 0))
            record('recovery_completed', method='fresh connection; acknowledged slot-0 PNG')
        except Exception as recovery_error:
            record('recovery_failed', error_type=type(recovery_error).__name__, message=str(recovery_error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device')
    parser.add_argument('--profile', choices=('default', 'throughput'), required=True)
    parser.add_argument('--fps', type=int, choices=(10, 12, 15, 20), default=15)
    parser.add_argument('--seconds', type=int, choices=(30, 60, 120), default=30)
    parser.add_argument('--fast', action='store_true', help='PNG writes without GATT response; still require each final image reply')
    parser.add_argument('--timer-ms', type=int, choices=(1,), help='Scoped 1-ms Windows timer request during streaming')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('This experiment requires Windows 11 and the WinRT Bluetooth API.')
    frames = build_frames(args.seconds, fps=args.fps)
    with args.output.open('x', encoding='utf-8') as output:
        logging.basicConfig(filename=args.output.with_suffix('.debug.log'), filemode='x', level=logging.DEBUG)
        acks = PngReplies()
        logger = logging.getLogger('pypixelcolor.lib.transport.ack_manager')
        logger.addHandler(acks)
        try:
            asyncio.run(experiment(args, frames, Recorder(output, echo=False), acks))
        finally:
            logger.removeHandler(acks)


if __name__ == '__main__':
    main()
