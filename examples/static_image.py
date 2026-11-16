"""Send one 64x16 diagnostic image using the reference PNG/CRC upload.

Run only after the 64x16 corner experiment has been visually confirmed. Generates
a PNG preview/capture before connecting. PNG mode performs the documented
information/time and version exchange (Europe/Berlin). No automatic retries or
animation queue. Raw mode is retained for reproducing the failed raw-frame test;
it did not display an image on the owner's unit.
"""

import argparse
import asyncio
import hashlib
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from led_matrix_hacker.experiments import Recorder
from led_matrix_hacker.library_link import library_connection
from led_matrix_hacker.framebuffer import diagnostic_image, to_rgb_bytes
from led_matrix_hacker.protocol import reference_rgb_frame
from pypixelcolor.commands.send_image import send_image_hex
from pypixelcolor.lib.transport.send_plan import single_window_plan


async def experiment(device, plan, output, image_digest, image_format, windows_cached_services=False, label="64x16"):
    record = Recorder(output)
    record("experiment", name=f"reference-64x16-static-{image_format}-frame", dimensions=[64, 16],
           rgb_sha256=image_digest, visual_result="unverified", image_label=label)
    try:
        async with library_connection(device, record, windows_cached_services=windows_cached_services, write_delay=.01) as link:
            if image_format == "png":
                await link.initialize()
            _, _, replies = await link.send(plan)
            if image_format == "png":
                record("image_reply", payload_hex=replies[-1].hex(), matches_reference_ack=True)
            await asyncio.sleep(1)
        record("finished", visual_result="awaiting_owner_observation")
    except BaseException as error:
        record("error", error_type=type(error).__name__, message=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device")
    parser.add_argument("--output", type=Path, required=True, help="New JSONL capture")
    parser.add_argument("--preview", type=Path, required=True, help="New diagnostic PNG")
    parser.add_argument("--format", choices=("png", "raw"), default="png")
    parser.add_argument("--windows-cached-services", action="store_true", help="Reuse previously verified FA GATT metadata on Windows")
    parser.add_argument("--label", default="64x16", help="1..5 ASCII letters/digits/spaces to identify a new upload")
    args = parser.parse_args()
    image = diagnostic_image(label=args.label)
    pixels = to_rgb_bytes(image, width=64, height=16)
    png_buffer = BytesIO()
    image.save(png_buffer, format="PNG", optimize=True)
    png = png_buffer.getvalue()
    plan = (send_image_hex(png.hex(), '.png') if args.format == "png" else
            single_window_plan('failed_raw_frame_reference', reference_rgb_frame(pixels, width=64, height=16), requires_ack=False))
    if args.format == "png":
        ZoneInfo("Europe/Berlin")
    with args.output.open("x", encoding="utf-8") as output:
        with args.preview.open("xb") as preview:
            preview.write(png)
        asyncio.run(experiment(args.device, plan, output, hashlib.sha256(pixels).hexdigest(),
                               args.format, args.windows_cached_services, args.label))


if __name__ == "__main__":
    main()
