import asyncio

from PIL import Image
import pytest

from tools.experiments.grouped_snake_stream import (
    batch_probe_image, pack_pixel_commands, paint, pixel_groups, play, probe_image, snake_frames,
)


def apply_groups(before, after):
    image = before.copy()
    for colour, points in pixel_groups(before, after):
        assert 1 <= len(points) <= 123
        for point in points:
            image.putpixel(point, colour)
    return image


def test_full_baseline_paints_every_coordinate_and_splits_at_the_upstream_limit():
    target = probe_image()
    groups = pixel_groups(None, target)
    points = [point for _, batch in groups for point in batch]
    assert len(points) == len(set(points)) == 1024
    assert all(len(batch) <= 123 for _, batch in groups)
    image = Image.new('RGB', (64, 16), 'magenta')
    for colour, points in groups:
        for point in points:
            image.putpixel(point, colour)
    assert image.tobytes() == target.tobytes()


def test_snake_pilot_uses_normal_growth_without_collisions():
    initial, frames = snake_frames(1800)
    assert len(frames) == 1800
    assert all(board.phase == 'running' for _, board in frames)
    assert frames[-1][1].score > 0
    assert len(frames[-1][1].body) == frames[-1][1].score + 4
    assert initial.size == (64, 16)
    counts = [len(pixel_groups(before, after))
              for before, (after, _) in zip([initial] + [image for image, _ in frames[:-1]], frames)]
    assert max(counts) <= 4
    assert counts.count(3) > len(counts) * .95


def test_diff_from_last_completed_image_recovers_skipped_states_and_erases_old_pixels():
    previous, frames = snake_frames(300)
    for index in (0, 8, 19, 75, 161, 299):
        target = frames[index][0]
        assert apply_groups(previous, target).tobytes() == target.tobytes()
        previous = target
    assert pixel_groups(previous, previous) == []


def test_slow_schedule_applies_current_state_without_accumulating_stale_diffs():
    initial, frames = snake_frames(15)
    now = [0.0]
    actual = initial.copy()
    records = []
    async def sleep(seconds):
        now[0] += seconds
    async def send(before, after):
        nonlocal actual
        assert actual.tobytes() == before.tobytes()
        actual = apply_groups(actual, after)
        now[0] += .15
        return len(pixel_groups(before, after)), 0
    result = asyncio.run(play(send, initial, frames, lambda kind, **data: records.append((kind, data)),
                              fps=15, clock=lambda: now[0], sleep=sleep))
    completed = [data for kind, data in records if kind == 'frame_completed']
    assert result['completed'] == len(completed) < 15
    assert result['skipped'] + result['completed'] == 15
    assert actual.tobytes() == frames[completed[-1]['frame'] - 1][0].tobytes()


def test_upstream_grouped_builder_encodes_all_selected_coordinates():
    from pypixelcolor.commands import set_fun_mode
    if not hasattr(set_fun_mode, 'set_pixels'):
        pytest.skip('Requires the isolated PR #88 checkout.')
    for colour, points in pixel_groups(None, probe_image()):
        plan = set_fun_mode.set_pixels(points, bytes(colour).hex())
        packet = plan.windows[0].data
        assert packet[8:] == bytes(value for point in points for value in point)
        assert packet[5:8] == bytes(colour)
        assert not plan.ack_policy.ack_per_window and not plan.ack_policy.ack_final


def test_batching_preserves_complete_command_boundaries_and_byte_order():
    packets = [bytes((10, 0, 5, 1, 0, 255, 0, 0, x, 4)) for x in range(5)]
    assert pack_pixel_commands(packets, 24) == [b''.join(packets[:2]), b''.join(packets[2:4]), packets[4]]
    assert pack_pixel_commands([], 24) == []
    with pytest.raises(ValueError):
        pack_pixel_commands(packets, 9)
    with pytest.raises(ValueError):
        pack_pixel_commands([b'\x05\x00\x04\x01\x01'], 24)
    with pytest.raises(ValueError):
        pack_pixel_commands([packets[0][:-1]], 24)


@pytest.mark.parametrize(('budget', 'expected_writes'), [(500, 1), (80, 2), (40, 3)])
def test_batch_paint_preserves_all_colours_using_real_upstream_builders(budget, expected_writes):
    from types import SimpleNamespace
    from pypixelcolor.commands import set_fun_mode
    if not hasattr(set_fun_mode, 'set_pixels'):
        pytest.skip('Requires the isolated PR #88 checkout.')
    target = batch_probe_image()
    actual = Image.new('RGB', (64, 16), 'black')
    payloads = []
    async def send(plan, *, response, timeout):
        assert response and timeout == 4
        assert not plan.ack_policy.ack_per_window and not plan.ack_policy.ack_final
        payload = plan.windows[0].data
        assert len(payload) <= budget
        payloads.append(payload)
        offset = 0
        while offset < len(payload):
            length = int.from_bytes(payload[offset:offset + 2], 'little')
            command = payload[offset:offset + length]
            assert len(command) == length and command[2:4] == b'\x05\x01'
            for x, y in zip(command[8::2], command[9::2]):
                actual.putpixel((x, y), tuple(command[5:8]))
            offset += length
        assert offset == len(payload)
    link = SimpleNamespace(client=SimpleNamespace(chunk_size=budget), send=send, record=lambda *a, **kw: None)
    writes, points = asyncio.run(paint(link, None, actual.copy(), target, batch=True))
    assert writes == len(payloads) == expected_writes and points == 48
    assert actual.tobytes() == target.tobytes()
