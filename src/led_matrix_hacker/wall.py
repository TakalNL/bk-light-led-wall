"""A logical RGB canvas mapped onto independently connected 64x16 panels."""

from dataclasses import dataclass, replace
from io import BytesIO
import json

from PIL import Image, ImageDraw, ImageOps


@dataclass(frozen=True)
class Tile:
    device: str
    x: int = 0
    y: int = 0
    rotation: int = 0

    def __post_init__(self):
        if not isinstance(self.device, str) or not self.device.strip():
            raise ValueError('Each panel needs a Bluetooth identifier or exact unique name.')
        if any(type(v) is not int for v in (self.x, self.y, self.rotation)):
            raise ValueError('Panel coordinates and rotation must be integers.')
        if self.x < 0 or self.y < 0 or self.rotation not in (0, 90, 180, 270):
            raise ValueError('Use nonnegative coordinates and rotation 0, 90, 180 or 270.')

    @property
    def size(self):
        return (16, 64) if self.rotation in (90, 270) else (64, 16)

    @property
    def box(self):
        width, height = self.size
        return self.x, self.y, self.x + width, self.y + height


@dataclass(frozen=True)
class Layout:
    tiles: tuple[Tile, ...]

    def __post_init__(self):
        if not isinstance(self.tiles, tuple) or not 1 <= len(self.tiles) <= 16:
            raise ValueError('A layout needs 1 to 16 panels.')
        devices = [tile.device.strip().casefold() for tile in self.tiles]
        if len(set(devices)) != len(devices):
            raise ValueError('Each panel must have a different Bluetooth identifier.')
        if max(self.size) > 512:
            raise ValueError('The combined canvas must fit within 512x512 pixels.')
        for index, tile in enumerate(self.tiles):
            left, top, right, bottom = tile.box
            for other in self.tiles[:index]:
                x0, y0, x1, y1 = other.box
                if left < x1 and right > x0 and top < y1 and bottom > y0:
                    raise ValueError('Panel areas overlap. Move them apart in the layout.')

    @property
    def size(self):
        return max(t.box[2] for t in self.tiles), max(t.box[3] for t in self.tiles)

    def split(self, image):
        if image.size != self.size:
            raise ValueError(f'Expected a canvas of {self.size}, received {image.size}.')
        # Rotation describes clockwise physical mounting. Undo it for the upload.
        return tuple(image.convert('RGB').crop(tile.box).rotate(tile.rotation, expand=True)
                     for tile in self.tiles)

    @property
    def linear_spacing(self):
        """Return the axis and uniform gap for an ordered row/column, else None."""
        if len(self.tiles) < 2:
            return None
        for vertical in (True, False):
            positions = [tile.y if vertical else tile.x for tile in self.tiles]
            cross = [tile.x if vertical else tile.y for tile in self.tiles]
            lengths = [tile.size[1 if vertical else 0] for tile in self.tiles]
            gaps = [positions[i]-positions[i-1]-lengths[i-1] for i in range(1, len(positions))]
            if len(set(cross)) == 1 and len(set(gaps)) == 1 and gaps[0] >= 0:
                return vertical, gaps[0]
        return None

    def arranged(self, vertical, gap=0, *, origin=(0, 0)):
        if type(gap) is not int or not 0 <= gap <= 32:
            raise ValueError('Bezel compensation must be a whole number from 0 to 32 pixels.')
        tiles, offset = [], 0
        for tile in self.tiles:
            tiles.append(replace(tile, x=origin[0]+(0 if vertical else offset),
                                 y=origin[1]+(offset if vertical else 0)))
            offset += tile.size[1 if vertical else 0]+gap
        return Layout(tuple(tiles))

    def with_gap(self, gap):
        spacing = self.linear_spacing
        if spacing is None:
            raise ValueError('Gap control needs a vertical stack or horizontal row. Use panel positions for custom layouts.')
        first = self.tiles[0]
        return self.arranged(spacing[0], gap, origin=(first.x, first.y))

    def preview(self, image):
        """Show only physical pixels; virtual strips behind bezels stay black."""
        if image.size != self.size:
            raise ValueError('Preview size does not match the layout.')
        result = Image.new('RGB', self.size)
        for tile in self.tiles:
            result.paste(image.crop(tile.box), tile.box[:2])
        return result

    def to_dict(self):
        return {'version': 1, 'panels': [dict(device=t.device, x=t.x, y=t.y, rotation=t.rotation)
                                         for t in self.tiles]}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('Unsupported wall settings version.')
        panels = data.get('panels')
        if not isinstance(panels, list) or not 1 <= len(panels) <= 16:
            raise ValueError('Wall settings need 1 to 16 panels.')
        if any(not isinstance(p, dict) or set(p) != {'device', 'x', 'y', 'rotation'} for p in panels):
            raise ValueError('Invalid panel settings.')
        return cls(tuple(Tile(**p) for p in panels))


