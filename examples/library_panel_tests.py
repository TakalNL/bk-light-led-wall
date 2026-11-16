"""Bounded panel tests using pinned pypixelcolor command builders and send_plan.

Install the project with pip install -e ".[experiments]". The library
connection is adapted for our verified Windows cache/MTU settings and tracing.
No library source files are modified. The clock query uses Berlin local time.
"""

import argparse
import asyncio
import hashlib
import logging
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont
from pypixelcolor.commands.send_image import send_image, send_image_hex
from pypixelcolor.commands.set_fun_mode import set_pixel
from pypixelcolor.commands.show_slot import show_slot

from led_matrix_hacker.experiments import Recorder
from led_matrix_hacker.animation import DIGITS
from led_matrix_hacker.library_link import library_connection


def game_scene(index=0, label='LIVE', *, pixel_hud=False, counter_digits=3):
    image = Image.new('RGB',(64,16),'black')
    draw = ImageDraw.Draw(image)
    draw.rectangle((0,0,63,15),outline=(0,0,96))
    draw.line((5,8,58,8),fill=(0,64,64))
    for x,y,color in [(0,0,'red'),(61,0,'green'),(0,13,'blue'),(61,13,'yellow')]:
        draw.rectangle((x,y,x+2,y+2),fill=color)
    if pixel_hud:
        glyphs={**DIGITS,
                'P':('111','101','111','100','100'),
                'G':('111','100','101','101','111'),
                'I':('111','010','010','010','111'),
                'X':('101','101','010','101','101')}
        for text,left in [(label,6),(f'{index:0{counter_digits}d}' if index else '',43)]:
            for position,character in enumerate(text):
                for y,bits in enumerate(glyphs[character],1):
                    for x,bit in enumerate(bits,left+4*position):
                        if bit=='1': image.putpixel((x,y),(255,255,255))
    else:
        draw.text((6,0),label,font=ImageFont.load_default(size=8),fill='white')
        if index:
            draw.text((43,0),f'{index:0{counter_digits}d}',font=ImageFont.load_default(size=8),fill='white')
    x = 3 + index % 56
    draw.rectangle((x,10,x+1,11),fill=(255,192,0))
    return image


def png_plan(image, *, indexed=False):
    output=BytesIO()
    if indexed:
        # Reduce antialiasing shades in the test HUD to fit a whole PNG command
        # in one acknowledged ATT write. This is an explicit format experiment.
        colors=[(0,0,0),(0,0,96),(0,64,64),(255,0,0),(0,128,0),
                (0,0,255),(255,255,0),(255,255,255),(255,192,0)]
        colors.extend((level,level,level) for level in (32,64,96,128,160,192,224))
        palette=Image.new('P',(1,1))
        palette.putpalette([channel for color in colors for channel in color])
        image=image.quantize(palette=palette,dither=Image.Dither.NONE)
    image.save(output,format='PNG',optimize=True,**({'bits':4} if indexed else {}))
    return send_image_hex(output.getvalue().hex(), '.png')


def pixel_motion_updates(previous, current):
    old={(3+previous%56+dx,10+dy) for dx in range(2) for dy in range(2)}
    new={(3+current%56+dx,10+dy) for dx in range(2) for dy in range(2)}
    return [(x,y,'000000') for x,y in sorted(old-new)] + [
        (x,y,'FFC000') for x,y in sorted(new-old)]


