"""Real GIF encoding/decoding and transport barriers, without Bluetooth hardware."""
import asyncio
from io import BytesIO
import threading
from types import SimpleNamespace
from zlib import crc32

from PIL import Image
import pytest

from games.common.panel import LatestBoard
from games.common.wall import stream_canvas
from games.wall.app import WallApp
from led_matrix_hacker.native_animation import NativePlayback, animation_plan, prepare_animation
from led_matrix_hacker.wall import CanvasFrame, Layout, Tile, fit_image, load_media


def decode(data):
    frames, durations = [], []
    with Image.open(BytesIO(data)) as gif:
        assert gif.size == (64, 16) and gif.info['loop'] == 0
        for index in range(gif.n_frames):
            gif.seek(index)
            frames.append(gif.convert('RGB'))
            durations.append(gif.info['duration'])
    return frames, durations


def fixture():
    layout = Layout((Tile('A'), Tile('B', y=19)))
    frames = [Image.new('RGB', layout.size, color) for color in ('red', 'blue', 'lime')]
    for frame in frames:
        frame.paste('yellow', (0, 16, 64, 19))
    return layout, frames, [.04, .11, .23]


@pytest.mark.parametrize('rotation', [0, 90, 180, 270])
def test_native_crops_bezels_and_undoes_rotation_on_common_timeline(rotation):
    layout = Layout((Tile('A', rotation=rotation), Tile('B', y=67, rotation=rotation)))
    frames = []
    for color in ('red', 'blue', 'lime'):
        image = Image.new('RGB', layout.size, 'yellow')
        for tile in layout.tiles:
            image.paste(color, tile.box)
            image.putpixel(tile.box[:2], (255, 255, 255))
        frames.append(image)
    prepared = prepare_animation(frames, [.04, .11, .23], layout)
    assert prepared.duration_ms == 230 and prepared.frame_count == 3
    for index, data in enumerate(prepared.gifs):
        decoded, durations = decode(data)
        assert durations == [40, 70, 120]
        assert [frame.tobytes() for frame in decoded] == [layout.split(f)[index].tobytes() for f in frames]


def test_static_half_and_changing_half_keep_identical_loop_lengths():
    layout, frames, deadlines = fixture()
    for frame in frames:
        frame.paste('red', layout.tiles[0].box)
    animation = prepare_animation(frames, deadlines, layout)
    halves = [decode(data) for data in animation.gifs]
    assert [sum(durations) for _, durations in halves] == [230, 230]
    assert len(halves[1][0]) == 3
    assert all(frame.getpixel((0, 0)) != (255, 255, 0) for half, _ in halves for frame in half)


def test_fast_gif_is_sampled_without_slowing_the_loop():
    layout = Layout((Tile('A'),))
    frames = [Image.new('RGB', layout.size, (index*20, 0, 0)) for index in range(10)]
    animation = prepare_animation(frames, [(index+1)*.02 for index in range(10)], layout)
    decoded, durations = decode(animation.gifs[0])
    assert durations == [30]*5+[50]
    assert sum(durations) == 200
    assert [frame.getpixel((0, 0))[0] for frame in decoded] == [0, 20, 60, 80, 120, 140]


def test_gif_disposal_and_transparency_are_resolved_before_panel_encoding(tmp_path):
    path = tmp_path/'transparent.gif'
    first = Image.new('P', (8, 8), 1)
    second = Image.new('P', (8, 8), 0)
    palette = [0, 0, 0, 255, 0, 0, 0, 0, 255]+[0]*759
    first.putpalette(palette)
    second.putpalette(palette)
    second.paste(2, (0, 0, 4, 8))
    first.save(path, save_all=True, append_images=[second], duration=[80, 120], disposal=2,
               loop=0, transparency=0, optimize=False)
    layout = Layout((Tile('A'), Tile('B', x=67)))
    frames, deadlines = load_media(path, layout.size, 'Fill')
    prepared = prepare_animation(frames, deadlines, layout)
    for index, data in enumerate(prepared.gifs):
        decoded, durations = decode(data)
        assert durations == [80, 120]
        assert [frame.tobytes() for frame in decoded] == [layout.split(f)[index].tobytes() for f in frames]


@pytest.mark.parametrize('mode', ['Fit', 'Fill', 'Stretch'])
def test_pillow_filters_large_sources_instead_of_aliasing(mode):
    source = Image.new('RGB', (256, 128))
    source.putdata([(255, 255, 255) if (x+y)%2 else (0, 0, 0) for y in range(128) for x in range(256)])
    fitted = fit_image(source, (64, 32), mode)
    assert all(120 <= channel <= 135 for channel in fitted.getpixel((32, 16)))


def test_mult_window_preview_headers_and_restart_match_exact_gif_crc():
    import random
    generator = random.Random(23)
    layout = Layout((Tile('A'),))
    frames = [Image.frombytes('RGB', layout.size, generator.randbytes(64*16*3)) for _ in range(32)]
    animation = prepare_animation(frames, [(i+1)*.04 for i in range(32)], layout)
    data = animation.gifs[0]
    plan, restart = animation_plan(data)
    assert len(plan.windows) > 1
    reconstructed = b''.join(window.data[15:] for window in plan.windows)
    assert reconstructed == data
    for index, window in enumerate(plan.windows):
        wire = window.data
        assert int.from_bytes(wire[:2], 'little') == len(wire)
        assert wire[2:5] == bytes((3, 0, 0 if index == 0 else 2))
        assert int.from_bytes(wire[5:9], 'little') == len(data)
        assert int.from_bytes(wire[9:13], 'little') == crc32(data)
        assert wire[13:15] == b'\x02\x65'
    assert restart == b'\x0f\x00'+plan.windows[0].data[2:15]


