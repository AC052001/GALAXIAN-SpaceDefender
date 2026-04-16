"""
GALAXIAN - Space Defender  (Enhanced Edition)
A polished Pygame recreation of the classic arcade game.

Controls:
  Arrow Keys / A,D  - Move ship left / right
  Arrow Keys / W,S  - Move ship up / down
  SPACE              - Fire
  P                  - Pause
  ESC                - Back to title / Quit

Requirements:  pip install pygame
"""

import pygame
import random
import math
import sys

# ─── Initialization ───────────────────────────────────────────────────
pygame.init()

try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    SOUND_OK = True
except Exception:
    SOUND_OK = False

# ─── Constants ─────────────────────────────────────────────────────────
WIDTH, HEIGHT = 520, 720
FPS = 60

BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
RED        = (255, 40, 40)
YELLOW     = (255, 255, 0)
CYAN       = (0, 255, 255)
ORANGE     = (255, 180, 40)
GRAY       = (100, 100, 120)
GOLD       = (255, 215, 0)
DEEP_BLUE  = (5, 5, 25)

COLS = 10
FORM_SX = 40
FORM_SY = 38
FORM_OX = (WIDTH - COLS * FORM_SX) // 2 + FORM_SX // 2
FORM_OY = 95

PLAYER_Y_MIN = HEIGHT // 2          # upper bound for vertical movement
PLAYER_Y_MAX = HEIGHT - 45          # lower bound

TYPE_BASIC     = 0
TYPE_DIVER     = 1
TYPE_COMMANDER = 2
TYPE_FLAGSHIP  = 3

PW_SHIELD = 0
PW_DUAL   = 1
PW_RAPID  = 2

E_COLOR = {0: (100, 255, 100), 1: (80, 180, 255),
           2: (255, 80, 80),   3: (255, 60, 60)}
E_EDGE  = {0: WHITE, 1: (200, 230, 255), 2: YELLOW, 3: GOLD}
PTS_FORM = {0: 30, 1: 50, 2: 70, 3: 100}
PTS_DIVE = {0: 60, 1: 80, 2: 100, 3: 150}

# Dive pattern identifiers
DIVE_SWOOP   = 0
DIVE_SPIRAL  = 1
DIVE_ZIGZAG  = 2
DIVE_DIRECT  = 3
DIVE_WAVE    = 4

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GALAXIAN — Space Defender")
clock = pygame.time.Clock()


# ─── Utility ───────────────────────────────────────────────────────────
def _smooth(t):
    """Smoothstep interpolation."""
    return t * t * (3 - 2 * t)


def _smoother(t):
    """Quintic smoothstep (even smoother curves)."""
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(a, b, t):
    return a + (b - a) * t


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def _ease_in_quad(t):
    return t * t


# ─── Sound Helpers ─────────────────────────────────────────────────────
def _mk(freq, dur, vol=0.2, fend=None, wave='sine', sr=44100):
    if not SOUND_OK:
        return None
    try:
        n = int(sr * dur)
        buf = bytearray(n * 2)
        if fend is None:
            fend = freq
        for i in range(n):
            t = i / sr
            env = max(0.0, 1.0 - t / dur)
            f = freq + (fend - freq) * (t / dur)
            if wave == 'square':
                val = 1.0 if math.sin(2 * math.pi * f * t) > 0 else -1.0
            elif wave == 'saw':
                val = 2.0 * ((f * t) % 1.0) - 1.0
            else:
                val = math.sin(2 * math.pi * f * t)
            v = int(32767 * vol * env * val)
            v = max(-32768, min(32767, v))
            buf[i * 2] = v & 0xFF
            buf[i * 2 + 1] = (v >> 8) & 0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))
    except Exception:
        return None


def _play(s):
    if s and SOUND_OK:
        try:
            s.play()
        except Exception:
            pass


SND_SHOOT   = _mk(880, 0.07, 0.12, 1400)
SND_BOOM    = _mk(220, 0.22, 0.18, 55)
SND_DIE     = _mk(160, 0.5, 0.25, 35)
SND_DIVE    = _mk(300, 0.1, 0.06, 650)
SND_BONUS   = _mk(600, 0.3, 0.12, 1200)
SND_READY   = _mk(440, 0.15, 0.1, 880)
SND_POWERUP = _mk(500, 0.25, 0.15, 1500, 'square')
SND_COMBO   = _mk(700, 0.12, 0.1, 1100)
SND_HIT     = _mk(300, 0.08, 0.1, 100)


# ─── Star Field ────────────────────────────────────────────────────────
class Star:
    __slots__ = ('x', 'y', 'sp', 'br', 'sz', 'tw')

    def __init__(self, init=False):
        self.x = random.randint(0, WIDTH - 1)
        self.y = random.randint(0, HEIGHT - 1) if init else random.randint(-20, 0)
        self.sp = random.uniform(0.1, 1.5)
        self.br = random.randint(40, 220)
        self.sz = 1 if self.sp < 0.5 else (2 if self.sp < 1.0 else 3)
        self.tw = random.uniform(0, math.tau)

    def update(self):
        self.y += self.sp
        self.tw += 0.05
        if self.y >= HEIGHT:
            self.x = random.randint(0, WIDTH - 1)
            self.y = -1

    def draw(self, surf):
        b = int(self.br * (0.7 + 0.3 * math.sin(self.tw)))
        b = _clamp(b, 20, 255)
        c = (b, b, min(255, b + 20))
        if self.sz <= 1:
            surf.set_at((int(self.x), int(self.y)), c)
        else:
            pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.sz - 1)


# ─── Nebula Background ────────────────────────────────────────────────
class Nebula:
    def __init__(self):
        self.blobs = []
        for _ in range(5):
            self.blobs.append({
                'x': random.randint(0, WIDTH),
                'y': random.randint(0, HEIGHT),
                'r': random.randint(60, 150),
                'col': random.choice([
                    (15, 5, 30), (5, 10, 25), (20, 5, 15),
                    (5, 15, 20), (15, 10, 5)
                ]),
                'sp': random.uniform(0.02, 0.08)
            })

    def update(self):
        for b in self.blobs:
            b['y'] += b['sp']
            if b['y'] - b['r'] > HEIGHT:
                b['y'] = -b['r']
                b['x'] = random.randint(0, WIDTH)

    def draw(self, surf):
        for b in self.blobs:
            s = pygame.Surface((b['r'] * 2, b['r'] * 2), pygame.SRCALPHA)
            col = b['col']
            for ring in range(b['r'], 0, -3):
                alpha = int(12 * (ring / b['r']))
                pygame.draw.circle(s, (*col, alpha), (b['r'], b['r']), ring)
            surf.blit(s, (int(b['x'] - b['r']), int(b['y'] - b['r'])))


# ─── Particle System ──────────────────────────────────────────────────
class Particle:
    __slots__ = ('x', 'y', 'dx', 'dy', 'life', 'ml', 'col', 'sz', 'grav', 'fric')

    def __init__(self, x, y, col, gravity=0.04, friction=0.98):
        self.x, self.y = x, y
        a = random.uniform(0, math.tau)
        sp = random.uniform(0.5, 5.5)
        self.dx = math.cos(a) * sp
        self.dy = math.sin(a) * sp
        self.life = random.randint(10, 35)
        self.ml = self.life
        self.col = col
        self.sz = random.uniform(1.0, 4.0)
        self.grav = gravity
        self.fric = friction

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.dy += self.grav
        self.dx *= self.fric
        self.life -= 1

    def draw(self, surf):
        a = max(0.0, self.life / self.ml)
        r = min(255, int(self.col[0] * a + 200 * (1 - a) * 0.3))
        g = min(255, int(self.col[1] * a))
        b = min(255, int(self.col[2] * a))
        radius = max(1, int(self.sz * a))
        pygame.draw.circle(surf, (r, g, b), (int(self.x), int(self.y)), radius)


