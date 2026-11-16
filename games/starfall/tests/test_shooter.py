from io import BytesIO

from PIL import Image
import pytest

from games.starfall.game import (DT, Enemy, Pickup, SPAWNS, STATS, Shooter,
                                       Shot, flight_png, render_flight)


def game():
    value = Shooter()
    value.toggle_pause()
    return value


def test_ready_pause_restart_and_player_stays_on_left():
    value = Shooter()
    value.tick()
    assert value.time == 0 and value.lives == 3
    value.toggle_pause()
    value.spawn_index = len(SPAWNS)
    value.controls(1,1,False)
    for _ in range(100): value.tick()
    assert value.x == 15 and value.y == 10
    value.pause()
    state = value.snapshot()
    value.tick()
    assert value.snapshot() == state
    value.restart()
    assert value.phase == 'ready' and value.lives == 3 and value.score == 0


def test_three_enemy_types_have_distinct_motion_health_and_gunner_shoots():
    value = game()
    for kind in STATS: value.spawn_enemy(kind,5)
    positions = {e.kind:(e.x,e.y) for e in value.enemies}
    next(e for e in value.enemies if e.kind == 'gunner').fire_wait = 0
    value.tick()
    assert {e.hp for e in value.enemies} == {1,2,3}
    assert all(e.x < positions[e.kind][0] for e in value.enemies)
    assert next(e for e in value.enemies if e.kind == 'weaver').y != 5
    assert any(s.hostile and s.vx < 0 for s in value.shots)


def test_twin_cannons_and_rapid_fire_are_real_independent_upgrades():
    def shots(twin,rapid):
        value = game()
        value.twin,value.rapid = twin,rapid
        value.controls(0,0,True)
        for _ in range(20): value.tick()
        return [s for s in value.shots if not s.hostile]
    normal = shots(False,False)
    twin = shots(True,False)
    rapid = shots(False,True)
    assert len(twin) == 2*len(normal)
    assert len({s.y for s in twin}) == 2
    assert len(rapid) > len(normal)


def test_supply_pickups_are_collectible_and_survive_losing_a_life():
    value = game()
    value.time = 9.95
    value.tick()
    assert any(p.kind == 'twin' for p in value.pickups)
    value.pickups = [Pickup('twin',value.x+1,value.y+1)]
    value.tick()
    assert value.twin
    value.pickups = [Pickup('rapid',value.x+1,value.y+1)]
    value.tick()
    assert value.rapid
    value.hit()
    assert value.twin and value.rapid and value.lives == 2


def test_exactly_three_lives_and_hit_interstitial_freezes_campaign():
    value = game()
    value.score = 1234
    for remaining in (2,1,0):
        value.hit()
        value.hit()  # Multiple simultaneous contacts do not consume extra lives.
        assert value.lives == remaining and value.score == 1234
        if remaining:
            assert value.phase == 'respawn'
            campaign_time = value.time
            for _ in range(36): value.tick()
            assert value.phase == 'running' and value.time == campaign_time and value.immune > 0
            value.hit()
            assert value.lives == remaining  # Respawn immunity.
            value.immune = 0
        else:
            assert value.phase == 'over'


def test_pause_during_respawn_returns_to_interstitial():
    value = game()
    value.hit()
    value.pause()
    assert value.phase == 'paused'
    value.toggle_pause()
    assert value.phase == 'respawn'


def test_enemy_projectile_and_ram_each_cost_one_life():
    for projectile in (True,False):
        value = game()
        if projectile: value.shots = [Shot(value.x+2,value.y+2,0,hostile=True)]
        else: value.enemies = [Enemy('drone',value.x+1,value.y+1,1)]
        value.tick()
        assert value.lives == 2 and value.phase == 'respawn'


def test_enemy_kill_awards_points_once_and_boss_kill_finishes_with_bonus():
    value = game()
    value.enemies = [Enemy('drone',10,7,1)]
    value.shots = [Shot(10,7,0),Shot(10,7,0)]
    value.tick()
    assert value.score == 100 and not value.enemies
    value.lives = 2
    value.boss = Enemy('boss',52,3,1)
    value.shots = [Shot(53,7,0)]
    value.tick()
    assert value.phase == 'won' and value.score == 2100 and value.lives == 2
    final = value.snapshot()
    value.tick()
    assert value.snapshot() == final


def test_boss_waits_for_last_wave_and_changes_attack_below_half_health():
    value = game()
    value.time = 51
    value.spawn_index = len(SPAWNS)
    value.enemies = [Enemy('drone',20,3,1)]
    value.tick()
    assert value.boss is None
    value.enemies.clear()
    value.tick()
    assert value.boss.hp == 96
    value.boss.x = 52
    value.boss_fire_wait = 0
    value.tick()
    first = [s for s in value.shots if s.hostile]
    assert len(first) == 3 and value.boss_fire_wait == 1.5
    value.shots.clear()
    value.boss.hp = 40
    value.boss_fire_wait = 0
    value.tick()
    assert len(value.shots) == 3 and value.boss_fire_wait == 1.0


def test_points_and_remaining_lives_are_drawn_on_each_result_screen():
    value = game()
    value.score,value.lives = 1234,2
    for phase in ('respawn','over','won'):
        value.phase = phase
        image = render_flight(value.snapshot())
        # L2 occupies x51..57 in the top row; PTS 001234 occupies the lower row.
        assert image.getpixel((51,1)) == (255,224,32)
        assert image.getpixel((55,1)) == (255,224,32)
        assert image.getpixel((2,9)) == (240,240,240)
        with Image.open(BytesIO(flight_png(value.snapshot()))) as decoded:
            assert decoded.mode == 'RGB' and decoded.size == (64,16)


def test_full_campaign_and_rgb_frame_sizes_with_invulnerability_for_coverage():
    pytest.importorskip('pypixelcolor')
    from pypixelcolor.commands.send_image import send_image_hex
    value = game()
    value.immune = 1000  # Coverage driver, not a player-accessible invulnerability mode.
    value.controls(0,0,True)
    seen = set()
    largest = 0
    for index in range(2400):
        value.tick()
        seen.update(e.kind for e in value.enemies)
        if index%2 == 0:
            png = flight_png(value.snapshot())
            packet = send_image_hex(png.hex(),'.png').windows[0].data
            largest = max(largest,len(packet))
            assert packet[14] == 0 and len(packet) <= 500
        if value.phase == 'won': break
    assert seen == set(STATS)
    assert value.phase == 'won' and value.boss.hp <= 0
    assert value.twin and value.rapid and value.lives == 3 and value.score > 2250
    assert largest > 200
