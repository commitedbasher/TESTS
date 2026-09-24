#!/usr/bin/env python3
"""
Orbe sufriente: animación en pixel art de 80x95 px.

Un orbe morado que levita con cara de sufrimiento, una grieta que brilla,
lágrimas que caen al suelo y fragmentos de cristal y piedras rúnicas
orbitando a su alrededor. El bucle es perfecto: el último fotograma enlaza
con el primero.

Salida (en la misma carpeta que este script):
  orbe_sufriente.gif              animación a tamaño real, fondo transparente
  orbe_sufriente_x4.gif           vista previa ampliada x4 con fondo oscuro
  orbe_sufriente_spritesheet.png  tira horizontal con todos los fotogramas

Uso:
  pip install pillow
  python3 generar_orbe.py
"""

import math
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

W, H = 80, 95          # tamaño del lienzo
FRAMES = 48            # fotogramas del bucle
FRAME_MS = 70          # duración de cada fotograma
PREVIEW_SCALE = 4
PREVIEW_BG = '2a2340'

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
PALETTE = {
    # contorno y rampa del orbe: sombras frías, luces rosadas
    'o0': '140a26', 'p1': '2a1245', 'p2': '43186b', 'p3': '5f2294',
    'p4': '7d31b8', 'p5': '9b4bd6', 'p6': 'bb74ea', 'p7': 'dca6f7',
    'p8': 'f6e4ff', 'w': 'ffffff',
    # luz rebotada y energía interior
    'm1': 'a23aa8', 'm2': 'e36fd3', 'm3': 'ffb8ee',
    # cian mágico: runas, lágrimas, destellos
    'c0': '0e3b57', 'c1': '1b7fa6', 'c2': '3fd0e6', 'c3': 'a9f6ff',
    # piedra
    's0': '120f1f', 's1': '262338', 's2': '3b3752', 's3': '57536f',
    's4': '807b97', 's5': 'a9a5bd',
    # oro
    'g1': 'a0621a', 'g2': 'e8a83a', 'g3': 'ffe28a',
    # boca
    'mo': '1c0616', 'tg': 'b3305f', 'tg2': 'e0588f',
    'te': 'eee2ff', 'te2': 'a894c9',
    # sombra en el suelo
    'sh': '0d0718',
}
RGB = {k: tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) for k, v in PALETTE.items()}

# Un paso más oscuro de cada color: se usa para lo que pasa por detrás del orbe.
DARKER = {
    'w': 'p8', 'p8': 'p7', 'p7': 'p6', 'p6': 'p5', 'p5': 'p4', 'p4': 'p3',
    'p3': 'p2', 'p2': 'p1', 'p1': 'o0', 'o0': 'o0',
    'm3': 'm2', 'm2': 'm1', 'm1': 'p2',
    'c3': 'c2', 'c2': 'c1', 'c1': 'c0', 'c0': 'o0',
    's5': 's4', 's4': 's3', 's3': 's2', 's2': 's1', 's1': 's0', 's0': 's0',
    'g3': 'g2', 'g2': 'g1', 'g1': 's1',
}

BAYER4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def tau(x):
    return 2.0 * math.pi * x


def darken(c, steps):
    for _ in range(steps):
        c = DARKER.get(c, c)
    return c


# ---------------------------------------------------------------------------
# Lienzo
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self):
        self.px = [[None] * W for _ in range(H)]

    def put(self, x, y, c):
        if c and 0 <= x < W and 0 <= y < H:
            self.px[y][x] = c

    def get(self, x, y):
        if 0 <= x < W and 0 <= y < H:
            return self.px[y][x]
        return None

    def sprite(self, rows, x0, y0, cmap):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                self.put(x0 + i, y0 + j, cmap.get(ch))


def mirrored(half_rows):
    """Completa un sprite simétrico a partir de su mitad izquierda."""
    return [row + row[::-1] for row in half_rows]


# ---------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------
def point_in_poly(px, py, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > py) != (yj > py):
            if px < xi + (py - yi) * (xj - xi) / (yj - yi):
                inside = not inside
        j = i
    return inside


