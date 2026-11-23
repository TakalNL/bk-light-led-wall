from types import SimpleNamespace

from PIL import ImageChops
import pytest

from games.common.panel import LatestBoard
from games.micromaze.game import DT, Maze, render_view
from games.wall.app import WallApp
from led_matrix_hacker.wall import Layout, Tile


class Label:
    def set(self, text):
        self.text = text


def wall_app(layout):
    """Exercise controller logic without opening a window or Bluetooth link."""
    app = WallApp.__new__(WallApp)
    app.layout = layout
    app.snake = app.maze = app.last_frame = None
    app.key_down = set()
    app.playing = app.closing = False
    app.mailbox = LatestBoard()
    app.canvas = SimpleNamespace(focus_set=lambda: None)
    app.content = Label()
    app._draw_preview = lambda: None
    return app


@pytest.mark.parametrize('second', [Tile('B',y=16), Tile('B',x=64), Tile('B',y=19)])
def test_maze_uses_one_camera_and_splits_full_canvas_without_scaling(second):
    app = wall_app(Layout((Tile('A'),second)))
    app.set_mode('Micromaze')
    assert not app.playing and app.maze.phase == 'ready'
    image = app.last_frame.image()
    assert image.size == app.layout.size
    assert image.tobytes() == render_view(app.maze.snapshot(),app.layout.size).tobytes()
    for tile, panel in zip(app.layout.tiles, app.layout.split(image)):
        assert panel.size == (64,16)
        assert panel.tobytes() == image.crop(tile.box).tobytes()


@pytest.mark.parametrize('tiles', [
    (Tile('A'), Tile('B',y=16)),
    (Tile('A'), Tile('B',y=19)),
    (Tile('A',y=19), Tile('B')),
    (Tile('A'), Tile('B',x=67)),
    (Tile('A',x=4,y=5,rotation=90), Tile('B',x=23,y=5,rotation=90)),
])
def test_completion_message_stays_wholly_inside_top_panel(tiles):
    app = wall_app(Layout(tiles))
    app.set_mode('Micromaze')
    before = app.last_frame.image()
    app.maze.phase = 'won'
    app._render()
    after = app.last_frame.image()
    left,top,right,bottom = min(tiles,key=lambda tile: (tile.y,tile.x)).box
    x0,y0,x1,y1 = ImageChops.difference(before,after).getbbox()
    assert left <= x0 < x1 <= right and top <= y0 < y1 <= bottom
    text_pixels = [(x,y) for y in range(after.height) for x in range(after.width)
                   if after.getpixel((x,y)) == (96,255,144)]
    assert len(text_pixels) == 35  # All four 3x5 letters remain visible.
    assert all(left <= x < right and top <= y < bottom for x,y in text_pixels)


def test_maze_controls_run_at_20hz_and_pause_clears_held_keys(monkeypatch):
    app = wall_app(Layout((Tile('A'),Tile('B',y=16))))
    app.set_mode('Micromaze')
    monkeypatch.setattr('games.wall.app.time.monotonic',lambda: 10)
    app.toggle()
    widget = SimpleNamespace(winfo_class=lambda: 'Canvas')
    app._key(SimpleNamespace(widget=widget,keysym='w'))
    app._advance_maze(10+DT/2)
    assert app.maze.elapsed == 0
    app._advance_maze(10+DT)
    assert app.maze.elapsed == DT and app.maze.x > 1.5
    app.root = SimpleNamespace(focus_displayof=lambda: None)
    app._focus_lost()
    assert app.maze.phase == 'paused' and not app.playing and not app.key_down
    assert app.maze.forward == app.maze.turn == app.maze.strafe == 0
    paused = app.maze.snapshot()
    app.toggle()
    app._advance_maze(10+DT)
    assert app.maze.x == paused.x
    app._key(SimpleNamespace(widget=widget,keysym='r'))
    assert app.maze.snapshot() == Maze().snapshot() and not app.playing


def test_maze_does_not_catch_up_unbounded_time_after_stall(monkeypatch):
    app = wall_app(Layout((Tile('A'),Tile('B',y=16))))
    app.set_mode('Micromaze')
    monkeypatch.setattr('games.wall.app.time.monotonic',lambda: 10)
    app.toggle()
    app.key_down.add('w')
    app._advance_maze(60)
    assert app.maze.elapsed == pytest.approx(4*DT)
    assert app.next_move == 60+DT
    app.set_mode('Identify')
    assert app.maze.phase == 'paused' and not app.key_down and not app.playing
