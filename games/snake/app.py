"""Local desktop Snake prototype: python -m games.snake.app."""

import argparse
import logging
from pathlib import Path
import tkinter as tk

from .game import Snake, render_board, board_png
from games.common.app import GameApp


class SnakeApp(GameApp):
    game_class = Snake
    render = staticmethod(render_board)
    encode = staticmethod(board_png)
    heading = 'SNAKE'
    window_title = 'Snake · LED Matrix'
    subtitle = '32 × 8 cells · 2 × 2 LEDs per cell'
    help_text = 'Arrow keys / WASD steer     Space starts or pauses     R starts a new game'
    log_name = 'snake'
    default_speed = '5'
    speeds = ('3','4','5','6','7','8')
    active_phases = ('running',)

    def _status_text(self):
        statuses = {'ready':'Ready — press Space to start',
                    'running':'Playing — avoid the walls and your tail',
                    'paused':'Paused — Space to resume',
                    'over':'Game over — press R for a new game',
                    'won':'Board complete! Press R to play again'}
        return statuses[self.game.phase]

    def _key(self, event):
        if event.widget.winfo_class() in ('TEntry','TCombobox','Entry','TSpinbox'): return
        key = event.keysym.lower()
        turns = {'up':'up','w':'up','down':'down','s':'down',
                 'left':'left','a':'left','right':'right','d':'right'}
        if key in turns:
            self.game.turn(turns[key])
            return 'break'
        if key in ('space','r','escape'):
            if key in self.key_down: return 'break'
            self.key_down.add(key)
            if key == 'space': self.toggle_play()
            elif key == 'r': self.restart()
            else:
                self.game.pause()
                self._publish()
            return 'break'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',default='')
    parser.add_argument('--connect',action='store_true')
    parser.add_argument('--preview',action='store_true',help='Play locally without Bluetooth.')
    parser.add_argument('--capture-dir',type=Path,default=Path('captures'))
    args = parser.parse_args()
    args.capture_dir.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=args.capture_dir/'snake-errors.log',level=logging.ERROR)
    root = tk.Tk()
    def callback_error(error_type,value,traceback):
        logging.error('Snake UI error',exc_info=(error_type,value,traceback))
        app.connection_status.set('An app error occurred; see snake-errors.log.')
        app.game.pause()
    root.report_callback_exception = callback_error
    app = SnakeApp(root,capture_dir=args.capture_dir,device=args.device,
                   connect=args.connect,preview=args.preview)
    root.mainloop()


if __name__ == '__main__': main()