def raster_poly(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cells = set()
    for y in range(math.floor(min(ys)), math.ceil(max(ys)) + 1):
        for x in range(math.floor(min(xs)), math.ceil(max(xs)) + 1):
            if point_in_poly(x + 0.5, y + 0.5, pts):
                cells.add((x, y))
    return cells


def outer_ring(cells):
    ring = set()
    for (x, y) in cells:
        for dx, dy in N4:
            n = (x + dx, y + dy)
            if n not in cells:
                ring.add(n)
    return ring


# ---------------------------------------------------------------------------
# Composición general y línea de tiempo
# ---------------------------------------------------------------------------
R = 20                 # radio del orbe
ORB_X, ORB_Y = 40, 44  # centro del orbe (esquina entre píxeles)
GROUND_Y = 89          # fila del suelo (sombra y salpicaduras)

TENSION = range(30, 34)   # el orbe se estremece y aprieta los dientes
SCREAM = range(34, 41)    # espasmo de dolor: grita, la grieta destella
RELEASE = range(41, 44)   # solloza y vuelve a aguantar
SHAKE = {30: 1, 31: -1, 32: 1, 33: -1, 34: 1, 35: -1, 36: 1, 37: -1, 38: 1, 39: 0, 40: -1}


def bob(f, lag=0.0):
    """Levitación: dos oscilaciones por bucle."""
    return -3.0 * math.sin(tau(2.0 * (f - lag) / FRAMES))


# ---------------------------------------------------------------------------
# Orbe
# ---------------------------------------------------------------------------
LIGHT = (-0.45, -0.6, 0.66)
_l = math.sqrt(sum(v * v for v in LIGHT))
LIGHT = tuple(v / _l for v in LIGHT)

ORB_RAMP = ('p1', 'p2', 'p3', 'p4', 'p5', 'p6')


def build_orb():
    """Orbe base relativo a su centro: {(dx, dy): color}."""
    inside = set()
    for dy in range(-R, R):
        for dx in range(-R, R):
            fx, fy = dx + 0.5, dy + 0.5
            if fx * fx + fy * fy <= R * R:
                inside.add((dx, dy))
    base = {}
    for (dx, dy) in inside:
        if any((dx + ex, dy + ey) not in inside for ex, ey in N4):
            base[(dx, dy)] = 'o0'
            continue
        nx, ny = (dx + 0.5) / R, (dy + 0.5) / R
        rho = math.sqrt(nx * nx + ny * ny)
        nz = math.sqrt(max(0.0, 1.0 - rho * rho))
        diff = max(0.0, nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2])
        v = 0.06 + 0.94 * diff
        v += (BAYER4[dy % 4][dx % 4] / 16.0 - 0.47) * 0.07
        idx = max(0, min(len(ORB_RAMP) - 1, int(v * len(ORB_RAMP))))
        c = ORB_RAMP[idx]
        # luz rebotada magenta en el borde inferior derecho
        rim = nx * 0.55 + ny * 0.83
        if rho > 0.87 and rim > 0.72:
            c = 'm2' if (rho > 0.92 and rim > 0.9) else 'm1'
        # reflejo curvo en el borde superior izquierdo
        ang = math.degrees(math.atan2(ny, nx))
        if 0.8 < rho < 0.9 and -160 < ang < -112:
            c = 'p7'
        base[(dx, dy)] = c
    return base, inside


ORB_BASE, ORB_INSIDE = build_orb()

HIGHLIGHT = [
    "..77..",
    ".7888.",
    "78WW8.",
    "78W8..",
    ".77...",
]
HIGHLIGHT_CMAP = {'7': 'p7', '8': 'p8', 'W': 'w'}

# Grieta en forma de "Y" invertida que baja desde el borde superior derecho
# (coordenadas relativas al centro del orbe).
CRACK = [(5, -19), (5, -18), (6, -17), (6, -16), (7, -15), (8, -15), (9, -14),
         (10, -13), (11, -12), (12, -11), (5, -15), (4, -14), (3, -14)]
CRACK_CORE = {(6, -17), (6, -16), (7, -15), (5, -15)}   # donde brilla la energía


