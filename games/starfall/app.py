"""STARFALL desktop shooter: python -m games.starfall.app."""

import tkinter as tk
from tkinter import ttk

from .game import Shooter, flight_png, render_flight
from games.common.launch import launch_game
from games.common.app import GameApp


class ShooterApp(GameApp):
    game_class = Shooter
    render = staticmethod(render_flight)
    encode = staticmethod(flight_png)
    heading = 'STARFALL'
    window_title = 'Starfall · LED Matrix'
    subtitle = '3 waves · 3 lives · carrier boss'
    help_text = 'Move: arrows / WASD    Fire: Space    Launch: Enter    Pause: P    Restart: R'
    log_name = 'starfall'
    default_speed = '20'
    speeds = ()
    active_phases = ('running','respawn')

    def __init__(self,root,**kwargs):
        self.auto_fire = tk.BooleanVar(root,value=False)
        super().__init__(root,**kwargs)

    def _build(self):
        super()._build()
        self.play_button.configure(text='Launch / Pause')
        ttk.Checkbutton(self.controls,text='Auto-fire',variable=self.auto_fire,
                        command=self.canvas.focus_set).pack(side='left',padx=18)

    def _score_text(self):
        return f'{self.game.score:05d}   L{self.game.lives}'

    def _status_text(self):
        game = self.game
        upgrades = ('Twin cannons' if game.twin else 'Single cannon')+' · '+(
            'Rapid fire' if game.rapid else 'Standard fire')
        if game.phase == 'ready': return 'Ready — Enter to launch. Hold Space to fire; collect cyan T and yellow R capsules.'
        if game.phase == 'paused': return 'Paused — Enter or P to resume · '+upgrades
        if game.phase == 'over': return f'Game over · {game.score} points · {game.lives} lives · R for a new run'
        if game.phase == 'won': return f'Carrier defeated! {game.score} points · {game.lives} lives · R for a new run'
        if game.phase == 'respawn': return f'Ship lost · {game.score} points · {game.lives} lives left · Returning…'
        stage = f'BOSS: CARRIER {game.boss.hp}/96 HP' if game.boss else f'Wave {game.wave}/3'
        return stage+' · '+upgrades

    def _advance_game(self):
        keys = self.key_down
        dx = int(bool(keys & {'right','d'}))-int(bool(keys & {'left','a'}))
        dy = int(bool(keys & {'down','s'}))-int(bool(keys & {'up','w'}))
        self.game.controls(dx,dy,'space' in keys or self.auto_fire.get())
        self.game.tick()

    def _key(self,event):
        if event.widget.winfo_class() in ('TEntry','TCombobox','Entry','TSpinbox'): return
        key = event.keysym.lower()
        if key in ('up','down','left','right','w','a','s','d','space'):
            self.key_down.add(key)
            return 'break'
        if key in ('return','kp_enter','p','r','escape'):
            if key in self.key_down: return 'break'
            self.key_down.add(key)
            if key in ('return','kp_enter','p'): self.toggle_play()
            elif key == 'r': self.restart()
            else:
                self.game.pause()
                self._publish()
            return 'break'


def main():
    launch_game(ShooterApp, description=__doc__)


if __name__ == '__main__': main()
