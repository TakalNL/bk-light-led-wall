"""Supervised pixel tests over one connection; control file advances each stage."""

import argparse
import asyncio
import logging
from pathlib import Path

from pypixelcolor.commands.set_fun_mode import set_pixel

from tools.experiments.library_panel_tests import game_scene
from led_matrix_hacker.recording import Recorder
from led_matrix_hacker.library_link import library_connection


def pixel_changes(before, after):
    return [(x,y,'%02X%02X%02X' % after.getpixel((x,y)))
            for y in range(16) for x in range(64)
            if before.getpixel((x,y)) != after.getpixel((x,y))]


async def wait_command(path, command, record):
    record('stage_ready',next_command=command)
    async with asyncio.timeout(600):
        while not path.exists() or path.read_text(encoding='utf-8-sig').strip()!=command:
            await asyncio.sleep(.25)
    record('stage_advanced',command=command)


async def patch(link, info, x0, color):
    for y in range(10,13):
        for x in range(x0,x0+3):
            await link.send(set_pixel(x,y,color,device_info=info),response=True)


async def run(args, output):
    record=Recorder(output)
    record('experiment',name='single-connection-native-pixels',fps=args.fps,frames=args.frames)
    try:
        async with library_connection(args.device,record,chunk_size=500) as link:
            info=await link.initialize()
            await patch(link,info,30,'FF0000')
            record('red_block_drawn')
            await wait_command(args.control,'add',record)
            await patch(link,info,40,'00FF00')
            record('green_block_added')
            await wait_command(args.control,'erase',record)
            await patch(link,info,30,'000000')
            record('red_block_erased')
            await wait_command(args.control,'baseline',record)
            previous=game_scene(0,'PIX'+str(args.fps),pixel_hud=True)
            # Draw the entire framebuffer explicitly, including black pixels.
            # This is coordinate drawing, not a ROM-clear/reset command.
            for y in range(16):
                for x in range(64):
                    color='%02X%02X%02X' % previous.getpixel((x,y))
                    await link.send(set_pixel(x,y,color,device_info=info),response=True)
                if y%4==3: record('baseline_progress',rows=y+1)
            record('pixel_baseline_drawn')
            await wait_command(args.control,'run',record)
            plans=[]
            for index in range(1,args.frames+1):
                current=game_scene(index,'PIX'+str(args.fps),pixel_hud=True)
                changes=pixel_changes(previous,current)
                plans.append([set_pixel(x,y,color,device_info=info) for x,y,color in changes])
                previous=current
            clock=asyncio.get_running_loop().time
            start=clock()
            completed=0
            record('motion_started',fps=args.fps,frames=args.frames,response=False)
            for index,updates in enumerate(plans,1):
                due=start+(index-1)/args.fps
                await asyncio.sleep(max(0,due-clock()))
                sent=clock()
                if sent-due>0.5/args.fps:
                    record('motion_stopped_late',completed=completed,next_frame=index,
                           lateness_ms=round((sent-due)*1000,3))
                    break
                for plan in updates: await link.send(plan,response=False)
                completed=index
                record('motion_frame_completed',frame=index,writes=len(updates),
                       seconds=round(clock()-sent,6),start_seconds=round(sent-start,6),
                       lateness_ms=round((sent-due)*1000,3))
            await asyncio.sleep(max(0,start+completed/args.fps-clock()))
            record('motion_completed',completed=completed,requested=args.frames,
                   seconds=round(clock()-start,6))
            barrier_start=clock()
            await link.initialize(versions=False)
            seconds=clock()-barrier_start
            record('pixel_transport_barrier_completed',seconds=round(seconds,6))
            await wait_command(args.control,'finish',record)
        record('finished')
    except BaseException as error:
        record('error',error_type=type(error).__name__,message=str(error))
        raise


def main():
    logging.basicConfig(level=logging.ERROR)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--control',type=Path,required=True)
    parser.add_argument('--fps',type=int,choices=[5,10,15,20],default=20)
    parser.add_argument('--frames',type=int,choices=range(1,301),default=200)
    args=parser.parse_args()
    if args.control.exists(): parser.error('Use a fresh control path.')
    with args.output.open('x',encoding='utf-8') as output:
        asyncio.run(run(args,output))


if __name__=='__main__': main()
