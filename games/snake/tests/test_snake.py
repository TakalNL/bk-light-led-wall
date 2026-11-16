import asyncio
from io import BytesIO
import random
import threading
from types import SimpleNamespace

from PIL import Image
import pytest

from games.snake.game import Board, HEIGHT, Snake, WIDTH, board_png
from games.common.panel import LatestBoard


def game():
    value = Snake(rng=random.Random(1))
    value.food = (0,0)
    value.toggle_pause()
    return value


def test_ready_pause_and_restart_prevent_unintended_movement():
    value = Snake()
    first = value.snapshot()
    assert not value.tick() and value.snapshot() == first
    value.toggle_pause()
    value.tick()
    value.pause()
    paused = value.snapshot()
    assert not value.tick() and value.snapshot() == paused
    value.restart()
    assert value.phase == 'ready' and value.score == 0 and len(value.body) == 4


def test_eating_grows_once_and_new_food_avoids_snake():
    value = game()
    value.food = (9,4)
    value.tick()
    assert value.body[0] == (9,4) and len(value.body) == 5 and value.score == 1
    assert value.food not in value.body


def test_quick_turns_are_buffered_but_never_reverse_the_snake():
    value = game()
    assert not value.turn('left')
    assert value.turn('up') and value.turn('left')
    assert not value.turn('down')  # Two queued turns, not an unbounded input queue.
    value.tick()
    assert value.body[0] == (8,3)
    value.tick()
    assert value.body[0] == (7,3)


def test_moving_into_the_vacating_tail_is_legal():
    value = game()
    value.body = [(1,1),(1,2),(0,2),(0,1)]
    value.direction = 'up'
    value.turn('left')
    value.tick()
    assert value.phase == 'running' and value.body[0] == (0,1)


@pytest.mark.parametrize('body,direction',[
    ([(31,4),(30,4),(29,4)],'right'),
    ([(1,1),(1,2),(0,2),(0,1),(0,0)],'left'),
])
def test_wall_and_body_collision_end_game_without_invalid_position(body,direction):
    value = game()
    value.body,value.direction = body.copy(),direction
    value.tick()
    assert value.phase == 'over' and value.body == body


def test_filling_last_free_cell_wins_without_food_loop():
    value = game()
    value.body = [(0,0)] + [(x,y) for y in range(HEIGHT) for x in range(WIDTH)
                            if (x,y) not in ((0,0),(1,0))]
    value.food = (1,0)
    value.tick()
    assert value.phase == 'won' and value.food is None and len(value.body) == WIDTH*HEIGHT


def test_actual_rgb_packets_fit_one_write_for_dense_board_and_all_phases():
    pytest.importorskip('pypixelcolor')
    from pypixelcolor.commands.send_image import send_image_hex
    rng = random.Random(42)
    cells = [(x,y) for y in range(HEIGHT) for x in range(WIDTH)]
    rng.shuffle(cells)
    for length in (4,30,100,200,255):
        for phase in ('ready','running','paused','over','won'):
            board = Board(tuple(cells[:length]),cells[-1],phase,length-4)
            png = board_png(board)
            with Image.open(BytesIO(png)) as image:
                assert image.mode == 'RGB' and image.size == (64,16)
            packet = send_image_hex(png.hex(),'.png').windows[0].data
            assert len(packet) <= 500
            assert packet[14] == 0  # Non-saving slot; do not replace startup GIF.


def test_mailbox_replaces_old_states_and_ignores_unchanged_boards():
    mailbox = LatestBoard()
    value = game()
    mailbox.publish(value.snapshot())
    mailbox.publish(value.snapshot())
    assert mailbox.read()[0] == 1
    value.tick()
    latest = value.snapshot()
    mailbox.publish(latest)
    assert mailbox.read() == (2,latest)


def test_worker_has_one_frame_in_flight_and_sends_latest_after_slow_reply():
    pytest.importorskip('pypixelcolor')
    from games.common.panel import stream_boards
    async def run():
        mailbox = LatestBoard()
        value = game()
        mailbox.publish(value.snapshot())
        entered,release = asyncio.Event(),asyncio.Event()
        stop = threading.Event()
        packets = []
        class Link:
            client = SimpleNamespace(is_connected=True)
            active = False
            async def send(self, plan, **kwargs):
                assert not self.active and kwargs['response'] is True
                self.active = True
                packets.append(plan.windows[0].data)
                if len(packets) == 1:
                    entered.set()
                    await release.wait()
                else: stop.set()
                self.active = False
                return None,0,[bytes.fromhex('0500020003')]
        events = []
        task = asyncio.create_task(stream_boards(Link(),mailbox,stop,
            lambda kind,**data: events.append((kind,data)),lambda *a,**k: None,encode=board_png))
        await entered.wait()
        for _ in range(3):
            value.tick()
            mailbox.publish(value.snapshot())
        release.set()
        await asyncio.wait_for(task,1)
        assert len(packets) == 2 and packets[-1][15:] == board_png(value.snapshot())
        assert events[-1][1]['superseded'] == 2
    asyncio.run(run())


def test_bad_image_reply_stops_stream_instead_of_retrying():
    pytest.importorskip('pypixelcolor')
    from games.common.panel import stream_boards
    async def run():
        mailbox = LatestBoard()
        mailbox.publish(game().snapshot())
        class Link:
            client = SimpleNamespace(is_connected=True)
            writes = 0
            async def send(self, plan, **kwargs):
                self.writes += 1
                return None,0,[bytes.fromhex('0500020001')]
        link = Link()
        with pytest.raises(ValueError,match='expected image reply'):
            await stream_boards(link,mailbox,threading.Event(),lambda *a,**k: None,
                                lambda *a,**k: None,encode=board_png)
        assert link.writes == 1
    asyncio.run(run())


def test_idle_disconnect_is_reported_without_waiting_for_another_board():
    pytest.importorskip('pypixelcolor')
    from games.common.panel import stream_boards
    async def run():
        link = SimpleNamespace(client=SimpleNamespace(is_connected=False))
        with pytest.raises(ConnectionError,match='panel disconnected'):
            await stream_boards(link,LatestBoard(),threading.Event(),lambda *a,**k: None,
                                lambda *a,**k: None,encode=board_png)
    asyncio.run(run())
