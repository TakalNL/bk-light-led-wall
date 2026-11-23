"""Connect a complete wall, identify panels, and stream a boundary-crossing pattern."""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from queue import Queue
from statistics import median
import threading

from games.common.panel import LatestBoard
from games.common.wall import WallWorker
from led_matrix_hacker.recording import Recorder
from led_matrix_hacker.wall import CanvasFrame, Layout, Tile, demo_image, identify_image, load_layout


async def exercise(layout, output, *, seconds=10, fps=10, align_timing=False):
    mailbox, events = LatestBoard(), Queue()
    identify = CanvasFrame.from_image(identify_image(layout))
    mailbox.publish(identify)
    alignment = threading.Event()
    if align_timing:
        alignment.set()
    worker = WallWorker(layout, mailbox, events, Path('unused'), fps=fps, timing_alignment=alignment)
    frames, start, final_version = [], None, None

    def emit(kind, **data):
        nonlocal start
        if kind == 'connected':
            start = asyncio.get_running_loop().time()
        if kind == 'frame':
            frames.append(data)
            if final_version is not None and data['version'] == final_version:
                worker.close()
        elif kind == 'progress':
            print(data['message'], flush=True)

    worker.emit = emit
    record = Recorder(output, echo=False, trace_packets=False)

    async def produce():
        nonlocal final_version
        while not worker.stop.is_set():
            if start is not None:
                elapsed = asyncio.get_running_loop().time()-start
                if elapsed >= seconds+2:
                    mailbox.publish(identify)
                    final_version = mailbox.read()[0]
                elif elapsed >= 2:
                    mailbox.publish(CanvasFrame.from_image(demo_image(layout.size, int((elapsed-2)*fps))))
            await asyncio.sleep(1/fps)

    producer = asyncio.create_task(produce())
    try:
        async with asyncio.timeout(120 + seconds):
            await worker._run(record)
    finally:
        producer.cancel()
        await asyncio.gather(producer, return_exceptions=True)
    if not frames:
        raise RuntimeError('No combined frames completed.')
    record('wall_test_finished', completed_frames=len(frames), visual_result='awaiting_owner_observation')
    settled = frames[3:] or frames
    print(f"Timing alignment {'on' if align_timing else 'off'}: median ACK gap "
          f"{median(frame['completion_skew_ms'] for frame in settled):.1f} ms "
          f"(not measured LED onset).")
    print(f"Both/all panels acknowledged {len(frames)} combined frames. "
          f"Last wall reply: {frames[-1]['reply_ms']:.1f} ms. Visual alignment needs owner confirmation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('devices', nargs='*')
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--arrangement', choices=('stacked', 'horizontal'), default='stacked')
    parser.add_argument('--seconds', type=int, choices=range(1, 61), default=10)
    parser.add_argument('--fps', type=int, choices=range(1, 11), default=10)
    parser.add_argument('--align-timing', action='store_true', help='Delay faster panels to target aligned completion replies.')
    args = parser.parse_args()
    if args.settings and args.devices:
        parser.error('Choose saved settings or device identifiers.')
    if args.settings:
        layout = load_layout(args.settings)
    elif args.devices:
        layout = Layout(tuple(Tile(device, x=i*64 if args.arrangement == 'horizontal' else 0,
                                   y=i*16 if args.arrangement == 'stacked' else 0)
                              for i, device in enumerate(args.devices)))
    else:
        parser.error('Supply panel identifiers or --settings.')
    folder = Path('captures')
    folder.mkdir(exist_ok=True)
    stem = 'wall-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    identify_image(layout).save(folder/(stem+'.png'))
    with (folder/(stem+'.jsonl')).open('x', encoding='utf-8') as output:
        asyncio.run(exercise(layout, output, seconds=args.seconds, fps=args.fps, align_timing=args.align_timing))
    print(f'Capture: {folder/(stem+".jsonl")}')


if __name__ == '__main__':
    main()
