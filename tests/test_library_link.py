import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip('pypixelcolor')
from pypixelcolor.commands.send_image import _build_send_plan
from pypixelcolor.commands.set_fun_mode import set_pixel
from pypixelcolor.lib.transport.ack_manager import AckManager

from led_matrix_hacker.library_link import LibraryLink, TracedClient
from led_matrix_hacker.local_animation import build_numbered_gif



def test_upstream_set_pixel_is_an_independent_coordinate_update_without_ack():
    plan=set_pixel(32,8,'FFC000')
    assert plan.windows[0].data==bytes.fromhex('0a00050100ffc0002008')
    assert not plan.ack_policy.ack_per_window and not plan.ack_policy.ack_final


def test_upstream_fast_transport_captures_final_reply_and_records_false_response():
    records=[]
    async def run():
        payload=build_numbered_gif()
        plan=_build_send_plan(payload,True)
        packet=plan.windows[0].data
        class Raw:
            callback=None
            chunks=[]
            async def start_notify(self, char, callback):
                self.callback=callback
            async def write_gatt_char(self, char, data, *, response):
                assert response is False
                self.chunks.append(bytes(data))
                if sum(map(len,self.chunks))==len(packet):
                    self.callback(SimpleNamespace(uuid='notify'),bytes.fromhex('0500030003'))
        raw=Raw()
        record=lambda kind,**fields: records.append((kind,fields))
        client=TracedClient(raw,record)
        client.chunk_size=244
        client.without_response_limit=244
        ack=AckManager()
        await client.start_notify('notify',ack.make_notify_handler())
        link=LibraryLink(client,ack,record)
        result,_,replies=await link.send(plan,response=False)
        assert result.success and replies==[bytes.fromhex('0500030003')]
        assert b''.join(raw.chunks)==packet
    asyncio.run(run())
    assert sum(kind=='library_notification' for kind,_ in records)==1


def test_pixel_motion_changes_only_ball_strip_and_preserves_scene_outside():
    from examples.library_panel_tests import game_scene, pixel_motion_updates
    image=game_scene(0,'PIX30')
    original=image.copy()
    for index in range(1,121):
        updates=pixel_motion_updates(index-1,index)
        assert len(updates)==(8 if index%56==0 else 4)
        for x,y,color in updates:
            assert 3<=x<=59 and y in (10,11)
            image.putpixel((x,y),tuple(bytes.fromhex(color)))
        expected={(3+index%56+dx,10+dy) for dx in range(2) for dy in range(2)}
        assert {(x,y) for x in range(3,60) for y in (10,11)
                if image.getpixel((x,y))==(255,192,0)}==expected
    assert image.crop((0,0,64,10)).tobytes()==original.crop((0,0,64,10)).tobytes()
    assert image.crop((0,12,64,16)).tobytes()==original.crop((0,12,64,16)).tobytes()


def test_indexed_live_pngs_fit_one_500_byte_write_with_distinct_counters():
    from io import BytesIO
    from PIL import Image
    from examples.library_panel_tests import game_scene, png_plan
    decoded=set()
    for index in range(1,301):
        scene=game_scene(index,'PNG20')
        plan=png_plan(scene,indexed=True)
        assert len(plan.windows)==1 and len(plan.windows[0].data)<=500
        with Image.open(BytesIO(plan.windows[0].data[15:])) as image:
            assert image.size==(64,16) and image.format=='PNG'
            rgb=image.convert('RGB')
            for point in ((0,0),(63,0),(0,15),(63,15),(0,8),(20,8),
                          (3+index%56,10)):
                assert rgb.getpixel(point)==scene.getpixel(point)
            decoded.add(rgb.tobytes())
    assert len(decoded)==300


def test_bitmap_hud_rgb_live_frames_fit_one_write_without_image_changes():
    from io import BytesIO
    from PIL import Image
    from examples.library_panel_tests import game_scene, png_plan
    decoded=set()
    for index in range(1,301):
        scene=game_scene(index,'PNG20',pixel_hud=True)
        packet=png_plan(scene).windows[0].data
        assert len(packet)<=500
        with Image.open(BytesIO(packet[15:])) as image:
            assert image.mode=='RGB' and image.size==(64,16)
            assert image.tobytes()==scene.tobytes()
            decoded.add(image.tobytes())
    assert len(decoded)==300


def test_native_deltas_reconstruct_motion_and_counter_without_static_changes():
    from examples.library_panel_tests import game_scene
    from examples.pixel_session import pixel_changes
    actual=game_scene(0,'PIX20',pixel_hud=True)
    for index in range(1,201):
        expected=game_scene(index,'PIX20',pixel_hud=True)
        changes=pixel_changes(actual,expected)
        assert 0<len(changes)<64
        for x,y,color in changes:
            assert (43<=x<=53 and 1<=y<=5) or (3<=x<=59 and 10<=y<=11)
            actual.putpixel((x,y),tuple(bytes.fromhex(color)))
        assert actual.tobytes()==expected.tobytes()


def test_five_minute_rgb_counter_stays_inside_border_and_one_write():
    from io import BytesIO
    from PIL import Image
    from examples.library_panel_tests import game_scene, png_plan
    reference=game_scene(0,'PNG10',pixel_hud=True,counter_digits=4)
    decoded=set()
    for index in range(1,3001):
        scene=game_scene(index,'END' if index==3000 else 'PNG10',
                         pixel_hud=True,counter_digits=4)
        packet=png_plan(scene).windows[0].data
        assert len(packet)<=500
        with Image.open(BytesIO(packet[15:])) as image:
            assert image.mode=='RGB' and image.tobytes()==scene.tobytes()
            for box in ((0,0,64,1),(0,15,64,16),(61,0,64,16)):
                assert image.crop(box).tobytes()==reference.crop(box).tobytes()
            decoded.add(image.tobytes())
    assert len(decoded)==3000