def draw_orb(cv, ox, oy, f):
    for (dx, dy), c in ORB_BASE.items():
        cv.put(ox + dx, oy + dy, c)
    cv.sprite(HIGHLIGHT, ox - 14, oy - 16, HIGHLIGHT_CMAP)

    # grieta: fisura oscura con un canto iluminado y energía que late dentro;
    # durante el grito toda la grieta destella
    flash = f in SCREAM and f < SCREAM.start + 4
    pulse = 0.5 + 0.5 * math.sin(tau(3 * f / FRAMES))
    crack = set(CRACK)
    for (dx, dy) in CRACK:
        n = (dx + 1, dy + 1)
        if n not in crack and n in ORB_INSIDE and ORB_BASE[n] != 'o0':
            cv.put(ox + n[0], oy + n[1], 'm3' if flash else 'p7')
    for i, (dx, dy) in enumerate(CRACK):
        if flash:
            c = 'w'
        elif (dx, dy) in CRACK_CORE:
            c = 'm3' if pulse > 0.5 else 'm2'
        else:
            c = 'o0' if i % 3 else 'p1'
        cv.put(ox + dx, oy + dy, c)


# ---------------------------------------------------------------------------
# Cara (mitades izquierdas; la derecha se refleja)
# ---------------------------------------------------------------------------
FACE_CMAP = {
    'k': 'o0', 't': 'te', 'T': 'te2', 'm': 'mo', 'g': 'tg', 'G': 'tg2', 'C': 'c3',
}

BROWS = mirrored([
    ".........kk.",
    ".......kkkk.",
    ".....kkk....",
    "....k.......",
])

EYES = mirrored([
    "...kk.......",
    "....kkk.....",
    "..C...kkk...",
    "....kkk.....",
    "...kk.......",
])

EYES_TIGHT = mirrored([
    "..kkk.......",
    "....kkkk....",
    ".CC....kkk..",
    "....kkkk....",
    "..kkk.......",
])

MOUTH_GRIMACE_A = mirrored([
    "........kkkk",
    "......kkttTt",
    ".....ktttTtt",
    ".....kkkkkkk",
    ".....ktttTtt",
    "......kkttTt",
    "........kkkk",
])

MOUTH_GRIMACE_B = mirrored([
    ".......kkkkk",
    "......kttTtt",
    ".....ktttTtt",
    ".....kkkkkkk",
    "......kttTtt",
    ".......kkkkk",
    "............",
])

MOUTH_SCREAM = mirrored([
    ".........kkk",
    ".......kkttt",
    "......kmmmmm",
    ".....kmmmmmm",
    ".....kmmmggg",
    "......kmgGGg",
    ".......kkkkk",
])

MOUTH_SOB = mirrored([
    "............",
    ".........kkk",
    ".......kkmmm",
    "......kmmmgg",
    ".......kkkkk",
    "............",
    "............",
])

FACE_X = -12   # desplazamiento de la cara respecto al centro del orbe


