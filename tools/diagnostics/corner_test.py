"""Place three-pixel L markers at explicitly selected candidate grid corners.

Uses only the previously verified pixel command. Does not clear the background.
Candidate dimensions must come from hardware/reference evidence, not a guess.
"""

import argparse
import asyncio
from pathlib import Path

from led_matrix_hacker.recording import Recorder
from led_matrix_hacker.library_link import library_connection
from led_matrix_hacker.protocol import pixel_plan


def markers(width, height):
    if not 3 <= width <= 256 or not 3 <= height <= 256:
        raise ValueError("Candidate dimensions must be in 3..256.")
    return [
        ("red_top_left", (255, 0, 0), [(0, 0), (1, 0), (0, 1)]),
        ("green_top_right", (0, 255, 0), [(width - 1, 0), (width - 2, 0), (width - 1, 1)]),
        ("blue_bottom_left", (0, 0, 255), [(0, height - 1), (1, height - 1), (0, height - 2)]),
        ("yellow_bottom_right", (255, 255, 0),
         [(width - 1, height - 1), (width - 2, height - 1), (width - 1, height - 2)]),
    ]


async def experiment(device, width, height, output):
    groups = markers(width, height)
    packets = [(name, x, y, pixel_plan(x, y, rgb, width=width, height=height))
               for name, rgb, points in groups for x, y in points]
    record = Recorder(output)
    record("experiment", name="candidate-grid-corners", candidate_dimensions=[width, height],
           max_application_writes=len(packets), visual_result="unverified")
    try:
        async with library_connection(device, record, windows_cached_services=False, write_delay=.01) as link:
            for name, x, y, packet in packets:
                await link.send(packet)
                await asyncio.sleep(0.05)
        record("finished", visual_result="awaiting_owner_observation",
               expected="red TL, green TR, blue BL, yellow BR; three-pixel L markers at edges")
    except BaseException as error:
        record("error", error_type=type(error).__name__, message=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    markers(args.width, args.height)
    with args.output.open("x", encoding="utf-8") as output:
        asyncio.run(experiment(args.device, args.width, args.height, output))


if __name__ == "__main__":
    main()
