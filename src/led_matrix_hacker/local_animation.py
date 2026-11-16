"""Small generated GIF for a source-backed panel-local playback experiment."""

from io import BytesIO

from PIL import Image

from .animation import build_sprite_frames


def build_numbered_gif():
    """Twenty 200ms frames, 01/20 through 20/20, with an infinite loop extension.

    A fixed eight-color palette preserves exact diagnostic pixels and limits
    file size. No transparency or external artwork. Device timing is unverified.
    """
    palette = Image.new("P", (1, 1))
    palette.putpalette([
        0, 0, 0, 0, 0, 96, 0, 96, 0, 255, 192, 0, 255, 255, 255,
        0, 0, 0, 0, 0, 0, 0, 0, 0,
    ])
    frames = []
    for source in build_sprite_frames(fps=2, frame_counter=True):
        with Image.open(BytesIO(source.png)) as image:
            frames.append(image.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE))
    output = BytesIO()
    frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:],
                   duration=200, loop=0, disposal=2, optimize=True)
    return output.getvalue()