def load_layout(path):
    return Layout.from_dict(json.loads(path.read_text(encoding='utf-8')))


def save_layout(path, layout):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(layout.to_dict(), indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


@dataclass(frozen=True)
class CanvasFrame:
    size: tuple[int, int]
    pixels: bytes
    phase: str = 'wall'
    score: int = 0
    layout: Layout | None = None

    @classmethod
    def from_image(cls, image, *, layout=None):
        if layout is not None and image.size != layout.size:
            raise ValueError('Frame size does not match its panel layout.')
        return cls(image.size, image.convert('RGB').tobytes(), layout=layout)

    def image(self):
        return Image.frombytes('RGB', self.size, self.pixels)


def png_bytes(image):
    output = BytesIO()
    image.save(output, format='PNG', optimize=True)
    return output.getvalue()


def fit_image(image, size, mode='Fit'):
    rgba = image.convert('RGBA')
    background = Image.new('RGBA', rgba.size, (0, 0, 0, 255))
    image = Image.alpha_composite(background, rgba).convert('RGB')
    # Filter reductions to avoid aliasing in photos/large GIFs. Keep pixel art
    # crisp when expanding a small source onto the wall.
    resampling = (Image.Resampling.LANCZOS if image.width > size[0] or image.height > size[1]
                  else Image.Resampling.NEAREST)
    if mode == 'Fill':
        return ImageOps.fit(image, size, method=resampling)
    if mode == 'Stretch':
        return image.resize(size, resampling)
    if mode != 'Fit':
        raise ValueError('Choose Fit, Fill or Stretch.')
    result = Image.new('RGB', size)
    fitted = ImageOps.contain(image, size, method=resampling)
    result.paste(fitted, ((size[0]-fitted.width)//2, (size[1]-fitted.height)//2))
    return result


def load_media(path, size, mode='Fit'):
    """Decode GIF disposal/timing with Pillow, bounded to 48 MB of RGB frames."""
    from PIL import ImageSequence
    frames, deadlines, elapsed = [], [], 0.0
    with Image.open(path) as source:
        for index, frame in enumerate(ImageSequence.Iterator(source)):
            if index >= 1000 or (index+1)*size[0]*size[1] > 16_000_000:
                raise ValueError('Animation is too large; use fewer frames or a smaller canvas.')
            frames.append(fit_image(frame, size, mode))
            elapsed += max(20, frame.info.get('duration', 100))/1000
            deadlines.append(elapsed)
    return frames, deadlines


def identify_image(layout):
    image = Image.new('RGB', layout.size)
    draw = ImageDraw.Draw(image)
    colors = ('#40dfff', '#ff9c40', '#74ff80', '#ff60cf')
    for index, tile in enumerate(layout.tiles):
        x0, y0, x1, y1 = tile.box
        color = colors[index % len(colors)]
        draw.rectangle((x0, y0, x1-1, y1-1), outline=color)
        draw.text((x0+3, y0+1), str(index+1), fill=color)
        # A top-right marker makes physical rotation observable.
        draw.rectangle((x1-5, y0+2, x1-3, y0+4), fill='white')
    return image


def demo_image(size, step):
    """A moving ring crosses panel boundaries; grid lines expose alignment."""
    width, height = size
    image = Image.new('RGB', size, '#020610')
    draw = ImageDraw.Draw(image)
    for x in range(0, width, 8):
        draw.line((x, 0, x, height-1), fill='#102034')
    for y in range(0, height, 8):
        draw.line((0, y, width-1, y), fill='#102034')
    radius = max(4, min(width, height)//3)
    x, y = width//2, step % (height+radius*2)-radius
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline='#60ffc0', width=2)
    draw.line((0, step % height, width-1, step % height), fill='#ff6060')
    return image
