"""Snake rules and original 64x16 RGB artwork; no Bluetooth or windowing."""

from collections import deque
from dataclasses import dataclass
from io import BytesIO
import random

from PIL import Image, ImageDraw

from led_matrix_hacker.graphics import DIGITS

WIDTH, HEIGHT = 32, 8
DIRECTIONS = {'up': (0,-1), 'down': (0,1), 'left': (-1,0), 'right': (1,0)}


@dataclass(frozen=True)
class Board:
    body: tuple[tuple[int, int], ...]
    food: tuple[int, int] | None
    phase: str
    score: int


class Snake:
    def __init__(self, *, rng=None):
        self.rng = rng or random.Random()
        self.restart()

    def restart(self):
        self.body = [(8,4), (7,4), (6,4), (5,4)]
        self.direction = 'right'
        self.turns = deque()
        self.phase = 'ready'
        self.score = 0
        self.food = self._food()

    def _food(self):
        occupied = set(self.body)
        free = [(x,y) for y in range(HEIGHT) for x in range(WIDTH) if (x,y) not in occupied]
        return self.rng.choice(free) if free else None

    def toggle_pause(self):
        if self.phase in ('ready','paused'): self.phase = 'running'
        elif self.phase == 'running': self.phase = 'paused'

    def pause(self):
        if self.phase == 'running': self.phase = 'paused'

    def turn(self, direction):
        if direction not in DIRECTIONS or self.phase not in ('running','ready','paused'):
            return False
        previous = self.turns[-1] if self.turns else self.direction
        dx,dy = DIRECTIONS[direction]
        px,py = DIRECTIONS[previous]
        if direction == previous or (dx == -px and dy == -py) or len(self.turns) >= 2:
            return False
        self.turns.append(direction)
        return True

    def tick(self):
        if self.phase != 'running': return False
        if self.turns: self.direction = self.turns.popleft()
        dx,dy = DIRECTIONS[self.direction]
        x,y = self.body[0]
        head = (x+dx,y+dy)
        growing = head == self.food
        occupied = self.body if growing else self.body[:-1]
        if not (0 <= head[0] < WIDTH and 0 <= head[1] < HEIGHT) or head in occupied:
            self.phase = 'over'
            self.turns.clear()
            return True
        self.body.insert(0,head)
        if growing:
            self.score += 1
            self.food = self._food()
            if self.food is None: self.phase = 'won'
        else:
            self.body.pop()
        return True

    def snapshot(self):
        return Board(tuple(self.body),self.food,self.phase,self.score)


def render_board(board):
    image = Image.new('RGB',(64,16),'black')
    draw = ImageDraw.Draw(image)
    if board.food is not None:
        x,y = board.food
        draw.rectangle((x*2,y*2,x*2+1,y*2+1),fill=(255,48,64))
    for index,(x,y) in enumerate(board.body):
        color = (160,255,208) if index == 0 else (0,192,96)
        if board.phase == 'over': color = (255,96,64) if index == 0 else (96,24,16)
        draw.rectangle((x*2,y*2,x*2+1,y*2+1),fill=color)
    if board.phase == 'paused':
        draw.rectangle((29,5,30,10),fill=(255,192,0))
        draw.rectangle((33,5,34,10),fill=(255,192,0))
    if board.phase in ('over','won'):
        draw.rectangle((25,5,38,11),fill='black')
        for offset,letter in enumerate('END'):
            for y,bits in enumerate(DIGITS[letter],6):
                for x,bit in enumerate(bits,26+offset*4):
                    if bit == '1': image.putpixel((x,y),(255,255,255))
    return image


def board_png(board):
    output = BytesIO()
    render_board(board).save(output,format='PNG',optimize=True)
    return output.getvalue()
