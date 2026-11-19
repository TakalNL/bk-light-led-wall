import asyncio
from contextlib import asynccontextmanager
from io import BytesIO
from queue import Queue
import threading
from types import SimpleNamespace

from PIL import Image
import pytest

from games.common.panel import LatestBoard
from games.common.wall import WallWorker, stream_canvas
from games.snake.game import Snake, render_board
from led_matrix_hacker.wall import (
    CanvasFrame, Layout, Tile, fit_image, load_layout, load_media, save_layout,
)


def stacked():
    return Layout((Tile('A'), Tile('B', y=16)))


def test_stacked_canvas_splits_at_the_seam_without_scaling():
    image = Image.new('RGB', (64, 32), 'red')
    image.paste('blue', (0, 16, 64, 32))
    image.putpixel((5, 15), (1, 2, 3))
    image.putpixel((5, 16), (4, 5, 6))
    top, bottom = stacked().split(image)
    assert top.size == bottom.size == (64, 16)
    assert top.getpixel((5, 15)) == (1, 2, 3)
    assert bottom.getpixel((5, 0)) == (4, 5, 6)
    assert top.getpixel((0, 0)) == (255, 0, 0)
    assert bottom.getpixel((0, 0)) == (0, 0, 255)


@pytest.mark.parametrize('rotation', [0, 90, 180, 270])
def test_rotation_upload_undoes_clockwise_mounting(rotation):
    tile = Tile('A', rotation=rotation)
    layout = Layout((tile,))
    image = Image.new('RGB', layout.size)
    for x in range(image.width):
        for y in range(image.height):
            image.putpixel((x, y), (x, y, 73))
    upload, = layout.split(image)
    assert upload.size == (64, 16)
    assert upload.rotate(-rotation, expand=True).tobytes() == image.tobytes()


@pytest.mark.parametrize('tiles', [(), (Tile('A'), Tile('a', y=16)),
                                  (Tile('A'), Tile('B', y=15)), (Tile('A', x=500),)])
def test_invalid_layouts_rejected_before_connecting(tiles):
    with pytest.raises(ValueError):
        Layout(tiles)


@pytest.mark.parametrize('kwargs', [dict(device=''), dict(device='A', x=-1), dict(device='A', rotation=45),
                                   dict(device='A', x=True), dict(device='A', y='16')])
def test_invalid_tile_fields(kwargs):
    with pytest.raises(ValueError):
        Tile(**kwargs)


def test_offsets_gaps_and_canvas_size_validation():
    layout = Layout((Tile('A', x=4, y=5), Tile('B', x=70, y=20)))
    assert layout.size == (134, 36)
    assert all(t.size == (64, 16) for t in layout.tiles)
    with pytest.raises(ValueError, match='Expected a canvas'):
        layout.split(Image.new('RGB', (64, 32)))


@pytest.mark.parametrize('gap', [0, 2, 3, 32])
@pytest.mark.parametrize('vertical', [True, False])
def test_variable_compensation_skips_exact_rows_or_columns(gap, vertical):
    layout = stacked().arranged(vertical, gap)
    assert layout.linear_spacing == (vertical, gap)
    assert layout.size == ((64, 32+gap) if vertical else (128+gap, 16))
    image = Image.new('RGB', layout.size)
    for y in range(image.height):
        for x in range(image.width):
            image.putpixel((x, y), (x % 256, y, 73))
    first, second = layout.split(image)
    assert first.getpixel((0, 0)) == (0, 0, 73)
    assert second.getpixel((0, 0)) == ((0, 16+gap, 73) if vertical else (64+gap, 0, 73))
    assert first.size == second.size == (64, 16)
    preview = layout.preview(image)
    for offset in range(gap):
        assert preview.getpixel((0, 16+offset) if vertical else (64+offset, 0)) == (0, 0, 0)
    assert preview.getpixel(layout.tiles[1].box[:2]) == second.getpixel((0, 0))
    assert layout.with_gap(0) == stacked().arranged(vertical)


