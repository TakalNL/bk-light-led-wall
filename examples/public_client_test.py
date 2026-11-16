"""Test the unmodified pypixelcolor AsyncClient on the known 64x16 panel.

Connect performs upstream's automatic information/clock and firmware queries.
Content mode also uploads original native-size PNG/GIF files to non-saving slot
0. No project transport adapter, monkeypatches, BLE options or retries are used.
Debug logs may contain the device identifier; keep them private.
"""

import argparse
import asyncio
from dataclasses import asdict
import hashlib
import logging
from pathlib import Path
import time

from PIL import Image
from pypixelcolor import AsyncClient

from led_matrix_hacker.experiments import Recorder


async def step(record, name, operation, *, timeout=40):
    record('api_call_started', operation=name)
    start = time.monotonic()
    async with asyncio.timeout(timeout):
        result = await operation
    record('api_call_returned', operation=name, seconds=round(time.monotonic()-start, 6))
    return result


def check_content(path, expected_format):
    with Image.open(path) as image:
        if image.size != (64, 16) or image.format != expected_format:
            raise ValueError(f'Expected an original native-size 64x16 {expected_format}.')
    return dict(file=path.name, bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


async def experiment(args, record):
    client = AsyncClient(args.device)  # All upstream constructor defaults.
    record('experiment', api='pypixelcolor.AsyncClient', version=client.version(),
           mode=args.mode, reconnect=args.reconnect, connection_options='upstream defaults',
           write_with_response=True, save_slot=0,
           clock_side_effect='upstream synchronizes time-of-day to host local time')
    try:
        info = await step(record, 'connect', client.connect())
        record('device_info', **asdict(info))
        if (info.device_type, info.width, info.height) != (0x83, 64, 16):
            raise ValueError('Device does not match the tested 0x83 / 64x16 profile.')
        if client.get_device_info() is not info:
            raise ValueError('The public cached device-info getter returned a different object.')
        if args.mode == 'content':
            await step(record, 'send_png', client.send_image(args.png, save_slot=0))
            record('png_observation_started', **check_content(args.png, 'PNG'), seconds=args.hold)
            await asyncio.sleep(args.hold)
            await step(record, 'send_gif', client.send_image(args.gif, save_slot=0))
            record('gif_submitted', **check_content(args.gif, 'GIF'))
        await step(record, 'disconnect', client.disconnect(), timeout=10)
        if args.reconnect:
            reconnected = await step(record, 'reconnect_same_instance', client.connect())
            record('reconnected_device_info', **asdict(reconnected))
            if (reconnected.device_type, reconnected.width, reconnected.height) != (0x83, 64, 16):
                raise ValueError('The reconnected device profile changed.')
            await step(record, 'disconnect_after_reconnect', client.disconnect(), timeout=10)
        if args.mode == 'content':
            record('gif_observation_started', connection_closed=True, seconds=12)
            await asyncio.sleep(12)
        record('finished', visual_result='awaiting_owner_observation' if args.mode == 'content' else 'not_applicable')
    except BaseException as error:
        record('error', error_type=type(error).__name__, message=str(error))
        raise
    finally:
        # Public cleanup only; process exit also releases any partially opened
        # native handles if upstream's failed-connect cleanup is incomplete.
        try:
            await step(record, 'final_public_disconnect', client.disconnect(), timeout=10)
        except Exception as error:
            record('cleanup_error', error_type=type(error).__name__, message=str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', help='Previously identified panel address')
    parser.add_argument('--mode', choices=('connect', 'content'), default='connect')
    parser.add_argument('--reconnect', action='store_true', help='Reconnect the same public client instance once')
    parser.add_argument('--png', type=Path)
    parser.add_argument('--gif', type=Path)
    parser.add_argument('--hold', type=int, choices=(4, 8, 12), default=8)
    parser.add_argument('--output', type=Path, required=True, help='New private JSONL capture; also creates a .debug.log')
    args = parser.parse_args()
    if args.mode == 'content':
        if args.png is None or args.gif is None:
            parser.error('Content mode requires --png and --gif original diagnostic files.')
        check_content(args.png, 'PNG')
        check_content(args.gif, 'GIF')
    with args.output.open('x', encoding='utf-8') as output:
        logging.basicConfig(filename=args.output.with_suffix('.debug.log'), filemode='x',
                            level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
        asyncio.run(experiment(args, Recorder(output)))


if __name__ == '__main__':
    main()
