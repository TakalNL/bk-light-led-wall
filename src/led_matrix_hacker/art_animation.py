"""Prepare native-size downloaded art for bounded local playback comparisons."""

from io import BytesIO

from PIL import Image, ImageDraw

from .animation import _pixel_text


def inspect_gif(gif, *, capacity_test=False):
    size_limit = 2*1024*1024 if capacity_test else 256*1024
    count_limit = 4096 if capacity_test else 600
    if len(gif) > size_limit:
        raise ValueError("GIF exceeds the bounded size for this experiment.")
    with Image.open(BytesIO(gif)) as image:
        if image.format != "GIF" or image.size != (64, 16):
            raise ValueError("Expected a native 64x16 GIF.")
        if not 2 <= image.n_frames <= count_limit:
            raise ValueError(f"Expected 2..{count_limit} GIF frames for this experiment.")
        durations = []
        for index in range(image.n_frames):
            image.seek(index)
            duration = image.info.get("duration", 0)
            if not 20 <= duration <= 1000:
                raise ValueError("GIF frame durations must be 20..1000 ms.")
            durations.append(duration)
        return {"frames": image.n_frames, "encoded_durations_ms": sorted(set(durations)),
                "encoded_loop_ms": sum(durations), "encoded_loop_count": image.info.get("loop")}


def prepare_eyes_gif(source, *, frames=44, fps=10, capacity_test=False):
    """Keep art at native size; centre gap displays encoded fps and frame index.

    Repeat the source motion when more frames are requested. The changing
    counter makes these distinct decoded frames; it does not invent new poses.
    """
    count_limit = 4096 if capacity_test else 600
    if type(frames) is not int or not 2 <= frames <= count_limit:
        raise ValueError(f"Frame count must be an integer in 2..{count_limit}.")
    if type(fps) is not int or fps not in (10, 20, 25, 50):
        raise ValueError("Encoded fps must be 10, 20, 25 or 50.")
    sources = []
    with Image.open(BytesIO(source)) as image:
        if image.format != "GIF" or image.size != (64, 16) or not 2 <= image.n_frames <= 600:
            raise ValueError("Expected a native 64x16 source animation with 2..600 frames.")
        for index in range(image.n_frames):
            image.seek(index)
            rgba = image.convert("RGBA")
            black = Image.new("RGBA", image.size, (0, 0, 0, 255))
            sources.append(Image.alpha_composite(black, rgba).convert("RGB"))
    output_frames = []
    for index in range(frames):
        frame = sources[index % len(sources)].copy()
        draw = ImageDraw.Draw(frame)
        draw.rectangle((25, 0, 39, 15), fill="black")
        _pixel_text(frame, f"{fps:02d}", 28, 1)
        draw.line((27, 7, 37, 7), fill=(0, 0, 96))
        digits=max(3,len(str(frames)))
        _pixel_text(frame, f"{index + 1:0{digits}d}", 25 if digits==4 else 26, 10)
        output_frames.append(frame.quantize(colors=32, dither=Image.Dither.NONE))
    output = BytesIO()
    output_frames[0].save(output, format="GIF", save_all=True, append_images=output_frames[1:],
                          duration=1000 // fps, disposal=2, loop=0, optimize=True)
    gif = output.getvalue()
    metadata = inspect_gif(gif,capacity_test=capacity_test)
    if metadata['frames'] != frames:
        raise ValueError("GIF encoding merged requested frames; abort capacity comparison.")
    return gif


def prepare_rate_comparison(source):
    """Four 44-frame sections labelled 10/20/25/50, in one 176-frame loop."""
    frames, durations = [], []
    for fps in (10, 20, 25, 50):
        with Image.open(BytesIO(prepare_eyes_gif(source, fps=fps))) as image:
            for index in range(image.n_frames):
                image.seek(index)
                frames.append(image.convert("RGB").quantize(colors=32, dither=Image.Dither.NONE))
                durations.append(1000 // fps)
    output = BytesIO()
    frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2, optimize=True)
    gif = output.getvalue()
    metadata = inspect_gif(gif)
    if metadata['frames'] != 176 or metadata['encoded_loop_ms'] != 9240:
        raise ValueError("Rate comparison did not preserve its frame count and timings.")
    return gif
