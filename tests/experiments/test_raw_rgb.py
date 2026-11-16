import pytest

from tools.experiments.raw_rgb import reference_rgb_frame


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
