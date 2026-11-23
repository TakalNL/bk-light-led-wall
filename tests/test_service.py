"""Application lifecycle without Bluetooth: state, input ownership and recovery."""
import asyncio
from pathlib import Path
from queue import Queue
import threading

import pytest

from led_matrix_hacker.service import Conflict, WallService

LAYOUT = {'version': 1, 'panels': [
    {'device':'top', 'x':0, 'y':0, 'rotation':0},
    {'device':'bottom', 'x':0, 'y':16, 'rotation':0},
]}


class Worker:
    instances = []

    def __init__(self, layout, mailbox, events, path, **options):
        self.layout, self.mailbox, self.events = layout, mailbox, events
        self.options, self.path = options, path
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run)
        self.instances.append(self)

    def run(self):
        self.events.put(('connected', {'panels':len(self.layout.tiles)}))
        self.stop.wait()
        self.events.put(('disconnected', {}))

    def start(self): self.thread.start()
    def close(self): self.stop.set()


def controller(tmp_path, **kwargs):
    return WallService(tmp_path/'settings.json', tmp_path/'captures', worker_factory=Worker, **kwargs)


def test_setup_is_explicit_validated_and_persisted(tmp_path):
    app = controller(tmp_path)
    assert not app.state()['configured'] and app.worker is None
    with pytest.raises(ValueError, match='save your panels'):
        app.connect()
    app.set_layout(LAYOUT)
    app.set_timing(True)
    restored = controller(tmp_path)
    assert restored.layout == app.layout and restored.alignment.is_set()
    duplicate = {'version':1,'panels':[LAYOUT['panels'][0],LAYOUT['panels'][0]]}
    with pytest.raises(ValueError):
        app.set_layout(duplicate)
    assert controller(tmp_path).layout == restored.layout


def test_explicit_controller_takeover_pauses_and_releases_held_inputs(tmp_path):
    app = controller(tmp_path)
    app.set_mode('micromaze')
    app.claim('phone1')
    app.game_action('phone1', 'toggle')
    app.input('phone1', ['up'])
    with pytest.raises(Conflict): app.claim('phone2')
    app.claim('phone2', takeover=True)
    assert app.owner == 'phone2' and app.game.phase == 'paused' and not app.keys
    with pytest.raises(Conflict): app.input('phone1', ['up'])
    app.release('phone1')
    assert app.owner == 'phone2'
    app.release('phone2')
    assert app.owner is None


def test_input_watchdog_pauses_without_browser_cooperation(tmp_path):
    async def run():
        now = [0.0]
        app = controller(tmp_path, clock=lambda:now[0])
        app.set_mode('starfall')
        app.claim('phone')
        app.game_action('phone', 'toggle')
        app.input('phone', ['right','fire'])
        await app.start()
        now[0] = 2
        await asyncio.sleep(.08)
        assert app.owner is None and not app.keys and app.game.phase == 'paused'
        assert not app.game.firing and app.game.dx == 0
        await app.close()
    asyncio.run(run())


@pytest.mark.parametrize('count',[1,2,3])
def test_live_worker_is_single_owner_and_cleanup_joins_it(tmp_path,count):
    async def run():
        app = controller(tmp_path)
        app.set_layout({'version':1,'panels':[{'device':f'panel-{i}','x':0,'y':16*i,'rotation':0} for i in range(count)]})
        await app.start()
        app.connect()
        worker = app.worker
        with pytest.raises(Conflict): app.connect()
        with pytest.raises(Conflict): app.set_layout(LAYOUT)
        await asyncio.sleep(.08)
        assert app.connection == 'connected'
        assert worker.mailbox.read()[1].size == (64,16*count)
        for mode in ('demo','snake','micromaze','starfall'):
            app.set_mode(mode)
            await asyncio.sleep(.06)
            assert worker.mailbox.read()[1].size == (64,16*count)
            assert app.worker is worker
        worker.events.put(('error', {'message':'Panel disconnected'}))
        app.claim('phone')
        await asyncio.sleep(.08)
        assert app.error == 'Panel disconnected' and app.owner is None
        await app.close()
        assert not worker.thread.is_alive() and app.worker is None
    asyncio.run(run())


def test_scanning_does_not_open_connections_and_busy_scan_is_rejected(tmp_path):
    async def scanner(seconds):
        assert seconds == 8
        return {'devices':[{'identifier':'found'}]}
    async def run():
        app = controller(tmp_path, scanner=scanner)
        report = await app.discover()
        assert report['devices'][0]['identifier'] == 'found' and app.worker is None
        app.set_layout(LAYOUT)
        app.connect()
        try:
            with pytest.raises(Conflict): await app.discover()
        finally:
            await app.close()
    asyncio.run(run())


