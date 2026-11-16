"""STARFALL: finite side-scrolling campaign and original 64x16 RGB art."""

from dataclasses import dataclass
from io import BytesIO
import math

from PIL import Image, ImageDraw

from led_matrix_hacker.graphics import DIGITS

DT = .05
SPRITES = {
    'ship': ('10000','11100','11111','11100','10000'),
    'drone': ('0110','1111','0110'),
    'weaver': ('10101','01110','11111','01110','10101'),
    'gunner': ('11111','10101','11111','01010','10001'),
    'boss': ('001111100','011111110','110101011','111111111','110000011',
             '111111111','110101011','011111110','001111100'),
    'twin': ('111','010','010'),
    'rapid': ('110','111','101'),
}
COLORS = {'ship':(128,240,255),'drone':(64,224,96),'weaver':(224,64,224),
          'gunner':(255,160,32),'boss':(224,64,96),'twin':(64,224,255),'rapid':(255,224,32)}
STATS = {'drone':(1,6.0,100),'weaver':(2,5.5,180),'gunner':(3,4.5,250)}
SPAWNS = tuple((base+t,kind,y) for base in (0,17,34) for t,kind,y in
               ((1,'drone',3),(3.5,'weaver',8),(6,'gunner',5),
                (9,'drone',11),(12,'weaver',2),(14.5,'gunner',9)))
FONT = {**DIGITS,
    ' ':('000',)*5,'A':('010','101','111','101','101'),
    'B':('110','101','110','101','110'),'H':('101','101','111','101','101'),
    'I':('111','010','010','010','111'),'L':('100','100','100','100','111'),
    'O':('111','101','101','101','111'),'P':('111','101','111','100','100'),
    'R':('110','101','110','101','101'),'S':('111','100','111','001','111'),
    'T':('111','010','010','010','010'),'U':('101','101','101','101','111'),
    'W':('101','101','111','111','101'),'Y':('101','101','010','010','010')}


@dataclass
class Enemy:
    kind: str
    x: float
    y: float
    hp: int
    base_y: float = 5
    age: float = 0
    fire_wait: float = 1.8


@dataclass
class Shot:
    x: float
    y: float
    vx: float
    vy: float = 0
    hostile: bool = False


@dataclass
class Pickup:
    kind: str
    x: float
    y: float


@dataclass(frozen=True)
class Flight:
    phase: str
    score: int
    lives: int
    x: int
    y: int
    time: float
    immune: bool
    twin: bool
    rapid: bool
    enemies: tuple
    shots: tuple
    pickups: tuple
    explosions: tuple
    boss: tuple | None


def overlap(a,b):
    x,y,w,h = a
    xx,yy,ww,hh = b
    return x < xx+ww and x+w > xx and y < yy+hh and y+h > yy


