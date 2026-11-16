"""Bounded host-streamed sprite experiment using verified PNG uploads."""

import asyncio
import time
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from pypixelcolor.commands.send_image import send_image_hex
from pypixelcolor.lib.transport.send_plan import SendPlan


EXPECTED_REPLY = bytes.fromhex("0500020003")
DIGITS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "/": ("001", "001", "010", "100", "100"),
    "E": ("111", "100", "111", "100", "111"),
    "N": ("101", "111", "111", "111", "101"),
    "D": ("110", "101", "101", "101", "110"),
}
SPRITE = (
    "00100100",
    "00011000",
    "00111100",
    "01111110",
    "11011011",
    "11111111",
    "10100101",
    "00100100",
)


@dataclass(frozen=True)
class SpriteFrame:
    index: int
    x: int
    png: bytes
    plan: SendPlan
    counter: str | None = None


def frame_count(fps, duration_seconds=10):
    if type(fps) is not int or fps not in (2, 5):
        raise ValueError("Only the bounded 2 or 5 fps experiments are supported.")
    if type(duration_seconds) is not int or duration_seconds not in (10, 60):
        raise ValueError("Only bounded 10 or 60 second experiments are supported.")
    return fps * duration_seconds


def _pixel_text(image, text, x, y):
    for character in text:
        for row, bits in enumerate(DIGITS[character]):
            for column, bit in enumerate(bits):
                if bit == "1":
                    image.putpixel((x + column, y + row), (255, 255, 255))
        x += 4


def build_sprite_frames(*, fps=2, frame_counter=False, duration_seconds=10):
    """Prepare ten-second sprite passes with one continuous optional counter."""
    count = frame_count(fps, duration_seconds)
    cycle_frames = fps * 10
    digits = len(str(count))
    frames = []
    for index in range(count):
        x = 1 + round((index % cycle_frames) * 53 / (cycle_frames - 1))
        image = Image.new("RGB", (64, 16), "black")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 63, 15), outline=(0, 0, 96))
        progress_y = 9 if frame_counter else 14
        draw.line((1, progress_y, x + 7, progress_y), fill=(0, 96, 0))
        for y, row in enumerate(SPRITE, start=1 if frame_counter else 4):
            for offset, pixel in enumerate(row):
                if pixel == "1":
                    image.putpixel((x + offset, y), (255, 192, 0))
        counter = f"{index + 1:0{digits}d}/{count:0{digits}d}" if frame_counter else None
        if counter:
            _pixel_text(image, counter, 2, 10)
        if index == count - 1:
            if counter:
                _pixel_text(image, "END", 2 + len(counter) * 4 + 4, 10)
            else:
                draw.text((3, 2), "END", font=ImageFont.load_default(size=10), fill="white")
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        png = buffer.getvalue()
        frames.append(SpriteFrame(index + 1, x, png, send_image_hex(png.hex(), '.png', save_slot=0), counter))
    return frames


async def stream_frames(link, frames, record, *, fps=2, duration_seconds=10,
                        clock=time.monotonic, sleep=asyncio.sleep):
    """One frame in flight; abort on bad reply or >half-period lateness.

    Deadlines are absolute to avoid accumulating drift. A slow connection stops
    playback instead of sending a burst to catch up. No partial-frame retries.
    """
    count = frame_count(fps, duration_seconds)
    interval = 1 / fps
    if len(frames) != count or [frame.index for frame in frames] != list(range(1, count + 1)):
        raise ValueError(f"This bounded experiment requires exactly {count} frames in order.")
    started = clock()
    record("playback_started", fps=fps, frames=count, planned_duration_seconds=duration_seconds,
           maximum_lateness_ms=interval * 500)
    async with asyncio.timeout(duration_seconds + 5):
        for offset, frame in enumerate(frames):
            due = started + offset * interval
            await sleep(max(0, due - clock()))
            sent_at = clock()
            late = sent_at - due
            if late > interval / 2:
                raise TimeoutError("Playback fell behind by more than half a frame period; stopping without catch-up.")
            record("animation_frame_started", frame=frame.index, x=frame.x,
                   visible_counter=frame.counter,
                   playback_seconds=round(sent_at - started, 6),
                   schedule_lateness_ms=round(late * 1000, 3))
            _, _, replies = await link.send(frame.plan, response=True, timeout=2)
            reply = replies[-1] if replies else b''
            record("animation_frame_reply", frame=frame.index, payload_hex=reply.hex(),
                   matches_reference_ack=reply == EXPECTED_REPLY,
                   request_reply_ms=round((clock() - sent_at) * 1000, 3))
            if reply != EXPECTED_REPLY:
                raise ValueError("Unexpected PNG reply; stopping before the next frame.")
        await sleep(max(0, started + count * interval - clock()))
    record("playback_completed", frames=count,
           duration_seconds=round(clock() - started, 6), visual_result="unverified")