class ExplosionRing:
    __slots__ = ('x', 'y', 'radius', 'max_radius', 'col', 'life')

    def __init__(self, x, y, col, max_r=30):
        self.x, self.y = x, y
        self.radius = 2
        self.max_radius = max_r
        self.col = col
        self.life = 20

    def update(self):
        self.radius += (self.max_radius - self.radius) * 0.15
        self.life -= 1

    def draw(self, surf):
        if self.life > 0:
            r, g, b = self.col
            pygame.draw.circle(
                surf, (min(255, r), min(255, g), min(255, b)),
                (int(self.x), int(self.y)), int(self.radius), 2
            )


# ─── Score Popup ───────────────────────────────────────────────────────
class ScorePopup:
    __slots__ = ('x', 'y', 'txt', 'life', 'col', 'scale')

    def __init__(self, x, y, pts, col):
        self.x, self.y = x, y
        self.txt = str(pts)
        self.life = 50
        self.col = col
        self.scale = 1.5

    def update(self):
        self.y -= 0.7
        self.life -= 1
        if self.scale > 1.0:
            self.scale -= 0.05

    def draw(self, surf, font):
        if self.life > 0:
            c = (min(255, self.col[0] + 80),
                 min(255, self.col[1] + 80),
                 min(255, self.col[2] + 80))
            sz = max(18, int(22 * self.scale))
            fn = pygame.font.Font(None, sz)
            t = fn.render(self.txt, True, c)
            surf.blit(t, (int(self.x) - t.get_width() // 2, int(self.y)))


# ─── Combo Display ─────────────────────────────────────────────────────
class ComboDisplay:
    def __init__(self):
        self.combo = 0
        self.timer = 0
        self.max_combo = 0
        self.display_timer = 0

    def add(self):
        self.combo += 1
        self.timer = 90
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        self.display_timer = 60

    def reset(self):
        self.combo = 0
        self.timer = 0

    def update(self):
        if self.timer > 0:
            self.timer -= 1
            if self.timer <= 0:
                self.combo = 0
        if self.display_timer > 0:
            self.display_timer -= 1

    def get_multiplier(self):
        if self.combo < 3:
            return 1
        if self.combo < 6:
            return 2
        if self.combo < 10:
            return 3
        return 4

    def draw(self, surf):
        if self.combo >= 2 and self.display_timer > 0:
            fn = pygame.font.Font(None, 36)
            mult = self.get_multiplier()
            colors = [
                (255, 255, 255), (100, 255, 100),
                (255, 255, 0), (255, 100, 100)
            ]
            c = colors[min(mult - 1, 3)]
            txt = f"COMBO x{self.combo}  ({mult}x MULTIPLIER)"
            t = fn.render(txt, True, c)
            surf.blit(t, (WIDTH // 2 - t.get_width() // 2, 52))


# ─── Power-Up ──────────────────────────────────────────────────────────
class PowerUp:
    __slots__ = ('x', 'y', 'ptype', 'alive', 'dy', 'anim')

    COLORS = {PW_SHIELD: (100, 200, 255), PW_DUAL: (255, 200, 50),
              PW_RAPID: (100, 255, 100)}
    LABELS = {PW_SHIELD: 'S', PW_DUAL: 'D', PW_RAPID: 'R'}

    def __init__(self, x, y, ptype):
        self.x, self.y = x, y
        self.ptype = ptype
        self.alive = True
        self.dy = 1.5
        self.anim = 0

    def update(self):
        self.y += self.dy
        self.anim += 1
        if self.y > HEIGHT + 20:
            self.alive = False

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        c = self.COLORS[self.ptype]
        glow_r = 12 + int(3 * math.sin(self.anim * 0.15))
        pygame.draw.circle(surf, (c[0] // 3, c[1] // 3, c[2] // 3), (x, y), glow_r)
        pygame.draw.circle(surf, c, (x, y), 8)
        pygame.draw.circle(surf, WHITE, (x, y), 8, 1)
        fn = pygame.font.Font(None, 16)
        t = fn.render(self.LABELS[self.ptype], True, BLACK)
        surf.blit(t, (x - t.get_width() // 2, y - t.get_height() // 2))


# ─── Player Bullet ─────────────────────────────────────────────────────
class PlayerBullet:
    __slots__ = ('x', 'y', 'dx', 'alive', 'trail')

    def __init__(self, x, y, dx=0):
        self.x, self.y = x, y
        self.dx = dx
        self.alive = True
        self.trail = []

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)
        self.y -= 10
        self.x += self.dx
        self.x = _clamp(self.x, 0, WIDTH)
        if self.y < -12:
            self.alive = False

    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = (i + 1) / len(self.trail) if self.trail else 1
            r = int(100 * alpha)
            g = int(100 * alpha)
            b = int(255 * alpha)
            pygame.draw.circle(surf, (r, g, b),
                             (int(tx), int(ty)), max(1, int(2 * alpha)))
        ix, iy = int(self.x), int(self.y)
        pygame.draw.rect(surf, (160, 160, 255), (ix - 2, iy, 4, 14))
        pygame.draw.rect(surf, WHITE, (ix - 1, iy + 2, 2, 10))


# ─── Player ────────────────────────────────────────────────────────────
class Player:
    """The player's ship — now with 5 lives and full 2-D movement."""

    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 70
        self.speed = 5.0
        self.vspeed = 3.5            # vertical move speed
        self.lives = 5               # ◀ changed from 3 → 5
        self.bullets = []
        self.max_bullets = 1
        self.respawn = 0
        self.inv = 0
        self.alive = True
        self.anim = 0
        # Power-up timers
        self.shield = 0
        self.rapid_fire = 0
        self.dual_shot = 0
        self.shoot_cooldown = 0

    def update(self, keys):
        self.anim += 1
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        if self.shield > 0:
            self.shield -= 1
        if self.rapid_fire > 0:
            self.rapid_fire -= 1
        if self.dual_shot > 0:
            self.dual_shot -= 1
        self.max_bullets = 2 if self.dual_shot > 0 else 1

        if not self.alive:
            self.respawn -= 1
            if self.respawn <= 0 and self.lives > 0:
                self.alive = True
                self.inv = 150
                self.x = WIDTH / 2
                self.y = HEIGHT - 70
                self.bullets.clear()
            return

        if self.inv > 0:
            self.inv -= 1

        # Horizontal movement  (← → / A D)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += self.speed

        # Vertical movement    (↑ ↓ / W S)
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= self.vspeed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += self.vspeed

        self.x = _clamp(self.x, 20, WIDTH - 20)
        self.y = _clamp(self.y, PLAYER_Y_MIN, PLAYER_Y_MAX)

        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.alive]

    def shoot(self):
        if not self.alive:
            return
        if self.shoot_cooldown > 0:
            return
        if len(self.bullets) >= self.max_bullets:
            return
        cooldown = 6 if self.rapid_fire > 0 else 0
        self.shoot_cooldown = cooldown

        if self.dual_shot > 0:
            self.bullets.append(PlayerBullet(self.x - 8, self.y - 14))
            self.bullets.append(PlayerBullet(self.x + 8, self.y - 14))
        else:
            self.bullets.append(PlayerBullet(self.x, self.y - 14))
        _play(SND_SHOOT)

    def hit(self):
        if self.inv > 0 or not self.alive:
            return False
        if self.shield > 0:
            self.shield = 0
            _play(SND_HIT)
            return False
        self.alive = False
        self.lives -= 1
        self.bullets.clear()
        self.respawn = 120
        self.shield = 0
        self.rapid_fire = 0
        self.dual_shot = 0
        _play(SND_DIE)
        return True

    def apply_powerup(self, pw):
        _play(SND_POWERUP)
        if pw == PW_SHIELD:
            self.shield = 600
        elif pw == PW_DUAL:
            self.dual_shot = 480
        elif pw == PW_RAPID:
            self.rapid_fire = 480

    def draw(self, surf):
        if not self.alive:
            return
        if self.inv > 0 and (self.inv // 4) % 2:
            return

        x, y = int(self.x), int(self.y)

        # Engine flame
        fh = 6 + int(4 * abs(math.sin(self.anim * 0.3)))
        fw = 5 + int(3 * abs(math.sin(self.anim * 0.5)))
        pygame.draw.polygon(surf, ORANGE,
                          [(x - fw, y + 10), (x, y + 10 + fh), (x + fw, y + 10)])
        pygame.draw.polygon(surf, YELLOW,
                          [(x - fw + 2, y + 10), (x, y + 8 + fh), (x + fw - 2, y + 10)])

        # Ship body
        body = [
            (x, y - 16), (x - 5, y - 8), (x - 8, y + 2),
            (x - 18, y + 12), (x - 8, y + 6), (x - 4, y + 11),
            (x + 4, y + 11), (x + 8, y + 6), (x + 18, y + 12),
            (x + 8, y + 2), (x + 5, y - 8)
        ]
        pygame.draw.polygon(surf, (190, 210, 255), body)
        pygame.draw.polygon(surf, WHITE, body, 1)

        # Cockpit
        pygame.draw.ellipse(surf, CYAN, (x - 3, y - 10, 6, 9))
        pygame.draw.ellipse(surf, WHITE, (x - 2, y - 9, 4, 7))

        # Wing details
        pygame.draw.line(surf, (150, 170, 220), (x - 8, y + 2), (x - 16, y + 10), 1)
        pygame.draw.line(surf, (150, 170, 220), (x + 8, y + 2), (x + 16, y + 10), 1)

        # Shield bubble
        if self.shield > 0:
            sa = 100 + int(50 * math.sin(self.anim * 0.2))
            if self.shield < 120:
                if (self.shield // 8) % 2:
                    sa = 50
            ss = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.circle(ss, (100, 200, 255, sa), (22, 22), 20, 3)
            pygame.draw.circle(ss, (100, 200, 255, sa // 3), (22, 22), 18)
            surf.blit(ss, (x - 22, y - 22))

        # Active power-up dots
        indicators = []
        if self.dual_shot > 0:
            indicators.append((x - 22, y + 2, (255, 200, 50)))
        if self.rapid_fire > 0:
            indicators.append((x + 18, y + 2, (100, 255, 100)))
        for ix, iy, ic in indicators:
            pygame.draw.circle(surf, ic, (ix, iy), 3)


# ─── Enemy Bullet ──────────────────────────────────────────────────────
class EBullet:
    __slots__ = ('x', 'y', 'dx', 'dy', 'alive', 'trail')

    def __init__(self, x, y, tx, ty, sp=3.5):
        self.x, self.y = x, y
        d = math.hypot(tx - x, ty - y) or 1
        self.dx = (tx - x) / d * sp
        self.dy = (ty - y) / d * sp
        self.alive = True
        self.trail = []

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 3:
            self.trail.pop(0)
        self.x += self.dx
        self.y += self.dy
        if not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20):
            self.alive = False

    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = (i + 1) / len(self.trail) if self.trail else 1
            c = (int(180 * alpha), int(140 * alpha), int(30 * alpha))
            pygame.draw.circle(surf, c, (int(tx), int(ty)), max(1, int(2 * alpha)))
        ix, iy = int(self.x), int(self.y)
        pygame.draw.circle(surf, (255, 200, 50), (ix, iy), 3)
        pygame.draw.circle(surf, WHITE, (ix, iy), 1)


# ─── Enemy ─────────────────────────────────────────────────────────────
# Enemies now have 5 distinct dive patterns, dynamic speed curves,
# and more organic formation movement.

class Enemy:
    def __init__(self, row, col, et):
        self.row, self.col, self.et = row, col, et
        self.bfx = FORM_OX + col * FORM_SX
        self.bfy = FORM_OY + row * FORM_SY
        # Start off-screen for entrance animation
        self.x = float(self.bfx)
        self.y = -40.0 - row * 30 - random.uniform(0, 20)
        self.state = 'entering'
        self.alive = True
        self.dpath = []
        self.didx = 0
        self.dsp = 0
        self.rpath = []
        self.ridx = 0
        self.anim = 0
        self.at = random.randint(0, 11)      # stagger animation phase
        self.is_esc = False
        self.leader = None
        self.eox = 0
        self.eoy = 0
        self.scd = 0
        self.escort_bonus = False
        self.flash = 0
        self.dive_type = DIVE_SWOOP           # which pattern to use
        self.dive_speed_curve = []             # per-point speed multiplier
        # Unique phase offsets for organic formation bobbing
        self.phase_x = random.uniform(0, math.tau)
        self.phase_y = random.uniform(0, math.tau)
        self.freq_x = random.uniform(0.08, 0.16)
        self.freq_y = random.uniform(0.06, 0.13)
        self.amp_x = random.uniform(0.8, 2.2)
        self.amp_y = random.uniform(0.5, 1.5)

    @property
    def color(self):
        return E_COLOR[self.et]

    def pts(self, combo_mult=1):
        bonus = 50 if self.escort_bonus else 0
        base = (PTS_DIVE[self.et] if self.state == 'diving'
                else PTS_FORM[self.et] + bonus)
        return base * combo_mult

    # ── Dive triggering ────────────────────────────────────────────────
    def start_dive(self, px, py, escort=False, leader=None, dive_type=None):
        if self.state != 'formation':
            return
        self.state = 'diving'
        self.is_esc = escort
        self.leader = leader
        if escort and leader:
            self.eox = random.choice([-40, -30, 30, 40])
            self.eoy = random.randint(15, 35)
            self.escort_bonus = leader.et == TYPE_FLAGSHIP

        # Choose dive pattern
        if dive_type is not None:
            self.dive_type = dive_type
        else:
            self.dive_type = self._pick_dive_type()

        self.dpath, self.dive_speed_curve = self._build_dive(px, py)
        self.didx = 0.0  # float for smooth interpolation
        # Base dive speed varies by type (smooth float-based stepping)
        base_speeds = {TYPE_BASIC: 1.0, TYPE_DIVER: 1.5,
                       TYPE_COMMANDER: 1.2, TYPE_FLAGSHIP: 1.0}
        self.dsp = base_speeds.get(self.et, 2.0)
        self.scd = random.randint(10, 40)
        _play(SND_DIVE)

    def _pick_dive_type(self):
        """Select a dive pattern appropriate for this enemy type."""
        weights = {
            TYPE_BASIC:     [30, 10, 25, 20, 15],   # prefers swoop/zigzag
            TYPE_DIVER:     [15, 30, 10, 15, 30],    # prefers spiral/wave
            TYPE_COMMANDER: [20, 20, 20, 25, 15],    # balanced, more direct
            TYPE_FLAGSHIP:  [20, 25, 10, 30, 15],    # prefers direct/spiral
        }
        w = weights.get(self.et, [25, 25, 25, 25, 25])
        return random.choices(
            [DIVE_SWOOP, DIVE_SPIRAL, DIVE_ZIGZAG, DIVE_DIRECT, DIVE_WAVE],
            weights=w, k=1)[0]

    # ── Dive path builders ─────────────────────────────────────────────
    def _build_dive(self, px, py):
        """Dispatch to the appropriate path generator."""
        builders = {
            DIVE_SWOOP:  self._dive_swoop,
            DIVE_SPIRAL: self._dive_spiral,
            DIVE_ZIGZAG: self._dive_zigzag,
            DIVE_DIRECT: self._dive_direct,
            DIVE_WAVE:   self._dive_wave,
        }
        return builders[self.dive_type](px, py)

    def _make_speed_curve(self, n, accel_zone=0.4, decel_zone=0.15):
        """Create a speed multiplier curve that accelerates toward the player
        and decelerates past them."""
        curve = []
        for i in range(n):
            t = i / n
            if t < accel_zone:
                # Gentle ramp up
                u = t / accel_zone
                mult = 0.6 + 0.5 * _smooth(u)
            elif t > 1.0 - decel_zone:
                # Gentle slow down
                u = (t - (1.0 - decel_zone)) / decel_zone
                mult = 1.1 - 0.3 * _smooth(u)
            else:
                # Cruising speed
                mult = 1.0 + 0.08 * math.sin(t * 8)
            curve.append(mult)
        return curve

    # ─── Swooping dive (classic curved approach) ───────────────────────
    def _dive_swoop(self, px, py):
        sx, sy = self.x, self.y
        side = random.choice([-1, 1])
        w1x = sx + side * random.randint(60, 150)
        w1y = sy + random.randint(60, 130)
        w2x = px + random.randint(-60, 60)
        w2y = py - random.randint(20, 80)
        w3x = px + side * random.randint(100, 200)
        w3y = HEIGHT + 70
        pts = []
        N = 160
        for i in range(N):
            t = i / N
            if t < 0.30:
                u = t / 0.30
                x = sx + (w1x - sx) * _smoother(u)
                y = sy + (w1y - sy) * _smoother(u)
                x += math.sin(u * math.pi * 3) * side * 20
            elif t < 0.58:
                u = (t - 0.30) / 0.28
                x = w1x + (w2x - w1x) * _smoother(u)
                y = w1y + (w2y - w1y) * _smoother(u)
                x += math.sin(u * math.pi * 2) * side * 25
            else:
                u = (t - 0.58) / 0.42
                x = w2x + (w3x - w2x) * _smoother(u)
                y = w2y + (w3y - w2y) * _smoother(u)
                x += math.sin(u * math.pi) * side * 15
            pts.append((x, y))
        return pts, self._make_speed_curve(N, 0.35, 0.15)

    # ─── Spiral dive (tightens around player position) ─────────────────
    def _dive_spiral(self, px, py):
        sx, sy = self.x, self.y
        pts = []
        N = 180
        cx, cy = px, py - 40   # aim near player
        # Initial angle from enemy to player
        start_angle = math.atan2(cy - sy, cx - sx)
        start_dist = math.hypot(cx - sx, cy - sy) + 50
        spiral_dir = random.choice([-1, 1])
        rotations = random.uniform(1.5, 2.5)
        for i in range(N):
            t = i / N
            angle = start_angle + spiral_dir * t * rotations * math.pi * 2
            # Radius shrinks then grows
            if t < 0.55:
                u = t / 0.55
                radius = start_dist * (1.0 - 0.7 * _smooth(u))
            else:
                u = (t - 0.55) / 0.45
                radius = start_dist * 0.3 + start_dist * 2.0 * _smooth(u)
            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius
            # Ensure overall downward movement
            y = sy + (HEIGHT + 70 - sy) * t + math.sin(angle) * radius * 0.3
            pts.append((x, y))
        return pts, self._make_speed_curve(N, 0.3, 0.2)

    # ─── Zigzag dive (sharp direction changes) ─────────────────────────
    def _dive_zigzag(self, px, py):
        sx, sy = self.x, self.y
        pts = []
        N = 150
        side = random.choice([-1, 1])
        num_zigs = random.randint(4, 7)
        zig_width = random.randint(30, 70)
        # Create waypoints
        waypoints = [(sx, sy)]
        for z in range(num_zigs):
            progress = (z + 1) / num_zigs
            zx = px + side * zig_width * (1 if z % 2 == 0 else -1)
            zx += random.randint(-20, 20)
            zy = sy + (HEIGHT + 70 - sy) * progress
            waypoints.append((zx, zy))
        waypoints.append((px + side * random.randint(80, 160), HEIGHT + 70))
        # Interpolate through waypoints
        seg_len = N // (len(waypoints) - 1)
        for seg in range(len(waypoints) - 1):
            ax, ay = waypoints[seg]
            bx, by = waypoints[seg + 1]
            count = seg_len if seg < len(waypoints) - 2 else N - len(pts)
            for i in range(count):
                u = i / max(1, count)
                x = ax + (bx - ax) * _smoother(u)
                y = ay + (by - ay) * _smoother(u)
                pts.append((x, y))
        return pts[:N], self._make_speed_curve(len(pts[:N]), 0.3, 0.1)

    # ─── Direct dive (fast beeline toward player then curve away) ──────
    def _dive_direct(self, px, py):
        sx, sy = self.x, self.y
        pts = []
        N = 120
        side = random.choice([-1, 1])
        # Straight at player
        mid_x = px + random.randint(-15, 15)
        mid_y = py + random.randint(-10, 20)
        # Then sharp curve away
        end_x = px + side * random.randint(100, 220)
        end_y = HEIGHT + 70
        for i in range(N):
            t = i / N
            if t < 0.5:
                u = t / 0.5
                x = sx + (mid_x - sx) * _smoother(u)
                y = sy + (mid_y - sy) * _smoother(u)
            else:
                u = (t - 0.5) / 0.5
                x = mid_x + (end_x - mid_x) * _smoother(u)
                y = mid_y + (end_y - mid_y) * _smoother(u)
            pts.append((x, y))
        # Speed curve: smooth start, steady middle, smooth exit
        curve = []
        for i in range(N):
            t = i / N
            if t < 0.2:
                curve.append(0.5 + 0.7 * _smooth(t / 0.2))
            elif t < 0.6:
                curve.append(1.2)
            else:
                curve.append(1.2 - 0.3 * _smooth((t - 0.6) / 0.4))
        return pts, curve

    # ─── Wave dive (undulating sine pattern) ───────────────────────────
    def _dive_wave(self, px, py):
        sx, sy = self.x, self.y
        pts = []
        N = 170
        side = random.choice([-1, 1])
        wave_freq = random.uniform(3.0, 5.0)
        wave_amp_start = random.uniform(15, 30)
        wave_amp_end = random.uniform(40, 70)
        # Center line curves toward player then away
        cx1 = (sx + px) / 2 + side * random.randint(20, 60)
        cy1 = (sy + py) / 2 - random.randint(20, 60)
        for i in range(N):
            t = i / N
            # Center path
            if t < 0.55:
                u = t / 0.55
                cx = sx + (cx1 - sx) * _smooth(u)
                cy = sy + (cy1 - sy) * _smooth(u)
            else:
                u = (t - 0.55) / 0.45
                cx = cx1 + (px + side * 120 - cx1) * _smooth(u)
                cy = cy1 + (HEIGHT + 70 - cy1) * _smooth(u)
            # Sine wave offset grows over time
            amp = _lerp(wave_amp_start, wave_amp_end, t)
            offset_x = math.sin(t * wave_freq * math.pi * 2) * amp * side
            pts.append((cx + offset_x, cy))
        return pts, self._make_speed_curve(N, 0.4, 0.1)

    # ── Return path (gentle curve back to formation) ───────────────────
    def _makereturn(self, fdx):
        sx, sy = self.x, self.y
        tx = self.bfx + fdx
        ty = self.bfy
        pts = []
        # Arc upward with a slight horizontal sweep
        sweep = random.choice([-1, 1]) * random.randint(40, 100)
        apex_x = (sx + tx) / 2 + sweep
        apex_y = -60 - random.randint(0, 40)
        N1 = 20
        N2 = 30
        for i in range(N1):
            u = i / N1
            x = sx + (apex_x - sx) * _smoother(u)
            y = sy + (apex_y - sy) * _smoother(u)
            pts.append((x, y))
        for i in range(N2):
            u = i / N2
            x = apex_x + (tx - apex_x) * _smoother(u)
            y = apex_y + (ty - apex_y) * _smoother(u)
            pts.append((x, y))
        return pts

    # ── Update ─────────────────────────────────────────────────────────
    def update(self, px, py, fdx, global_tick=0):
        self.at += 1
        if self.at >= 12:
            self.at = 0
            self.anim = 1 - self.anim
        if self.flash > 0:
            self.flash -= 1

        if self.state == 'entering':
            self.y += 2.5
            self.x = _lerp(self.x, self.bfx + fdx, 0.05)
            if self.y >= self.bfy:
                self.y = self.bfy
                self.x = self.bfx + fdx
                self.state = 'formation'

        elif self.state == 'formation':
            # Organic bobbing — each enemy has unique phase/frequency
            self.x = (self.bfx + fdx
                      + math.sin(global_tick * self.freq_x + self.phase_x) * self.amp_x)
            self.y = (self.bfy
                      + math.sin(global_tick * self.freq_y + self.phase_y) * self.amp_y)
            # Subtle breathing: amplitude pulses slowly
            breath = 1.0 + 0.15 * math.sin(global_tick * 0.01 + self.row * 0.3)
            self.x = self.bfx + fdx + (self.x - self.bfx - fdx) * breath
            self.y = self.bfy + (self.y - self.bfy) * breath

        elif self.state == 'diving':
            if (self.is_esc and self.leader
                    and self.leader.alive
                    and self.leader.state == 'diving'):
                self.x = self.leader.x + self.eox
                self.y = self.leader.y + self.eoy
            else:
                self.is_esc = False
                # Smooth float-based path traversal with interpolation
                idx_int = int(self.didx)
                if idx_int < len(self.dive_speed_curve):
                    speed_mult = self.dive_speed_curve[idx_int]
                else:
                    speed_mult = 1.0
                step = self.dsp * speed_mult  # float step, no int() truncation
                self.didx += step
                idx_int = int(self.didx)
                frac = self.didx - idx_int
                path_len = len(self.dpath)
                if idx_int + 1 < path_len:
                    # Linear interpolation between consecutive points
                    p1 = self.dpath[idx_int]
                    p2 = self.dpath[idx_int + 1]
                    self.x = p1[0] + (p2[0] - p1[0]) * frac
                    self.y = p1[1] + (p2[1] - p1[1]) * frac
                elif idx_int < path_len:
                    self.x, self.y = self.dpath[idx_int]
                else:
                    self.state = 'returning'
                    self.rpath = self._makereturn(fdx)
                    self.ridx = 0.0
            if self.scd > 0:
                self.scd -= 1

        elif self.state == 'returning':
            # Smooth float-based return with interpolation
            self.ridx += 1.8  # smooth cruise back
            idx_int = int(self.ridx)
            frac = self.ridx - idx_int
            path_len = len(self.rpath)
            if idx_int + 1 < path_len:
                p1 = self.rpath[idx_int]
                p2 = self.rpath[idx_int + 1]
                self.x = p1[0] + (p2[0] - p1[0]) * frac
                self.y = p1[1] + (p2[1] - p1[1]) * frac
            elif idx_int < path_len:
                self.x, self.y = self.rpath[idx_int]
            else:
                self.state = 'formation'
                self.x = self.bfx + fdx
                self.y = self.bfy

    def try_shoot(self, px, py):
        """Attempt to fire — probability increases when closer to player."""
        if self.state != 'diving' or self.scd > 0:
            return None
        # Base chance; higher when near player horizontally
        dist = abs(self.x - px)
        base_prob = 0.02
        if dist < 60:
            base_prob = 0.05
        elif dist < 120:
            base_prob = 0.035
        if random.random() < base_prob:
            self.scd = random.randint(25, 65)
            speed = 3.0 + random.random() * 1.2
            # Add slight randomness to aim
            tx = px + random.randint(-25, 25)
            ty = py + random.randint(-10, 10)
            return EBullet(self.x, self.y + 12, tx, ty, speed)
        return None

    # ── Draw ───────────────────────────────────────────────────────────
    def draw(self, surf):
        if not self.alive:
            return
        x, y, f = int(self.x), int(self.y), self.anim
        c, h = E_COLOR[self.et], E_EDGE[self.et]
        if self.flash > 0:
            c = WHITE

        if self.et == TYPE_BASIC:
            p = ([(x, y-10), (x-12, y+5), (x-6, y+2), (x-4, y+10),
                  (x+4, y+10), (x+6, y+2), (x+12, y+5)] if f == 0 else
                 [(x, y-10), (x-10, y+8), (x-4, y+4), (x-4, y+10),
                  (x+4, y+10), (x+4, y+4), (x+10, y+8)])
            pygame.draw.polygon(surf, c, p)
            pygame.draw.polygon(surf, h, p, 1)
            pygame.draw.circle(surf, h, (x, y), 2)

        elif self.et == TYPE_DIVER:
            p = ([(x, y-12), (x-8, y-2), (x-14, y+7), (x-6, y+3),
                  (x-3, y+10), (x+3, y+10), (x+6, y+3), (x+14, y+7),
                  (x+8, y-2)] if f == 0 else
                 [(x, y-12), (x-6, y), (x-12, y+9), (x-4, y+5),
                  (x-3, y+10), (x+3, y+10), (x+4, y+5), (x+12, y+9),
                  (x+6, y)])
            pygame.draw.polygon(surf, c, p)
            pygame.draw.polygon(surf, h, p, 1)
            pygame.draw.circle(surf, (200, 230, 255), (x, y - 2), 3)

        elif self.et == TYPE_COMMANDER:
            p = ([(x, y-13), (x-10, y-4), (x-16, y+5), (x-8, y+1),
                  (x-6, y+11), (x+6, y+11), (x+8, y+1), (x+16, y+5),
                  (x+10, y-4)] if f == 0 else
                 [(x, y-13), (x-8, y-2), (x-14, y+7), (x-6, y+3),
                  (x-5, y+11), (x+5, y+11), (x+6, y+3), (x+14, y+7),
                  (x+8, y-2)])
            pygame.draw.polygon(surf, c, p)
            pygame.draw.polygon(surf, h, p, 1)
            pygame.draw.circle(surf, h, (x, y - 3), 3)

        elif self.et == TYPE_FLAGSHIP:
            bc = (255, 80 + 40 * f, 60) if f == 0 else (255, 120, 60)
            if self.flash > 0:
                bc = WHITE
            p = ([(x, y-14), (x-12, y-4), (x-18, y+5), (x-10, y+1),
                  (x-7, y+12), (x+7, y+12), (x+10, y+1), (x+18, y+5),
                  (x+12, y-4)] if f == 0 else
                 [(x, y-14), (x-10, y-2), (x-16, y+7), (x-8, y+3),
                  (x-6, y+12), (x+6, y+12), (x+8, y+3), (x+16, y+7),
                  (x+10, y-2)])
            pygame.draw.polygon(surf, bc, p)
            pygame.draw.polygon(surf, GOLD, p, 2)
            pygame.draw.circle(surf, GOLD, (x, y - 4), 4)
            pygame.draw.circle(surf, WHITE, (x, y - 4), 2)
            pygame.draw.line(surf, GOLD, (x - 12, y - 4), (x - 17, y - 13), 2)
            pygame.draw.line(surf, GOLD, (x + 12, y - 4), (x + 17, y - 13), 2)

        # Trail when diving
        if self.state == 'diving':
            tc = (c[0] // 4, c[1] // 4, c[2] // 4)
            for i in range(3):
                pygame.draw.circle(surf, tc,
                                 (x, y - 5 - i * 4), max(1, 3 - i))


# ─── Screen Shake ──────────────────────────────────────────────────────
class ScreenShake:
    def __init__(self):
        self.intensity = 0
        self.offset_x = 0
        self.offset_y = 0

    def shake(self, intensity=8):
        self.intensity = max(self.intensity, intensity)

    def update(self):
        if self.intensity > 0:
            self.offset_x = random.randint(
                -int(self.intensity), int(self.intensity))
            self.offset_y = random.randint(
                -int(self.intensity), int(self.intensity))
            self.intensity *= 0.85
            if self.intensity < 0.5:
                self.intensity = 0
                self.offset_x = 0
                self.offset_y = 0
        else:
            self.offset_x = 0
            self.offset_y = 0


# ─── Game ──────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.stars = [Star(True) for _ in range(150)]
        self.nebula = Nebula()
        self.shake = ScreenShake()
        self.combo = ComboDisplay()
        self.hi = 0
        self.global_tick = 0
        self._full_reset()

    def _full_reset(self):
        self.state = 'title'
        self.tick = 0
        self.player = Player()
        self.enemies = []
        self.ebullets = []
        self.particles = []
        self.rings = []
        self.popups = []
        self.powerups = []
        self.score = 0
        self.stage = 0
        self.dt = 0
        self.di = 180
        self.fsw = 0
        self.fss = 0.3
        self.fsa = 25
        self.clr_t = 0
        self.ready_t = 0
        self.paused = False
        self.combo.reset()
        self.global_tick = 0
        # Formation breath phase
        self.breath_phase = 0.0

    def start(self):
        hi = self.hi
        self._full_reset()
        self.hi = hi
        self.state = 'ready'
        self._setup()
        self.ready_t = 120
        _play(SND_READY)

    def _get_layout(self):
        s = self.stage
        if s == 1:
            return [
                [None, None, None, TYPE_COMMANDER, TYPE_FLAGSHIP,
                 TYPE_FLAGSHIP, TYPE_COMMANDER, None, None, None],
                [None, None, None, None, TYPE_COMMANDER,
                 TYPE_COMMANDER, None, None, None, None],
                [TYPE_DIVER] * 10,
                [TYPE_BASIC] * 10,
                [TYPE_BASIC] * 10,
            ]
        elif s == 2:
            return [
                [None, None, TYPE_FLAGSHIP, TYPE_FLAGSHIP, TYPE_FLAGSHIP,
                 TYPE_FLAGSHIP, TYPE_FLAGSHIP, TYPE_FLAGSHIP, None, None],
                [None, None, None, TYPE_COMMANDER, TYPE_COMMANDER,
                 TYPE_COMMANDER, TYPE_COMMANDER, None, None, None],
                [TYPE_DIVER] * 10,
                [TYPE_DIVER] * 10,
                [TYPE_BASIC] * 10,
            ]
        elif s == 3:
            return [
                [TYPE_FLAGSHIP] * 10,
                [None, None, TYPE_COMMANDER, TYPE_COMMANDER,
                 TYPE_COMMANDER, TYPE_COMMANDER, TYPE_COMMANDER,
                 TYPE_COMMANDER, None, None],
                [TYPE_DIVER] * 10,
                [TYPE_DIVER] * 10,
                [TYPE_COMMANDER] * 10,
            ]
        else:
            row_templates = [
                [TYPE_FLAGSHIP] * 10,
                [TYPE_COMMANDER] * 10,
                [TYPE_DIVER] * 10,
                [TYPE_BASIC] * 10,
            ]
            layout = []
            for r in range(min(6, 4 + s // 3)):
                row = [None] * 10
                template = row_templates[r % len(row_templates)]
                for c_idx in range(10):
                    if random.random() < min(0.8, 0.3 + s * 0.05):
                        row[c_idx] = template[c_idx]
                    else:
                        row[c_idx] = random.choice(
                            [TYPE_DIVER, TYPE_COMMANDER, TYPE_BASIC])
                layout.append(row)
            return layout

    def _setup(self):
        self.stage += 1
        self.enemies.clear()
        self.ebullets.clear()
        self.powerups.clear()
        self.dt = 100
        self.fsw = 0
        layout = self._get_layout()
        for r, row in enumerate(layout):
            for c, et in enumerate(row):
                if et is not None:
                    self.enemies.append(Enemy(r, c, et))
        self.di = max(35, 180 - (self.stage - 1) * 16)
        self.fss = 0.3 + (self.stage - 1) * 0.03
        self.fsa = min(65, 25 + (self.stage - 1) * 4)

    # ── Coordinated dive attacks ───────────────────────────────────────
    def _dive(self):
        form = [e for e in self.enemies if e.state == 'formation']
        if not form:
            return
        px, py = self.player.x, self.player.y
        fl = [e for e in form if e.et == TYPE_FLAGSHIP]
        cm = [e for e in form if e.et == TYPE_COMMANDER]
        dv = [e for e in form if e.et == TYPE_DIVER]
        ba = [e for e in form if e.et == TYPE_BASIC]

        attack_roll = random.random()

        if attack_roll < 0.10 and fl:
            # ── Flagship + escort V-formation dive ─────────────────────
            ld = random.choice(fl)
            ld.start_dive(px, py, dive_type=DIVE_DIRECT)
            es = [e for e in form
                  if e is not ld
                  and e.et in (TYPE_DIVER, TYPE_COMMANDER)
                  and abs(e.col - ld.col) <= 4]
            random.shuffle(es)
            for i, e in enumerate(es[:3]):
                offset = (i + 1) * 12
                e.eox_pre = offset * (1 if e.col > ld.col else -1)
                e.start_dive(px, py, True, ld,
                             dive_type=[DIVE_SWOOP, DIVE_WAVE, DIVE_SPIRAL][i % 3])

        elif attack_roll < 0.22 and cm:
            # ── Commander spiral attack ────────────────────────────────
            c = random.choice(cm)
            c.start_dive(px, py, dive_type=DIVE_SPIRAL)
            if random.random() < 0.5:
                es = [e for e in form
                      if e is not c
                      and e.et in (TYPE_DIVER, TYPE_BASIC)
                      and abs(e.col - c.col) <= 3]
                if es:
                    es[0].start_dive(px, py, True, c,
                                     dive_type=DIVE_SWOOP)

        elif attack_roll < 0.40 and dv:
            # ── Diver wave/zigzag attack ───────────────────────────────
            d = random.choice(dv)
            d.start_dive(px, py, dive_type=random.choice([DIVE_WAVE, DIVE_ZIGZAG]))

        elif attack_roll < 0.55 and len(ba) >= 2:
            # ── Basic pair pincer attack ───────────────────────────────
            pair = random.sample(ba, min(2, len(ba)))
            for i, e in enumerate(pair):
                e.start_dive(px, py,
                             dive_type=DIVE_ZIGZAG if i == 0 else DIVE_SWOOP)

        elif attack_roll < 0.70 and fl:
            # ── Flagship spiral with escorts ───────────────────────────
            ld = random.choice(fl)
            ld.start_dive(px, py, dive_type=DIVE_SPIRAL)
            es = [e for e in form
                  if e is not ld and e.et == TYPE_DIVER
                  and abs(e.col - ld.col) <= 3]
            random.shuffle(es)
            for e in es[:2]:
                e.start_dive(px, py, True, ld, dive_type=DIVE_WAVE)

        else:
            # ── Single random dive ─────────────────────────────────────
            pool = dv or ba or cm or fl
            if pool:
                e = random.choice(pool)
                e.start_dive(px, py)

        # Extra dives in later stages (escalating difficulty)
        if self.stage >= 2:
            extra_chance = min(0.65, (self.stage - 1) * 0.13)
            if random.random() < extra_chance:
                ex_pool = [e for e in self.enemies
                           if e.state == 'formation' and e.et == TYPE_DIVER]
                if ex_pool:
                    random.choice(ex_pool).start_dive(
                        px, py, dive_type=random.choice(
                            [DIVE_SPIRAL, DIVE_WAVE, DIVE_ZIGZAG]))

        # Even more aggression in later stages
        if self.stage >= 4 and random.random() < min(0.4, (self.stage - 3) * 0.1):
            ex_pool = [e for e in self.enemies if e.state == 'formation']
            if len(ex_pool) >= 3:
                # Small group wave attack
                group = random.sample(ex_pool, 3)
                for i, e in enumerate(group):
                    e.start_dive(px, py, dive_type=DIVE_WAVE)

    def _boom(self, x, y, c, n=18):
        for _ in range(n):
            self.particles.append(Particle(x, y, c))

    def _spawn_powerup(self, x, y):
        if random.random() < 0.08:
            pw = random.choice([PW_SHIELD, PW_DUAL, PW_RAPID])
            self.powerups.append(PowerUp(x, y, pw))

    def _collide(self):
        if not self.player.alive:
            return

        # Player bullets vs enemies
        for bullet in self.player.bullets:
            if not bullet.alive:
                continue
            bx, by = bullet.x, bullet.y
            for e in self.enemies:
                if not e.alive or e.state == 'returning':
                    continue
                if abs(bx - e.x) < 14 and abs(by - e.y) < 14:
                    mult = self.combo.get_multiplier()
                    p = e.pts(mult)
                    self.score += p
                    e.alive = False
                    bullet.alive = False
                    self._boom(e.x, e.y, e.color, 26)
                    self.rings.append(ExplosionRing(e.x, e.y, e.color, 25))
                    self.shake.shake(4)
                    self.combo.add()
                    self.popups.append(ScorePopup(e.x, e.y - 15, p, e.color))
                    self._spawn_powerup(e.x, e.y)
                    _play(SND_BOOM)
                    if (self.combo.combo >= 3
                            and self.combo.combo % 3 == 0):
                        _play(SND_COMBO)
                    break

        # Enemy bullets vs player
        for b in self.ebullets:
            if not b.alive:
                continue
            if (abs(b.x - self.player.x) < 11
                    and abs(b.y - self.player.y) < 14):
                b.alive = False
                if self.player.hit():
                    self._boom(self.player.x, self.player.y, CYAN, 40)
                    self._boom(self.player.x, self.player.y, WHITE, 18)
                    self.rings.append(
                        ExplosionRing(self.player.x, self.player.y, CYAN, 35))
                    self.shake.shake(12)
                    self.combo.reset()

        # Enemies vs player (collision)
        for e in self.enemies:
            if not e.alive or e.state != 'diving':
                continue
            if (abs(e.x - self.player.x) < 17
                    and abs(e.y - self.player.y) < 17):
                e.alive = False
                self._boom(e.x, e.y, e.color, 18)
                if self.player.hit():
                    self._boom(self.player.x, self.player.y, CYAN, 40)
                    self.rings.append(
                        ExplosionRing(self.player.x, self.player.y, RED, 30))
                    self.shake.shake(12)
                    self.combo.reset()

        # Player vs power-ups
        for pw in self.powerups:
            if not pw.alive:
                continue
            if (abs(pw.x - self.player.x) < 18
                    and abs(pw.y - self.player.y) < 18):
                pw.alive = False
                self.player.apply_powerup(pw.ptype)
                self._boom(pw.x, pw.y, PowerUp.COLORS[pw.ptype], 12)

    def _upd_play(self):
        if self.paused:
            return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            self.player.shoot()
        self.player.update(keys)

        # Formation sway with breathing
        self.fsw += self.fss
        self.breath_phase += 0.008
        breath_offset = math.sin(self.breath_phase) * 5
        fdx = math.sin(self.fsw) * self.fsa + breath_offset

        # Update enemies — pass global tick for organic movement
        for e in self.enemies:
            if e.alive:
                e.update(self.player.x, self.player.y, fdx, self.global_tick)
                b = e.try_shoot(self.player.x, self.player.y)
                if b:
                    self.ebullets.append(b)
        self.enemies = [e for e in self.enemies if e.alive]

        for b in self.ebullets:
            b.update()
        self.ebullets = [b for b in self.ebullets if b.alive]

        for p in self.particles[:]:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

        for r in self.rings[:]:
            r.update()
        self.rings = [r for r in self.rings if r.life > 0]

        for pp in self.popups[:]:
            pp.update()
        self.popups = [pp for pp in self.popups if pp.life > 0]

        for pw in self.powerups[:]:
            pw.update()
        self.powerups = [pw for pw in self.powerups if pw.alive]

        self.combo.update()
        self.shake.update()

        self._collide()

        self.dt -= 1
        if self.dt <= 0:
            self._dive()
            self.dt = self.di + random.randint(-12, 12)

        if not self.enemies:
            bonus = self.stage * 100
            self.score += bonus
            self.state = 'stage_clear'
            self.clr_t = 160
            _play(SND_BONUS)

        if (not self.player.alive
                and self.player.lives <= 0
                and self.player.respawn <= 0):
            self.state = 'game_over'
            if self.score > self.hi:
                self.hi = self.score

    def update(self):
        self.tick += 1
        self.global_tick += 1
        for s in self.stars:
            s.update()
        self.nebula.update()

        if self.state == 'ready':
            self.ready_t -= 1
            fdx = math.sin(self.fsw) * self.fsa
            for e in self.enemies:
                if e.alive:
                    e.update(self.player.x, self.player.y, fdx, self.global_tick)
            if self.ready_t <= 0:
                self.state = 'playing'

        elif self.state == 'playing':
            self._upd_play()

        elif self.state == 'stage_clear':
            self.clr_t -= 1
            for p in self.particles[:]:
                p.update()
            self.particles = [p for p in self.particles if p.life > 0]
            for r in self.rings[:]:
                r.update()
            self.rings = [r for r in self.rings if r.life > 0]
            for pp in self.popups[:]:
                pp.update()
            self.popups = [pp for pp in self.popups if pp.life > 0]
            if self.clr_t <= 0:
                self._setup()
                self.state = 'ready'
                self.ready_t = 90

        else:
            for p in self.particles[:]:
                p.update()
            self.particles = [p for p in self.particles if p.life > 0]
            for r in self.rings[:]:
                r.update()
            self.rings = [r for r in self.rings if r.life > 0]
            for pp in self.popups[:]:
                pp.update()
            self.popups = [pp for pp in self.popups if pp.life > 0]

    # ─── Drawing Methods ───────────────────────────────────────────────

    def _draw_game(self, surf):
        for e in self.enemies:
            e.draw(surf)
        for b in self.ebullets:
            b.draw(surf)
        self.player.draw(surf)
        for b in self.player.bullets:
            if b.alive:
                b.draw(surf)
        for p in self.particles:
            p.draw(surf)
        for r in self.rings:
            r.draw(surf)
        for pw in self.powerups:
            pw.draw(surf)
        fn_s = pygame.font.Font(None, 22)
        for pp in self.popups:
            pp.draw(surf, fn_s)

    def _hud(self, surf):
        fn = pygame.font.Font(None, 28)
        fs = pygame.font.Font(None, 22)
        ft = pygame.font.Font(None, 20)

        s_txt = fn.render(f"SCORE  {self.score:>7}", True, WHITE)
        surf.blit(s_txt, (10, 8))

        h_txt = fs.render(f"HI {self.hi}", True, YELLOW)
        surf.blit(h_txt, (WIDTH - h_txt.get_width() - 10, 10))

        st_txt = fs.render(f"STAGE {self.stage}", True, CYAN)
        surf.blit(st_txt, (WIDTH // 2 - st_txt.get_width() // 2, 10))

        # Lives (5 ships max)
        for i in range(self.player.lives):
            lx, ly = 12 + i * 22, 38
            p = [(lx, ly - 6), (lx - 6, ly + 3), (lx - 2, ly + 1),
                 (lx - 2, ly + 6), (lx + 2, ly + 6), (lx + 2, ly + 1),
                 (lx + 6, ly + 3)]
            pygame.draw.polygon(surf, CYAN, p)

        # Power-up timers
        pw_x, pw_y = WIDTH - 110, 38
        if self.player.shield > 0:
            secs = self.player.shield // 60 + 1
            t = ft.render(f"SHIELD {secs}s", True, (100, 200, 255))
            surf.blit(t, (pw_x, pw_y))
            pw_y += 16
        if self.player.dual_shot > 0:
            secs = self.player.dual_shot // 60 + 1
            t = ft.render(f"DUAL {secs}s", True, (255, 200, 50))
            surf.blit(t, (pw_x, pw_y))
            pw_y += 16
        if self.player.rapid_fire > 0:
            secs = self.player.rapid_fire // 60 + 1
            t = ft.render(f"RAPID {secs}s", True, (100, 255, 100))
            surf.blit(t, (pw_x, pw_y))

        self.combo.draw(surf)

    def _title(self, surf):
        fb = pygame.font.Font(None, 78)
        fm = pygame.font.Font(None, 38)
        fs = pygame.font.Font(None, 24)
        ft = pygame.font.Font(None, 20)
        t = self.tick

        r = int(128 + 127 * math.sin(t * 0.04))
        g = int(128 + 127 * math.sin(t * 0.04 + 2.1))
        b = int(128 + 127 * math.sin(t * 0.04 + 4.2))
        ti = fb.render("GALAXIAN", True, (r, g, b))
        surf.blit(ti, (WIDTH // 2 - ti.get_width() // 2, 110))

        su = fm.render("\u2605 SPACE DEFENDER \u2605", True, (180, 180, 220))
        surf.blit(su, (WIDTH // 2 - su.get_width() // 2, 185))

        # Mini formation preview
        preview_y = 240
        scale_x, scale_y = 28, 26
        preview = [
            [None, None, None, TYPE_COMMANDER, TYPE_FLAGSHIP,
             TYPE_FLAGSHIP, TYPE_COMMANDER, None, None, None],
            [None, None, None, None, TYPE_COMMANDER,
             TYPE_COMMANDER, None, None, None, None],
            [TYPE_DIVER] * 10,
            [TYPE_BASIC] * 10,
            [TYPE_BASIC] * 10,
        ]
        ox = (WIDTH - 10 * scale_x) // 2 + scale_x // 2
        for ri, row in enumerate(preview):
            for ci, et in enumerate(row):
                if et is not None:
                    ex = ox + ci * scale_x
                    ey = preview_y + ri * scale_y
                    sz = 6
                    pd = [(ex, ey - sz), (ex - sz, ey + sz // 2),
                          (ex, ey + sz), (ex + sz, ey + sz // 2)]
                    pygame.draw.polygon(surf, E_COLOR[et], pd)
                    pygame.draw.polygon(surf, E_EDGE[et], pd, 1)

        # Enemy legend
        y0 = 390
        legends = [
            (TYPE_FLAGSHIP, "FLAGSHIP", "150 PTS"),
            (TYPE_COMMANDER, "COMMANDER", "100 PTS"),
            (TYPE_DIVER, "DIVER", "80 PTS"),
            (TYPE_BASIC, "FIGHTER", "60 PTS"),
        ]
        for i, (et, nm, pt) in enumerate(legends):
            yy = y0 + i * 32
            ex = WIDTH // 2 - 100
            sz = 7
            pd = [(ex, yy - sz), (ex - sz, yy + sz // 2),
                  (ex, yy + sz), (ex + sz, yy + sz // 2)]
            pygame.draw.polygon(surf, E_COLOR[et], pd)
            pygame.draw.polygon(surf, E_EDGE[et], pd, 1)
            surf.blit(fs.render(nm, True, E_COLOR[et]), (ex + 18, yy - 8))
            surf.blit(ft.render(pt + " (diving)", True, (160, 160, 170)),
                     (ex + 18, yy + 8))

        if (self.tick // 30) % 2:
            st = fm.render("PRESS SPACE TO START", True, YELLOW)
            surf.blit(st, (WIDTH // 2 - st.get_width() // 2, 535))

        # Draw controls as separate lines to avoid Unicode issues
        ctrl_y = 578
        c1 = ft.render("Arrow Keys / W A S D : Move", True, GRAY)
        surf.blit(c1, (WIDTH // 2 - c1.get_width() // 2, ctrl_y))
        c2 = ft.render("SPACE : Fire    P : Pause    ESC : Quit", True, GRAY)
        surf.blit(c2, (WIDTH // 2 - c2.get_width() // 2, ctrl_y + 20))
        ct2 = ft.render("5 lives  -  Destroy all enemies to advance!",
                        True, (80, 80, 100))
        surf.blit(ct2, (WIDTH // 2 - ct2.get_width() // 2, ctrl_y + 42))

        if self.hi > 0:
            hs = fs.render(f"HIGH SCORE: {self.hi}", True, GOLD)
            surf.blit(hs, (WIDTH // 2 - hs.get_width() // 2, 560))

    def _gameover(self, surf):
        fb = pygame.font.Font(None, 64)
        fm = pygame.font.Font(None, 34)
        fs = pygame.font.Font(None, 24)

        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        surf.blit(ov, (0, 0))

        go = fb.render("GAME OVER", True, RED)
        surf.blit(go, (WIDTH // 2 - go.get_width() // 2, HEIGHT // 2 - 90))

        sc = fm.render(f"FINAL SCORE: {self.score}", True, WHITE)
        surf.blit(sc, (WIDTH // 2 - sc.get_width() // 2, HEIGHT // 2 - 25))

        sg = fs.render(f"STAGE REACHED: {self.stage}", True, CYAN)
        surf.blit(sg, (WIDTH // 2 - sg.get_width() // 2, HEIGHT // 2 + 10))

        if self.score > 0 and self.score >= self.hi:
            nh = fm.render("NEW HIGH SCORE!", True, GOLD)
            surf.blit(nh, (WIDTH // 2 - nh.get_width() // 2,
                          HEIGHT // 2 + 45))

        if (self.tick // 30) % 2:
            rs = fm.render("PRESS SPACE TO RESTART", True, WHITE)
            surf.blit(rs, (WIDTH // 2 - rs.get_width() // 2,
                          HEIGHT // 2 + 90))

    def _stageclear(self, surf):
        fn = pygame.font.Font(None, 48)
        fs = pygame.font.Font(None, 32)

        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 110))
        surf.blit(ov, (0, 0))

        t = fn.render(f"STAGE {self.stage} CLEAR!", True, CYAN)
        surf.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 30))

        bt = fs.render(
            f"STAGE BONUS: +{self.stage * 100}", True, YELLOW)
        surf.blit(bt, (WIDTH // 2 - bt.get_width() // 2, HEIGHT // 2 + 20))

    def _ready_screen(self, surf):
        fn = pygame.font.Font(None, 48)
        if (self.tick // 20) % 2:
            t = fn.render(f"STAGE {self.stage}", True, CYAN)
            surf.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 40))
            r = fn.render("READY!", True, YELLOW)
            surf.blit(r, (WIDTH // 2 - r.get_width() // 2, HEIGHT // 2 + 15))

    def _pause_screen(self, surf):
        fn = pygame.font.Font(None, 48)
        fm = pygame.font.Font(None, 28)
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 140))
        surf.blit(ov, (0, 0))
        t = fn.render("PAUSED", True, WHITE)
        surf.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 30))
        h = fm.render("Press P to resume", True, GRAY)
        surf.blit(h, (WIDTH // 2 - h.get_width() // 2, HEIGHT // 2 + 20))

    def draw(self, surf):
        if self.shake.intensity > 0:
            render_surf = pygame.Surface((WIDTH, HEIGHT))
        else:
            render_surf = surf

        render_surf.fill(DEEP_BLUE)
        self.nebula.draw(render_surf)
        for st in self.stars:
            st.draw(render_surf)

        if self.state == 'title':
            self._title(render_surf)
        else:
            self._draw_game(render_surf)
            self._hud(render_surf)
            if self.state == 'game_over':
                self._gameover(render_surf)
            elif self.state == 'stage_clear':
                self._stageclear(render_surf)
            elif self.state == 'ready':
                self._ready_screen(render_surf)
            if self.paused and self.state == 'playing':
                self._pause_screen(render_surf)

        if self.shake.intensity > 0:
            surf.fill(BLACK)
            surf.blit(render_surf,
                     (self.shake.offset_x, self.shake.offset_y))


# ─── Main Loop ─────────────────────────────────────────────────────────
def main():
    game = Game()

    while True:
        clock.tick(FPS)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if game.state in ('playing', 'ready', 'stage_clear'):
                        game.state = 'title'
                        game.paused = False
                    else:
                        pygame.quit()
                        sys.exit()

                if ev.key == pygame.K_p and game.state == 'playing':
                    game.paused = not game.paused

                if ev.key == pygame.K_SPACE:
                    if game.state == 'title':
                        game.start()
                    elif game.state == 'game_over':
                        game.start()

        game.update()
        game.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
