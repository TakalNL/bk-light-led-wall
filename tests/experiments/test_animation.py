import asyncio
from io import BytesIO

import pytest
from PIL import Image

from tools.experiments.animation import EXPECTED_REPLY, build_sprite_frames, stream_frames


class Clock:
    now = 0.0

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds


def test_sprite_frames_fit_verified_grid_and_png_crc_frames():
    import binascii

    frames = build_sprite_frames()
    assert len(frames) == 20
    assert len({frame.png for frame in frames}) == 20
    assert frames[0].x == 1 and frames[-1].x == 54
    for frame in frames:
        image = Image.open(BytesIO(frame.png))
        assert image.size == (64, 16) and image.mode == "RGB"
        yellow = [(x, y) for y in range(16) for x in range(64)
                  if image.getpixel((x, y)) == (255, 192, 0)]
        assert len(yellow) == 34
        assert min(x for x, _ in yellow) == frame.x
        assert max(x for x, _ in yellow) == frame.x + 7
        assert frame.plan.windows[0].data[15:] == frame.png
        assert int.from_bytes(frame.plan.windows[0].data[9:13], "little") == binascii.crc32(frame.png)


def run_stream(latency, reply=EXPECTED_REPLY, *, fps=2, duration_seconds=10):
    clock, starts, records = Clock(), [], []

    class Link:
        async def send(self, plan, **options):
            assert options['response'] is True
            starts.append(clock())
            clock.now += latency
            return None, latency, [reply]

    async def run():
        await stream_frames(Link(), build_sprite_frames(fps=fps, duration_seconds=duration_seconds),
                            lambda kind, **fields: records.append((kind, fields)),
                            fps=fps, duration_seconds=duration_seconds, clock=clock, sleep=clock.sleep)

    return run, starts, records, clock


def test_playback_uses_absolute_half_second_deadlines_and_holds_final_frame():
    run, starts, records, clock = run_stream(0.14)
    asyncio.run(run())
    assert starts == [index * 0.5 for index in range(20)]
    assert clock() == 10
    assert records[-1][0] == "playback_completed"


def test_slow_link_stops_instead_of_bursting_to_catch_up():
    run, starts, records, _ = run_stream(0.8)
    with pytest.raises(TimeoutError, match="fell behind"):
        asyncio.run(run())
    assert starts == [0]
    assert not any(kind == "playback_completed" for kind, _ in records)


def test_unexpected_image_reply_stops_before_next_frame():
    run, starts, _, _ = run_stream(0.14, bytes.fromhex("0500020001"))
    with pytest.raises(ValueError, match="Unexpected PNG reply"):
        asyncio.run(run())
    assert starts == [0]


def test_five_fps_uses_fifty_frames_over_ten_seconds():
    run, starts, records, clock = run_stream(0.08, fps=5)
    asyncio.run(run())
    assert starts == pytest.approx([index / 5 for index in range(50)])
    assert clock() == 10
    assert records[-1][1]['frames'] == 50


def test_five_fps_stops_when_more_than_one_hundred_ms_late():
    run, starts, _, _ = run_stream(0.31, fps=5)
    with pytest.raises(TimeoutError, match="fell behind"):
        asyncio.run(run())
    assert starts == [0]


def test_fifty_counters_are_visible_below_sprite_and_match_frame_numbers():
    # Decode the rendered 3x5 digit cells against independently specified glyphs.
    glyphs = ["111101101101111", "010110010010111", "111001111100111",
              "111001111001111", "101101111001001", "111100111001111",
              "111100111101111", "111001010010010", "111101111101111",
              "111101111001111"]
    frames = build_sprite_frames(fps=5, frame_counter=True)
    assert len({frame.png for frame in frames}) == 50
    for index, frame in enumerate(frames, start=1):
        image = Image.open(BytesIO(frame.png))
        assert frame.counter == f"{index:02d}/50"
        for cell, digit in ((0, index // 10), (1, index % 10), (3, 5), (4, 0)):
            actual = ''.join('1' if image.getpixel((2 + 4 * cell + dx, 10 + dy)) == (255, 255, 255)
                             else '0' for dy in range(5) for dx in range(3))
            assert actual == glyphs[digit]
        yellow = [(x, y) for y in range(16) for x in range(64)
                  if image.getpixel((x, y)) == (255, 192, 0)]
        assert len(yellow) == 34
        assert max(y for _, y in yellow) == 8


@pytest.mark.parametrize('fps', [0, -1, 10, True, 2.0])
def test_unsupported_frame_rates_rejected_before_preparation(fps):
    with pytest.raises(ValueError, match="2 or 5 fps"):
        build_sprite_frames(fps=fps)


def test_minute_stream_sends_three_hundred_frames_at_five_fps():
    run, starts, records, clock = run_stream(0.1, fps=5, duration_seconds=60)
    asyncio.run(run())
    assert starts == pytest.approx([index / 5 for index in range(300)])
    assert clock() == 60
    assert records[-1][1]['frames'] == 300
    assert records[0][1]['planned_duration_seconds'] == 60


def test_minute_counter_crosses_hundreds_without_overlap_and_sprite_loops():
    frames = build_sprite_frames(fps=5, duration_seconds=60, frame_counter=True)
    assert len({frame.png for frame in frames}) == 300
    assert [frame.counter for frame in frames] == [f'{index:03d}/300' for index in range(1,301)]
    assert [frames[index].x for index in (0,49,50,99,100,299)] == [1,54,1,54,1,54]
    # Hundreds column transitions: 099 -> 100 -> 199 -> 200 -> 299 -> 300.
    expected_hundreds = {
        99: '111101101101111', 100: '010110010010111',
        199: '010110010010111', 200: '111001111100111',
        299: '111001111100111', 300: '111001111001111',
    }
    for index, expected in expected_hundreds.items():
        image = Image.open(BytesIO(frames[index-1].png))
        actual = ''.join('1' if image.getpixel((2+dx, 10+dy)) == (255,255,255)
                         else '0' for dy in range(5) for dx in range(3))
        assert actual == expected
    final = Image.open(BytesIO(frames[-1].png))
    # Blank gap between the seven-character counter and final END at x=34.
    assert all(final.getpixel((x,y)) == (0,0,0) for x in range(29,34) for y in range(10,15))
    assert final.getpixel((34,10)) == (255,255,255)


@pytest.mark.parametrize('seconds', [0, -1, 11, 61, True, 60.0])
def test_unsupported_durations_rejected_before_preparation(seconds):
    with pytest.raises(ValueError, match="10 or 60 second"):
        build_sprite_frames(duration_seconds=seconds)