def test_gap_is_supported_for_demo_and_maze_but_rejected_for_snake(tmp_path):
    app = controller(tmp_path)
    app.set_layout({'version':1,'panels':[LAYOUT['panels'][0],{**LAYOUT['panels'][1],'y':19}]})
    for mode in ('demo','micromaze','starfall'):
        app.set_mode(mode)
        app.render()
        assert app.image.size == (64,35)
        assert app.image.crop((0,16,64,19)).getbbox() is None
    with pytest.raises(ValueError, match='without gaps'):
        app.set_mode('snake')
    assert app.mode == 'starfall'


@pytest.mark.parametrize('keys', [None,{},['bogus'],[[]],['up']*8])
def test_bad_inputs_cannot_mutate_game_controls(tmp_path, keys):
    app = controller(tmp_path)
    app.claim('phone')
    app.input('phone',['left'])
    with pytest.raises(ValueError): app.input('phone',keys)
    assert app.keys == {'left'}


def test_individual_disconnect_reconnect_and_removal_keep_remaining_wall_usable(tmp_path):
    async def run():
        app = controller(tmp_path)
        app.set_layout(LAYOUT)
        app.connect()
        app.claim('phone')
        app.set_mode('demo')
        first = app.worker
        try:
            await app.panel_action('top', 'disconnect')
            assert not first.thread.is_alive()
            assert app.owner == 'phone' and app.mode == 'demo'
            assert [t.device for t in app.worker.layout.tiles] == ['bottom']
            assert app.worker.layout.tiles[0].y == 0 and app.image.size == (64,16)
            assert app.layout.to_dict() == LAYOUT  # mounting positions remain saved
            assert controller(tmp_path).excluded == {'top'}
            app.set_timing(True)
            assert controller(tmp_path).excluded == {'top'}
            await app.panel_action('top', 'connect')
            assert app.image.size == (64,32) and len(app.worker.layout.tiles) == 2
            assert app.owner == 'phone' and not app.excluded
            await app.panel_action('top', 'remove')
            assert [t.device for t in app.layout.tiles] == ['bottom']
            assert app.layout.tiles[0].y == 0 and app.image.size == (64,16)
            assert controller(tmp_path).layout == app.layout
            await app.panel_action('bottom', 'remove')
            assert app.worker is None and app.layout is None
            assert not app.state()['configured'] and app.owner == 'phone'
            assert not controller(tmp_path).state()['configured']
        finally:
            await app.close()
    asyncio.run(run())


def test_last_panel_disconnect_is_persistent_and_can_be_reconnected(tmp_path):
    async def run():
        app = controller(tmp_path)
        app.set_layout({'version':1,'panels':[LAYOUT['panels'][0]]})
        app.connect()
        try:
            await app.panel_action('top', 'disconnect')
            assert app.worker is None and app.layout is not None
            assert app.connection == 'disconnected'
            with pytest.raises(ValueError, match='panel card'):
                app.connect()
            restored = controller(tmp_path)
            assert restored.excluded == {'top'} and restored.active_layout is None
            await app.panel_action('top', 'connect')
            assert app.worker.layout.size == (64,16)
            assert not controller(tmp_path).excluded
        finally:
            await app.close()
    asyncio.run(run())


def test_panel_connect_from_idle_starts_only_that_panel(tmp_path):
    async def run():
        app = controller(tmp_path)
        app.set_layout(LAYOUT)
        try:
            await app.panel_action('bottom','connect')
            assert [t.device for t in app.worker.layout.tiles] == ['bottom']
            assert app.excluded == {'top'}
            await app.panel_action('top','connect')
            assert len(app.worker.layout.tiles) == 2 and not app.excluded
        finally:
            await app.close()
    asyncio.run(run())


def test_invalid_panel_action_does_not_interrupt_worker(tmp_path):
    async def run():
        app = controller(tmp_path)
        app.set_layout(LAYOUT)
        app.connect()
        worker = app.worker
        try:
            for device, action in [('missing','remove'),('top','unknown')]:
                with pytest.raises(ValueError):
                    await app.panel_action(device, action)
                assert app.worker is worker and worker.thread.is_alive()
        finally:
            await app.close()
    asyncio.run(run())


def test_changing_active_panels_clears_old_media_and_resets_game_without_gaps_error(tmp_path):
    async def run():
        app = controller(tmp_path)
        app.set_layout({'version':1,'panels':[
            {'device':str(i),'x':0,'y':16*i,'rotation':0} for i in range(3)]})
        app.set_mode('snake')
        app.claim('phone')
        app.game_action('phone','toggle')
        await app.panel_action('1','disconnect')
        assert app.mode == 'identify' and app.game is None  # a hole remains in the physical wall
        assert app.active_layout.size == (64,48)
        app.media_frames, app.media_deadlines = [app.image.copy()], [.1]
        app.set_mode('media')
        await app.panel_action('0','disconnect')
        assert not app.media_frames and app.mode == 'identify' and app.image.size == (64,16)
        assert app.owner == 'phone'
    asyncio.run(run())
