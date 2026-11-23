"""Local web interface for the headless LED wall service."""

import argparse
import asyncio
from collections import deque
from contextlib import suppress
from io import BytesIO
from importlib.resources import files
import json
import logging
from pathlib import Path
import secrets
import socket
import time
from urllib.parse import urlsplit
import uuid
import webbrowser
import weakref

from aiohttp import web, WSMsgType
from bleak.exc import BleakError
from PIL import Image, UnidentifiedImageError

from .service import Conflict, WallService
from .wall import load_media

SERVICE = web.AppKey('service', WallService)
TOKEN = web.AppKey('token', str)
SOCKETS = web.AppKey('sockets', weakref.WeakSet)
PAIR_CODE = web.AppKey('pair_code', str)
PAIR_FAILURES = web.AppKey('pair_failures', deque)
PHONE_URLS = web.AppKey('phone_urls', tuple)
ASSETS = {'index.html': 'text/html', 'app.js': 'text/javascript', 'style.css': 'text/css'}


@web.middleware
async def access(request, handler):
    if request.path.startswith('/api/'):
        origin = request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host:
            raise web.HTTPForbidden(text='Open the interface using its own address.')
        if request.path not in ('/api/ws', '/api/pair'):
            authorization = request.headers.get('Authorization', '')
            if not secrets.compare_digest(authorization.encode(), ('Bearer '+request.app[TOKEN]).encode()):
                raise web.HTTPUnauthorized(text='Use the access link printed by the server.')
    try:
        response = await handler(request)
    except Conflict as error:
        response = web.json_response({'error': str(error)}, status=409)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        response = web.json_response({'error': str(error) or 'Invalid request.'}, status=400)
    except (OSError, BleakError, TimeoutError) as error:
        logging.getLogger(__name__).warning('Application operation failed: %s', error)
        response = web.json_response({'error': str(error)}, status=503)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; img-src 'self' blob:; connect-src 'self'; "
        "script-src 'self'; style-src 'self'; frame-ancestors 'none'")
    return response


async def asset(request):
    name = request.match_info.get('name', 'index.html')
    if name not in ASSETS:
        raise web.HTTPNotFound()
    return web.Response(body=files('led_matrix_hacker').joinpath('web', name).read_bytes(),
                        content_type=ASSETS[name])


async def state(request):
    return web.json_response(request.app[SERVICE].state())


async def pair(request):
    failures = request.app[PAIR_FAILURES]
    now = time.monotonic()
    while failures and failures[0] <= now-60:
        failures.popleft()
    if len(failures) >= 5:
        raise web.HTTPTooManyRequests(text='Too many attempts. Wait one minute and try again.')
    data = await request.json()
    supplied = data.get('code', '') if isinstance(data, dict) else ''
    if not isinstance(supplied, str) or not secrets.compare_digest(supplied.encode(), request.app[PAIR_CODE].encode()):
        failures.append(now)
        raise web.HTTPUnauthorized(text='Incorrect access code. Use the six digits shown by LED Wall.')
    return web.json_response({'token': request.app[TOKEN]})


async def phone_access(request):
    return web.json_response({'code': request.app[PAIR_CODE], 'urls': list(request.app[PHONE_URLS])})


async def phone_qr(request):
    import qrcode
    from qrcode.image.pil import PilImage
    urls = request.app[PHONE_URLS]
    index = int(request.match_info['index'])
    if not 0 <= index < len(urls):
        raise web.HTTPNotFound()
    output = BytesIO()
    qrcode.make(urls[index]+'/#'+request.app[TOKEN], image_factory=PilImage).save(output, format='PNG')
    return web.Response(body=output.getvalue(), content_type='image/png')


async def operation(request):
    service = request.app[SERVICE]
    action = request.match_info['action']
    if action not in {'scan', 'layout', 'connect', 'disconnect', 'panel', 'mode', 'timing', 'media'}:
        raise web.HTTPNotFound()
    async with service.operation_lock:
        if action == 'scan':
            return web.json_response(await service.discover())
        service.require_owner(request.headers.get('X-LED-Controller'))
        if action == 'media':
            mode = request.query.get('fit', 'Fit')
            if mode not in ('Fit', 'Fill', 'Stretch'):
                raise ValueError('Choose Fit, Fill or Stretch.')
            data = await request.read()
            size = service.render_layout.size

            def decode():
                try:
                    with Image.open(BytesIO(data)) as source:
                        if source.format not in ('PNG', 'GIF'):
                            raise ValueError('Choose a PNG image or GIF animation.')
                        count = getattr(source, 'n_frames', 1)
                        if source.width*source.height*count > 16_000_000:
                            raise ValueError('Media is too large. Use smaller images or fewer frames.')
                    return load_media(BytesIO(data), size, mode)
                except (UnidentifiedImageError, Image.DecompressionBombError) as error:
                    raise ValueError('This file could not be opened as a supported image.') from error

            frames, deadlines = await asyncio.to_thread(decode)
            service.media_frames, service.media_deadlines = frames, deadlines
            service.set_mode('media')
        else:
            data = await request.json() if request.can_read_body else {}
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')
            if action == 'layout':
                service.set_layout(data)
            elif action == 'connect':
                service.connect()
            elif action == 'disconnect':
                await service.disconnect()
            elif action == 'panel':
                await service.panel_action(data.get('device'), data.get('action'))
            elif action == 'mode':
                service.set_mode(data.get('mode'))
            elif action == 'timing':
                enabled = data.get('enabled')
                if type(enabled) is not bool:
                    raise ValueError('Timing alignment must be true or false.')
                service.set_timing(enabled)
        return web.json_response(service.state())