def test_compensation_preserves_mounting_anchor_and_saved_value(tmp_path):
    layout = Layout((Tile('A', 4, 5, 90), Tile('B', 4, 69, 180), Tile('C', 4, 85)))
    adjusted = layout.with_gap(3)
    assert [tile.y for tile in adjusted.tiles] == [5, 72, 91]
    assert [tile.x for tile in adjusted.tiles] == [4]*3
    assert [tile.rotation for tile in adjusted.tiles] == [90, 180, 0]
    path = tmp_path/'compensated.json'
    save_layout(path, adjusted)
    restored = load_layout(path)
    assert restored.linear_spacing == (True, 3)
    assert restored.with_gap(0) == layout


@pytest.mark.parametrize('gap', [-1, 33, 2.5, True])
def test_invalid_compensation_rejected(gap):
    with pytest.raises(ValueError, match='whole number'):
        stacked().with_gap(gap)


def test_custom_layout_cannot_be_rearranged_by_gap_control():
    layout = Layout((Tile('A'), Tile('B', 8, 19)))
    assert layout.linear_spacing is None
    with pytest.raises(ValueError, match='custom layouts'):
        layout.with_gap(3)


def test_layout_settings_roundtrip_and_corruption(tmp_path):
    path = tmp_path/'nested'/'wall.json'
    save_layout(path, stacked())
    assert load_layout(path) == stacked()
    assert not path.with_suffix('.json.tmp').exists()
    path.write_text('{"version": 1, "panels": [{"device": "A"}]}')
    with pytest.raises(ValueError):
        load_layout(path)


def test_frame_freezes_mutable_pillow_image():
    image = Image.new('RGB', (64, 32), 'red')
    frame = CanvasFrame.from_image(image)
    image.paste('blue', (0, 0, 64, 32))
    assert frame.image().getpixel((0, 0)) == (255, 0, 0)


def test_fit_modes_and_transparency():
    image = Image.new('RGBA', (16, 16), (255, 0, 0, 0))
    assert fit_image(image, (64, 32)).getpixel((32, 16)) == (0, 0, 0)
    image = Image.new('RGB', (16, 16), 'red')
    assert fit_image(image, (64, 32)).getpixel((0, 0)) == (0, 0, 0)
    for mode in ('Fill', 'Stretch'):
        assert fit_image(image, (64, 32), mode).getpixel((0, 0)) == (255, 0, 0)


def test_gif_frames_keep_timing_and_fill_whole_canvas(tmp_path):
    path = tmp_path/'animation.gif'
    first = Image.new('RGB', (8, 8), 'red')
    first.save(path, save_all=True, append_images=[Image.new('RGB', (8, 8), 'blue')],
               duration=[100, 250], loop=0)
    frames, deadlines = load_media(path, (64, 32), 'Fill')
    assert deadlines == pytest.approx([.1, .35])
    assert [f.size for f in frames] == [(64, 32)]*2
    assert frames[1].getpixel((0, 0)) == (0, 0, 255)


def test_snake_crosses_horizontal_panel_seam_on_full_canvas():
    snake = Snake(width=32, height=16)
    snake.body = [(12, 7), (12, 6), (12, 5), (12, 4)]
    snake.direction, snake.food = 'down', (0, 0)
    snake.toggle_pause()
    snake.tick()
    assert snake.body[0] == (12, 8) and snake.phase == 'running'
    image = render_board(snake.snapshot())
    assert image.size == (64, 32)
    top, bottom = stacked().split(image)
    assert top.getpixel((24, 14)) == (0, 192, 96)
    assert bottom.getpixel((24, 0)) == (160, 255, 208)