class Shooter:
    def __init__(self): self.restart()

    def restart(self):
        self.phase = 'ready'
        self.resume_phase = 'running'
        self.score,self.lives = 0,3
        self.x,self.y = 3.0,5.0
        self.time = 0.0
        self.immune = 0.0
        self.respawn_wait = 0.0
        self.twin,self.rapid = False,False
        self.enemies,self.shots,self.pickups,self.explosions = [],[],[],[]
        self.boss = None
        self.boss_age = 0.0
        self.boss_fire_wait = 1.5
        self.spawn_index = 0
        self.supplies = set()
        self.fire_wait = 0.0
        self.dx,self.dy,self.firing = 0,0,False

    @property
    def wave(self): return 4 if self.boss else min(3,1+int(self.time//17))

    def toggle_pause(self):
        if self.phase == 'ready': self.phase = 'running'
        elif self.phase == 'paused': self.phase = self.resume_phase
        elif self.phase in ('running','respawn'):
            self.resume_phase,self.phase = self.phase,'paused'

    def pause(self):
        if self.phase in ('running','respawn'): self.toggle_pause()

    def controls(self, dx, dy, firing):
        self.dx,self.dy = max(-1,min(1,dx)),max(-1,min(1,dy))
        self.firing = bool(firing)

    def spawn_enemy(self,kind,y):
        self.enemies.append(Enemy(kind,64,float(y),STATS[kind][0],float(y)))

    def supply(self,kind,x=35,y=None):
        owned = self.twin if kind == 'twin' else self.rapid
        if not owned and not any(p.kind == kind for p in self.pickups):
            self.pickups.append(Pickup(kind,float(x),self.y+1 if y is None else max(1,min(11,y))))

    def hit(self):
        if self.phase != 'running' or self.immune > 0: return
        self.lives -= 1
        self.shots.clear()
        self.phase = 'respawn' if self.lives else 'over'
        self.respawn_wait = 1.8
        self.x,self.y = 3.0,5.0
        # Clear enemies immediately beside the respawn point, without awarding points.
        self.enemies = [e for e in self.enemies if e.x > 16]

    def _fire(self):
        ys = (self.y+1,self.y+3) if self.twin else (self.y+2,)
        for y in ys: self.shots.append(Shot(self.x+5,y,25))
        self.fire_wait = .15 if self.rapid else .35

    def _enemy_fire(self,enemy):
        height = len(SPRITES[enemy.kind])
        y = enemy.y+height/2
        travel = max(.5,(enemy.x-self.x)/12)
        vy = max(-3,min(3,(self.y+2-y)/travel))
        self.shots.append(Shot(enemy.x-1,y,-12,vy,True))

    def _boss_step(self):
        boss = self.boss
        self.boss_age += DT
        boss.x = max(52,boss.x-5*DT)
        boss.y = 3+2*math.sin(self.boss_age*.8)
        if boss.x > 55: return
        self.boss_fire_wait -= DT
        if self.boss_fire_wait <= 1e-9:
            origin = boss.y+4
            aim = max(-2,min(2,(self.y+2-origin)/4))
            spread = 3 if boss.hp > 48 else 4
            for delta in (-spread,0,spread):
                self.shots.append(Shot(boss.x-1,origin,-11,aim+delta,True))
            self.boss_fire_wait = 1.5 if boss.hp > 48 else 1.0

    def _resolve_shots(self):
        survivors = []
        for shot in self.shots:
            if shot.hostile:
                survivors.append(shot)
                continue
            target = next((e for e in self.enemies if e.hp > 0 and
                overlap((shot.x,shot.y,2,1),(e.x,e.y,len(SPRITES[e.kind][0]),len(SPRITES[e.kind])))),None)
            if target:
                target.hp -= 1
                if target.hp == 0:
                    self.score += STATS[target.kind][2]
                    self.explosions.append((target.x,target.y,.3))
                    if target.kind == 'gunner':
                        self.supply('twin' if not self.twin else 'rapid',target.x,target.y)
                continue
            if self.boss and overlap((shot.x,shot.y,2,1),(self.boss.x,self.boss.y,9,9)):
                self.boss.hp -= 1
                if self.boss.hp <= 0:
                    self.score += 1500+self.lives*250
                    self.phase = 'won'
                    self.shots.clear()
                    return
                continue
            survivors.append(shot)
        self.shots = survivors
        self.enemies = [e for e in self.enemies if e.hp > 0]

    def tick(self):
        if self.phase == 'respawn':
            self.respawn_wait -= DT
            if self.respawn_wait <= 1e-9:
                self.phase,self.immune = 'running',2.5
            return
        if self.phase != 'running': return
        self.time += DT
        self.immune = max(0,self.immune-DT)
        scale = 1/math.sqrt(2) if self.dx and self.dy else 1
        self.x = max(1,min(15,self.x+self.dx*12*DT*scale))
        self.y = max(1,min(10,self.y+self.dy*12*DT*scale))
        self.fire_wait = max(0,self.fire_wait-DT)
        if self.firing and self.fire_wait <= 1e-9: self._fire()
        while self.spawn_index < len(SPAWNS) and SPAWNS[self.spawn_index][0] <= self.time+1e-9:
            _,kind,y = SPAWNS[self.spawn_index]
            self.spawn_enemy(kind,y)
            self.spawn_index += 1
        for when,kind in ((10,'twin'),(27,'rapid')):
            if self.time >= when and kind not in self.supplies:
                self.supply(kind)
                self.supplies.add(kind)
        for enemy in self.enemies:
            enemy.age += DT
            enemy.x -= STATS[enemy.kind][1]*DT
            if enemy.kind == 'weaver':
                enemy.y = max(1,min(10,enemy.base_y+2*math.sin(enemy.age*2.4)))
            if enemy.kind == 'gunner':
                enemy.fire_wait -= DT
                if enemy.fire_wait <= 1e-9:
                    self._enemy_fire(enemy)
                    enemy.fire_wait = 2.4
        self.enemies = [e for e in self.enemies if e.x > -6]
        if self.time >= 51 and self.spawn_index == len(SPAWNS) and not self.enemies and self.boss is None:
            self.boss = Enemy('boss',64,3,96)
        if self.boss: self._boss_step()
        for shot in self.shots:
            shot.x += shot.vx*DT
            shot.y += shot.vy*DT
        self.shots = [s for s in self.shots if -3 < s.x < 67 and .5 <= s.y <= 14.5]
        self._resolve_shots()
        if self.phase != 'running': return
        ship_box = (self.x+1,self.y+1,3,3)
        for pickup in self.pickups:
            pickup.x -= 7*DT
            if overlap(ship_box,(pickup.x,pickup.y,3,3)):
                if pickup.kind == 'twin': self.twin = True
                else: self.rapid = True
                pickup.x = -10
        self.pickups = [p for p in self.pickups if p.x > -4]
        self.explosions = [(x,y,left-DT) for x,y,left in self.explosions if left > DT][-4:]
        if self.immune <= 0:
            collision = any(overlap(ship_box,(s.x,s.y,2,1)) for s in self.shots if s.hostile)
            collision |= any(overlap(ship_box,(e.x,e.y,len(SPRITES[e.kind][0]),len(SPRITES[e.kind])))
                             for e in self.enemies)
            if collision: self.hit()

    def snapshot(self):
        return Flight(self.phase,self.score,self.lives,round(self.x),round(self.y),round(self.time,2),
            self.immune > 0,self.twin,self.rapid,
            tuple((e.kind,round(e.x),round(e.y),e.hp) for e in self.enemies),
            tuple((round(s.x),round(s.y),s.hostile) for s in self.shots),
            tuple((p.kind,round(p.x),round(p.y)) for p in self.pickups),
            tuple((round(x),round(y)) for x,y,_ in self.explosions),
            None if self.boss is None else (round(self.boss.x),round(self.boss.y),self.boss.hp))


def text(image,value,x,y,color=(240,240,240)):
    for index,character in enumerate(value):
        for row,bits in enumerate(FONT[character]):
            for column,bit in enumerate(bits):
                if bit == '1': image.putpixel((x+index*4+column,y+row),color)


def sprite(draw,kind,x,y,color=None):
    for row,bits in enumerate(SPRITES[kind]):
        for column,bit in enumerate(bits):
            if bit == '1': draw.point((x+column,y+row),fill=color or COLORS[kind])


def render_flight(board):
    image = Image.new('RGB',(64,16),'black')
    draw = ImageDraw.Draw(image)
    if board.phase in ('over','won','respawn'):
        banner = {'over':'OUT','won':'WIN','respawn':'HIT'}[board.phase]
        text(image,banner,2,1,(64,224,160) if board.phase == 'won' else (255,96,64))
        text(image,'L'+str(board.lives),51,1,(255,224,32))
        text(image,'PTS '+f'{board.score:06d}'[-6:],2,9)
        return image
    for index in range(10):
        x = (index*19-int(board.time*4))%64
        draw.point((x,1+(index*5)%14),fill=(0,0,32))
    for kind,x,y,_ in board.enemies: sprite(draw,kind,x,y)
    if board.boss:
        x,y,hp = board.boss
        sprite(draw,'boss',x,y,(255,128,32) if hp <= 48 else None)
        draw.line((46,0,62,0),fill=(48,8,16))
        draw.line((46,0,46+round(16*max(0,hp)/96),0),fill=(255,64,96))
    for x,y,hostile in board.shots:
        draw.line((x,y,x+1,y),fill=(255,96,32) if hostile else (255,240,128))
    for kind,x,y in board.pickups:
        sprite(draw,kind,x,y)
    for x,y in board.explosions:
        draw.line((x-1,y+1,x+3,y+1),fill=(255,160,32))
        draw.line((x+1,y-1,x+1,y+3),fill=(255,160,32))
    if not board.immune or int(board.time*8)%2 == 0:
        sprite(draw,'ship',board.x,board.y)
        draw.point((board.x-1,board.y+2),fill=(255,160,32))
    for life in range(board.lives): draw.point((life*2,0),fill=(64,224,255))
    if board.twin: draw.point((0,15),fill=COLORS['twin'])
    if board.rapid: draw.point((2,15),fill=COLORS['rapid'])
    if board.phase in ('ready','paused'):
        value = 'READY' if board.phase == 'ready' else 'PAUSE'
        draw.rectangle((21,4,42,11),fill='black')
        text(image,value,22,5)
    return image


def flight_png(board):
    output = BytesIO()
    render_flight(board).save(output,format='PNG',optimize=True)
    return output.getvalue()