async def websocket(request):
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=16_384)
    await ws.prepare(request)
    request.app[SOCKETS].add(ws)
    service = request.app[SERVICE]
    client = uuid.uuid4().hex
    try:
        authentication = await ws.receive_json(timeout=10)
        supplied = authentication.get('token', '') if isinstance(authentication, dict) else ''
        if not isinstance(supplied, str) or not secrets.compare_digest(supplied.encode(), request.app[TOKEN].encode()):
            await ws.close(code=1008, message=b'Use the server access link.')
            return ws
    except (ValueError, TypeError, TimeoutError):
        await ws.close(code=1008, message=b'Authentication required.')
        return ws
    await ws.send_json({'type': 'ready', 'client_id': client})

    async def publish():
        version = -1
        while not ws.closed:
            await ws.send_json({'type': 'state', **service.state()})
            if service.preview_version != version:
                version = service.preview_version
                await ws.send_bytes(service.preview_png)
            await asyncio.sleep(.1)

    publisher = asyncio.create_task(publish())
    try:
        async for message in ws:
            if message.type != WSMsgType.TEXT:
                break
            try:
                data = json.loads(message.data)
                kind = data.get('type')
                if kind == 'claim':
                    takeover = data.get('takeover', False)
                    if type(takeover) is not bool:
                        raise ValueError('Invalid takeover request.')
                    service.claim(client, takeover=takeover)
                elif kind == 'release':
                    service.release(client)
                elif kind == 'input':
                    service.input(client, data.get('keys'))
                elif kind == 'playback':
                    service.game_action(client, data.get('action'))
                else:
                    raise ValueError('Unsupported browser action.')
            except (ValueError, TypeError, AttributeError) as error:
                await ws.send_json({'type': 'error', 'message': str(error)})
    finally:
        service.release(client)
        publisher.cancel()
        with suppress(asyncio.CancelledError, ConnectionError, RuntimeError):
            await publisher
    return ws


def create_app(service, *, token, pairing_code=None, phone_urls=()):
    app = web.Application(middlewares=[access], client_max_size=8*1024*1024)
    app[SERVICE], app[TOKEN] = service, token
    app[SOCKETS] = weakref.WeakSet()
    app[PAIR_CODE] = pairing_code or f'{secrets.randbelow(1_000_000):06d}'
    app[PAIR_FAILURES] = deque()
    app[PHONE_URLS] = tuple(phone_urls)

    async def shutdown(app):
        await asyncio.gather(*(ws.close(code=1001, message=b'Server stopping')
                               for ws in list(app[SOCKETS])))

    app.on_shutdown.append(shutdown)

    async def lifecycle(app):
        await service.start()
        try:
            yield
        finally:
            await service.close()

    app.cleanup_ctx.append(lifecycle)
    app.add_routes([web.get('/', asset), web.get('/{name:app.js|style.css}', asset),
                    web.get('/api/state', state), web.get('/api/ws', websocket),
                    web.post('/api/pair', pair), web.get('/api/access', phone_access),
                    web.get('/api/access/{index:\\d+}/qr.png', phone_qr),
                    web.post('/api/{action}', operation)])
    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description='Run LED Wall with a local, phone-friendly web interface.')
    parser.add_argument('--host', default='127.0.0.1', help='Use 0.0.0.0 to allow phones on your LAN.')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--settings', type=Path, default=Path('.state/web-wall-settings.json'))
    parser.add_argument('--capture-dir', type=Path, default=Path('captures'))
    opening = parser.add_mutually_exclusive_group()
    opening.add_argument('--open', action='store_true', help='Open the access link in this computer\'s browser.')
    opening.add_argument('--no-open', action='store_true', help='Keep the browser closed.')
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('Use a port from 1 to 65535.')
    token = secrets.token_urlsafe(24)
    pairing_code = f'{secrets.randbelow(1_000_000):06d}'
    phone_urls = []
    local = f'http://127.0.0.1:{args.port}/#{token}'
    print('LED WALL — local web controller', flush=True)
    print('Open on this host:', local, flush=True)
    if args.host == '0.0.0.0':
        try:
            addresses = {r[4][0] for r in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
            # A UDP connect selects a local route without transmitting a packet.
            # Ubuntu often resolves its own hostname only to 127.0.1.1.
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
                    route.connect(('192.0.2.1', 9))
                    addresses.add(route.getsockname()[0])
            except OSError:
                pass
            for address in sorted(addresses):
                if not address.startswith('127.'):
                    phone_urls.append(f'http://{address}:{args.port}')
        except OSError:
            print(f'Phone / LAN access: http://<this-host-IP>:{args.port}', flush=True)
    elif args.host != '127.0.0.1':
        phone_urls.append(f'http://{args.host}:{args.port}')
    for url in phone_urls:
        print('Phone / LAN address:', url, flush=True)
    print('Access code:', pairing_code, flush=True)
    print('Keep the access link private. The phone and Bluetooth host must share a network.', flush=True)
    service = WallService(args.settings, args.capture_dir)
    app = create_app(service, token=token, pairing_code=pairing_code, phone_urls=phone_urls)
    # aiohttp calls this only after its listening sockets have started, so a
    # failed bind cannot open a browser with a code for a nonexistent session.
    def ready(_):
        webbrowser.open(local)
    web.run_app(app, host=args.host, port=args.port,
                access_log=None, print=ready if args.open else None)


if __name__ == '__main__':
    main()