async def upload(link, args, record):
    data=args.input.read_bytes()
    if len(data)>2*1024*1024:
        raise ValueError('Input exceeds bounded 2 MiB experiment.')
    with Image.open(BytesIO(data)) as image:
        if image.size != (64,16) or image.format not in ('GIF','PNG'):
            raise ValueError('Expected verified native dimensions and PNG/GIF.')
        count=getattr(image,'n_frames',1)
        if count>4096:
            raise ValueError('GIF exceeds the bounded 4096-frame experiment.')
        durations=[]
        for index in range(count):
            image.seek(index)
            durations.append(image.info.get('duration',0))
    record('content',bytes=len(data),frames=count,encoded_duration_ms=sum(durations),
           sha256=hashlib.sha256(data).hexdigest(),save_slot=args.slot)
    # Omit device_info: input is already native-size and validated. This preserves
    # exact GIF bytes instead of upstream's optional resize/re-encode path.
    plan=send_image(args.input,save_slot=args.slot)
    _,elapsed,replies=await link.send(plan,response=not args.fast,timeout=args.upload_timeout)
    opcode=3 if args.input.suffix.lower()=='.gif' else 2
    if not replies or replies[-1] != bytes((5,0,opcode,0,3)):
        raise ValueError('No strict final completion reply for image.')
    record('upload_completed',seconds=round(elapsed,6),save_slot=args.slot,fast=args.fast)


async def paced_motion(link, args, record, info):
    partial=args.mode=='pixels'
    label=('PIX' if partial else 'PNG')+str(args.fps)
    if partial:
        await link.send(png_plan(game_scene(0,label,pixel_hud=args.pixel_hud),
                                 indexed=args.indexed_png),response=True)
    plans=[]
    if not partial:
        plans=[png_plan(game_scene(index,'END' if args.end_label and index==args.frames else label,
                                  pixel_hud=args.pixel_hud,counter_digits=max(3,len(str(args.frames)))),
                        indexed=args.indexed_png)
               for index in range(1,args.frames+1)]
    clock=asyncio.get_running_loop().time
    start=clock()
    previous=0
    completed=0
    record('motion_started',method=args.mode,fps=args.fps,frames=args.frames,
           indexed_png=args.indexed_png,
           pixel_hud=args.pixel_hud,
           planned_duration_seconds=args.frames/args.fps,
           maximum_lateness_ms=500/args.fps,
           response=not args.fast,partial_counter='final count only; moving ball is live' if partial else 'per frame')
    for index in range(1,args.frames+1):
        due=start+(index-1)/args.fps
        await asyncio.sleep(max(0,due-clock()))
        sent=clock()
        if sent-due>0.5/args.fps:
            record('motion_stopped_late',completed=completed,next_frame=index,
                   lateness_ms=round((sent-due)*1000,3))
            break
        first_write=link.client.write_count
        if partial:
            for x,y,color in pixel_motion_updates(previous,index):
                await link.send(set_pixel(x,y,color,device_info=info),response=not args.fast)
            previous=index
        else:
            _,_,replies=await link.send(plans[index-1],response=not args.fast)
            if replies[-1:] != [bytes.fromhex('0500020003')]:
                raise ValueError('Missing strict PNG frame reply.')
        completed=index
        record('motion_frame_completed',frame=index,seconds=round(clock()-sent,6),
               writes=link.client.write_count-first_write,
               start_seconds=round(sent-start,6),lateness_ms=round((sent-due)*1000,3))
    await asyncio.sleep(max(0,start+completed/args.fps-clock()))
    record('motion_completed',completed=completed,requested=args.frames,
           seconds=round(clock()-start,6),method=args.mode,fps=args.fps)
    if partial:
        # A known ordered query after all pixel submissions helps expose queued
        # transport work. Its response is not a timestamp of screen rendering.
        barrier_start=clock()
        await link.initialize(versions=False)
        seconds=clock()-barrier_start
        record('pixel_transport_barrier_completed',seconds=round(seconds,6))
        await asyncio.sleep(1)


async def pixel_overlay_probe(link, record, info):
    # A static patch isolates buffer/mode behavior from motion and scheduling.
    _,_,replies=await link.send(png_plan(game_scene(1,'PNG10',pixel_hud=True)))
    if replies[-1:] != [bytes.fromhex('0500020003')]:
        raise ValueError('Missing baseline PNG completion reply.')
    await asyncio.sleep(3)
    for y in range(10,13):
        for x in range(30,33):
            await link.send(set_pixel(x,y,'FF0000',device_info=info),response=True)
    record('pixel_overlay_patch_completed',x=30,y=10,width=3,height=3,
           expected='red block plus unchanged PNG border, HUD, corners and yellow square')


