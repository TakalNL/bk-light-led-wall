from collections import deque
from dataclasses import replace
from io import BytesIO
import math

from PIL import Image
import pytest

from games.micromaze.game import (DT, EXIT, LEVEL, Maze, View, cast_ray,
                                    render_view, solid, view_png)


def route_to_exit():
    queue = deque([[(1,1)]])
    seen = {(1,1)}
    while queue:
        path = queue.popleft()
        if path[-1] == EXIT: return path
        x,y = path[-1]
        for cell in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if cell not in seen and not solid(cell[0]+.5,cell[1]+.5):
                seen.add(cell)
                queue.append(path+[cell])
    raise AssertionError('No route to the exit')


def running():
    game = Maze()
    game.toggle_pause()
    return game


def test_pause_and_restart_do_not_move_or_keep_old_controls():
    game = Maze()
    game.controls(1,1)
    ready = game.snapshot()
    game.tick()
    assert game.snapshot() == ready
    game.toggle_pause()
    game.tick()
    assert game.elapsed == DT and game.x != ready.x
    game.pause()
    paused = game.snapshot()
    game.tick()
    assert game.snapshot() == paused and game.forward == game.turn == 0
    game.toggle_pause()
    game.tick()
    assert game.x == paused.x and game.angle == paused.angle
    game.restart()
    assert game.snapshot() == ready


def test_collision_and_strafing_slide_without_entering_walls():
    game = running()
    game.controls(0,0,-1)
    for _ in range(100): game.tick()
    assert 1.2 <= game.y < 1.3
    # Continue into the northern wall while moving east; wall sliding still works.
    game.controls(1,0,-1)
    for _ in range(200):
        game.tick()
        assert game.fits(game.x,game.y)
    assert 5.7 < game.x <= 5.8 and 1.2 <= game.y < 1.3
    assert not game.fits(1.1,1.1)
    assert solid(-.1,1) and solid(100,100)


def test_diagonal_movement_does_not_make_player_faster():
    straight,diagonal = running(),running()
    straight.controls(1,0)
    diagonal.controls(1,0,1)
    straight.tick()
    diagonal.tick()
    assert math.hypot(diagonal.x-1.5,diagonal.y-1.5) == pytest.approx(straight.x-1.5)


@pytest.mark.parametrize('direction,distance,cell',[
    ((1,0),4.5,(6,1)),((0,-1),.5,(1,0)),((-1,0),.5,(0,1)),
])
def test_dda_axis_aligned_rays_hit_expected_wall(direction,distance,cell):
    hit = cast_ray(1.5,1.5,*direction)
    assert hit.distance == pytest.approx(distance)
    assert (hit.x,hit.y) == cell and 0 <= hit.u < 1


def test_entire_maze_is_connected_and_can_be_won_by_movement_and_turning():
    assert len({len(row) for row in LEVEL}) == 1
    reachable = {(1,1)}
    queue = deque(reachable)
    while queue:
        x,y = queue.popleft()
        for cell in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if cell not in reachable and not solid(cell[0]+.5,cell[1]+.5):
                reachable.add(cell)
                queue.append(cell)
    assert len(reachable) == sum(c != '#' for row in LEVEL for c in row)
    game = running()
    # Follow cell centres with the same turning/movement controls as the GUI.
    for x,y in route_to_exit()[1:]:
        for _ in range(150):
            dx,dy = x+.5-game.x,y+.5-game.y
            if math.hypot(dx,dy) < .1 or game.phase == 'won': break
            error = (math.atan2(dy,dx)-game.angle+math.pi) % math.tau-math.pi
            game.controls(1 if abs(error) < .065 else 0,
                          max(-1,min(1,error/(DT*1.65))))
            game.tick()
            assert game.fits(game.x,game.y)
        else: pytest.fail(f'Could not navigate to {(x,y)}')
    assert game.phase == 'won'
    won = game.snapshot()
    game.tick()
    assert game.snapshot() == won


def test_exit_portal_is_depth_occluded_and_visible_when_in_sight():
    hidden = render_view(View(1.5,1.5,0,'running',0))
    visible = render_view(View(13.5,7.5,math.pi/2,'running',0))
    assert (64,255,112) not in [color for _,color in hidden.getcolors(1024)]
    assert (64,255,112) in [color for _,color in visible.getcolors(1024)]
    # A nearby wall at x=12 hides the portal even when looking toward it.
    blocked = render_view(View(11.5,7.5,math.pi/4,'running',0))
    assert (64,255,112) not in [color for _,color in blocked.getcolors(1024)]


def test_rgb_frames_fit_one_acknowledged_packet_throughout_the_maze():
    largest = 0
    for y,row in enumerate(LEVEL):
        for x,tile in enumerate(row):
            if tile == '#': continue
            for step in range(16):
                view = View(x+.5,y+.5,step*math.tau/16,'running',0)
                payload = view_png(view)
                largest = max(largest,len(payload)+15)
                image = Image.open(BytesIO(payload))
                assert image.mode == 'RGB' and image.size == (64,16)
    assert largest <= 500
    won = view_png(replace(view,phase='won'))
    assert len(won)+15 <= 500
