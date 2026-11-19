"""LED Wall: flexible multi-panel canvas, media player and full-canvas Snake."""

import argparse
import asyncio
from bisect import bisect_right
from datetime import datetime
import logging
from pathlib import Path
from queue import Empty, Queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from games.common.panel import LatestBoard
from games.common.wall import WallWorker
from games.snake.game import Snake, render_board
from led_matrix_hacker.discovery import scan
from led_matrix_hacker.wall import (
    CanvasFrame, Layout, Tile, demo_image, identify_image, load_layout, load_media, save_layout,
)


class WallApp:
    def __init__(self, root, *, settings=Path('.state/wall-settings.json'),
                 capture_dir=Path('captures'), connect=False, demo=False):
        self.root, self.settings, self.capture_dir = root, settings, capture_dir
        capture_dir.mkdir(parents=True, exist_ok=True)
        self.events, self.mailbox = Queue(), LatestBoard()
        self.worker = None
        self.connected = self.closing = self.scanning = False
        self.last_error = ''
        self.mode, self.playing = 'Identify', False
        self.epoch = time.monotonic()
        self.snake, self.next_move = None, 0
        self.media_path, self.media_frames, self.media_deadlines = None, [], []
        self.last_frame = None
        self.status = tk.StringVar(value='Configure panels, then connect the wall.')
        self.metrics = tk.StringVar(value='No frames sent')
        self.content = tk.StringVar(value='Identify panels')
        self.fit = tk.StringVar(value='Fit')
        self.gap = tk.StringVar(value='0')
        self.device = tk.StringVar()
        self.x, self.y, self.rotation = tk.StringVar(value='0'), tk.StringVar(value='0'), tk.StringVar(value='0')
        self.edit_controls = []
        self._build()
        try:
            layout = load_layout(settings)
        except FileNotFoundError:
            layout = Layout((Tile('Panel 1'), Tile('Panel 2', y=16)))
        except (OSError, ValueError, TypeError) as error:
            self.status.set(f'Saved layout could not be loaded: {error}')
            layout = Layout((Tile('Panel 1'), Tile('Panel 2', y=16)))
        self.layout = layout
        self._sync_gap()
        for tile in layout.tiles:
            self.table.insert('', 'end', values=(tile.device, tile.x, tile.y, tile.rotation))
        self.table.selection_set(self.table.get_children()[0])
        self._select()
        self._publish(identify_image(layout))
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<KeyPress>', self._key)
        root.bind('<FocusOut>', lambda event: root.after(80, self._focus_lost))
        root.after(25, self._update)
        if demo:
            self.set_mode('Demo')
        if connect:
            root.after(300, self.connect)

    def _build(self):
        root = self.root
        root.title('LED Wall - shared canvas')
        root.configure(bg='#101820')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TButton', padding=(9, 6))
        outer = ttk.Frame(root, padding=18)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='LED WALL', font=('Segoe UI', 24, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='One canvas across your panels · coordinates are pixels · rotation is clockwise').pack(anchor='w')
        self.canvas = tk.Canvas(outer, width=768, height=384, bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, pady=12)
        self.canvas.bind('<Configure>', lambda event: self._draw_preview())
        self.canvas.bind('<Button-1>', lambda event: self.canvas.focus_set())
        self.table = ttk.Treeview(outer, columns=('device', 'x', 'y', 'rotation'), show='headings', height=3,
                                  selectmode='browse')
        for column, label, width in (('device', 'Bluetooth identifier / exact name', 380),
                                      ('x', 'X', 70), ('y', 'Y', 70), ('rotation', 'Rotation', 90)):
            self.table.heading(column, text=label)
            self.table.column(column, width=width)
        self.table.pack(fill='x')
        self.table.bind('<<TreeviewSelect>>', lambda event: self._select())
        editor = ttk.Frame(outer)
        editor.pack(fill='x', pady=8)
        self.device_input = ttk.Combobox(editor, textvariable=self.device, width=32)
        self.device_input.pack(side='left')
        self.edit_controls.append(self.device_input)
        for name, variable in (('X', self.x), ('Y', self.y)):
            ttk.Label(editor, text=name).pack(side='left', padx=(8, 2))
            entry = ttk.Entry(editor, textvariable=variable, width=4)
            entry.pack(side='left')
            self.edit_controls.append(entry)
        rotate = ttk.Combobox(editor, textvariable=self.rotation, values=(0, 90, 180, 270), width=5, state='readonly')
        rotate.pack(side='left', padx=8)
        self.rotation_input = rotate
        self.edit_controls.append(rotate)
        self._edit_button(editor, 'Apply panel', self.apply_panel)
        arrangement = ttk.Frame(outer)
        arrangement.pack(fill='x')
        for text, action in (('Scan Bluetooth', self.scan), ('Stack vertically', lambda: self.arrange(True)),
                             ('Side by side', lambda: self.arrange(False)), ('Reverse order', self.reverse),
                             ('Add panel', self.add_panel), ('Remove', self.remove_panel)):
            self._edit_button(arrangement, text, action)
        compensation = ttk.Frame(outer)
        compensation.pack(fill='x', pady=(8, 0))
        ttk.Label(compensation, text='Bezel gap (pixels)').pack(side='left', padx=(0, 8))
        self.gap_input = ttk.Spinbox(compensation, textvariable=self.gap, from_=0, to=32,
                                     increment=1, width=4, command=self.apply_compensation)
        self.gap_input.pack(side='left')
        self.gap_input.bind('<Return>', lambda event: self.apply_compensation())
        self.gap_button = ttk.Button(compensation, text='Apply gap', command=self.apply_compensation)
        self.gap_button.pack(side='left', padx=8)
        ttk.Label(compensation, text='0 = off · adjustable during playback · hidden rows/columns').pack(side='left')
        playback = ttk.Frame(outer)
        playback.pack(fill='x', pady=(12, 6))
        self.connect_button = ttk.Button(playback, text='Connect wall', command=self.connect)
        self.connect_button.pack(side='left', padx=(0, 8))
        for text, action in (('Identify', lambda: self.set_mode('Identify')), ('Seam demo', lambda: self.set_mode('Demo')),
                             ('Snake', lambda: self.set_mode('Snake')), ('Open image / GIF', self.open_media),
                             ('Pause / Play', self.toggle), ('Clear', lambda: self.set_mode('Clear'))):
            ttk.Button(playback, text=text, command=action).pack(side='left', padx=2)
        options = ttk.Frame(outer)
        options.pack(fill='x', pady=4)
        fit = ttk.Combobox(options, textvariable=self.fit, values=('Fit', 'Fill', 'Stretch'), width=8, state='readonly')
        fit.pack(side='left')
        fit.bind('<<ComboboxSelected>>', lambda event: self._refit())
        ttk.Label(options, textvariable=self.content).pack(side='left', padx=12)
        ttk.Label(outer, text='Snake: arrows / WASD · Space pauses · R restarts · click preview for keyboard control').pack(anchor='w')
        ttk.Label(outer, textvariable=self.status, wraplength=820).pack(anchor='w', pady=(8, 3))
        ttk.Label(outer, textvariable=self.metrics).pack(anchor='w')
        root.minsize(920, 800)

    def _edit_button(self, parent, text, action):
        button = ttk.Button(parent, text=text, command=action)
        button.pack(side='left', padx=2)
        self.edit_controls.append(button)

    def _select(self):
        selected = self.table.selection()
        if selected:
            device, x, y, rotation = self.table.item(selected[0], 'values')
            for variable, value in zip((self.device, self.x, self.y, self.rotation), (device, x, y, rotation)):
                variable.set(value)

    def _busy(self):
        return self.worker is not None and self.worker.thread.is_alive()

    def _lock(self, locked):
        for control in self.edit_controls:
            control.configure(state='disabled' if locked else 'normal')
        if not locked:
            self.rotation_input.configure(state='readonly')

    def _read_layout(self):
        return Layout(tuple(Tile(str(values[0]).strip(), *(int(v) for v in values[1:]))
                            for item in self.table.get_children()
                            for values in [self.table.item(item, 'values')]))

    def _changed(self, *, preserve_animation=False):
        try:
            layout = self._read_layout()
            save_layout(self.settings, layout)
        except (ValueError, OSError) as error:
            self.status.set(str(error))
            return False
        self.layout = layout
        self._sync_gap()
        self.snake = None
        self.last_frame = None
        if self.mode == 'Media':
            if not self._refit():
                self.set_mode('Identify')
        elif preserve_animation and self.mode == 'Demo':
            self._render()
        else:
            self.set_mode(self.mode)
        self.status.set(f'Layout saved: {layout.size[0]}×{layout.size[1]} · {len(layout.tiles)} panels')
        return True

    def _sync_gap(self):
        spacing = self.layout.linear_spacing
        self.gap.set(str(spacing[1]) if spacing is not None else '0')

    def _replace_rows(self, layout):
        for item, tile in zip(self.table.get_children(), layout.tiles):
            self.table.item(item, values=(tile.device, tile.x, tile.y, tile.rotation))
        self._select()

    def apply_compensation(self):
        if self.closing or self.scanning or (self._busy() and not self.connected):
            self.status.set('Wait for the connection or scan to finish before adjusting compensation.')
            return False
        previous = self.layout
        try:
            layout = previous.with_gap(int(self.gap.get()))
        except ValueError as error:
            self.status.set(str(error))
            self._sync_gap()
            return False
        self._replace_rows(layout)
        if not self._changed(preserve_animation=True):
            self._replace_rows(previous)
            self._sync_gap()
            return False
        state = 'Wall connected' if self.connected else 'Layout saved'
        self.status.set(f'{state} · bezel gap {self.gap.get()} px · canvas {layout.size[0]}×{layout.size[1]}')
        return True

    def apply_panel(self):
        if self._busy() or not self.table.selection():
            return False
        item = self.table.selection()[0]
        previous = self.table.item(item, 'values')
        self.table.item(item, values=(self.device.get(), self.x.get(), self.y.get(), self.rotation.get()))
        if not self._changed():
            self.table.item(item, values=previous)
            return False
        self.canvas.focus_set()
        return True

    def arrange(self, vertical):
        if self._busy():
            return
        try:
            layout = self._read_layout().arranged(vertical, int(self.gap.get()))
        except ValueError as error:
            self.status.set(str(error))
            return
        previous = self.layout
        self._replace_rows(layout)
        if not self._changed():
            self._replace_rows(previous)

    def reverse(self):
        if self._busy():
            return
        items = self.table.get_children()
        devices = [self.table.item(item, 'values')[0] for item in reversed(items)]
        for item, device in zip(items, devices):
            values = self.table.item(item, 'values')
            self.table.item(item, values=(device, *values[1:]))
        self._changed()
        self._select()

    def add_panel(self):
        if self._busy() or len(self.table.get_children()) >= 16:
            return
        item = self.table.insert('', 'end', values=(f'Panel {len(self.table.get_children())+1}', 0, self.layout.size[1], 0))
        self.table.selection_set(item)
        self._changed()

    def remove_panel(self):
        if self._busy() or len(self.table.get_children()) <= 1 or not self.table.selection():
            return
        self.table.delete(self.table.selection()[0])
        self.table.selection_set(self.table.get_children()[0])
        self._changed()

    def scan(self):
        if self._busy() or self.scanning:
            return
        self.scanning = True
        self._lock(True)
        self.status.set('Scanning Bluetooth for 8 seconds...')

        def run():
            try:
                result = asyncio.run(scan(8, name_filter='LED'))
                self.events.put(('scan', dict(devices=result['devices'])))
            except Exception as error:
                self.events.put(('scan_error', dict(message=str(error))))

        threading.Thread(target=run, daemon=True, name='wall-scan').start()

    def connect(self):
        if self.scanning:
            return
        if self._busy():
            self.playing = False
            self.worker.close()
            self.connect_button.configure(state='disabled')
            self.status.set('Disconnecting all panels...')
            return
        # Include pending changes to the selected panel before connecting.
        if not self.apply_panel():
            return
        try:
            layout = self._read_layout()
            save_layout(self.settings, layout)
        except (ValueError, OSError) as error:
            self.status.set(str(error))
            return
        self.layout = layout
        self.last_error = ''
        self._lock(True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        self.worker = WallWorker(layout, self.mailbox, self.events, self.capture_dir/f'wall-ui-{stamp}.jsonl')
        self.connect_button.configure(text='Cancel connection')
        self.status.set('Finding the panels...')
        self.worker.start()

    def set_mode(self, mode):
        self.mode, self.epoch = mode, time.monotonic()
        self.playing = mode in ('Demo', 'Snake', 'Media')
        if mode == 'Snake':
            # Holes have no physical pixels. A rectangular game needs full coverage.
            if sum(t.size[0]*t.size[1] for t in self.layout.tiles) != self.layout.size[0]*self.layout.size[1]:
                self.status.set('Snake needs a rectangular layout without gaps.')
                self.mode, self.playing = 'Identify', False
            else:
                self.snake = Snake(width=self.layout.size[0]//2, height=self.layout.size[1]//2)
                self.next_move = time.monotonic()+.15
                self.playing = False
        self._render()
        self.canvas.focus_set()

    def _render(self):
        elapsed = time.monotonic()-self.epoch
        if self.mode == 'Identify':
            image = identify_image(self.layout)
        elif self.mode == 'Clear':
            image = Image.new('RGB', self.layout.size)
        elif self.mode == 'Demo':
            image = demo_image(self.layout.size, int(elapsed*10))
        elif self.mode == 'Snake':
            image = render_board(self.snake.snapshot())
        elif self.media_frames:
            index = bisect_right(self.media_deadlines, elapsed % self.media_deadlines[-1])
            image = self.media_frames[index]
        else:
            return
        self.content.set(f'{self.layout.size[0]}×{self.layout.size[1]} · {self.mode}' +
                         (f' · {self.snake.phase} · score {self.snake.score}' if self.mode == 'Snake' else ''))
        self._publish(image)

    def _publish(self, image):
        frame = CanvasFrame.from_image(image, layout=self.layout)
        if frame != self.last_frame:
            self.last_frame = frame
            self.mailbox.publish(frame)
            self._draw_preview()

    def _draw_preview(self):
        if self.last_frame is None:
            return
        image = self.layout.preview(self.last_frame.image())
        width, height = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        scale = min(width/image.width, height/image.height)
        size = max(1, int(image.width*scale)), max(1, int(image.height*scale))
        self.photo = ImageTk.PhotoImage(image.resize(size, Image.Resampling.NEAREST))
        self.canvas.delete('all')
        left, top = (width-size[0])/2, (height-size[1])/2
        self.canvas.create_image(left, top, anchor='nw', image=self.photo)
        for index, tile in enumerate(self.layout.tiles):
            x0, y0, x1, y1 = tile.box
            self.canvas.create_rectangle(left+x0*scale, top+y0*scale, left+x1*scale-1, top+y1*scale-1,
                                         outline='#718396', dash=(3, 3))
            self.canvas.create_text(left+x0*scale+4, top+y0*scale+4, anchor='nw', fill='#ffffff',
                                    text=str(index+1), font=('Segoe UI', 9))

    def open_media(self):
        path = filedialog.askopenfilename(filetypes=[('Images / GIF', '*.png *.gif *.jpg *.jpeg *.bmp *.webp'), ('All files', '*.*')])
        if path:
            previous = self.media_path
            self.media_path = Path(path)
            if not self._refit():
                self.media_path = previous

    def _refit(self):
        if self.media_path is None:
            return False
        try:
            frames, deadlines = load_media(self.media_path, self.layout.size, self.fit.get())
        except (OSError, ValueError) as error:
            self.status.set(f'Could not load image: {error}')
            return False
        self.media_frames, self.media_deadlines = frames, deadlines
        self.set_mode('Media')
        return True

    def toggle(self):
        if self.mode == 'Snake':
            if self.snake.phase in ('over', 'won'):
                self.snake.restart()
            self.snake.toggle_pause()
            self.playing = self.snake.phase == 'running'
            self.next_move = time.monotonic()+.15
            self._render()
        elif self.mode in ('Demo', 'Media'):
            if self.playing:
                self.paused_elapsed = time.monotonic()-self.epoch
            else:
                self.epoch = time.monotonic()-getattr(self, 'paused_elapsed', 0)
            self.playing = not self.playing
        self.canvas.focus_set()

    def _key(self, event):
        if event.widget.winfo_class() in ('TEntry', 'TCombobox', 'Entry', 'TSpinbox'):
            return
        key = event.keysym.lower()
        if key == 'space':
            self.toggle()
            return 'break'
        if self.mode != 'Snake':
            return
        if key == 'r':
            self.set_mode('Snake')
            return 'break'
        direction = dict(w='up', a='left', s='down', d='right').get(key, key)
        if direction in ('up', 'down', 'left', 'right'):
            self.snake.turn(direction)
            return 'break'

    def _focus_lost(self):
        if not self.closing and self.mode == 'Snake' and self.root.focus_displayof() is None:
            self.snake.pause()
            self.playing = False
            self._render()

    def _update(self):
        while True:
            try:
                kind, data = self.events.get_nowait()
            except Empty:
                break
            if kind == 'scan':
                self.scanning = False
                self._lock(False)
                devices = data['devices']
                self.device_input.configure(values=tuple(d['identifier'] for d in devices))
                names = ', '.join((d['advertised_name'] or d['name'] or d['identifier']) for d in devices)
                self.status.set(f'Found {len(devices)} LED devices: {names}. Select an identifier for each panel and Apply panel.')
            elif kind == 'scan_error':
                self.scanning = False
                self._lock(False)
                self.status.set('Bluetooth scan failed: '+data['message'])
            elif kind == 'progress':
                self.status.set(data['message'])
            elif kind == 'connected':
                self.connected = True
                self.status.set(f"All {data['panels']} panels connected · {data['fps']} fps target · combined {data['size'][0]}×{data['size'][1]}")
                self.connect_button.configure(text='Disconnect wall', state='normal')
            elif kind == 'frame':
                timings = ' / '.join(f'{ms:.0f}' for ms in data['panel_reply_ms'])
                self.metrics.set(f"{data['frames']} combined frames · wall reply {data['reply_ms']:.0f} ms · panel replies {timings} ms · skipped {data['superseded']}")
            elif kind == 'error':
                self.last_error = data['message']
                self.status.set('Wall stopped: '+self.last_error)
                self.playing = False
                if self.snake:
                    self.snake.pause()
            elif kind == 'disconnected':
                self.connected = self.playing = False
                if self.snake:
                    self.snake.pause()
                if not self.last_error:
                    self.status.set('Wall disconnected. Reconnect to resume output.')
                self.connect_button.configure(text='Connect wall', state='normal')
                self._lock(False)
        if self.closing:
            if not self._busy():
                self.root.destroy()
                return
        elif self.playing:
            if self.mode == 'Snake' and time.monotonic() >= self.next_move:
                self.snake.tick()
                self.next_move = time.monotonic()+.15
                self.playing = self.snake.phase == 'running'
            self._render()
        self.root.after(25, self._update)

    def close(self):
        self.closing, self.playing = True, False
        self._lock(True)
        self.connect_button.configure(state='disabled')
        self.gap_input.configure(state='disabled')
        self.gap_button.configure(state='disabled')
        self.status.set('Closing all panel connections...')
        if self.worker:
            self.worker.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings', type=Path, default=Path('.state/wall-settings.json'))
    parser.add_argument('--capture-dir', type=Path, default=Path('captures'))
    parser.add_argument('--connect', action='store_true')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    args.capture_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=args.capture_dir/'wall-errors.log', level=logging.ERROR)
    root = tk.Tk()
    app = WallApp(root, settings=args.settings, capture_dir=args.capture_dir, connect=args.connect, demo=args.demo)

    def callback_error(error_type, value, traceback):
        logging.error('Wall UI error', exc_info=(error_type, value, traceback))
        app.playing = False
        app.status.set('An app error occurred; see wall-errors.log.')

    root.report_callback_exception = callback_error
    root.mainloop()


if __name__ == '__main__':
    main()
