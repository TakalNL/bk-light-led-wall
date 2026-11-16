"""Shared desktop game shell: preview, input lifecycle and panel controls."""

from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
import time
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from .panel import LatestBoard, PanelWorker
from .profiles import STANDARD, available_profiles
from .settings import load_panel_settings, save_panel_settings


BACKGROUND = '#101820'
PANEL = '#17232e'
TEXT = '#e6eef4'
MUTED = '#9eafbd'
GREEN = '#65e6ae'


class GameApp:
    # Subclasses provide the game, renderer, encoder and keyboard/status methods.
    game_class = None
    render = None
    encode = None
    heading = 'GAME'
    window_title = 'Game - LED Matrix'
    subtitle = ''
    help_text = ''
    log_name = 'game'
    default_speed = '20'
    speeds = ()
    active_phases = ('running',)

    def __init__(self, root, *, capture_dir, device='', connect=False, preview=False,
                 settings_path=None, trace_packets=False):
        self.root = root
        self.capture_dir = Path(capture_dir)
        self.capture_dir.mkdir(parents=True,exist_ok=True)
        self.settings = Path(settings_path) if settings_path is not None else Path('.state/panel-settings.json')
        saved = load_panel_settings(self.settings)
        self.trace_packets = trace_packets
        if not device: device = saved['device']
        self.stream_profiles = available_profiles()
        selected = next((p for p in self.stream_profiles if p.key == saved['stream_profile']), STANDARD)
        self.game = self.game_class()
        self.mailbox = LatestBoard()
        self.events = Queue()
        self.worker = None
        self.connected = False
        self.connecting = False
        self.closing = False
        self.last_error = ''
        self.last_board = None
        self.next_tick = time.monotonic()
        self.key_down = set()
        self.device = tk.StringVar(value=device)
        self.stream_profile = tk.StringVar(value=selected.label)
        self.preview_only = tk.BooleanVar(value=preview)
        self.speed = tk.StringVar(value=self.default_speed)
        self.score = tk.StringVar(value='00')
        self.game_status = tk.StringVar(value='Ready — press Space to start')
        self.connection_status = tk.StringVar(value='Panel disconnected')
        self.metrics = tk.StringVar(value='No frames sent yet')
        self._build()
        root.bind('<KeyPress>',self._key)
        root.bind('<KeyRelease>',lambda event: self.key_down.discard(event.keysym.lower()))
        root.bind('<FocusOut>',lambda event: root.after(80,self._check_focus))
        root.protocol('WM_DELETE_WINDOW',self.close)
        self._publish()
        root.after(30,self._update)
        if connect and device and not preview: root.after(300,self.connect_panel)

    def _build(self):
        root = self.root
        root.title(self.window_title)
        root.configure(bg=BACKGROUND)
        root.resizable(False,False)
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TButton',font=('Segoe UI',10),padding=(14,8))
        style.configure('TEntry',padding=6)
        style.configure('TCheckbutton',background=BACKGROUND,foreground=TEXT,font=('Segoe UI',10))
        style.map('TCheckbutton',background=[('active',BACKGROUND)])
        outer = tk.Frame(root,bg=BACKGROUND,padx=28,pady=24)
        outer.pack()
        header = tk.Frame(outer,bg=BACKGROUND)
        header.pack(fill='x')
        tk.Label(header,text=self.heading,font=('Segoe UI',28,'bold'),fg=GREEN,bg=BACKGROUND).pack(side='left')
        tk.Label(header,text=self.subtitle,font=('Segoe UI',10),
                 fg=MUTED,bg=BACKGROUND).pack(side='left',padx=22)
        tk.Label(header,textvariable=self.score,font=('Segoe UI',28,'bold'),
                 fg=TEXT,bg=BACKGROUND).pack(side='right')
        tk.Label(outer,text='GAME PREVIEW',font=('Segoe UI',9,'bold'),fg=MUTED,
                 bg=BACKGROUND,anchor='w').pack(fill='x',pady=(18,8))
        self.canvas = tk.Canvas(outer,width=768,height=192,bg='#000000',
                                highlightthickness=1,highlightbackground='#344351')
        self.canvas.pack()
        self.canvas.bind('<Button-1>',lambda event: self.canvas.focus_set())
        self.preview_image = self.canvas.create_image(0,0,anchor='nw')
        tk.Label(outer,textvariable=self.game_status,font=('Segoe UI',12,'bold'),
                 fg=TEXT,bg=BACKGROUND,anchor='w',wraplength=768).pack(fill='x',pady=(14,8))
        controls = tk.Frame(outer,bg=BACKGROUND)
        self.controls = controls
        controls.pack(fill='x')
        self.play_button = ttk.Button(controls,text='Start / Pause',command=self.toggle_play)
        self.play_button.pack(side='left')
        ttk.Button(controls,text='New game',command=self.restart).pack(side='left',padx=8)
        if self.speeds:
            tk.Label(controls,text='Moves / sec',font=('Segoe UI',10),fg=MUTED,
                     bg=BACKGROUND).pack(side='left',padx=(18,6))
            speed = ttk.Combobox(controls,textvariable=self.speed,values=self.speeds,
                                 state='readonly',width=3)
            speed.pack(side='left')
            speed.bind('<<ComboboxSelected>>',self._speed_changed)
        tk.Label(outer,text=self.help_text,
                 font=('Segoe UI',10),fg=MUTED,bg=BACKGROUND,anchor='w').pack(fill='x',pady=(12,18))
        line = tk.Frame(outer,bg=PANEL,height=1)
        line.pack(fill='x',pady=(0,14))
        connection = tk.Frame(outer,bg=BACKGROUND)
        connection.pack(fill='x')
        tk.Label(connection,text='Panel',font=('Segoe UI',10),fg=MUTED,
                 bg=BACKGROUND).pack(side='left',padx=(0,10))
        self.device_entry = ttk.Entry(connection,textvariable=self.device,width=27)
        self.device_entry.pack(side='left')
        self.connect_button = ttk.Button(connection,text='Connect panel',command=self.connect_panel)
        self.connect_button.pack(side='left',padx=8)
        ttk.Checkbutton(connection,text='Play on PC only',variable=self.preview_only,
                        command=self._preview_changed).pack(side='right')
        output = tk.Frame(outer,bg=BACKGROUND)
        output.pack(fill='x',pady=(10,0))
        tk.Label(output,text='Panel updates',font=('Segoe UI',10),fg=MUTED,
                 bg=BACKGROUND).pack(side='left',padx=(0,10))
        self.profile_selector = ttk.Combobox(output,textvariable=self.stream_profile,
            values=tuple(p.label for p in self.stream_profiles),state='readonly',width=21)
        self.profile_selector.pack(side='left')
        self.profile_selector.bind('<<ComboboxSelected>>',lambda event: self.canvas.focus_set())
        tk.Label(output,text='Choose before connecting',font=('Segoe UI',9),fg=MUTED,
                 bg=BACKGROUND).pack(side='left',padx=12)
        tk.Label(outer,textvariable=self.connection_status,font=('Segoe UI',10),fg=MUTED,
                 bg=BACKGROUND,anchor='w',wraplength=768).pack(fill='x',pady=(10,4))
        tk.Label(outer,textvariable=self.metrics,font=('Segoe UI',9),fg=MUTED,
                 bg=BACKGROUND,anchor='w').pack(fill='x')
        root.after(100,self.canvas.focus_set)

    def _publish(self):
        board = self.game.snapshot()
        self.mailbox.publish(board)
        if board != self.last_board:
            self.photo = ImageTk.PhotoImage(self.render(board).resize((768,192),Image.Resampling.NEAREST))
            self.canvas.itemconfigure(self.preview_image,image=self.photo)
            self.last_board = board
        self.score.set(self._score_text())
        self.game_status.set(self._status_text())

    def _score_text(self):
        return f'{self.game.score:02d}'

    def _status_text(self):
        raise NotImplementedError

    def _advance_game(self):
        self.game.tick()

    def toggle_play(self):
        if not self.preview_only.get() and not self.connected:
            self.connection_status.set('Connect the panel first, or choose “Play on PC only”.')
            return
        if self.game.phase in ('over','won'): self.game.restart()
        self.game.toggle_pause()
        self.next_tick = time.monotonic()+1/int(self.speed.get())
        self._publish()
        self.canvas.focus_set()

    def restart(self):
        self.game.restart()
        self._publish()
        self.canvas.focus_set()

    def _speed_changed(self, event=None):
        self.next_tick = time.monotonic()+1/int(self.speed.get())
        self.canvas.focus_set()

    def _preview_changed(self):
        self.game.pause()
        if self.preview_only.get() and self.worker: self.worker.close()
        self._publish()
        self.canvas.focus_set()

    def _check_focus(self):
        if not self.closing and self.root.focus_displayof() is None:
            self.key_down.clear()
            self.game.pause()
            self._publish()

    def _key(self, event):
        raise NotImplementedError

    def connect_panel(self):
        if self.worker and self.worker.thread.is_alive():
            self.game.pause()
            self._publish()
            self.worker.close()
            self.connection_status.set('Disconnecting…')
            self.connect_button.configure(state='disabled')
            return
        device = self.device.get().strip()
        if not device:
            self.connection_status.set('Enter the panel identifier or exact Bluetooth name.')
            return
        self.preview_only.set(False)
        self.game.pause()
        self._publish()
        self.last_error = ''
        self.connected = False
        self.connecting = True
        self.connection_status.set('Finding and connecting to the panel…')
        self.connect_button.configure(text='Cancel connection')
        self.device_entry.configure(state='disabled')
        self.profile_selector.configure(state='disabled')
        profile = next(p for p in self.stream_profiles if p.label == self.stream_profile.get())
        save_panel_settings(self.settings,device=device,profile=profile.key)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        path = self.capture_dir/f'{self.log_name}-{stamp}.jsonl'
        self.worker = PanelWorker(device,self.mailbox,self.events,path,
                                  encode=self.encode,game_name=self.log_name,profile=profile.key,
                                  trace_packets=self.trace_packets)
        self.worker.start()
        self.canvas.focus_set()

    def _update(self):
        while True:
            try: kind,data = self.events.get_nowait()
            except Empty: break
            if kind == 'connected':
                self.connected,self.connecting = True,False
                status = f"Panel connected - {data['fps']} fps target"
                if data.get('fallback'): status += ' (Windows mode unavailable; using Standard)'
                self.connection_status.set(status)
                self.connect_button.configure(text='Disconnect',state='normal')
            elif kind == 'frame':
                self.metrics.set(f"{data['frames']} frames sent  ·  last reply {data['reply_ms']:.0f} ms"
                                 f"  ·  image {data['bytes']} bytes  ·  skipped updates {data['superseded']}")
            elif kind == 'error':
                self.last_error = data['message']
                self.game.pause()
                self._publish()
                self.connection_status.set('Panel stopped: '+self.last_error)
            elif kind == 'disconnected':
                self.connected,self.connecting = False,False
                self.game.pause()
                self._publish()
                if not self.last_error: self.connection_status.set('Panel disconnected')
                self.connect_button.configure(text='Connect panel',state='normal')
                self.device_entry.configure(state='normal')
                self.profile_selector.configure(state='readonly')
        if self.closing:
            if not self.worker or not self.worker.thread.is_alive():
                self.root.destroy()
                return
        elif self.game.phase in self.active_phases and time.monotonic() >= self.next_tick:
            interval = 1/int(self.speed.get())
            for _ in range(4):
                if self.game.phase not in self.active_phases or time.monotonic() < self.next_tick: break
                self._advance_game()
                self.next_tick += interval
            if time.monotonic()-self.next_tick > interval*4:
                self.next_tick = time.monotonic()+interval
            self._publish()
        self.root.after(15,self._update)

    def close(self):
        self.closing = True
        self.game.pause()
        self.connection_status.set('Closing the panel connection…')
        self.connect_button.configure(state='disabled')
        self.play_button.configure(state='disabled')
        if self.worker: self.worker.close()

