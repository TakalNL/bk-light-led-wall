"""Upload one bounded GIF, disconnect, then allow time to observe local playback.

Source-backed experimental GIF framing; no persistent slot, retries or frame
stream. The information exchange also sets Europe/Berlin time-of-day.
"""

import argparse
import asyncio
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo

from led_matrix_hacker.recording import Recorder
from led_matrix_hacker.library_link import library_connection
from tools.experiments.local_animation import build_numbered_gif
from tools.experiments.art_animation import inspect_gif
from pypixelcolor.commands.send_image import send_image_hex


async def experiment(device, gif, output, *, windows_cached_services=False):
    metadata = inspect_gif(gif)
    plan = send_image_hex(gif.hex(), '.gif', save_slot=0)
    record = Recorder(output)
    record("experiment", name="panel-local-numbered-gif", dimensions=[64, 16],
           gif_sha256=hashlib.sha256(gif).hexdigest(), gif_bytes=len(gif), **metadata,
           windows=len(plan.windows), save_slot=0,
           visual_result="unverified")
    try:
        async with library_connection(device, record, windows_cached_services=windows_cached_services, write_delay=.01) as link:
            await link.initialize()
            _, _, replies = await link.send(plan, timeout=120)
            record("gif_reply", payload_hex=replies[-1].hex(), reference_completion_status=True)
        observe_seconds = max(12, min(60, metadata['encoded_loop_ms'] / 1000 * 2 + 2))
        record("autonomous_observation_started", connection_closed=True, duration_seconds=observe_seconds,
               application_writes_during_observation=0)
        await asyncio.sleep(observe_seconds)
        record("finished", connection_closed=True, visual_result="awaiting_owner_observation")
    except BaseException as error:
        record("error", error_type=type(error).__name__, message=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device")
    parser.add_argument("--output", type=Path, required=True, help="New JSONL capture")
    parser.add_argument("--preview", type=Path, required=True, help="New generated GIF")
    parser.add_argument("--windows-cached-services", action="store_true")
    parser.add_argument("--input", type=Path, help="Existing native 64x16 GIF, up to 600 frames / 256 KiB")
    args = parser.parse_args()
    ZoneInfo("Europe/Berlin")
    gif = args.input.read_bytes() if args.input else build_numbered_gif()
    inspect_gif(gif)
    with args.output.open("x", encoding="utf-8") as output:
        with args.preview.open("xb") as preview:
            preview.write(gif)
        asyncio.run(experiment(args.device, gif, output,
                               windows_cached_services=args.windows_cached_services))


if __name__ == "__main__":
    main()
