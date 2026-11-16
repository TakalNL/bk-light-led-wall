"""Validation and evidence metadata around the pinned pypixelcolor protocol.

FA02 pixels, information replies and PNG/GIF CRC uploads have hardware evidence
on the owner's 64x16 unit. The raw RGB reference failed its visual check and is
retained only for reproducing that negative result. Sources are pinned in RESEARCH.md.
"""

from datetime import datetime

from pypixelcolor.commands.set_time import set_time
from pypixelcolor.commands.set_fun_mode import set_pixel
from pypixelcolor.lib.constants import WRITE_UUID, NOTIFY_UUID
from pypixelcolor.lib.device_info import DEVICE_TYPE_MAP, LED_SIZE_MAP

SERVICE_UUID = "000000fa-0000-1000-8000-00805f9b34fb"

def device_info_request(local_time: datetime) -> bytes:
    """Published 0x8001 request: also synchronizes time-of-day on the panel."""
    if local_time.tzinfo is None or local_time.utcoffset() is None:
        raise ValueError("Pass an aware local datetime; do not infer the host timezone.")
    return set_time(local_time.hour, local_time.minute, local_time.second).windows[0].data


def _check_reply(payload: bytes, opcode: bytes, minimum: int) -> None:
    if len(payload) < minimum or payload[2:4] != opcode:
        raise ValueError("Unexpected or truncated reply; preserve raw bytes for investigation.")
    if int.from_bytes(payload[:2], "little") != len(payload):
        raise ValueError("Reply length prefix disagrees with received length.")


def parse_device_info(payload: bytes) -> dict:
    _check_reply(payload, b"\x01\x80", 5)
    device_type = payload[4]
    # Upstream's parser defaults unknown codes to 64x64; diagnostics must not.
    # These upstream mappings are references, not physical measurements.
    dimensions = LED_SIZE_MAP.get(DEVICE_TYPE_MAP.get(device_type))
    return {
        "device_type": device_type,
        "device_type_hex": f"0x{device_type:02x}",
        "reference_dimensions": list(dimensions) if dimensions else None,
        "dimensions_status": "reference_mapping_only" if dimensions else "unknown_type",
        "raw_reply_hex": payload.hex(),
    }


def parse_versions(payload: bytes) -> dict:
    _check_reply(payload, b"\x05\x80", 8)
    if len(payload) != 8:
        raise ValueError("Unexpected version reply size; do not guess extra fields.")
    return {
        "mcu_version_bytes": list(payload[4:6]),
        "secondary_version_bytes": list(payload[6:8]),
        "raw_reply_hex": payload.hex(),
    }


def pixel_plan(x: int, y: int, rgb: tuple[int, int, int], *, width: int, height: int):
    """Validate selected bounds, then use upstream's pixel command builder."""
    values = (x, y, width, height, *rgb)
    if len(rgb) != 3 or any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("Coordinates, dimensions and RGB channels must be integers.")
    if not (1 <= width <= 256 and 1 <= height <= 256 and 0 <= x < width and 0 <= y < height):
        raise ValueError("Coordinate outside selected dimensions, or dimensions exceed byte coordinates.")
    if any(not 0 <= channel <= 255 for channel in rgb):
        raise ValueError("RGB channels must be in 0..255.")
    return set_pixel(x, y, bytes(rgb).hex())


def reference_rgb_frame(pixels: bytes, *, width: int, height: int) -> bytes:
    """The exact 64x16 live RGB888 format from mx2rel/matrix.js.

    Other sizes are deliberately rejected: the fixed header's individual fields
    have not been experimentally varied. This path did not render the diagnostic
    image on the owner's unit; use the verified PNG path for static images.
    """
    if (width, height) != (64, 16):
        raise ValueError("The reference live-frame format is limited to 64x16.")
    if len(pixels) != 64 * 16 * 3:
        raise ValueError("Expected exactly 3072 row-major RGB888 bytes.")
    return bytes.fromhex("090c000000000c0000") + bytes(pixels)