def draw_face(cv, ox, oy, f):
    screaming = f in SCREAM
    tense = f in TENSION or screaming
    cv.sprite(BROWS, ox + FACE_X, oy - 11 + (1 if tense else 0), FACE_CMAP)
    cv.sprite(EYES_TIGHT if tense else EYES, ox + FACE_X, oy - 6, FACE_CMAP)
    if screaming:
        mouth = MOUTH_SCREAM
    elif f in RELEASE:
        mouth = MOUTH_SOB
    elif f in TENSION:
        mouth = MOUTH_GRIMACE_A if f % 2 == 0 else MOUTH_GRIMACE_B
    else:
        mouth = MOUTH_GRIMACE_A if (f // 2) % 2 == 0 else MOUTH_GRIMACE_B
    cv.sprite(mouth, ox + FACE_X, oy + 1, FACE_CMAP)


# ---------------------------------------------------------------------------
# Lágrimas
# ---------------------------------------------------------------------------
# Reguero de lágrimas por la mejilla izquierda (la derecha se refleja),
# relativo al centro del orbe.
TEAR_STREAM = [(-10 - (dy + 4) // 6, dy) for dy in range(-4, 15)]
# gotas que caen al suelo: (fotograma de inicio, lado -1 izquierdo / +1 derecho)
DROPS = [(0, -1), (13, 1), (25, -1), (37, 1)]
DROP = [".C", "CW", "cC"]
TEAR_CMAP = {'C': 'c3', 'c': 'c2', 'W': 'w'}


def mirror_dx(dx, side):
    return dx if side < 0 else -1 - dx


def draw_tear_streams(cv, f, ox, oy):
    n = len(TEAR_STREAM)
    for side in (-1, 1):
        shine = (f * 2 + (0 if side < 0 else 9)) % (n + 8)
        for i, (dx, dy) in enumerate(TEAR_STREAM):
            c = 'c3' if i in (shine, shine - 1) else 'c2'
            cv.put(ox + mirror_dx(dx, side), oy + dy, c)


def drop_track(start, side):
    """Estado de una gota fotograma a fotograma: (fase, paso, x, y)."""
    dx, dy = TEAR_STREAM[-1]
    track = []
    for age in range(3):                        # se forma al final del reguero
        g = start + age
        track.append(('form', age, ORB_X + mirror_dx(dx, side),
                      ORB_Y + round(bob(g)) + dy))
    x = ORB_X + mirror_dx(dx, side)
    y = ORB_Y + round(bob(start + 3)) + dy + 1
    k = 0
    while y < GROUND_Y - 2:                     # caída libre
        track.append(('fall', k, x, int(y)))
        k += 1
        y += 1.0 + 0.8 * k
    for s in range(3):                          # salpicadura
        track.append(('splash', s, x, GROUND_Y))
    return track


DROP_TRACKS = [(start, drop_track(start, side)) for start, side in DROPS]


def draw_drops(cv, f):
    for start, track in DROP_TRACKS:
        age = (f - start) % FRAMES
        if age >= len(track):
            continue
        state, k, x, y = track[age]
        if state == 'form':
            cv.put(x, y + 1, 'c3')
            if k >= 1:
                cv.put(x, y + 2, 'c2')
            if k >= 2:
                cv.put(x + 1, y + 2, 'c3')
        elif state == 'fall':
            cv.sprite(DROP, x, y, TEAR_CMAP)
        else:
            draw_splash(cv, x, k)


def draw_splash(cv, x, k):
    y = GROUND_Y - 1
    if k == 0:
        for dx in (-1, 0, 1, 2):
            cv.put(x + dx, y, 'c2')
        cv.put(x, y - 1, 'c3')
        cv.put(x + 1, y - 1, 'c3')
    elif k == 1:
        cv.put(x - 2, y - 1, 'c3')
        cv.put(x + 3, y - 1, 'c3')
        cv.put(x - 1, y, 'c2')
        cv.put(x + 2, y, 'c2')
    elif k == 2:
        cv.put(x - 3, y - 2, 'c2')
        cv.put(x + 4, y - 2, 'c2')


# ---------------------------------------------------------------------------
# Sombra en el suelo
# ---------------------------------------------------------------------------
def draw_shadow(cv, f):
    lift = bob(f)                       # negativo = más alto
    hw = 13.5 + lift * 0.9
    hh = 2.6 + lift * 0.12
    for y in range(GROUND_Y - 4, GROUND_Y + 5):
        for x in range(0, W):
            nx = (x + 0.5 - ORB_X) / hw
            ny = (y + 0.5 - GROUND_Y) / hh
            d = nx * nx + ny * ny
            if d <= 0.55:
                cv.put(x, y, 'sh')
            elif d <= 1.0 and (x + y) % 2 == 0:
                cv.put(x, y, 'sh')


# ---------------------------------------------------------------------------
# Objetos en órbita
# ---------------------------------------------------------------------------
ORBIT_A, ORBIT_B = 33.0, 14.5
ORBIT_TILT = -0.18


def orbit_pos(theta, cx, cy, a=ORBIT_A, b=ORBIT_B):
    ex, ey = a * math.cos(theta), b * math.sin(theta)
    ct, st = math.cos(ORBIT_TILT), math.sin(ORBIT_TILT)
    return cx + ex * ct - ey * st, cy + ex * st + ey * ct, math.sin(theta)


STONES = {
    'A': dict(poly=[(-4, -2), (-2, -4), (2, -4.2), (4.5, -1), (4, 3), (1, 4.2), (-3, 3.8), (-4.6, 1)],
              rune=["r.r", ".r.", ".r."], ramp='c'),
    'B': dict(poly=[(-1, -5.2), (2.5, -3), (3.4, 2), (1, 5), (-2.6, 4), (-3.4, -1)],
              rune=[".r.", "r.r", ".r.", ".r."], ramp='g'),
    'C': dict(poly=[(-5.5, -1), (-3, -3.6), (3, -3.4), (5.6, 0), (4, 3.2), (-3.5, 3.4)],
              rune=[".r.", "r.r", ".r."], ramp='c'),
}
STONE_RAMP = ('s1', 's2', 's3', 's4', 's5')
RUNE_COLORS = {'c': ('c1', 'c2', 'c3'), 'g': ('g1', 'g2', 'g3')}


def draw_stone(cv, spec, x, y, rot, scale, dark, glow):
    ca, sa = math.cos(rot), math.sin(rot)
    pts = [(x + (px * ca - py * sa) * scale, y + (px * sa + py * ca) * scale)
           for px, py in spec['poly']]
    cells = raster_poly(pts)
    if not cells:
        return
    ring = outer_ring(cells)
    for (px, py) in ring:
        cv.put(px, py, darken('s0', dark))
    rx = max(abs(p[0] - x) for p in pts) or 1
    ry = max(abs(p[1] - y) for p in pts) or 1
    for (px, py) in cells:
        nx, ny = (px + 0.5 - x) / rx, (py + 0.5 - y) / ry
        v = 0.5 - (nx * 0.6 + ny * 0.8) * 0.45
        v += (BAYER4[py % 4][px % 4] / 16.0 - 0.47) * 0.12
        idx = max(0, min(len(STONE_RAMP) - 1, int(v * len(STONE_RAMP))))
        cv.put(px, py, darken(STONE_RAMP[idx], dark))
    _, mid, hi = RUNE_COLORS[spec['ramp']]
    rune = spec['rune']
    rx0 = int(round(x - len(rune[0]) / 2.0))
    ry0 = int(round(y - len(rune) / 2.0))
    col = hi if glow else mid
    for j, row in enumerate(rune):
        for i, ch in enumerate(row):
            if ch == 'r' and (rx0 + i, ry0 + j) in cells:
                cv.put(rx0 + i, ry0 + j, darken(col, dark))


def draw_shard(cv, x, y, length, width, rot, tumble, dark):
    ux, uy = math.cos(rot), math.sin(rot)
    vx, vy = -uy, ux
    face = math.cos(tumble)
    w = max(1.25, width * abs(face))
    pts = [(x + ux * length * 0.6, y + uy * length * 0.6),
           (x + vx * w, y + vy * w),
           (x - ux * length * 0.4, y - uy * length * 0.4),
           (x - vx * w * 0.8, y - vy * w * 0.8)]
    cells = raster_poly(pts)
    if not cells:
        return
    for (px, py) in outer_ring(cells):
        cv.put(px, py, darken('o0', dark))
    light_side = 1 if face > 0 else -1
    for (px, py) in cells:
        s = (px + 0.5 - x) * vx + (py + 0.5 - y) * vy
        c = 'p7' if s * light_side > 0 else 'p4'
        cv.put(px, py, darken(c, dark))
    if abs(face) > 0.85:
        tx, ty = int(math.floor(x + ux * length * 0.35)), int(math.floor(y + uy * length * 0.35))
        cv.put(tx, ty, darken('w', dark))


# (tipo, fase inicial en la órbita como fracción de vuelta, parámetros).
# Las fases están elegidas para que ningún objeto pase justo delante de la
# boca en mitad del grito (fotogramas 35-39).
ORBITERS = [
    ('stone', 0.271, dict(key='A', spin=0.6)),
    ('shard', 0.438, dict(length=11, width=2.8, spin=-1.0, tumble=3)),
    ('stone', 0.604, dict(key='B', spin=-0.5)),
    ('shard', 0.771, dict(length=8, width=2.2, spin=1.0, tumble=4)),
    ('stone', 0.938, dict(key='C', spin=0.4)),
    ('shard', 0.104, dict(length=9, width=2.5, spin=-2.0, tumble=2)),
]

SPECKS = [(0.08, 0.9, 'p6'), (0.25, 1.1, 'c2'), (0.41, 0.85, 'p7'), (0.55, 1.05, 'c3'),
          (0.72, 0.92, 'p6'), (0.88, 1.12, 'm3')]


def orbit_center(f):
    return ORB_X, ORB_Y + bob(f, lag=2.0)


def draw_orbiters(cv, f, front):
    cx, cy = orbit_center(f)
    push = 0.0
    if f in SCREAM:
        push = [2.0, 3.0, 3.0, 2.0, 1.2, 0.6, 0.2][f - SCREAM.start]
    a, b = ORBIT_A + push, ORBIT_B + push * 0.35
    t = f / FRAMES
    items = []
    for kind, phase, p in ORBITERS:
        theta = tau(phase - t)
        x, y, z = orbit_pos(theta, cx, cy, a, b)
        y += math.sin(tau(2 * t + phase * 3)) * 0.8
        if (z >= 0) != front:
            continue
        items.append((z, kind, x, y, theta, phase, p))
    items.sort(key=lambda it: it[0])

    # estelas
    for z, kind, x, y, theta, phase, p in items:
        col = 'p6' if kind == 'shard' else RUNE_COLORS[STONES[p['key']]['ramp']][1]
        for k in range(1, 5):
            tx, ty, tz = orbit_pos(theta + 0.11 * (k + 1.3), cx, cy, a, b)
            if (tz >= 0) != front:
                continue
            if k == 4 and (f + int(phase * 6)) % 2:
                continue
            c = darken(col, (k - 1) // 2 + (0 if tz >= 0 else 1))
            cv.put(int(math.floor(tx)), int(math.floor(ty)), c)

    for z, kind, x, y, theta, phase, p in items:
        dark = 0 if z > -0.25 else (1 if z > -0.7 else 2)
        scale = 0.85 + 0.2 * (z + 1) / 2
        if kind == 'stone':
            spec = STONES[p['key']]
            rot = math.sin(tau(t + phase)) * 0.35 * p['spin']
            glow = ((f + int(phase * 12)) // 3) % 2 == 0 or f in SCREAM
            draw_stone(cv, spec, x, y, rot, scale, dark, glow)
        else:
            rot = tau(p['spin'] * t + phase)
            tumble = tau(p['tumble'] * t + phase)
            draw_shard(cv, x, y, p['length'] * scale, p['width'] * scale, rot, tumble, dark)

    for phase, rf, col in SPECKS:
        theta = tau(phase - 1.5 * t)
        x, y, z = orbit_pos(theta, cx, cy, a * rf, b * rf)
        if (z >= 0) != front:
            continue
        if (f + int(phase * 10)) % 4 == 0:
            continue
        cv.put(int(math.floor(x)), int(math.floor(y)), darken(col, 0 if z >= 0 else 1))


# ---------------------------------------------------------------------------
# Efectos: onda de choque, aura, motas, destellos y chispas de la grieta
# ---------------------------------------------------------------------------
def draw_shockwave(cv, f, ox, oy):
    if f not in SCREAM:
        return
    k = f - SCREAM.start
    if k > 5:
        return
    r = R + 2 + k * 3.2
    cols = ['p8', 'p7', 'p6', 'p5', 'p4', 'p3']
    for y in range(int(oy - r - 2), int(oy + r + 3)):
        for x in range(int(ox - r - 2), int(ox + r + 3)):
            d = math.hypot(x + 0.5 - ox, y + 0.5 - oy)
            if abs(d - r) < 0.55:
                if k >= 3 and (x + y) % 2:
                    continue
                if k >= 5 and (x // 2 + y) % 2:
                    continue
                cv.put(x, y, cols[k])


def draw_aura(cv, f, ox, oy):
    """Energía que gira pegada al contorno del orbe (4 lóbulos)."""
    t = f / FRAMES
    strong = f in SCREAM and f < SCREAM.start + 4
    for dy in range(-R - 3, R + 3):
        for dx in range(-R - 3, R + 3):
            if (dx, dy) in ORB_INSIDE:
                continue
            fx, fy = dx + 0.5, dy + 0.5
            d = math.hypot(fx, fy)
            a = math.atan2(fy, fx)
            if d < R + 1.2:
                wave = math.sin(4 * a - tau(3 * t))
                if strong:
                    cv.put(ox + dx, oy + dy, 'm2')
                elif wave > 0.2:
                    cv.put(ox + dx, oy + dy, 'p5' if wave > 0.75 else 'p4')
            elif d < R + 2.2:
                wave = math.sin(4 * a - tau(3 * t) + 0.5)
                if wave > 0.6 and (dx + dy) % 2 == 0:
                    cv.put(ox + dx, oy + dy, 'p3')


# Motas que suben desde la sombra hacia el orbe: la magia que lo sostiene.
LIFT_MOTES = [(0, -8), (6, 5), (12, -2), (18, 9), (24, -10), (30, 2), (36, 7), (42, -5)]


def draw_lift_motes(cv, f):
    for start, dx in LIFT_MOTES:
        age = (f - start) % FRAMES
        if age >= 14:
            continue
        sway = round(math.sin(age * 0.6 + dx) * 0.8)
        y = GROUND_Y - 2 - int(age * 1.6)
        c = 'p3' if age < 4 else ('p4' if age < 8 else ('p5' if age < 12 else 'p6'))
        cv.put(ORB_X + dx + sway, y, c)


SPARKLES = [(0, 12, 12), (7, 68, 22), (13, 9, 60), (20, 70, 64), (26, 58, 9),
            (33, 20, 30), (38, 64, 38), (43, 30, 6)]


def draw_sparkles(cv, f):
    for start, x, y in SPARKLES:
        age = (f - start) % FRAMES
        if age == 0 or age == 4:
            cv.put(x, y, 'c2')
        elif age == 1 or age == 3:
            cv.put(x, y, 'w')
            for dx, dy in N4:
                cv.put(x + dx, y + dy, 'c2')
        elif age == 2:
            cv.put(x, y, 'w')
            for dx, dy in N4:
                cv.put(x + dx, y + dy, 'c3')
                cv.put(x + 2 * dx, y + 2 * dy, 'c2')


MOTES = [0, 8, 16, 24, 30, 35, 38, 42]


def draw_motes(cv, f, ox, oy):
    """Chispas que escapan de la grieta y suben."""
    for i, start in enumerate(MOTES):
        age = (f - start) % FRAMES
        if age >= 12:
            continue
        sx, sy = CRACK[(i * 3) % len(CRACK)]
        x = ox + sx + round(math.sin(age * 0.7 + i) * 1.2) + (age // 4)
        y = oy + sy - 2 - int(age * 1.3)
        c = 'm3' if age < 3 else ('m2' if age < 7 else 'p5')
        cv.put(x, y, c)


# ---------------------------------------------------------------------------
# Fotograma completo
# ---------------------------------------------------------------------------
def render(f):
    cv = Canvas()
    ox = ORB_X + SHAKE.get(f, 0)
    oy = ORB_Y + round(bob(f))
    draw_shadow(cv, f)
    draw_lift_motes(cv, f)
    draw_orbiters(cv, f, front=False)
    draw_shockwave(cv, f, ox, oy)
    draw_aura(cv, f, ox, oy)
    draw_orb(cv, ox, oy, f)
    draw_face(cv, ox, oy, f)
    draw_tear_streams(cv, f, ox, oy)
    draw_drops(cv, f)
    draw_orbiters(cv, f, front=True)
    draw_motes(cv, f, ox, oy)
    draw_sparkles(cv, f)
    return cv


# ---------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------
def export(frames):
    names = sorted(RGB)
    index = {name: i + 1 for i, name in enumerate(names)}   # 0 = transparente

    def paletted(cv, bg=None):
        img = Image.new('P', (W, H), 0)
        img.putdata([index[c] if c else 0 for row in cv.px for c in row])
        pal = list(bg or (0, 0, 0))
        for name in names:
            pal.extend(RGB[name])
        img.putpalette(pal)
        return img

    # GIF a tamaño real con transparencia
    gif = [paletted(cv) for cv in frames]
    gif[0].save(os.path.join(HERE, 'orbe_sufriente.gif'), save_all=True,
                append_images=gif[1:], duration=FRAME_MS, loop=0,
                transparency=0, disposal=2, optimize=False)

    # vista previa ampliada con fondo
    bg = tuple(int(PREVIEW_BG[i:i + 2], 16) for i in (0, 2, 4))
    big = [paletted(cv, bg).resize((W * PREVIEW_SCALE, H * PREVIEW_SCALE), Image.NEAREST)
           for cv in frames]
    big[0].save(os.path.join(HERE, f'orbe_sufriente_x{PREVIEW_SCALE}.gif'), save_all=True,
                append_images=big[1:], duration=FRAME_MS, loop=0, optimize=False)

    # tira de sprites RGBA
    sheet = Image.new('RGBA', (W * len(frames), H), (0, 0, 0, 0))
    for i, cv in enumerate(frames):
        img = Image.new('RGBA', (W, H))
        img.putdata([RGB[c] + (255,) if c else (0, 0, 0, 0) for row in cv.px for c in row])
        sheet.paste(img, (i * W, 0))
    sheet.save(os.path.join(HERE, 'orbe_sufriente_spritesheet.png'))


def main():
    frames = [render(f) for f in range(FRAMES)]
    export(frames)
    print(f'{FRAMES} fotogramas de {W}x{H} px generados en {HERE}')


if __name__ == '__main__':
    main()