async def experiment(args, output):
    record=Recorder(output)
    record('experiment',name='pypixelcolor-'+args.mode,fast=args.fast,
           library_commit='c8cbaebca6df7797a7bcface8a1c4ca33e499973')
    try:
        async with library_connection(args.device,record,write_delay=args.write_delay,
                                      chunk_size=args.chunk_size) as link:
            info=await link.initialize()
            if args.mode=='upload':
                await upload(link,args,record)
                if args.settle:
                    record('settling_connected',seconds=args.settle)
                    await asyncio.sleep(args.settle)
            elif args.mode=='show-slot':
                await link.send(show_slot(args.slot))
                record('slot_selected',slot=args.slot)
            elif args.mode=='overlay':
                await pixel_overlay_probe(link,record,info)
            elif args.mode in ('pixel-add','pixel-erase'):
                x0,color=(40,'00FF00') if args.mode=='pixel-add' else (30,'000000')
                for y in range(10,13):
                    for x in range(x0,x0+3):
                        await link.send(set_pixel(x,y,color,device_info=info),response=True)
                record('pixel_patch_completed',x=x0,y=10,width=3,height=3,color=color)
            elif args.mode=='suite':
                for method,fps,frames,fast in [('stream',10,60,False),('stream',20,80,False),
                                              ('pixels',5,40,False),('pixels',20,120,True)]:
                    probe=SimpleNamespace(**vars(args))
                    probe.mode,probe.fps,probe.frames,probe.fast=method,fps,frames,fast
                    record('phase_started',method=method,fps=fps,fast=fast)
                    await paced_motion(link,probe,record,info)
                    record('phase_finished',method=method,fps=fps,fast=fast)
                    await asyncio.sleep(1)
            else:
                await paced_motion(link,args,record,info)
        record('disconnected')
        await asyncio.sleep(args.observe)
        record('finished',visual_result='awaiting_owner_observation')
    except BaseException as error:
        record('error',error_type=type(error).__name__,message=str(error))
        raise


def main():
    logging.basicConfig(level=logging.ERROR)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device')
    parser.add_argument('--mode',choices=['upload','stream','pixels','overlay','pixel-add',
                                        'pixel-erase','show-slot','suite'],required=True)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fast',action='store_true',
                        help='Unacknowledged writes; GIF and pixel-motion visual tests failed on this unit.')
    parser.add_argument('--indexed-png',action='store_true',
                        help='Reproduce the failed four-bit indexed-PNG probe (panel displayed black).')
    parser.add_argument('--pixel-hud',action='store_true',
                        help='Use a bitmap HUD while preserving RGB PNG encoding.')
    parser.add_argument('--end-label',action='store_true',
                        help='Label the final streamed frame END alongside its counter.')
    parser.add_argument('--write-delay',type=float,choices=[0,.005,.01,.02],default=0)
    parser.add_argument('--settle',type=int,choices=range(0,11),default=0)
    parser.add_argument('--upload-timeout',type=int,choices=[180,360],default=180)
    parser.add_argument('--chunk-size',type=int,choices=[244,500],default=244)
    parser.add_argument('--slot',type=int,choices=[0,1],default=0)
    parser.add_argument('--fps',type=int,choices=[5,10,15,20,30,40],default=10)
    parser.add_argument('--frames',type=int,default=60)
    parser.add_argument('--observe',type=int,choices=range(0,241),default=8)
    args=parser.parse_args()
    if not 1<=args.frames<=3000 or (args.mode=='upload' and args.input is None):
        parser.error('Use 1..3000 motion frames and supply --input for uploads.')
    if args.frames>300 and not (args.mode=='stream' and args.fps==10 and args.pixel_hud
                               and not args.fast and not args.indexed_png):
        parser.error('Long runs require --mode stream --fps 10 --pixel-hud with acknowledged RGB writes.')
    if args.mode=='show-slot' and args.slot==0:
        parser.error('Persistent selection test uses slot 1.')
    with args.output.open('x',encoding='utf-8') as output:
        asyncio.run(experiment(args,output))


if __name__=='__main__':
    main()
