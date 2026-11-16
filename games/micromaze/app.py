"""MICROMAZE desktop controller: python -m games.micromaze.app."""

import math
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from .game import Maze, render_map, render_view, view_png
from games.common.launch import launch_game
from games.common.app import BACKGROUND, GameApp


class MazeApp(GameApp):
    game_class = Maze
    render = staticmethod(render_view)
    encode = staticmethod(view_png)
    heading = 'MICROMAZE'
    window_title = 'Micromaze - LED Matrix'
    subtitle = '64 x 16 raycasting'
    help_text = 'W/S or Up/Down: walk    A/D or Left/Right: turn    Q/E: strafe    Enter: start/pause    R: reset    M: map'
    log_name = 'micromaze'
    default_speed = '20'
    speeds = ()

    def __init__(self,root,**kwargs):
        self.show_map = tk.BooleanVar(root,value=False)
        self.map_window = None
        super().__init__(root,**kwargs)

    def _build(self):
        super()._build()
        self.play_button.configure(text='Explore / Pause')
        ttk.Checkbutton(self.controls,text='Show map (PC only)',variable=self.show_map,
                        command=self._toggle_map).pack(side='left',padx=18)

    def _toggle_map(self):
        if self.show_map.get() and self.map_window is None:
            self.map_window = tk.Toplevel(self.root)
            self.map_window.title('Micromaze map - green is the exit')
            self.map_window.configure(bg=BACKGROUND)
            self.map_window.resizable(False,False)
            self.map_label = tk.Label(self.map_window,bg=BACKGROUND,padx=12,pady=12)
            self.map_label.pack()
            self.map_window.protocol('WM_DELETE_WINDOW',self._close_map)
            self.map_window.bind('<KeyPress>',self._key)
            self.map_window.bind('<KeyRelease>',lambda event: self.key_down.discard(event.keysym.lower()))
            self.map_window.bind('<FocusOut>',lambda event: self.root.after(80,self._check_focus))
        elif not self.show_map.get(): self._close_map()
        self._publish()
        self.canvas.focus_set()

    def _close_map(self):
        self.show_map.set(False)
        if self.map_window is not None: self.map_window.destroy()
        self.map_window = None

    def _publish(self):
        super()._publish()
        if self.map_window is not None:
            self.map_photo = ImageTk.PhotoImage(render_map(self.game.snapshot()))
            self.map_label.configure(image=self.map_photo)

    def _score_text(self):
        seconds = int(self.game.elapsed)
        return f'{seconds//60:02d}:{seconds%60:02d}'

    def _status_text(self):
        direction = ('E','SE','S','SW','W','NW','N','NE')[int((self.game.angle+math.pi/8)/(math.pi/4)) % 8]
        if self.game.phase == 'ready': return 'Enter to explore. Find the glowing green exit. M opens an optional map on the PC.'
        if self.game.phase == 'paused': return 'Paused - Enter to resume. Find the green exit.'
        if self.game.phase == 'won': return f'You found the exit in {self.game.elapsed:.1f} seconds! R for another walk.'
        return f'Find the green exit - facing {direction}. No enemies, no time limit. M for a map.'

    def _advance_game(self):
        keys = self.key_down
        forward = int(bool(keys & {'up','w'}))-int(bool(keys & {'down','s'}))
        turn = int(bool(keys & {'right','d'}))-int(bool(keys & {'left','a'}))
        strafe = int('e' in keys)-int('q' in keys)
        self.game.controls(forward,turn,strafe)
        self.game.tick()

    def restart(self):
        self.key_down.clear()
        super().restart()

    def _key(self,event):
        if event.widget.winfo_class() in ('TEntry','TCombobox','Entry','TSpinbox'): return
        key = event.keysym.lower()
        if key in ('up','down','left','right','w','a','s','d','q','e'):
            self.key_down.add(key)
            return 'break'
        if key in ('return','kp_enter','p','r','escape','m'):
            if key in self.key_down: return 'break'
            self.key_down.add(key)
            if key in ('return','kp_enter','p'): self.toggle_play()
            elif key == 'r': self.restart()
            elif key == 'm':
                self.show_map.set(not self.show_map.get())
                self._toggle_map()
            else:
                self.game.pause()
                self._publish()
            return 'break'


def main():
    launch_game(MazeApp, description=__doc__)


if __name__ == '__main__': main()
