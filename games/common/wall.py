"""One connection per tile, one canvas version in flight across the wall."""

import asyncio
from contextlib import AsyncExitStack

from led_matrix_hacker.wall import png_bytes

from .panel import PanelWorker


async def stream_canvas(links, layout, mailbox, stop, emit, record, *, fps=10,
                        device_infos=None, clock=None, sleep=asyncio.sleep):
    from pypixelcolor.commands.send_image import send_image_hex
    if type(fps) is not int or not 1 <= fps <= 10:
        raise ValueError('Wall output must target 1 to 10 fps.')
    if len(links) != len(layout.tiles):
        raise ValueError('Every panel needs a connection.')
    device_infos = [None]*len(links) if device_infos is None else device_infos
    if len(device_infos) != len(links):
        raise ValueError('Every panel needs its own device information.')
    clock = clock or asyncio.get_running_loop().time
    version, frames, next_due, superseded = 0, 0, 0.0, 0
    current_layout = layout

    async def upload(index, link, plan):
        started = clock()
        try:
            _, _, replies = await link.send(plan, response=True, timeout=4)
            if replies[-1:] != [bytes.fromhex('0500020003')]:
                raise ValueError('Missing expected image completion reply.')
        except Exception as error:
            raise ConnectionError(f'Panel {index+1}: {error}') from error
        return (clock()-started)*1000

    while not stop.is_set():
        for index, link in enumerate(links):
            if not link.client.is_connected:
                raise ConnectionError(f'Panel {index+1} disconnected. Reconnect the wall before resuming.')
        latest, frame = mailbox.read()
        if frame is None or latest == version:
            await sleep(.015)
            continue
        await sleep(max(0, next_due-clock()))
        if stop.is_set():
            break
        latest, frame = mailbox.read()
        superseded += max(0, latest-version-1) if version else 0
        frame_layout = frame.layout or layout
        if tuple(t.device for t in frame_layout.tiles) != tuple(t.device for t in layout.tiles):
            raise ValueError('Panel identities/order changed. Disconnect before changing devices.')
        if frame_layout != current_layout:
            record('wall_layout_changed', dimensions=list(frame_layout.size),
                   panel_boxes=[list(t.box) for t in frame_layout.tiles])
            current_layout = frame_layout
        images = frame_layout.split(frame.image())
        plans = [send_image_hex(png_bytes(image).hex(), '.png', save_slot=0, device_info=info)
                 for image, info in zip(images, device_infos)]
        started = clock()
        # Cancel and await siblings on any failed/ambiguous upload. No partial retries.
        try:
            async with asyncio.TaskGroup() as group:
                tasks = [group.create_task(upload(i, link, plan))
                         for i, (link, plan) in enumerate(zip(links, plans))]
        except ExceptionGroup as errors:
            raise errors.exceptions[0] from errors
        elapsed = (clock()-started)*1000
        reply_ms = [task.result() for task in tasks]
        frames += 1
        version = latest
        next_due = started + 1/fps
        data = dict(frames=frames, version=version, reply_ms=round(elapsed, 3),
                    panel_reply_ms=[round(ms, 3) for ms in reply_ms], superseded=superseded)
        record('wall_frame', **data)
        emit('frame', **data)


class WallWorker(PanelWorker):
    def __init__(self, layout, mailbox, events, log_path, *, fps=10, trace_packets=False):
        if type(fps) is not int or not 1 <= fps <= 10:
            raise ValueError('Wall output must target 1 to 10 fps.')
        super().__init__(layout.tiles[0].device, mailbox, events, log_path,
                         encode=None, game_name='wall', trace_packets=trace_packets)
        self.layout, self.fps = layout, fps

    async def _session(self, record):
        from led_matrix_hacker.discovery import resolve_device
        from led_matrix_hacker.library_link import library_connection
        # Resolve all first so aliases cannot open two links to the same hardware.
        devices = []
        for index, tile in enumerate(self.layout.tiles):
            self.emit('progress', message=f'Finding panel {index+1}/{len(self.layout.tiles)}...')
            device = await resolve_device(tile.device, timeout=15)
            if device.address.casefold() in [d.address.casefold() for d in devices]:
                raise ValueError('Two layout entries resolve to the same physical panel.')
            devices.append(device)
        async with AsyncExitStack() as stack:
            links, infos = [], []
            for index, device in enumerate(devices):
                self.emit('progress', message=f'Connecting panel {index+1}/{len(devices)}...')

                def panel_record(kind, _index=index, **fields):
                    record(kind, panel=_index+1, **fields)

                link = await stack.enter_async_context(library_connection(
                    device.address, panel_record, chunk_size=500))
                infos.append(await link.initialize(versions=False))
                links.append(link)
            record('wall_ready', panels=len(links), dimensions=list(self.layout.size), fps=self.fps)
            self.emit('connected', panels=len(links), size=self.layout.size, fps=self.fps)
            await stream_canvas(links, self.layout, self.mailbox, self.stop,
                                self.emit, record, fps=self.fps, device_infos=infos)

    async def _run(self, record):
        task = asyncio.create_task(self._session(record))
        try:
            while not task.done() and not self.stop.is_set():
                await asyncio.sleep(.05)
            if self.stop.is_set() and not task.done():
                task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                if not self.stop.is_set():
                    raise
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
