"""Headless wall/application lifecycle shared by browser and automation clients.

All application mutations run on one asyncio loop. The existing WallWorker owns
its BLE loop/thread; only immutable frames and its event queue cross that boundary.
"""

import asyncio
from dataclasses import replace
from bisect import bisect_right
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
import threading
import time
import json

from PIL import Image

from games.common.panel import LatestBoard
from games.common.wall import WallWorker
from games.micromaze.game import Maze, render_view
from games.snake.game import Snake, render_board
from games.starfall.game import Shooter, render_flight
from .discovery import scan
from .native_animation import NativePlayback
from .wall import (CanvasFrame, Layout, Tile, demo_image, fit_image, identify_image,
                   load_layout, png_bytes, save_layout)

MODES = ('identify', 'demo', 'snake', 'micromaze', 'starfall', 'clear', 'media')
KEYS = frozenset(('up', 'down', 'left', 'right', 'fire', 'strafe_left', 'strafe_right'))


class Conflict(ValueError):
    """An operation requires a different connection/controller state."""


class WallService:
    def __init__(self, settings_path, capture_dir, *, worker_factory=WallWorker,
                 scanner=scan, clock=time.monotonic):
        self.settings_path, self.capture_dir = Path(settings_path), Path(capture_dir)
        self.worker_factory, self.scanner, self.clock = worker_factory, scanner, clock
        self.layout = None
        self.error = None
        if self.settings_path.exists():
            try:
                self.layout = load_layout(self.settings_path)
            except (OSError, ValueError, KeyError, TypeError) as error:
                self.error = f'Saved setup could not be loaded: {error}'
        self.mailbox, self.events, self.alignment = LatestBoard(), Queue(), threading.Event()
        self.preferences_path = self.settings_path.with_suffix('.preferences.json')
        self.excluded = set()
        if self.preferences_path.exists():
            try:
                preferences = json.loads(self.preferences_path.read_text(encoding='utf8'))
                if type(preferences.get('timing_alignment')) is not bool:
                    raise ValueError('Invalid timing preference.')
                if preferences['timing_alignment']:
                    self.alignment.set()
                excluded = preferences.get('excluded_panels', [])
                if not isinstance(excluded, list) or any(not isinstance(p, str) for p in excluded):
                    raise ValueError('Invalid panel preference.')
                self.excluded = set(excluded)
            except (OSError, ValueError, TypeError, AttributeError) as error:
                self.error = f'Saved preferences could not be loaded: {error}'
        self.worker = None
        self.connection, self.progress = 'disconnected', 'Choose your panels to get started.'
        self.stats, self.devices, self.scanning = {}, [], False
        self.mode, self.game, self.owner = 'identify', None, None
        self.keys, self.last_input = set(), 0.0
        self.media_frames, self.media_deadlines = [], []
        self.media_animation = self.media_request = None
        self.media_generation = 0
        self.media_playing, self.media_elapsed = True, 0.0
        self.epoch, self.tick_number = self.clock(), 0
        self.image = Image.new('RGB', (64, 16))
        self.preview_png, self.preview_version = png_bytes(self.image), 0
        self.preview_frame = None
        self.task = None
        self.operation_lock = asyncio.Lock()

    @property
    def active_layout(self):
        tiles = tuple(t for t in self.layout.tiles if t.device not in self.excluded) if self.layout else ()
        if not tiles:
            return None
        # Keep relative placement and bezel gaps, but let a remaining panel use
        # its whole canvas even when its saved position was below/right of others.
        x, y = min(t.x for t in tiles), min(t.y for t in tiles)
        return Layout(tuple(replace(t, x=t.x-x, y=t.y-y) for t in tiles))

    @property
    def render_layout(self):
        return self.active_layout or self.layout or Layout((Tile('Preview'),))

    async def start(self):
        self.render()
        self.task = asyncio.create_task(self._run())

    async def close(self):
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
        await self.disconnect()

    def state(self):
        return dict(connection=self.connection, progress=self.progress, error=self.error,
                    configured=self.layout is not None,
                    layout=self.layout.to_dict() if self.layout else None,
                    excluded_panels=sorted(self.excluded),
                    size=list(self.render_layout.size), mode=self.mode,
                    game_phase=self.game.phase if self.game else None,
                    score=getattr(self.game, 'score', 0), controller=self.owner,
                    timing_alignment=self.alignment.is_set(), stats=self.stats,
                    preview_version=self.preview_version, scanning=self.scanning,
                    media_loaded=bool(self.media_frames), media_playing=self.media_playing,
                    media_native=self.mode == 'media' and self.media_animation is not None)

    def set_layout(self, data):
        if self.worker:
            raise Conflict('Disconnect the panels before changing their layout.')
        layout = Layout.from_dict(data)
        save_layout(self.settings_path, layout)
        self.layout = layout
        self.excluded.intersection_update(t.device for t in layout.tiles)
        self._save_preferences()
        self.media_frames, self.media_deadlines = [], []
        self.media_animation = self.media_request = None
        self.set_mode('identify')
        self.error = None
        return self.state()

    def set_timing(self, enabled):
        self._save_preferences(timing_alignment=enabled)
        self.alignment.set() if enabled else self.alignment.clear()

    def _save_preferences(self, *, timing_alignment=None):
        self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.preferences_path.with_suffix('.tmp')
        preferences = {'timing_alignment': self.alignment.is_set() if timing_alignment is None else timing_alignment,
                       'excluded_panels': sorted(self.excluded)}
        temporary.write_text(json.dumps(preferences)+'\n', encoding='utf8')
        temporary.replace(self.preferences_path)

    async def panel_action(self, device, action):
        if not self.layout or device not in {t.device for t in self.layout.tiles}:
            raise ValueError('Choose a panel from your saved layout.')
        if action not in ('connect', 'disconnect', 'remove'):
            raise ValueError('Choose connect, disconnect or remove.')
        if self.scanning:
            raise Conflict('Wait for the panel scan to finish.')
        was_active = self.worker is not None
        restart = was_active or action == 'connect'
        # Workers own the whole set of links. Join the previous worker before
        # publishing a different canvas or starting any replacement connections.
        await self.disconnect(release_controller=False)
        if action == 'remove':
            tiles = tuple(t for t in self.layout.tiles if t.device != device)
            spacing = self.layout.linear_spacing
            layout = Layout(tiles) if tiles else None
            if layout and spacing and spacing[1] <= 32:
                layout = layout.arranged(*spacing)
            if layout:
                save_layout(self.settings_path, layout)
            else:
                self.settings_path.unlink(missing_ok=True)
            self.layout = layout
            self.excluded.discard(device)
        elif action == 'disconnect':
            self.excluded.add(device)
        else:
            if not was_active:
                # A card's Connect starts that panel alone. The global Connect
                # button resumes the previously selected set instead.
                self.excluded.update(t.device for t in self.layout.tiles if t.device != device)
            self.excluded.discard(device)
        self._save_preferences()
        # Games restart paused on the resized canvas; decoded media must be
        # uploaded again because it was fitted to the previous dimensions.
        self.media_frames, self.media_deadlines = [], []
        self.media_animation = self.media_request = None
        mode = 'identify' if self.mode == 'media' else self.mode
        if mode == 'snake':
            layout = self.render_layout
            if sum(t.size[0]*t.size[1] for t in layout.tiles) != layout.size[0]*layout.size[1]:
                mode = 'identify'
        self.set_mode(mode)
        self.error, self.stats = None, {}
        if restart and self.active_layout:
            self.connect()
        else:
            self.progress = 'No panels active. Connect a panel below, or use the preview.'

    async def discover(self):
        if self.worker:
            raise Conflict('Disconnect before scanning for panels.')
        self.scanning = True
        try:
            report = await self.scanner(8)
            self.devices = report['devices']
            return report
        finally:
            self.scanning = False

    def connect(self):
        if self.worker:
            raise Conflict('A connection is already active or starting.')
        if self.layout is None:
            raise ValueError('Find and save your panels before connecting.')
        layout = self.active_layout
        if layout is None:
            raise ValueError('Connect a panel using its panel card first.')
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        path = self.capture_dir/('web-wall-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.jsonl')
        self.events = Queue()
        self.stats, self.error = {}, None
        self.connection, self.progress = 'connecting', 'Finding your panels...'
        self.render()
        self.worker = self.worker_factory(layout, self.mailbox, self.events, path,
                                          fps=10, timing_alignment=self.alignment)
        try:
            self.worker.start()
        except Exception:
            self.worker = None
            self.connection = 'disconnected'
            raise

    async def disconnect(self, *, release_controller=True):
        if release_controller:
            self.release(self.owner)
        if self.worker:
            worker = self.worker
            # Ignore completion/status from the retiring worker, including its
            # disconnected event, which otherwise releases the current browser.
            self.events = Queue()
            self.connection = 'disconnecting'
            worker.close()
            await asyncio.to_thread(worker.thread.join, 10)
            if worker.thread.is_alive():
                raise Conflict('Bluetooth is still closing. Wait before reconnecting.')
            self.worker = None
        self.connection, self.progress = 'disconnected', 'Panels disconnected. Preview is available.'

    def claim(self, client, *, takeover=False):
        if self.owner and self.owner != client and not takeover:
            raise Conflict('Another browser has control. Choose Take control to switch.')
        if self.owner != client:
            self.release(self.owner)
        self.owner, self.last_input = client, self.clock()

    def require_owner(self, client):
        if not client or self.owner != client:
            raise Conflict('Take control before changing playback or playing a game.')

    def release(self, client):
        if client != self.owner:
            return
        self.keys.clear()
        if self.game:
            self.game.pause()
            if self.mode == 'starfall':
                self.game.controls(0, 0, False)
        self.owner = None

    def input(self, client, keys):
        self.require_owner(client)
        if not isinstance(keys, list) or len(keys) > len(KEYS) or any(not isinstance(k, str) or k not in KEYS for k in keys):
            raise ValueError('Unsupported game controls.')
        changed = set(keys)-self.keys
        self.keys, self.last_input = set(keys), self.clock()
        if self.mode == 'snake' and self.game:
            for key in ('up', 'down', 'left', 'right'):
                if key in changed:
                    self.game.turn(key)

    def set_mode(self, mode):
        if mode not in MODES:
            raise ValueError('Choose a supported display mode.')
        layout = self.render_layout
        game = None
        if mode == 'snake':
            if sum(t.size[0]*t.size[1] for t in layout.tiles) != layout.size[0]*layout.size[1]:
                raise ValueError('Snake needs a rectangular wall without gaps. Use gap 0 for this game.')
            game = Snake(width=layout.size[0]//2, height=layout.size[1]//2)
        elif mode == 'micromaze':
            game = Maze()
        elif mode == 'starfall':
            game = Shooter()
        elif mode == 'media' and not self.media_frames:
            raise ValueError('Upload an image or GIF first.')
        if self.game:
            self.game.pause()
        self.keys.clear()
        self.mode, self.game, self.epoch, self.tick_number = mode, game, self.clock(), 0
        self.media_elapsed = 0.0
        self.media_playing = True
        if mode == 'media' and self.media_animation:
            self._restart_media()
        self.render()

    def _restart_media(self):
        self.media_elapsed = 0.0
        self.media_generation += 1
        self.media_request = NativePlayback(self.media_animation, self.media_generation)

    def game_action(self, client, action):
        self.require_owner(client)
        self.last_input = self.clock()
        if action not in ('toggle', 'restart', 'pause'):
            raise ValueError('Unsupported playback action.')
        self.keys.clear()
        if self.game:
            if action == 'restart':
                self.game.restart()
            elif action == 'pause':
                self.game.pause()
            else:
                self.game.toggle_pause()
        elif self.mode == 'media':
            if action == 'restart':
                self.media_elapsed = 0
                if self.media_animation:
                    self.media_playing = True
            else:
                self.media_playing = not self.media_playing if action == 'toggle' else False
            if self.media_animation and self.media_playing:
                self._restart_media()
        self.render()

    def render(self):
        layout = self.render_layout
        if self.mode == 'identify':
            image = identify_image(layout) if self.layout else Image.new('RGB', layout.size)
        elif self.mode == 'demo':
            image = demo_image(layout.size, int((self.clock()-self.epoch)*10))
        elif self.mode == 'snake':
            image = render_board(self.game.snapshot(), panel_boxes=tuple(t.box for t in layout.tiles))
        elif self.mode == 'micromaze':
            first = min(layout.tiles, key=lambda t: (t.y, t.x))
            image = render_view(self.game.snapshot(), layout.size, message_box=first.box)
        elif self.mode == 'starfall':
            image = fit_image(render_flight(self.game.snapshot()), layout.size)
        elif self.mode == 'media' and self.media_frames:
            index = bisect_right(self.media_deadlines, self.media_elapsed % self.media_deadlines[-1])
            image = self.media_frames[index]
        else:
            image = Image.new('RGB', layout.size)
        frame = CanvasFrame.from_image(image, layout=layout)
        if frame != self.preview_frame:
            self.preview_frame = frame
            self.image = layout.preview(image)
            self.preview_png = png_bytes(self.image)
            self.preview_version += 1
        request = (self.media_request if self.mode == 'media' and self.media_playing
                   and self.media_animation else frame)
        self.mailbox.publish(request)

    def _events(self):
        while True:
            try:
                kind, data = self.events.get_nowait()
            except Empty:
                return
            if kind == 'connected':
                self.connection, self.progress = 'connected', 'Panels connected and verified.'
            elif kind == 'progress':
                self.progress = data['message']
            elif kind == 'frame':
                self.stats = data
            elif kind == 'native_playing':
                if (self.mode == 'media' and self.media_playing and self.media_request
                        and data['generation'] == self.media_request.generation):
                    self.media_elapsed = 0.0
                    self.stats = dict(data, playback='native')
                    self.progress = 'Animation playing on the panels. Starts are approximately synchronized.'
            elif kind == 'error':
                self.error = data['message']
                self.release(self.owner)
            elif kind == 'disconnected':
                self.connection = 'disconnected'
                self.release(self.owner)

    async def _run(self):
        while True:
            self._events()
            if self.worker and not self.worker.thread.is_alive():
                self.worker = None
                self.connection = 'disconnected'
            if self.owner and self.clock()-self.last_input > 1.5:
                self.release(self.owner)
            if self.game:
                horizontal = int('right' in self.keys)-int('left' in self.keys)
                vertical = int('down' in self.keys)-int('up' in self.keys)
                if self.mode == 'micromaze':
                    self.game.controls(-vertical, horizontal,
                                       int('strafe_right' in self.keys)-int('strafe_left' in self.keys))
                elif self.mode == 'starfall':
                    self.game.controls(horizontal, vertical, 'fire' in self.keys)
                if self.mode != 'snake' or self.tick_number % 4 == 0:
                    self.game.tick()
            if self.mode == 'media' and self.media_playing:
                self.media_elapsed += .05
            self.tick_number += 1
            self.render()
            await asyncio.sleep(.05)