def test_wall_barrier_and_latest_frame_when_one_panel_is_slow():
    async def run():
        mailbox, stop = LatestBoard(), threading.Event()
        mailbox.publish(CanvasFrame.from_image(Image.new('RGB', (64, 32), 'red')))
        entered, release = asyncio.Event(), asyncio.Event()
        packets, records = [[], []], []
        class Link:
            client = SimpleNamespace(is_connected=True)
            def __init__(self, index):
                self.index = index
            async def send(self, plan, **kwargs):
                assert kwargs == dict(response=True, timeout=4)
                packet = plan.windows[0].data
                assert packet[14] == 0
                packets[self.index].append(packet)
                if self.index == 1 and len(packets[1]) == 1:
                    entered.set()
                    await release.wait()
                if len(packets[1]) == 2:
                    stop.set()
                return None, 0, [bytes.fromhex('0500020003')]
        task = asyncio.create_task(stream_canvas([Link(0), Link(1)], stacked(), mailbox, stop,
            lambda *a, **kw: None, lambda kind, **kw: records.append(kw),
            device_infos=[SimpleNamespace(width=64, height=16)]*2))
        await asyncio.wait_for(entered.wait(), 1)
        mailbox.publish(CanvasFrame.from_image(Image.new('RGB', (64, 32), 'green')))
        latest = Image.new('RGB', (64, 32), 'blue')
        mailbox.publish(CanvasFrame.from_image(latest))
        await asyncio.sleep(.12)
        assert [len(p) for p in packets] == [1, 1]
        release.set()
        await asyncio.wait_for(task, 1)
        assert [len(p) for p in packets] == [2, 2]
        for panel in packets:
            with Image.open(BytesIO(panel[-1][15:])) as image:
                assert image.size == (64, 16) and image.getpixel((0, 0)) == (0, 0, 255)
        assert records[-1]['superseded'] == 1
        assert [r['version'] for r in records] == [1, 3]
    asyncio.run(run())


def test_bad_reply_cancels_other_panel_without_retry():
    async def run():
        mailbox, cancelled = LatestBoard(), []
        mailbox.publish(CanvasFrame.from_image(Image.new('RGB', (64, 32))))
        entered = asyncio.Event()
        class Link:
            client = SimpleNamespace(is_connected=True)
            def __init__(self, bad):
                self.bad, self.calls = bad, 0
            async def send(self, *args, **kwargs):
                self.calls += 1
                if self.bad:
                    await entered.wait()
                    return None, 0, [b'wrong']
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.append(True)
        links = [Link(True), Link(False)]
        with pytest.raises(ConnectionError, match='Panel 1: Missing expected'):
            await stream_canvas(links, stacked(), mailbox, threading.Event(), lambda *a, **kw: None,
                                lambda *a, **kw: None)
        assert cancelled == [True] and [link.calls for link in links] == [1, 1]
    asyncio.run(run())


def test_idle_wall_disconnect_is_detected():
    async def run():
        links = [SimpleNamespace(client=SimpleNamespace(is_connected=False))]*2
        with pytest.raises(ConnectionError, match='Panel 1 disconnected'):
            await stream_canvas(links, stacked(), LatestBoard(), threading.Event(), lambda *a, **kw: None,
                                lambda *a, **kw: None)
    asyncio.run(run())


def test_live_gap_change_keeps_image_and_mapping_atomic_behind_frame_barrier():
    async def run():
        initial, changed = stacked(), stacked().with_gap(3)
        mailbox, stop = LatestBoard(), threading.Event()
        mailbox.publish(CanvasFrame.from_image(Image.new('RGB', initial.size, 'red'), layout=initial))
        entered, release = asyncio.Event(), asyncio.Event()
        packets, records = [[], []], []
        class Link:
            client = SimpleNamespace(is_connected=True)
            def __init__(self, index):
                self.index = index
            async def send(self, plan, **kwargs):
                packets[self.index].append(plan.windows[0].data)
                if self.index == 1 and len(packets[1]) == 1:
                    entered.set()
                    await release.wait()
                if self.index == 1 and len(packets[1]) == 2:
                    stop.set()
                return None, 0, [bytes.fromhex('0500020003')]
        task = asyncio.create_task(stream_canvas([Link(0), Link(1)], initial, mailbox, stop,
            lambda *a, **kw: None, lambda kind, **kw: records.append((kind, kw)),
            device_infos=[SimpleNamespace(width=64, height=16)]*2))
        await asyncio.wait_for(entered.wait(), 1)
        image = Image.new('RGB', changed.size, 'blue')
        image.paste('green', (0, 16, 64, 19))  # These virtual rows must never be sent.
        image.putpixel((0, 19), (12, 34, 56))
        mailbox.publish(CanvasFrame.from_image(image, layout=changed))
        assert [len(p) for p in packets] == [1, 1]
        release.set()
        await asyncio.wait_for(task, 1)
        with Image.open(BytesIO(packets[1][0][15:])) as frame:
            assert frame.getpixel((0, 0)) == (255, 0, 0)
        with Image.open(BytesIO(packets[1][1][15:])) as frame:
            assert frame.size == (64, 16) and frame.getpixel((0, 0)) == (12, 34, 56)
        changes = [data for kind, data in records if kind == 'wall_layout_changed']
        assert changes == [dict(dimensions=[64, 35], panel_boxes=[[0, 0, 64, 16], [0, 19, 64, 35]])]
    asyncio.run(run())


