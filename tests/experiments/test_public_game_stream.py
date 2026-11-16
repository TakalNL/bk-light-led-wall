import asyncio
from io import BytesIO
import hashlib
from types import SimpleNamespace

from PIL import Image
import pytest

from tools.experiments.public_game_stream import FPS, build_frames, stream


def test_normal_pilot_frames_cover_campaign_and_fit_existing_game_transport():
    frames = build_frames(120)
    assert len(frames) == 120 * FPS
    assert {'running', 'respawn', 'won'} <= {board.phase for _, board in frames}
    assert {'drone', 'weaver', 'gunner'} <= {enemy[0] for _, board in frames for enemy in board.enemies}
    assert any(board.boss for _, board in frames)
    assert any(board.phase == 'won' and board.twin and board.rapid and board.lives == 2 for _, board in frames)
    assert len({png for png, _ in frames}) > 1000
    for png, _ in frames:
        assert len(png) + 15 <= 500
        with Image.open(BytesIO(png)) as image:
            assert image.mode == 'RGB' and image.size == (64, 16)


def test_15fps_sampling_keeps_game_speed_and_preserves_original_10fps_fixture():
    original = build_frames(120)
    faster = build_frames(120, fps=15)
    assert len(faster) == 1800
    assert faster[-1] == original[-1]
    assert hashlib.sha256(b''.join(png for png, _ in original)).hexdigest() == (
        'a660c92240c61aa890cc2234fa0f01c415253ef7e368dfbad5708468cec97e44'
    )


def run_stream(latency, *, reply='0500020003', fps=FPS):
    now = [0.0]
    observed = []
    acks = SimpleNamespace(replies=[])
    frames = build_frames(1, fps=fps)
    records = []
    async def sleep(seconds):
        now[0] += seconds
    async def send(png):
        observed.append(next(index for index, (data, _) in enumerate(frames) if data == png))
        now[0] += latency
        acks.replies.append(reply)
    result = asyncio.run(stream(send, frames, lambda kind, **data: records.append((kind, data)),
                                acks, fps=fps, clock=lambda: now[0], sleep=sleep))
    return observed, result


@pytest.mark.parametrize('fps', [10, 15, 20])
def test_fast_stream_sends_all_frames_at_requested_rate(fps):
    observed, result = run_stream(.02, fps=fps)
    assert observed == list(range(fps))
    assert result['completed'] == fps and result['skipped'] == 0
    assert result['seconds'] == 1 and result['achieved_fps'] == fps


def test_slow_stream_selects_current_frame_without_queueing_old_states():
    observed, result = run_stream(.24)
    assert observed == [0, 2, 4, 7, 9]
    assert result['completed'] == 5 and result['skipped'] == 5
    assert not result['all_scheduled_frames_completed']


def test_nonfinal_image_reply_stops_the_stream():
    with pytest.raises(ValueError, match='strict PNG completion'):
        run_stream(.06, reply='0500020001')
