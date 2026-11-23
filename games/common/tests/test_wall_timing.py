import asyncio
import threading
from types import SimpleNamespace

from PIL import Image
import pytest

from games.common.panel import LatestBoard
from games.common.wall import PanelTiming, stream_canvas
from led_matrix_hacker.wall import CanvasFrame, Layout, Tile


def test_timing_needs_samples_rejects_outliers_and_follows_changed_connections():
    timing = PanelTiming(2)
    for _ in range(3):
        assert timing.delays(True) == [0, 0]
        timing.observe([.225, .080])
    assert timing.delays(True) == pytest.approx([0, .145])
    timing.observe([3, .080])
    assert timing.delays(True) == pytest.approx([0, .145])
    assert timing.delays(False) == [0, 0]
    for _ in range(4):
        timing.observe([.080, .225])
    assert timing.delays(True) == pytest.approx([.145, 0])


def test_delays_are_bounded_even_when_one_panel_stalls():
    timing = PanelTiming(3)
    for _ in range(3):
        timing.observe([2, .080, .160])
    assert timing.delays(True) == [0, .250, .250]
    single = PanelTiming(1)
    for _ in range(3):
        single.observe([.1])
    assert single.delays(True) == [0]


class UploadClock:
    """Separate simulated timelines for parallel uploads, joined at the barrier."""

    def __init__(self):
        self.owner = asyncio.current_task()
        self.now = 0
        self.times = {}

    def __call__(self):
        task = asyncio.current_task()
        if task is self.owner:
            self.now = max([self.now, *self.times.values()])
            return self.now
        return self.times.setdefault(task, self.now)

    async def sleep(self, delay):
        task = asyncio.current_task()
        if task is self.owner:
            self.now += delay
        else:
            self.times[task] = self()+delay
        await asyncio.sleep(0)


@pytest.mark.parametrize('enabled', [False, True])
def test_alignment_reduces_simulated_skew_without_slowing_the_frame_barrier(enabled):
    async def run():
        clock = UploadClock()
        layout = Layout((Tile('A'), Tile('B', y=16)))
        mailbox, stop, alignment = LatestBoard(), threading.Event(), threading.Event()
        if enabled:
            alignment.set()
        records, packets = [], [[], []]
        class Link:
            client = SimpleNamespace(is_connected=True)
            def __init__(self, index, duration):
                self.index, self.duration = index, duration
            async def send(self, plan, **kwargs):
                packets[self.index].append(plan.windows[0].data)
                await clock.sleep(self.duration)
                return None, 0, [bytes.fromhex('0500020003')]
        def publish(index):
            mailbox.publish(CanvasFrame.from_image(Image.new('RGB', layout.size, (index, 0, 0))))
        def emit(kind, **data):
            records.append(data)
            if len(records) == 6:
                stop.set()
            else:
                if enabled and len(records) == 4:
                    alignment.clear()  # Switch off while connected, then back on.
                elif enabled and len(records) == 5:
                    alignment.set()
                publish(len(records))
        publish(0)
        await stream_canvas([Link(0, .225), Link(1, .080)], layout, mailbox, stop,
                            emit, lambda *a, **kw: None, clock=clock, sleep=clock.sleep,
                            timing_alignment=alignment)
        assert len(records) == 6
        assert [frame['reply_ms'] for frame in records] == pytest.approx([225]*6)
        # Duration estimates exclude intentional waiting; it must not compound.
        for frame in records:
            assert frame['panel_reply_ms'] == pytest.approx([225, 80])
        assert [frame['completion_skew_ms'] for frame in records] == pytest.approx(
            [145, 145, 145, 0, 145, 0] if enabled else [145]*6)
        assert records[3]['panel_delay_ms'] == pytest.approx([0, 145] if enabled else [0, 0])
        assert [frame['version'] for frame in records] == list(range(1, 7))
        # Both links always carry the same version, despite staggered starts.
        assert packets[0] == packets[1] and len(packets[0]) == 6
    asyncio.run(run())


def test_failed_upload_cancels_a_sibling_waiting_for_its_start_delay():
    async def run():
        clock = UploadClock()
        layout = Layout((Tile('A'), Tile('B', y=16)))
        mailbox, alignment = LatestBoard(), threading.Event()
        alignment.set()
        delayed, cancelled = asyncio.Event(), []
        calls = [0, 0]
        async def sleep(delay):
            if asyncio.current_task() is not clock.owner and delay > 0:
                delayed.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.append(True)
            else:
                await clock.sleep(delay)
        class Link:
            client = SimpleNamespace(is_connected=True)
            def __init__(self, index):
                self.index = index
            async def send(self, plan, **kwargs):
                calls[self.index] += 1
                if self.index == 0 and calls[0] == 4:
                    await delayed.wait()
                    raise OSError('lost link')
                await clock.sleep(.225 if self.index == 0 else .080)
                return None, 0, [bytes.fromhex('0500020003')]
        def emit(kind, **data):
            mailbox.publish(CanvasFrame.from_image(Image.new('RGB', layout.size, (data['frames'], 0, 0))))
        mailbox.publish(CanvasFrame.from_image(Image.new('RGB', layout.size)))
        with pytest.raises(ConnectionError, match='Panel 1: lost link'):
            await stream_canvas([Link(0), Link(1)], layout, mailbox,
                                threading.Event(), emit, lambda *a, **kw: None,
                                clock=clock, sleep=sleep, timing_alignment=alignment)
        assert cancelled == [True] and calls == [4, 3]
    asyncio.run(asyncio.wait_for(run(), 1))