@pytest.mark.parametrize('change', ['pause', 'mode', None])
def test_upload_barrier_restart_and_no_frame_streaming(change):
    async def run():
        layout, frames, deadlines = fixture()
        request = NativePlayback(prepare_animation(frames, deadlines, layout), 7)
        mailbox, stop = LatestBoard(), threading.Event()
        mailbox.publish(request)
        release, entered = asyncio.Event(), asyncio.Event()
        calls, events = [], []

        class Link:
            client = SimpleNamespace(is_connected=True)

            def __init__(self, index):
                self.index = index

            async def send(self, plan, **kwargs):
                wire = plan.windows[0].data
                kind = 'restart' if len(wire) == 15 else 'gif' if wire[2] == 3 else 'png'
                calls.append((self.index, kind))
                if self.index == 1 and kind == 'gif':
                    entered.set()
                    await release.wait()
                if kind == 'png' and self.index == 1:
                    stop.set()
                return None, 0, [bytes.fromhex('0500030003' if wire[2] == 3 else '0500020003')]

        def emit(kind, **fields):
            events.append((kind, fields))

        task = asyncio.create_task(stream_canvas([Link(0), Link(1)], layout, mailbox, stop, emit,
                                                 lambda *args, **kwargs: None))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            assert calls == [(0, 'gif'), (1, 'gif')]
            if change:
                mailbox.publish(CanvasFrame.from_image(frames[0] if change == 'pause' else Image.new('RGB', layout.size), layout=layout))
            release.set()
            for _ in range(100):
                if stop.is_set() or any(kind == 'native_playing' for kind, _ in events):
                    break
                await asyncio.sleep(.005)
            if change:
                assert not any(kind == 'restart' for _, kind in calls)
            else:
                assert calls == [(0, 'gif'), (1, 'gif'), (0, 'restart'), (1, 'restart')]
                await asyncio.sleep(.15)
                assert len(calls) == 4  # Native loops produce no ongoing BLE writes.
                assert events[-1][1]['generation'] == 7
                stop.set()
            await asyncio.wait_for(task, 1)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(run())


def test_desktop_open_refit_pause_resume_and_gap_change(tmp_path):
    layout, frames, deadlines = fixture()
    source = tmp_path/'wall.gif'
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=[40, 70, 120], loop=0)
    app = WallApp.__new__(WallApp)
    app.layout, app.mailbox = layout, LatestBoard()
    app.media_path, app.media_generation = source, 0
    app.media_animation = app.media_request = app.last_frame = app.snake = app.maze = None
    app.key_down = set()
    app.fit = SimpleNamespace(get=lambda: 'Fill')
    app.canvas = SimpleNamespace(focus_set=lambda: None)
    app.status = app.content = SimpleNamespace(set=lambda value: None)
    app._draw_preview = lambda: None
    assert app._refit()
    version, request = app.mailbox.read()
    assert isinstance(request, NativePlayback)
    for _ in range(3):
        app._render()
    assert app.mailbox.read()[0] == version
    app.toggle()
    assert isinstance(app.mailbox.read()[1], CanvasFrame)
    app.toggle()
    resumed = app.mailbox.read()[1]
    assert resumed.animation is request.animation and resumed.generation > request.generation
    app.layout = layout.with_gap(5)
    assert app._refit()
    assert app.mailbox.read()[1].layout == app.layout


@pytest.mark.parametrize('failure_stage', ['gif', 'restart'])
def test_native_failure_cancels_siblings_and_never_retries(failure_stage):
    async def run():
        layout, frames, deadlines = fixture()
        mailbox = LatestBoard()
        mailbox.publish(NativePlayback(prepare_animation(frames, deadlines, layout)))
        entered = asyncio.Event()
        calls, cancelled = [], []

        class Link:
            client = SimpleNamespace(is_connected=True)

            def __init__(self, index):
                self.index = index

            async def send(self, plan, **kwargs):
                stage = 'restart' if len(plan.windows[0].data) == 15 else 'gif'
                calls.append((self.index, stage))
                if stage == failure_stage:
                    if self.index == 0:
                        await entered.wait()
                        return None, 0, [bytes.fromhex('0500030001')]
                    entered.set()
                    try:
                        await asyncio.Event().wait()
                    finally:
                        cancelled.append(self.index)
                return None, 0, [bytes.fromhex('0500030003')]

        with pytest.raises(ConnectionError, match='Panel 1'):
            await asyncio.wait_for(stream_canvas([Link(0), Link(1)], layout, mailbox, threading.Event(),
                                                  lambda *a, **kw: None, lambda *a, **kw: None), 1)
        assert cancelled == [1]
        assert len(calls) == (2 if failure_stage == 'gif' else 4)
    asyncio.run(run())
