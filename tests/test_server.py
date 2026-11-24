"""HTTP/WebSocket contract, access protection and real server cleanup."""
import asyncio
from io import BytesIO

from aiohttp import WSMsgType
from aiohttp.test_utils import TestClient, TestServer
from PIL import Image

from led_matrix_hacker.server import create_app
from led_matrix_hacker.service import WallService

TOKEN = 'test-access-key'


async def receive_json(ws, kind):
    while True:
        message = await asyncio.wait_for(ws.receive(),2)
        if message.type == WSMsgType.TEXT:
            data = message.json()
            if data.get('type') == kind:
                return data


async def login(client):
    ws = await client.ws_connect('/api/ws')
    await ws.send_json({'token':TOKEN})
    ready = await receive_json(ws,'ready')
    await ws.send_json({'type':'claim'})
    while True:
        state = await receive_json(ws,'state')
        if state['controller'] == ready['client_id']:
            break
    return ws, {'Authorization':'Bearer '+TOKEN,'X-LED-Controller':ready['client_id']}


def test_authentication_origin_and_bundled_interface(tmp_path):
    async def run():
        service = WallService(tmp_path/'settings.json',tmp_path/'captures')
        async with TestClient(TestServer(create_app(service, token=TOKEN))) as client:
            response = await client.get('/')
            assert response.status == 200 and 'Set up your wall' in await response.text()
            assert TOKEN not in await response.text()
            assert (await client.get('/app.js')).status == 200
            assert (await client.get('/api/state')).status == 401
            headers = {'Authorization':'Bearer '+TOKEN}
            assert (await client.get('/api/state',headers=headers)).status == 200
            assert (await client.post('/api/connect',headers={**headers,'Origin':'http://another-site.invalid'})).status == 403
            assert (await client.get('/private.txt')).status == 404
            ws = await client.ws_connect('/api/ws')
            await ws.send_json({'token':'incorrect'})
            assert (await ws.receive()).type == WSMsgType.CLOSE
            assert service.worker is None
    asyncio.run(run())


def test_browser_ownership_media_and_disconnect_pause(tmp_path):
    async def run():
        service = WallService(tmp_path/'settings.json',tmp_path/'captures')
        async with TestClient(TestServer(create_app(service, token=TOKEN))) as client:
            ws, headers = await login(client)
            image = Image.new('RGB',(8,8),'red')
            media = BytesIO(); image.save(media,format='PNG')
            response = await client.post('/api/media',data=media.getvalue(),headers=headers)
            assert response.status == 200 and service.mode == 'media'
            assert service.image.getbbox() is not None
            response = await client.post('/api/mode',json={'mode':'micromaze'},headers=headers)
            assert response.status == 200
            await ws.send_json({'type':'playback','action':'toggle'})
            while (await receive_json(ws,'state'))['game_phase'] != 'running':
                pass
            other = await client.ws_connect('/api/ws'); await other.send_json({'token':TOKEN})
            await receive_json(other,'ready')
            await other.send_json({'type':'claim'})
            assert 'Another browser' in (await receive_json(other,'error'))['message']
            assert (await client.post('/api/mode',json={'mode':'demo'},headers={'Authorization':'Bearer '+TOKEN})).status == 409
            await ws.close()
            await asyncio.sleep(.08)
            assert service.owner is None and service.game.phase == 'paused'
            await other.close()
        assert service.task.done()
    asyncio.run(run())


def test_browser_gif_automatically_prepares_layout_and_native_playback(tmp_path):
    from led_matrix_hacker.native_animation import NativePlayback
    from led_matrix_hacker.wall import CanvasFrame

    async def run():
        service = WallService(tmp_path/'settings.json', tmp_path/'captures')
        async with TestClient(TestServer(create_app(service, token=TOKEN))) as client:
            ws, headers = await login(client)
            layout = dict(version=1, panels=[dict(device='A', x=0, y=0, rotation=0),
                                            dict(device='B', x=0, y=19, rotation=0)])
            response = await client.post('/api/layout', json=layout, headers=headers)
            assert response.status == 200
            first = Image.new('RGB', (128, 70), 'red')
            second = Image.new('RGB', (128, 70), 'blue')
            media = BytesIO()
            first.save(media, format='GIF', save_all=True, append_images=[second], duration=[40, 70], loop=0)
            response = await client.post('/api/media?fit=Fill', data=media.getvalue(), headers=headers)
            assert response.status == 200 and (await response.json())['media_native']
            request = service.mailbox.read()[1]
            assert isinstance(request, NativePlayback)
            assert request.layout.size == (64, 35) and request.animation.duration_ms == 110
            for data in request.animation.gifs:
                with Image.open(BytesIO(data)) as gif:
                    assert gif.size == (64, 16) and gif.n_frames == 2
            # Preview animation must not replace the native request with PNGs.
            service.media_elapsed = .05
            service.render()
            assert service.mailbox.read()[1] is request
            service.game_action(service.owner, 'pause')
            assert isinstance(service.mailbox.read()[1], CanvasFrame)
            service.game_action(service.owner, 'toggle')
            resumed = service.mailbox.read()[1]
            assert isinstance(resumed, NativePlayback) and resumed.generation > request.generation
            service.game_action(service.owner, 'restart')
            assert service.mailbox.read()[1].generation > resumed.generation
            # Late completion from an older upload cannot reset current playback.
            service.media_elapsed = .05
            service.events.put(('native_playing', dict(generation=request.generation)))
            service._events()
            assert service.media_elapsed == .05
            service.events.put(('native_playing', dict(generation=service.media_request.generation,
                                                      frames=2, duration_ms=110)))
            service._events()
            assert service.media_elapsed == 0 and service.stats['playback'] == 'native'
            # A still image automatically returns to normal PNG output.
            still = BytesIO(); first.save(still, format='PNG')
            response = await client.post('/api/media', data=still.getvalue(), headers=headers)
            assert response.status == 200 and not (await response.json())['media_native']
            assert isinstance(service.mailbox.read()[1], CanvasFrame)
            await ws.close()
    asyncio.run(run())


