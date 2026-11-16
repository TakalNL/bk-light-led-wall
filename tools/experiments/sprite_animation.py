"""Stream for 10 or 60 seconds at 2 or 5 fps, with an optional frame counter.

Leaves END and a yellow sprite on the right. Uses one connection and slot 0;
this tests host streaming, not stored GIF playback. Information request also
synchronizes panel time-of-day to Europe/Berlin. Stops on a failed frame.
"""

import argparse
import asyncio
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.experiments.animation import build_sprite_frames, stream_frames
from led_matrix_hacker.recording import Recorder
from led_matrix_hacker.library_link import library_connection


async def experiment(device, frames, output, *, windows_cached_services=False, fps=2,
                     duration_seconds=10):
    record = Recorder(output)
    record("experiment", name=f"sprite-png-stream-{fps}fps-{duration_seconds}s", dimensions=[64, 16],
           visual_result="unverified", final_image="END with yellow sprite at right",
           frame_counter=frames[-1].counter)
    try:
        async with library_connection(device, record, windows_cached_services=windows_cached_services, write_delay=.01) as link:
            await link.initialize()
            await stream_frames(link, frames, record, fps=fps, duration_seconds=duration_seconds)
        record("finished", visual_result="awaiting_owner_observation")
    except BaseException as error:
        record("error", error_type=type(error).__name__, message=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device")
    parser.add_argument("--output", type=Path, required=True, help="New JSONL capture")
    parser.add_argument("--previews", type=Path, required=True, help="New directory for PNG frames")
    parser.add_argument("--windows-cached-services", action="store_true")
    parser.add_argument("--fps", type=int, choices=(2, 5), default=2)
    parser.add_argument("--duration", type=int, choices=(10, 60), default=10, help="Playback seconds")
    parser.add_argument("--frame-counter", action="store_true", help="Show frame/total below the sprite")
    args = parser.parse_args()
    ZoneInfo("Europe/Berlin")
    frames = build_sprite_frames(fps=args.fps, frame_counter=args.frame_counter,
                                 duration_seconds=args.duration)
    with args.output.open("x", encoding="utf-8") as output:
        args.previews.mkdir()
        for frame in frames:
            (args.previews / f"{frame.index:02d}.png").write_bytes(frame.png)
        asyncio.run(experiment(args.device, frames, output,
                               windows_cached_services=args.windows_cached_services, fps=args.fps,
                               duration_seconds=args.duration))


if __name__ == "__main__":
    main()
