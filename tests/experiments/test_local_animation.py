import binascii
from io import BytesIO

from PIL import Image

from tools.experiments.animation import build_sprite_frames
from tools.experiments.local_animation import build_numbered_gif
from pypixelcolor.commands.send_image import send_image_hex


def test_gif_round_trip_preserves_every_numbered_frame_and_timing():
    gif = build_numbered_gif()
    image = Image.open(BytesIO(gif))
    assert len(gif) <= 12 * 1024
    assert image.size == (64, 16) and image.n_frames == 20
    assert image.info['loop'] == 0
    sources = build_sprite_frames(fps=2, frame_counter=True)
    for index, source in enumerate(sources):
        image.seek(index)
        assert image.info['duration'] == 200
        assert image.disposal_method == 2
        expected = Image.open(BytesIO(source.png)).convert('RGB')
        assert image.convert('RGB').tobytes() == expected.tobytes()


def test_gif_reference_packet_uses_correct_opcode_marker_crc_and_slot_zero():
    gif = build_numbered_gif()
    packet = send_image_hex(gif.hex(), '.gif').windows[0].data
    assert int.from_bytes(packet[:2], 'little') == len(packet) == len(gif) + 15
    assert packet[2:5] == bytes.fromhex('030000')
    assert int.from_bytes(packet[5:9], 'little') == len(gif)
    assert int.from_bytes(packet[9:13], 'little') == binascii.crc32(gif)
    assert packet[13:15] == bytes.fromhex('0200')
    assert packet[15:] == gif

