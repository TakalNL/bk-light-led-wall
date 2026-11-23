from queue import Queue
from types import SimpleNamespace

import pytest

from games.common.panel import LatestBoard
from games.wall.app import WallApp
from led_matrix_hacker.wall import Layout, Tile


class Label:
    def set(self, text):
        self.text = text


def wall_app(layout=None):
    app = WallApp.__new__(WallApp)
    app.layout = layout or Layout((Tile('A'), Tile('B', y=16)))
    app.snake = app.maze = app.last_frame = None
    app.key_down = set()
    app.playing = app.closing = False
    app.events, app.mailbox = Queue(), LatestBoard()
    app.root = SimpleNamespace(after=lambda *args: None, focus_displayof=lambda: None)
    app.canvas = SimpleNamespace(focus_set=lambda: None)
    app.content = Label()
    app._draw_preview = lambda: None
    app.set_mode('Snake')
    return app


def press(app, key, widget_class='Canvas'):
    return app._key(SimpleNamespace(keysym=key, widget=SimpleNamespace(winfo_class=lambda: widget_class)))


@pytest.mark.parametrize('key', ['space', 'Return', 'KP_Enter'])
def test_start_key_repeat_does_not_pause_and_game_advances(key, monkeypatch):
    app = wall_app()
    assert app.snake.phase == 'ready' and not app.playing
    assert 'to start' in app.content.text
    assert press(app, key) == 'break'
    assert app.snake.phase == 'running' and app.playing
    press(app, key)
    assert app.snake.phase == 'running' and app.playing
    before = app.snake.body[0]
    monkeypatch.setattr('games.wall.app.time.monotonic', lambda: app.next_move)
    app._update()
    assert app.snake.body[0] != before
    app.key_down.discard(key.lower())
    press(app, key)
    assert app.snake.phase == 'paused' and not app.playing
    assert 'to resume' in app.content.text


def test_focus_loss_and_escape_pause_then_restart_waits_for_start():
    app = wall_app()
    press(app, 'space')
    app._focus_lost()
    assert app.snake.phase == 'paused' and not app.playing and not app.key_down
    press(app, 'Return')
    assert app.snake.phase == 'running'
    press(app, 'Escape')
    assert app.snake.phase == 'paused' and not app.playing
    press(app, 'r')
    assert app.snake.phase == 'ready' and not app.playing
    press(app, 'Return')
    assert app.snake.phase == 'running'


@pytest.mark.parametrize('widget_class', ['TEntry', 'TCombobox', 'Entry', 'TSpinbox'])
def test_editing_fields_does_not_start_snake(widget_class):
    app = wall_app()
    press(app, 'Return', widget_class)
    press(app, 'space', widget_class)
    assert app.snake.phase == 'ready' and not app.playing and not app.key_down


@pytest.mark.parametrize('tiles', [
    (Tile('A'), Tile('B', y=16)),
    (Tile('B', y=16), Tile('A')),
    (Tile('A'), Tile('B', x=64, rotation=180)),
    (Tile('A', rotation=90), Tile('B', x=16, rotation=270)),
])
def test_game_over_words_fill_separate_panels_in_reading_order(tiles):
    app = wall_app(Layout(tiles))
    app.snake.phase = 'over'
    app._render()
    image = app.last_frame.image()
    assert image.size == app.layout.size
    for index, tile in enumerate(sorted(tiles, key=lambda tile: (tile.y, tile.x))):
        panel = image.crop(tile.box)
        scale = min(panel.width//15, panel.height//5)
        left, top = (panel.width-15*scale)//2, (panel.height-5*scale)//2
        assert panel.getbbox() == (left, top, left+15*scale, top+5*scale)
        assert {color for _, color in panel.getcolors()} == {(0, 0, 0), (255, 255, 255)}
        # G has an open upper-right stroke; O closes it on the second screen.
        assert panel.getpixel((left+2*scale, top+scale)) == ((0, 0, 0) if index == 0 else (255, 255, 255))
    for tile, upload in zip(tiles, app.layout.split(image)):
        assert upload.size == (64, 16)
        assert upload.rotate(-tile.rotation, expand=True).tobytes() == image.crop(tile.box).tobytes()
