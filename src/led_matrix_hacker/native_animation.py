"""Prepare synchronized native-size GIFs from one fitted wall animation."""

from bisect import bisect_right
from dataclasses import dataclass
from io import BytesIO
import math

from PIL import Image

from .wall import Layout


@dataclass(frozen=True)
class NativeAnimation:
    layout: Layout
    gifs: tuple[bytes, ...]
    frame_count: int
    duration_ms: int


@dataclass(frozen=True)
class NativePlayback:
    animation: NativeAnimation
    generation: int = 0

    @property
    def layout(self):
        return self.animation.layout


def prepare_animation(frames, deadlines, layout):
    """Keep wall geometry and one common timeline, including static panel halves.

    The tested native decoder appears to have a ~30-ms delay floor. Sample faster
    input on a 30-ms timeline instead of slowing the whole animation down. Slower
    and variable source timings are preserved to GIF centisecond precision.
    """
    if not frames or len(frames) != len(deadlines):
        raise ValueError('Animation needs matching frames and frame deadlines.')
    if len(frames) > 1000 or len(frames)*layout.size[0]*layout.size[1] > 16_000_000:
        raise ValueError('Animation is too large; use fewer frames or a smaller canvas.')
    if any(frame.size != layout.size for frame in frames):
        raise ValueError('Fit the animation to the whole wall before splitting it.')
    if any(not math.isfinite(value) for value in deadlines):
        raise ValueError('Animation frame deadlines must be finite.')
    ends = [round(value*1000/10)*10 for value in deadlines]
    durations = [end-start for start, end in zip([0]+ends[:-1], ends)]
    if any(duration <= 0 for duration in durations):
        raise ValueError('Animation frame deadlines must increase.')
    duration_ms = max(30, ends[-1])
    if min(durations) < 30:
        starts = list(range(0, duration_ms-29, 30))
        indices = [min(len(frames)-1, bisect_right(ends, start)) for start in starts]
        durations = [30]*len(starts)
        durations[-1] = duration_ms-starts[-1]
    else:
        indices = list(range(len(frames)))

    # Fit happens before this function: crop hidden bezel pixels and undo each
    # physical mounting rotation using the same mapping as live wall content.
    panels = [[] for _ in layout.tiles]
    for index in indices:
        for destination, image in zip(panels, layout.split(frames[index])):
            destination.append(image)
    gifs = []
    for panel in panels:
        # A shared palette per panel avoids frame-to-frame palette flicker.
        count = len(panel)
        samples = Image.new('RGB', (64, 16*count))
        for sample in range(count):
            samples.paste(panel[sample], (0, sample*16))
        palette = samples.quantize(colors=256, dither=Image.Dither.NONE)
        encoded = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in panel]
        output = BytesIO()
        encoded[0].save(output, format='GIF', save_all=True, append_images=encoded[1:],
                        duration=durations, loop=0, disposal=2, optimize=False,
                        palette=palette.getpalette())
        data = output.getvalue()
        if len(data) > 2*1024*1024:
            raise ValueError('A panel GIF exceeds 2 MiB; use a shorter or simpler animation.')
        # Pillow may merge identical frames on one half. Its encoded loop must
        # still exactly match every other panel, including a completely still half.
        with Image.open(BytesIO(data)) as gif:
            total = 0
            for index in range(gif.n_frames):
                gif.seek(index)
                total += gif.info.get('duration', 0)
            if gif.size != (64, 16) or total != duration_ms:
                raise ValueError('Panel GIF encoding changed the shared animation timeline.')
        gifs.append(data)
    return NativeAnimation(layout, tuple(gifs), len(indices), duration_ms)


def animation_plan(data):
    """Use the verified temporary 0x65 GIF preview/restart destination."""
    from pypixelcolor.commands.send_image import send_image_hex

    plan = send_image_hex(data.hex(), '.gif', save_slot=0x65)
    plan.windows = list(plan.windows)
    for window in plan.windows:
        if window.data[2:4] != b'\x03\x00' or window.data[14] != 0x65:
            raise ValueError('Unexpected GIF upload header.')
    restart = b'\x0f\x00'+plan.windows[0].data[2:15]
    return plan, restart
