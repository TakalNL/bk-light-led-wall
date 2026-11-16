import binascii
from io import BytesIO

import pytest
from PIL import Image

from tools.experiments.art_animation import inspect_gif, prepare_eyes_gif, prepare_rate_comparison
from pypixelcolor.commands.send_image import send_image_hex


def source_gif():
    first = Image.new('RGB', (64,16), 'orange')
    second = Image.new('RGB', (64,16), 'yellow')
    output = BytesIO()
    first.save(output, format='GIF', save_all=True, append_images=[second], duration=100, loop=0)
    return output.getvalue()


@pytest.mark.parametrize('fps,delay', [(10,100),(20,50),(25,40),(50,20)])
def test_eyes_preserves_native_size_frame_indices_and_exact_encoded_delay(fps, delay):
    gif = prepare_eyes_gif(source_gif(), frames=44, fps=fps)
    assert inspect_gif(gif) == {'frames':44, 'encoded_durations_ms':[delay],
                                'encoded_loop_ms':44*delay, 'encoded_loop_count':0}
    with Image.open(BytesIO(gif)) as image:
        for index in range(44):
            image.seek(index)
            frame = image.convert('RGB')
            assert frame.getpixel((0,0)) == ((255,165,0) if index%2==0 else (255,255,0))
        assert frame.getpixel((26,10)) == (255,255,255)  # hundreds digit 0


def test_multi_window_header_repeats_full_size_crc_and_marks_continuation():
    gif = b'GIF89a' + bytes(range(256)) * 100
    windows = [window.data for window in send_image_hex(gif.hex(), '.gif').windows]
    assert len(windows) == 3
    assert b''.join(window[15:] for window in windows) == gif
    for index, window in enumerate(windows):
        assert int.from_bytes(window[:2],'little') == len(window) <= 12*1024+15
        assert window[2:5] == bytes((3,0,0 if index==0 else 2))
        assert int.from_bytes(window[5:9],'little') == len(gif)
        assert int.from_bytes(window[9:13],'little') == binascii.crc32(gif)
        assert window[13:15] == b'\x02\x00'


def test_capacity_preserves_more_than_255_unique_numbered_frames():
    gif = prepare_eyes_gif(source_gif(), frames=528, fps=20)
    assert inspect_gif(gif)['frames'] == 528


def test_library_capacity_extension_preserves_four_digit_counter_and_frame_count():
    gif=prepare_eyes_gif(source_gif(),frames=1024,fps=20,capacity_test=True)
    metadata=inspect_gif(gif,capacity_test=True)
    assert metadata['frames']==1024 and metadata['encoded_loop_ms']==51200
    with Image.open(BytesIO(gif)) as image:
        image.seek(1023)
        # Top-left stroke of thousands digit 1: 010 (x25..27).
        assert image.convert('RGB').getpixel((26,10))==(255,255,255)
    with pytest.raises(ValueError):
        inspect_gif(gif)


def test_rate_comparison_preserves_sections_and_variable_durations():
    gif = prepare_rate_comparison(source_gif())
    assert inspect_gif(gif) == {'frames':176,'encoded_durations_ms':[20,40,50,100],
                                'encoded_loop_ms':9240,'encoded_loop_count':0}
    with Image.open(BytesIO(gif)) as image:
        durations = []
        for index in range(image.n_frames):
            image.seek(index)
            durations.append(image.info['duration'])
    assert durations == [100]*44 + [50]*44 + [40]*44 + [20]*44


@pytest.mark.parametrize('data', [b'',b'GIF89a',b'GIF89a'+bytes(256*1024)])
def test_window_upload_rejects_invalid_or_unbounded_input(data):
    with pytest.raises((ValueError, OSError)):
        inspect_gif(data)
