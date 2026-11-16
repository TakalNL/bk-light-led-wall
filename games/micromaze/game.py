"""MICROMAZE: an original, enemy-free 64x16 raycast maze."""

from dataclasses import dataclass
from io import BytesIO
import math

from PIL import Image, ImageDraw

DT = .05
SPEED = 1.65
TURN_SPEED = 1.65
RADIUS = .20
PLANE = .80  # Approximately 77 degrees horizontal field of view.
LEVEL = (
    '###############',
    '#.....#.......#',
    '#.###.#.#####.#',
    '#...#...#...#.#',
    '###.#####.#.#.#',
    '#...#.....#...#',
    '#.###.#####.#.#',
    '#.....#.....#.#',
    '#.#####.#####.#',
    '#.......#....E#',
    '###############',
)
EXIT = next((x,y) for y,row in enumerate(LEVEL) for x,c in enumerate(row) if c == 'E')


def solid(x, y):
    ix,iy = math.floor(x),math.floor(y)
    return not (0 <= iy < len(LEVEL) and 0 <= ix < len(LEVEL[0])) or LEVEL[iy][ix] == '#'


@dataclass(frozen=True)
class View:
    x: float
    y: float
    angle: float
    phase: str
    elapsed: float
    score: int = 0  # Shared panel-worker diagnostic interface.


class Maze:
    def __init__(self): self.restart()

    def restart(self):
        self.x,self.y,self.angle = 1.5,1.5,0.0
        self.phase = 'ready'
        self.elapsed = 0.0
        self.forward,self.turn,self.strafe = 0,0,0

    def controls(self, forward, turn, strafe=0):
        self.forward = max(-1,min(1,forward))
        self.turn = max(-1,min(1,turn))
        self.strafe = max(-1,min(1,strafe))

    def toggle_pause(self):
        if self.phase in ('ready','paused'): self.phase = 'running'
        elif self.phase == 'running': self.pause()

    def pause(self):
        if self.phase == 'running': self.phase = 'paused'
        self.controls(0,0,0)

    def fits(self, x, y):
        # A square footprint avoids squeezing through diagonal wall corners.
        return all(not solid(x+dx,y+dy) for dx in (-RADIUS,RADIUS) for dy in (-RADIUS,RADIUS))

    def tick(self):
        if self.phase != 'running': return
        self.elapsed += DT
        self.angle = (self.angle+self.turn*TURN_SPEED*DT) % math.tau
        cosine,sine = math.cos(self.angle),math.sin(self.angle)
        scale = SPEED*DT/max(1,math.hypot(self.forward,self.strafe))
        dx = (cosine*self.forward-sine*self.strafe)*scale
        dy = (sine*self.forward+cosine*self.strafe)*scale
        # Separate axes allow sliding along a wall without passing through it.
        if self.fits(self.x+dx,self.y): self.x += dx
        if self.fits(self.x,self.y+dy): self.y += dy
        if (math.floor(self.x),math.floor(self.y)) == EXIT:
            self.phase = 'won'
            self.controls(0,0,0)

    def snapshot(self):
        return View(self.x,self.y,self.angle,self.phase,self.elapsed)


@dataclass(frozen=True)
class Hit:
    distance: float
    x: int
    y: int
    side: int
    u: float


def cast_ray(x, y, dx, dy):
    """DDA wall hit. Unnormalised camera rays give perpendicular depth."""
    mx,my = math.floor(x),math.floor(y)
    delta_x = abs(1/dx) if dx else math.inf
    delta_y = abs(1/dy) if dy else math.inf
    step_x,step_y = (1 if dx >= 0 else -1),(1 if dy >= 0 else -1)
    side_x = ((mx+1-x) if dx >= 0 else (x-mx))*delta_x
    side_y = ((my+1-y) if dy >= 0 else (y-my))*delta_y
    for _ in range(128):
        if side_x < side_y:
            distance = side_x
            side_x += delta_x
            mx += step_x
            side = 0
        else:
            distance = side_y
            side_y += delta_y
            my += step_y
            side = 1
        if solid(mx+.5,my+.5):
            u = (y+distance*dy) if side == 0 else (x+distance*dx)
            return Hit(max(.01,distance),mx,my,side,u % 1)
    raise ValueError('Ray did not reach the level boundary')


