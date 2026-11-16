import asyncio
from contextlib import asynccontextmanager
from functools import partial
from queue import Queue
import threading
from types import SimpleNamespace

import pytest

from games.common import panel, profiles
from games.common.settings import load_panel_settings, save_panel_settings
from games.snake.game import Snake, board_png
from led_matrix_hacker.windows_connection import connection_profile


class Device:
    def __init__(self, *, status=1, negotiate=True):
        self.parameters = SimpleNamespace(connection_interval=18, connection_latency=0, link_timeout=200)
        self.status, self.negotiate = status, negotiate
        self.requests = self.closed = 0

    def get_connection_parameters(self):
        return self.parameters

    def request_preferred_connection_parameters(self, preferred):
        self.requests += 1
        if self.negotiate:
            self.parameters.connection_interval = 12
        return SimpleNamespace(status=self.status, close=self.close)

    def close(self):
        self.closed += 1


@pytest.fixture
def windows(monkeypatch):
    monkeypatch.setattr(profiles, 'sys', SimpleNamespace(platform='win32'))
    preferred = SimpleNamespace(min_connection_interval=12, max_connection_interval=12, connection_latency=0)
    monkeypatch.setattr(profiles, 'connection_profile', partial(connection_profile, preferred=preferred, settle_seconds=0))


def make_link(device):
    records = []
    link = SimpleNamespace(client=SimpleNamespace(_backend=SimpleNamespace(_requester=device)),
                           record=lambda kind, **fields: records.append((kind, fields)))
    return link, records


