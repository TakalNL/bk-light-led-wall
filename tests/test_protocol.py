from datetime import datetime, timezone

import pytest

from led_matrix_hacker.protocol import (
    device_info_request, parse_device_info, parse_versions, pixel_plan,
    reference_rgb_frame,
)


def test_pixel_matches_visually_verified_hardware_packets():
    assert pixel_plan(0, 0, (255, 0, 0), width=1, height=1).windows[0].data.hex() == "0a00050100ff00000000"
    assert pixel_plan(0, 0, (0, 255, 0), width=1, height=1).windows[0].data.hex() == "0a0005010000ff000000"
    assert pixel_plan(0, 0, (0, 0, 255), width=1, height=1).windows[0].data.hex() == "0a000501000000ff0000"


@pytest.mark.parametrize("x,y,rgb,width,height", [
    (-1, 0, (0, 0, 0), 64, 16), (64, 0, (0, 0, 0), 64, 16),
    (0, 16, (0, 0, 0), 64, 16), (0, 0, (256, 0, 0), 64, 16),
    (0, 0, (0, 0), 64, 16), (True, 0, (0, 0, 0), 64, 16),
    (0, 0, (0, 0, 0), 257, 16),
])
def test_invalid_pixel_bounds_are_rejected(x, y, rgb, width, height):
    with pytest.raises(ValueError):
        pixel_plan(x, y, rgb, width=width, height=height)


def test_information_request_uses_explicit_time_of_day():
    assert device_info_request(datetime(2026, 11, 14, 19, 23, 45, tzinfo=timezone.utc)).hex() == "0800018013172d00"
    with pytest.raises(ValueError, match="aware"):
        device_info_request(datetime(2026, 11, 14))


def test_reference_act1025_reply_is_not_a_dimension_measurement():
    # Reference fixture from Pupariaa/display_session.py, not our hardware yet.
    result = parse_device_info(bytes.fromhex("0b00018083063200000100"))
    assert result["device_type"] == 0x83
    assert result["reference_dimensions"] == [64, 16]
    assert result["dimensions_status"] == "reference_mapping_only"


def test_unknown_type_never_defaults_to_a_size():
    result = parse_device_info(bytes.fromhex("05000180ff"))
    assert result["reference_dimensions"] is None
    assert result["dimensions_status"] == "unknown_type"


@pytest.mark.parametrize("payload", ["", "04000180", "0500058083", "0600018083"])
def test_malformed_information_reply_is_rejected(payload):
    with pytest.raises(ValueError):
        parse_device_info(bytes.fromhex(payload))


def test_version_reply_keeps_raw_version_components():
    assert parse_versions(bytes.fromhex("080005800e030701"))["mcu_version_bytes"] == [14, 3]
    with pytest.raises(ValueError):
        parse_versions(bytes.fromhex("080005800e03"))


def test_observed_hardware_information_replies():
    assert parse_device_info(bytes.fromhex("0b00018083212a00000100"))["reference_dimensions"] == [64, 16]
    result = parse_versions(bytes.fromhex("080005800e020704"))
    assert result["mcu_version_bytes"] == [14, 2]
    assert result["secondary_version_bytes"] == [7, 4]


def test_reference_full_frame_layout_and_fragmentation():
    pixels = bytes((255, 0, 0, 0, 255, 0)) + bytes(3072 - 6)
    packet = reference_rgb_frame(pixels, width=64, height=16)
    assert len(packet) == 3081
    assert packet[:9] == bytes.fromhex("090c000000000c0000")
    assert packet[9:15] == bytes((255, 0, 0, 0, 255, 0))



@pytest.mark.parametrize("width,height,length", [(51, 16, 2448), (16, 64, 3072), (64, 16, 3071), (64, 16, 3073)])
def test_raw_frame_rejects_unverified_dimensions_and_wrong_length(width, height, length):
    with pytest.raises(ValueError):
        reference_rgb_frame(bytes(length), width=width, height=height)


def test_png_framing_preserves_file_length_crc_and_slot_zero():
    from io import BytesIO
    import zlib
    from PIL import Image

    output = BytesIO()
    Image.new("RGB", (64, 16), (255, 0, 0)).save(output, format="PNG")
    png = output.getvalue()
    from pypixelcolor.commands.send_image import send_image_hex
    packet = send_image_hex(png.hex(), '.png').windows[0].data
    assert int.from_bytes(packet[:2], "little") == len(packet) == len(png) + 15
    assert packet[2:5] == b"\x02\x00\x00"
    assert int.from_bytes(packet[5:9], "little") == len(png)
    assert int.from_bytes(packet[9:13], "little") == zlib.crc32(png)
    assert packet[13:15] == b"\x00\x00"
    assert packet[15:] == png