def test_live_mapping_rejects_new_devices_before_any_upload():
    async def run():
        mailbox = LatestBoard()
        layout = Layout((Tile('C'), Tile('B', y=19)))
        mailbox.publish(CanvasFrame.from_image(Image.new('RGB', layout.size), layout=layout))
        links = [SimpleNamespace(client=SimpleNamespace(is_connected=True))]*2
        with pytest.raises(ValueError, match='identities/order changed'):
            await stream_canvas(links, stacked(), mailbox, threading.Event(), lambda *a, **kw: None,
                                lambda *a, **kw: None)
    asyncio.run(run())


@pytest.mark.parametrize('failure', ['initialize', 'connect', 'cancel', 'duplicate'])
def test_partial_setup_and_cancel_close_every_open_link(monkeypatch, tmp_path, failure):
    from led_matrix_hacker import discovery, library_link
    opened, closed = [], []
    worker = WallWorker(stacked(), LatestBoard(), Queue(), tmp_path/'unused')
    async def resolve(identifier, **kwargs):
        return SimpleNamespace(address='same' if failure == 'duplicate' else identifier)
    @asynccontextmanager
    async def connect(device, record, **kwargs):
        if device == 'B' and failure == 'connect':
            raise OSError('connection failed')
        opened.append(device)
        async def initialize(**kwargs):
            if device == 'B' and failure == 'initialize':
                raise ValueError('unsupported panel')
            if device == 'B' and failure == 'cancel':
                worker.close()
                await asyncio.Event().wait()
        try:
            yield SimpleNamespace(initialize=initialize)
        finally:
            closed.append(device)
    monkeypatch.setattr(discovery, 'resolve_device', resolve)
    monkeypatch.setattr(library_link, 'library_connection', connect)
    async def run():
        if failure == 'cancel':
            await asyncio.wait_for(worker._run(lambda *a, **kw: None), 1)
        else:
            with pytest.raises((ValueError, OSError)):
                await worker._run(lambda *a, **kw: None)
    asyncio.run(run())
    assert closed == list(reversed(opened))
    if failure == 'duplicate':
        assert opened == []


def test_worker_cancels_both_inflight_uploads_and_closes_links(monkeypatch, tmp_path):
    from led_matrix_hacker import discovery, library_link
    entered, cancelled, closed = [], [], []
    mailbox = LatestBoard()
    mailbox.publish(CanvasFrame.from_image(Image.new('RGB', (64, 32))))
    worker = WallWorker(stacked(), mailbox, Queue(), tmp_path/'unused')
    async def resolve(identifier, **kwargs):
        return SimpleNamespace(address=identifier)
    @asynccontextmanager
    async def connect(device, record, **kwargs):
        async def initialize(**kwargs):
            return SimpleNamespace(width=64, height=16)
        async def send(*args, **kwargs):
            entered.append(device)
            if len(entered) == 2:
                worker.close()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(device)
        try:
            yield SimpleNamespace(initialize=initialize, send=send,
                                  client=SimpleNamespace(is_connected=True))
        finally:
            closed.append(device)
    monkeypatch.setattr(discovery, 'resolve_device', resolve)
    monkeypatch.setattr(library_link, 'library_connection', connect)
    asyncio.run(asyncio.wait_for(worker._run(lambda *a, **kw: None), 1))
    assert set(cancelled) == {'A', 'B'} and closed == ['B', 'A']
