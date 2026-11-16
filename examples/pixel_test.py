"""Bounded reference-command experiment; not a supported device driver.

Prerequisite: identify the target and confirm its 00FA/FA02/FA03 GATT interface.
Sends only the published pixel command at (0, 0): red, green, then blue.
Visual confirmation is required; successful writes do not prove rendering.

Uses pypixelcolor's pixel builder and the shared instrumented backend.
"""

import argparse
import asyncio
from pathlib import Path

from led_matrix_hacker.experiments import Recorder
from led_matrix_hacker.library_link import library_connection
from led_matrix_hacker.protocol import pixel_plan

SEQUENCE = (("red", (255, 0, 0)), ("green", (0, 255, 0)), ("blue", (0, 0, 255)))


async def experiment(device_id, output, hold=4):
    record = Recorder(output)

    record("experiment", name="published-pixel-command", coordinate=[0, 0],
           visual_result="unverified", max_application_writes=3, hold_seconds=hold)
    try:
        async with library_connection(device_id, record, windows_cached_services=False) as link:
            record("ready", message=f"Watch the corner pixel: red, green, blue, {hold} seconds each.")
            await asyncio.sleep(2)
            for color, rgb in SEQUENCE:
                await link.send(pixel_plan(0, 0, rgb, width=1, height=1))
                record("color_sent", color=color, visual_result="awaiting_owner_observation")
                await asyncio.sleep(hold)
        record("finished", visual_result="awaiting_owner_observation")
    except BaseException as error:
        record("error", error_type=type(error).__name__, message=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device", help="Previously identified device identifier")
    parser.add_argument("--output", type=Path, required=True, help="New JSONL log file")
    parser.add_argument("--hold", type=int, choices=(4, 8, 12), default=4, help="Seconds per color")
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as output:
        asyncio.run(experiment(args.device, output, args.hold))


if __name__ == "__main__":
    main()