# Distance bands keep colours and PNG sizes small; side shading makes corners legible.
WALLS = ((60,144,204),(196,112,64),(128,144,160))


def render_view(view):
    image = Image.new('RGB',(64,16),(12,16,28))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0,8,63,15),fill=(28,24,24))
    pixels = image.load()
    cosine,sine = math.cos(view.angle),math.sin(view.angle)
    depths = []
    for column in range(64):
        camera = (2*(column+.5)/64-1)*PLANE
        hit = cast_ray(view.x,view.y,cosine-sine*camera,sine+cosine*camera)
        depths.append(hit.distance)
        height = 16/hit.distance
        top,bottom = 8-height/2,8+height/2
        base = WALLS[min(2,max(0,hit.x)//5)]
        band = 1 if hit.distance < 2 else (.75 if hit.distance < 4 else .5)
        shade = band*(.7 if hit.side else 1)
        color = tuple(int(c*shade) for c in base)
        mortar = tuple(int(c*.65) for c in color)
        for row in range(max(0,math.ceil(top)),min(16,math.ceil(bottom))):
            v = (row+.5-top)/height
            # Two broad brick courses, with staggered vertical joints.
            joint = (hit.u+(.5 if v >= .5 else 0)) % 1 < .055
            pixels[column,row] = mortar if abs(v-.5) < .035 or joint else color
    _draw_exit(image,view,depths)
    # A tiny, quiet centre mark helps maintain bearing while turning.
    pixels[31,8] = (160,160,144)
    if view.phase == 'won':
        draw.rectangle((11,3,52,12),fill=(0,28,12))
        _text(draw,'EXIT',24,5,(96,255,144))
    return image


def _draw_exit(image, view, depths):
    cosine,sine = math.cos(view.angle),math.sin(view.angle)
    dx,dy = EXIT[0]+.5-view.x,EXIT[1]+.5-view.y
    depth = dx*cosine+dy*sine
    if depth <= .05: return
    lateral = -dx*sine+dy*cosine
    centre = 32+32*lateral/(PLANE*depth)
    width,height = (32*.65/(PLANE*depth)),16/depth
    left,top = centre-width/2,8-height/2
    pixels = image.load()
    for x in range(max(0,math.ceil(left)),min(64,math.ceil(left+width))):
        if depth >= depths[x]: continue
        u = (x+.5-left)/width
        for y in range(max(0,math.ceil(top)),min(16,math.ceil(top+height))):
            v = (y+.5-top)/height
            frame = u < .18 or u > .82 or v < .15
            pixels[x,y] = (64,255,112) if frame else (0,56,24)


FONT = {
    'E':('111','100','110','100','111'),
    'X':('101','101','010','101','101'),
    'I':('111','010','010','010','111'),
    'T':('111','010','010','010','010'),
}


def _text(draw, text, x, y, color):
    for char in text:
        for yy,row in enumerate(FONT[char]):
            for xx,bit in enumerate(row):
                if bit == '1': draw.point((x+xx,y+yy),fill=color)
        x += 4


def view_png(view):
    buffer = BytesIO()
    render_view(view).save(buffer,format='PNG',optimize=True)
    return buffer.getvalue()


def render_map(view):
    """Optional PC-only navigation aid. Never replaces the panel's 3D view."""
    scale = 14
    image = Image.new('RGB',(len(LEVEL[0])*scale,len(LEVEL)*scale),(16,24,32))
    draw = ImageDraw.Draw(image)
    for y,row in enumerate(LEVEL):
        for x,tile in enumerate(row):
            if tile == '#':
                draw.rectangle((x*scale,y*scale,(x+1)*scale-2,(y+1)*scale-2),fill=(60,76,92))
            elif tile == 'E':
                draw.rectangle((x*scale+2,y*scale+2,(x+1)*scale-3,(y+1)*scale-3),fill=(64,255,112))
    x,y = view.x*scale,view.y*scale
    draw.ellipse((x-3,y-3,x+3,y+3),fill=(255,224,96))
    draw.line((x,y,x+math.cos(view.angle)*10,y+math.sin(view.angle)*10),fill=(255,224,96),width=2)
    return image
