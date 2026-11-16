"""Shared game transport: one BLE worker and a latest-state mailbox."""

import asyncio
import math
from pathlib import Path
import threading

from led_matrix_hacker.experiments import Recorder

from .profiles import PROFILES, game_stream_profile


class LatestBoard:
    def __init__(self):
        self.lock = threading.Lock()
        self.version = 0
        self.board = None

    def publish(self, board):
        with self.lock:
            if board != self.board:
                self.version += 1
                self.board = board

    def read(self):
        with self.lock: return self.version,self.board


async def stream_boards(link, mailbox, stop, emit, record, *, encode, game_name='game', fps=10,
                        clock=None, sleep=asyncio.sleep):
    from pypixelcolor.commands.send_image import send_image_hex
    if type(fps) is not int or fps not in (10, 12):
        raise ValueError('Game output must target 10 or 12 fps.')
    version = 0
    frames = 0
    superseded = 0
    next_due = 0.0
    epoch = None
    clock = clock or asyncio.get_running_loop().time
    while not stop.is_set():
        if not link.client.is_connected:
            raise ConnectionError('The panel disconnected. Reconnect before resuming.')
        latest,board = mailbox.read()
        if board is None or latest == version:
            await sleep(.015)
            continue
        await sleep(max(0,next_due-clock()))
        if stop.is_set(): break
        latest,board = mailbox.read()  # Select the latest state after pacing.
        superseded += max(0,latest-version-1) if version else 0
        data = encode(board)
        plan = send_image_hex(data.hex(),'.png',save_slot=0)
        size = sum(len(window.data) for window in plan.windows)
        started = clock()
        _,_,replies = await link.send(plan,response=True,timeout=4)
        if replies[-1:] != [bytes.fromhex('0500020003')]:
            raise ValueError('The panel did not return the expected image reply.')
        seconds = clock()-started
        frames += 1
        version = latest
        if fps == 10:
            next_due = started+.1
        else:
            # Fixed deadlines prevent sleep overshoot accumulating each frame.
            # Skip elapsed slots; the mailbox still supplies only the latest state.
            if epoch is None: epoch = started
            next_due = epoch+(math.floor((started-epoch)*fps+1e-7)+1)/fps
        record(game_name+'_frame',frame=frames,version=version,phase=board.phase,score=board.score,
               bytes=size,reply_ms=round(seconds*1000,3),superseded=superseded)
        emit('frame',frames=frames,reply_ms=seconds*1000,bytes=size,superseded=superseded)


class PanelWorker:
    def __init__(self, device, mailbox, events, log_path, *, encode, game_name='game', profile='standard'):
        if profile not in PROFILES:
            raise ValueError('Unknown game streaming profile.')
        self.device,self.mailbox,self.events,self.log_path = device,mailbox,events,Path(log_path)
        self.profile = profile
        self.stop = threading.Event()
        self.encode,self.game_name = encode,game_name
        self.thread = threading.Thread(target=self._thread_main,daemon=True,name=game_name+'-bluetooth')

    def emit(self, kind, **data):
        self.events.put((kind,data))

    def start(self): self.thread.start()
    def close(self): self.stop.set()

    def _thread_main(self):
        try:
            with self.log_path.open('x',encoding='utf-8') as output:
                record = Recorder(output, echo=False)
                record(self.game_name+'_session_started')
                try:
                    asyncio.run(self._run(record))
                except Exception as error:
                    record(self.game_name+'_session_error',error_type=type(error).__name__,message=str(error))
                    raise
                record(self.game_name+'_session_finished')
        except Exception as error:
            self.emit('error',message=str(error) or type(error).__name__)
        finally:
            self.emit('disconnected')

    async def _run(self, record):
        from led_matrix_hacker.library_link import library_connection
        async def session():
            async with library_connection(self.device,record,chunk_size=500) as link:
                await link.initialize(versions=False)
                record(self.game_name+'_profile_verified', dimensions=[64,16])
                async with game_stream_profile(link,self.profile) as (effective,fallback):
                    self.emit('connected',profile=effective.key,fps=effective.fps,fallback=fallback)
                    try:
                        await stream_boards(link,self.mailbox,self.stop,self.emit,record,
                                            encode=self.encode,game_name=self.game_name,fps=effective.fps)
                    except Exception as error:
                        record(self.game_name+'_stream_error',message=str(error),error_type=type(error).__name__)
                        raise
        task = asyncio.create_task(session())
        try:
            while not task.done() and not self.stop.is_set(): await asyncio.sleep(.05)
            if self.stop.is_set() and not task.done(): task.cancel()
            try: await task
            except asyncio.CancelledError:
                if not self.stop.is_set(): raise
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)