def test_standard_profile_never_enters_windows_backend(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Standard must not request Windows tuning')
    monkeypatch.setattr(profiles, 'connection_profile', forbidden)
    link, _ = make_link(None)
    async def run():
        async with profiles.game_stream_profile(link, 'standard') as result:
            assert result == (profiles.STANDARD, None)
    asyncio.run(run())


def test_tuned_profile_keeps_request_until_scope_exits(windows):
    device = Device()
    link, _ = make_link(device)
    async def run():
        async with profiles.game_stream_profile(link, 'windows-12fps') as (actual, fallback):
            assert actual.fps == 12 and fallback is None
            assert device.requests == 1 and device.closed == 0
    asyncio.run(run())
    assert device.closed == 1


@pytest.mark.parametrize('status', [0, 2, 3])
def test_rejected_request_is_released_and_falls_back_to_ten_fps(windows, status):
    device = Device(status=status)
    link, records = make_link(device)
    async def run():
        async with profiles.game_stream_profile(link, 'windows-12fps') as (actual, fallback):
            assert actual == profiles.STANDARD and fallback
            assert device.closed == 1
    asyncio.run(run())
    assert device.requests == 1
    assert records[-1][1]['effective'] == 'standard'


def test_acceptance_without_negotiation_releases_hint_before_fallback(windows):
    device = Device(negotiate=False)
    link, _ = make_link(device)
    async def run():
        async with profiles.game_stream_profile(link, 'windows-12fps') as (actual, fallback):
            assert actual.fps == 10 and 'negotiate' in fallback
            assert device.closed == 1
    asyncio.run(run())


def test_missing_backend_falls_back_without_failing_connection(windows):
    link, _ = make_link(None)
    async def run():
        async with profiles.game_stream_profile(link, 'windows-12fps') as (actual, fallback):
            assert actual == profiles.STANDARD and fallback
    asyncio.run(run())


def test_other_platform_does_not_import_or_request_winrt(monkeypatch):
    monkeypatch.setattr(profiles, 'sys', SimpleNamespace(platform='linux'))
    device = Device()
    link, _ = make_link(device)
    async def run():
        assert profiles.available_profiles() == (profiles.STANDARD,)
        async with profiles.game_stream_profile(link, 'windows-12fps') as (actual, fallback):
            assert actual.fps == 10 and fallback
    asyncio.run(run())
    assert device.requests == device.closed == 0


@pytest.mark.parametrize('error', [OSError('upload failed'), asyncio.CancelledError()])
def test_stream_failure_or_cancellation_releases_hint_and_propagates(windows, error):
    device = Device()
    link, records = make_link(device)
    async def run():
        async with profiles.game_stream_profile(link, 'windows-12fps'):
            raise error
    with pytest.raises(type(error)):
        asyncio.run(run())
    assert device.closed == 1
    assert not any(kind == 'game_stream_preference_unavailable' for kind, _ in records)


@pytest.mark.parametrize('fps,overshoot,latency', [(10, 0, .02), (12, 0, .02),
                                               (10, .012, .02), (12, .012, .02),
                                               (12, 0, .22)])
def test_worker_paces_acknowledged_uploads_at_selected_rate(fps, overshoot, latency):
    now, starts = [0.0], []
    mailbox, stop = panel.LatestBoard(), threading.Event()
    game = Snake()
    game.toggle_pause()
    mailbox.publish(game.snapshot())
    async def sleep(delay):
        now[0] += delay + (overshoot if delay > 0 else 0)
    class Link:
        client = SimpleNamespace(is_connected=True)
        async def send(self, plan, *, response, timeout):
            assert response and plan.windows[0].data[14] == 0
            starts.append(now[0])
            now[0] += latency
            game.tick()
            mailbox.publish(game.snapshot())
            if len(starts) == 4:
                stop.set()
            return None, 0, [bytes.fromhex('0500020003')]
    asyncio.run(panel.stream_boards(Link(), mailbox, stop, lambda *a, **kw: None,
                                    lambda *a, **kw: None, encode=board_png, fps=fps,
                                    clock=lambda: now[0], sleep=sleep))
    if latency > 1/fps:
        assert starts == pytest.approx([i*latency for i in range(4)])
    elif fps == 10:
        assert starts == pytest.approx([i*(1/fps+overshoot) for i in range(4)])
    else:
        assert starts == pytest.approx([0]+[i/fps+overshoot for i in range(1,4)])


def test_reconnect_gets_fresh_preference_after_fallback(windows, monkeypatch, tmp_path):
    from led_matrix_hacker import library_link
    devices = [Device(status=2), Device()]
    disconnected = []
    worker, seen = None, []
    @asynccontextmanager
    async def connect(device_id, record, *, chunk_size):
        assert chunk_size == 500
        device = devices[len(disconnected)]
        link, _ = make_link(device)
        link.client.is_connected = True
        link.record = record
        async def initialize(**kwargs):
            pass
        async def send(*args, **kwargs):
            worker.close()
            return None, 0, [bytes.fromhex('0500020003')]
        link.initialize, link.send = initialize, send
        try:
            yield link
        finally:
            assert device.closed == 1
            disconnected.append(device)
    monkeypatch.setattr(library_link, 'library_connection', connect)
    async def run():
        nonlocal worker
        for _ in range(2):
            mailbox, events = panel.LatestBoard(), Queue()
            mailbox.publish(Snake().snapshot())
            worker = panel.PanelWorker('mock', mailbox, events, tmp_path/'unused',
                                       encode=board_png, profile='windows-12fps')
            await worker._run(lambda *a, **kw: None)
            kind, data = events.get_nowait()
            assert kind == 'connected'
            seen.append(data)
    asyncio.run(run())
    assert [s['fps'] for s in seen] == [10, 12]
    assert seen[0]['fallback'] and seen[1]['fallback'] is None
    assert len(disconnected) == 2


def test_worker_disconnect_cancels_pending_upload_and_releases_hint(windows, monkeypatch, tmp_path):
    from led_matrix_hacker import library_link
    device, entered, released = Device(), asyncio.Event(), []
    @asynccontextmanager
    async def connect(*args, **kwargs):
        link, _ = make_link(device)
        link.client.is_connected = True
        async def initialize(**kwargs):
            pass
        async def send(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()
        link.initialize, link.send = initialize, send
        try:
            yield link
        finally:
            assert device.closed == 1
            released.append(True)
    monkeypatch.setattr(library_link, 'library_connection', connect)
    async def run():
        mailbox = panel.LatestBoard()
        mailbox.publish(Snake().snapshot())
        worker = panel.PanelWorker('mock', mailbox, Queue(), tmp_path/'unused',
                                   encode=board_png, profile='windows-12fps')
        task = asyncio.create_task(worker._run(lambda *a, **kw: None))
        await asyncio.wait_for(entered.wait(), 1)
        worker.close()
        await asyncio.wait_for(task, 1)
    asyncio.run(run())
    assert released == [True]


def test_settings_default_to_standard_and_new_choice_persists(tmp_path):
    path = tmp_path/'settings.json'
    path.write_text('{"device":"mock"}', encoding='utf-8')
    assert load_panel_settings(path) == {'device': 'mock', 'stream_profile': 'standard'}
    save_panel_settings(path, device='mock', profile='windows-12fps')
    assert load_panel_settings(path) == {'device': 'mock', 'stream_profile': 'windows-12fps'}


@pytest.mark.parametrize('saved', ['not json', '[]', '{"device":123,"stream_profile":[]}',
                                 '{"stream_profile":"unknown"}'])
def test_invalid_settings_leave_standard_usable(tmp_path, saved):
    path = tmp_path/'settings.json'
    path.write_text(saved, encoding='utf-8')
    assert load_panel_settings(path) == {'device': '', 'stream_profile': 'standard'}
