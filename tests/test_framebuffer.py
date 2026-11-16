import pytest
from PIL import Image

from led_matrix_hacker.framebuffer import diagnostic_image, to_rgb_bytes


def test_rgb_order_is_row_major_without_rotation_or_mirroring():
    image = Image.new("RGB", (2, 2))
    image.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)])
    assert to_rgb_bytes(image, width=2, height=2) == bytes.fromhex("ff0000 00ff00 0000ff ffff00")


def test_transparency_is_composited_on_black():
    image = Image.new("RGBA", (2, 1))
    image.putdata([(255, 0, 0, 0), (0, 255, 0, 128)])
    assert to_rgb_bytes(image, width=2, height=1) == bytes((0, 0, 0, 0, 128, 0))


def test_size_mismatch_is_rejected_instead_of_silently_cropping():
    with pytest.raises(ValueError, match="dimensions"):
        to_rgb_bytes(Image.new("RGB", (2, 1)), width=1, height=2)


def test_diagnostic_pattern_preserves_edge_orientation_and_color_markers():
    image = diagnostic_image()
    assert image.size == (64, 16)
    assert image.getpixel((0, 0)) == (255, 0, 0)
    assert image.getpixel((63, 0)) == (0, 255, 0)
    assert image.getpixel((0, 15)) == (0, 0, 255)
    assert image.getpixel((63, 15)) == (255, 255, 0)
    assert image.getpixel((32, 0)) == (96, 96, 96)
    assert image.getpixel((47, 8)) == (255, 0, 0)
    assert image.getpixel((51, 8)) == (0, 255, 0)
    assert image.getpixel((55, 8)) == (0, 0, 255)