def test_malformed_requests_and_image_limits_are_errors_without_hardware(tmp_path):
    async def run():
        service = WallService(tmp_path/'settings.json',tmp_path/'captures')
        async with TestClient(TestServer(create_app(service, token=TOKEN))) as client:
            ws, headers = await login(client)
            for endpoint,payload in [('layout',[]),('timing',{'enabled':'true'}),('mode',{'mode':'untrusted'})]:
                assert (await client.post('/api/'+endpoint,json=payload,headers=headers)).status == 400
            assert (await client.post('/api/media',data=b'not an image',headers=headers)).status == 400
            assert (await client.post('/api/media',data=b'x'*(8*1024*1024+1),headers=headers)).status == 413
            assert service.worker is None
            await ws.close()
    asyncio.run(run())


def test_short_code_pairs_a_phone_and_qr_requires_authentication(tmp_path):
    async def run():
        service = WallService(tmp_path/'settings.json',tmp_path/'captures')
        app = create_app(service, token=TOKEN, pairing_code='123456', phone_urls=['http://192.168.1.2:8765'])
        async with TestClient(TestServer(app)) as client:
            assert (await client.get('/api/access')).status == 401
            assert (await client.get('/api/access/0/qr.png')).status == 401
            assert (await client.post('/api/pair',json={'code':'654321'})).status == 401
            response = await client.post('/api/pair',json={'code':'123456'},headers={'Origin':'http://elsewhere.invalid'})
            assert response.status == 403
            response = await client.post('/api/pair',json={'code':'123456'})
            assert response.status == 200 and (await response.json())['token'] == TOKEN
            assert response.headers['Cache-Control'] == 'no-store'
            headers = {'Authorization':'Bearer '+TOKEN}
            data = await (await client.get('/api/access',headers=headers)).json()
            assert data == {'code':'123456','urls':['http://192.168.1.2:8765']}
            response = await client.get('/api/access/0/qr.png',headers=headers)
            assert response.status == 200
            assert (await response.read()).startswith(b'\x89PNG')
            assert (await client.get('/api/access/1/qr.png',headers=headers)).status == 404
            assert service.worker is None
    asyncio.run(run())


def test_short_code_guessing_is_bounded(tmp_path):
    async def run():
        service = WallService(tmp_path/'settings.json',tmp_path/'captures')
        async with TestClient(TestServer(create_app(service,token=TOKEN,pairing_code='123456'))) as client:
            for _ in range(5):
                assert (await client.post('/api/pair',json={'code':'654321'})).status == 401
            assert (await client.post('/api/pair',json={'code':'123456'})).status == 429
            assert (await client.get('/api/state',headers={'Authorization':'Bearer '+TOKEN})).status == 200
    asyncio.run(run())


def test_individual_panel_controls_require_ownership_and_publish_saved_changes(tmp_path):
    async def run():
        service = WallService(tmp_path/'settings.json',tmp_path/'captures')
        async with TestClient(TestServer(create_app(service,token=TOKEN))) as client:
            ws, headers = await login(client)
            layout = {'version':1,'panels':[
                {'device':name,'x':0,'y':i*16,'rotation':0} for i,name in enumerate(('top','bottom'))]}
            assert (await client.post('/api/layout',json=layout,headers=headers)).status == 200
            payload = {'device':'top','action':'disconnect'}
            assert (await client.post('/api/panel',json=payload)).status == 401
            assert (await client.post('/api/panel',json=payload,headers={'Authorization':'Bearer '+TOKEN})).status == 409
            response = await client.post('/api/panel',json=payload,headers=headers)
            assert response.status == 200
            state = await response.json()
            assert state['excluded_panels'] == ['top'] and state['size'] == [64,16]
            assert state['controller'] == headers['X-LED-Controller']
            while (await receive_json(ws,'state'))['excluded_panels'] != ['top']:
                pass
            for name in ('top','bottom'):
                response = await client.post('/api/panel',json={'device':name,'action':'remove'},headers=headers)
                assert response.status == 200
            assert (await response.json())['layout'] is None and service.worker is None
            await ws.close()
    asyncio.run(run())
