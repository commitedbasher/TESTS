#!/usr/bin/env python3
"""
Gema sufriente: animación en pixel art de 80x95 px.

Una gema morada de talla irregular que levita. Dentro hay un rostro atrapado
que sufre en silencio: cuencas hundidas, cejas de angustia y una boca que se
abre despacio hasta un grito mudo, para luego hundirse otra vez en la
desesperación. Alrededor orbitan fragmentos de la propia gema y piedras
rúnicas que la mantienen sellada. El bucle es perfecto.

Salida (en la misma carpeta que este script):
  gema_sufriente.gif              animación a tamaño real, fondo transparente
  gema_sufriente_x4.gif           vista previa ampliada x4 con fondo oscuro
  gema_sufriente_spritesheet.png  tira horizontal con todos los fotogramas

Uso:
  pip install pillow
  python3 generar_gema.py
"""

import math
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

W, H = 80, 95          # tamaño del lienzo
FRAMES = 64            # fotogramas del bucle
FRAME_MS = 80          # duración de cada fotograma
PREVIEW_SCALE = 4
PREVIEW_BG = '17121f'

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
PALETTE = {
    # vacío (ojos y boca) y contorno
    'v0': '0a0612', 'g0': '150a24',
    # rampa de la gema: sombras índigo, luces lila pálido
    'g1': '1f1238', 'g2': '2c1850', 'g3': '3e1f6b', 'g4': '542784',
    'g5': '6d329c', 'g6': '8a45b4', 'g7': 'a860c8', 'g8': 'c587dc',
    'g9': 'e2b8ee', 'w': 'fff0fb',
    # rampa azul-violeta: las facetas que miran a la derecha o hacia abajo
    # cambian de color, como una tanzanita (pleocroísmo)
    'b1': '181236', 'b2': '221a52', 'b3': '2e2470', 'b4': '3b2f8c',
    'b5': '4b3ea6', 'b6': '6152bd', 'b7': '7e6fd2', 'b8': 'a193e3',
    'b9': 'c9bff3',
    # runas frías de los sellos
    'c0': '0f2a36', 'c1': '1d5a6c', 'c2': '4fb0c2', 'c3': 'b0ecf3',
    # obsidiana
    's0': '08070d', 's1': '14121c', 's2': '211e2b', 's3': '322e40',
    's4': '4a4560', 's5': '6b6585',
    # sombra en el suelo
    'sh': '06030b',
}
RGB = {k: tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) for k, v in PALETTE.items()}

GEM_RAMP = ('g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9', 'w')
BLUE_RAMP = ('b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b8', 'b9', 'w')

# Un paso más oscuro de cada color: para lo que pasa por detrás de la gema.
DARKER = {
    'w': 'g9', 'g9': 'g8', 'g8': 'g7', 'g7': 'g6', 'g6': 'g5', 'g5': 'g4',
    'g4': 'g3', 'g3': 'g2', 'g2': 'g1', 'g1': 'g0', 'g0': 'g0', 'v0': 'v0',
    'b9': 'b8', 'b8': 'b7', 'b7': 'b6', 'b6': 'b5', 'b5': 'b4', 'b4': 'b3',
    'b3': 'b2', 'b2': 'b1', 'b1': 'g0',
    'c3': 'c2', 'c2': 'c1', 'c1': 'c0', 'c0': 's0',
    's5': 's4', 's4': 's3', 's3': 's2', 's2': 's1', 's1': 's0', 's0': 's0',
}

BAYER4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def tau(x):
    return 2.0 * math.pi * x


def darken(c, steps):
    for _ in range(steps):
        c = DARKER.get(c, c)
    return c


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


def normalize(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


# ---------------------------------------------------------------------------
# Lienzo
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self):
        self.px = [[None] * W for _ in range(H)]

    def put(self, x, y, c):
        if c and 0 <= x < W and 0 <= y < H:
            self.px[y][x] = c


def mirrored(half_rows):
    """Sprite simétrico de ancho impar: cada fila llega hasta la columna central."""
    return [row + row[-2::-1] for row in half_rows]


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
# Línea de tiempo
# ---------------------------------------------------------------------------
GEM_X, GEM_Y = 40, 43   # centro de la gema
GROUND_Y = 89           # fila del suelo

# Temblor durante el grito mudo (desplazamiento horizontal).
SHAKE = {31: 1, 33: -1, 35: 1, 36: -1, 38: 1, 40: -1}


def anguish(f):
    """0,1 = desesperación contenida ... 1 = grito mudo (fotogramas 28-40)."""
    return 0.1 + 0.9 * (smoothstep(12, 28, f) - smoothstep(40, 62, f))


def bob(f, lag=0.0):
    """Levitación lenta y pesada: una oscilación por bucle."""
    return -2.0 * math.sin(tau((f - lag) / FRAMES))


# ---------------------------------------------------------------------------
# Gema: talla irregular con tabla central y facetas de corona
# ---------------------------------------------------------------------------
OUTLINE = [(2, -29), (12, -21), (18, -9), (19, 5), (11, 19),
           (-1, 30), (-11, 20), (-18, 8), (-17, -6), (-10, -20)]
TABLE = [(x * 0.52, y * 0.52 - 1) for x, y in OUTLINE]
TABLE_Z = 9.0           # altura de la tabla sobre el filetín

LIGHT = normalize((-0.45, -0.7, 0.55))
HALF = normalize((LIGHT[0], LIGHT[1], LIGHT[2] + 1.0))


def plane_normal(p3):
    """Normal del plano z = a*x + b*y + c que pasa por tres puntos."""
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = p3
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    a = ((z1 - z0) * (y2 - y0) - (z2 - z0) * (y1 - y0)) / det
    b = ((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / det
    return normalize((-a, -b, 1.0))


def facet_level(n):
    diff = max(0.0, sum(a * b for a, b in zip(n, LIGHT)))
    spec = max(0.0, sum(a * b for a, b in zip(n, HALF))) ** 24
    return max(0, min(7, int(1.0 + diff * 5.5 + spec * 3.0)))


def build_facets():
    facets = [(TABLE, (0.0, 0.0, 1.0))]
    n = len(OUTLINE)
    for i in range(n):
        o0, o1 = OUTLINE[i], OUTLINE[(i + 1) % n]
        t0, t1 = TABLE[i], TABLE[(i + 1) % n]
        for tri in ((o0, o1, t1), (o0, t1, t0)):
            p3 = [(p[0], p[1], TABLE_Z if p in (t0, t1) else 0.0) for p in tri]
            facets.append((tri, plane_normal(p3)))
    return facets


def build_gem():
    """Píxeles de la gema relativos a su centro con su faceta y nivel base."""
    facets = build_facets()
    cells = raster_poly(OUTLINE)
    facet_of = {}
    for (x, y) in cells:
        cx, cy = x + 0.5, y + 0.5
        for k, (poly, _) in enumerate(facets):
            if point_in_poly(cx, cy, poly):
                facet_of[(x, y)] = k
                break
        else:   # justo sobre una arista: la faceta más cercana
            facet_of[(x, y)] = min(
                range(len(facets)),
                key=lambda k: sum((sum(p[i] for p in facets[k][0]) / len(facets[k][0]) - c) ** 2
                                  for i, c in enumerate((cx, cy))))
    edge = {p for p in cells if any((p[0] + dx, p[1] + dy) not in cells for dx, dy in N4)}
    level = {p: facet_level(facets[facet_of[p]][1]) for p in cells}
    ramp = {}
    for p in cells:
        n = facets[facet_of[p]][1]
        blue = facet_of[p] != 0 and (n[0] > 0.15 or n[1] > 0.35)
        ramp[p] = BLUE_RAMP if blue else GEM_RAMP
    # arista de la tabla: canto iluminado arriba a la izquierda, sombra abajo
    for p in cells:
        if facet_of[p] != 0 or p in edge:
            continue
        if any(facet_of.get((p[0] + dx, p[1] + dy), 0) != 0 for dx, dy in N4):
            level[p] += 1 if (p[0] + p[1]) < -4 else -1
    return cells, edge, level, ramp


GEM_CELLS, GEM_EDGE, GEM_LEVEL, GEM_RAMP_OF = build_gem()

# Grietas (relativas al centro): una baja hacia el ojo derecho como una
# cicatriz y otra muerde el borde inferior izquierdo.
CRACKS = [(15, -15), (14, -15), (13, -14), (12, -13), (12, -12), (11, -11), (10, -10),
          (13, -12), (14, -11),
          (-15, 13), (-14, 13), (-13, 12), (-12, 12), (-11, 11), (-12, 11)]

# ---------------------------------------------------------------------------
# Rostro atrapado: relieves de luz y sombra sobre la gema
#   '#' vacío   '=' -2 niveles   '-' -1 nivel   'o' pupila   '.' nada
# Mitades izquierdas hasta la columna central (x = 0); la derecha se refleja.
# ---------------------------------------------------------------------------
FACE_DX, FACE_DY = 0, -2        # posición del rostro dentro de la gema

EYES_REST = mirrored([            # filas y = -12 .. 0
    "...........",
    "...........",
    "........-=.",
    "......-=-.-",
    "...--=-....",
    "..-........",
    "....-==-...",
    "..-=####=..",
    ".-=##o##-..",
    ".==###=-...",
    "..-==--....",
    "...--......",
    "...........",
])

EYES_BLINK = mirrored([           # parpadeo lento y pesado
    "...........",
    "...........",
    "........-=.",
    "......-=-.-",
    "...--=-....",
    "..-........",
    "....-==-...",
    "..-=-===-..",
    ".-=====-...",
    ".=##=-.....",
    "..--.......",
    "...........",
    "...........",
])
BLINK = (8, 9)
QUIVER = (58, 59, 62, 63, 2, 3, 6, 7)   # la mandíbula tiembla: un sollozo ahogado

EYES_STRAIN = mirrored([
    "...........",
    "........-=-",
    "......-==.-",
    "....-==-..=",
    "..-==-.....",
    "...........",
    ".....-===..",
    "..-=####-..",
    ".-=####=...",
    ".=##o#=....",
    "..=#=-.....",
    "...-.......",
    "...........",
])

EYES_SCREAM = mirrored([
    "........-=-",
    "......-==.=",
    "....-==-..=",
    "..-==-....-",
    "...........",
    "....-===-..",
    "..-=####=..",
    ".-=#####-..",
    ".=#####=...",
    ".=####=....",
    "..=##=.....",
    "...=-......",
    "..-........",
])

CHEEKS = mirrored([               # filas y = 1 .. 9, mejillas hundidas
    ".-........=",
    "..-.......-",
    "..-........",
    "..-........",
    "...-.......",
    "...-.......",
    "....-......",
    "....-......",
    "...........",
])

def centered(rows, width=21):
    """Centra un sprite de ancho impar en el ancho común del rostro."""
    pad = (width - len(rows[0])) // 2
    return ['.' * pad + row + '.' * pad for row in rows]


MOUTH_REST = centered([           # filas y = 4 .. 14
    "...........",
    "...=====...",
    "..=#####=..",
    ".=#######=.",
    "=##=---=##=",
    "#=-.....-=#",
    "-.........-",
    "...........",
    "...........",
    "...........",
    "...........",
])

MOUTH_TREMBLE = centered([
    "...........",
    "...=====...",
    "..=#####=..",
    ".=#######=.",
    "=#########=",
    "#=--...--=#",
    "-.........-",
    "...........",
    "...........",
    "...........",
    "...........",
])

MOUTH_OPEN = mirrored([
    "...........",
    "........===",
    ".......=###",
    "......=####",
    "......=####",
    "......#=-==",
    "......-....",
    "...........",
    "...........",
    "...........",
    "...........",
])

MOUTH_WIDE = mirrored([
    ".........==",
    "........=##",
    ".......=###",
    "......=####",
    "......=####",
    "......=####",
    ".......=###",
    "........=##",
    ".........==",
    "...........",
    "...........",
])

MOUTH_SCREAM = mirrored([
    ".........==",
    "........=##",
    ".......=###",
    ".......=###",
    ".......=###",
    ".......=###",
    ".......=###",
    ".......=###",
    "........=##",
    "........=##",
    ".........==",
])

FACE_W = 21     # ancho de todos los sprites del rostro


def face_layers(f):
    """Sprites del rostro para el fotograma f: [(filas, y_inicial)]."""
    a = anguish(f)
    if f in BLINK:
        eyes = EYES_BLINK
    elif a < 0.3:
        eyes = EYES_REST
    elif a < 0.7:
        eyes = EYES_STRAIN
    else:
        eyes = EYES_SCREAM
    if a < 0.2:
        mouth = MOUTH_TREMBLE if f in QUIVER else MOUTH_REST
    elif a < 0.45:
        mouth = MOUTH_OPEN
    elif a < 0.75:
        mouth = MOUTH_WIDE
    else:
        mouth = MOUTH_SCREAM
    lift = -1 if a >= 0.75 else 0      # el rostro se estira hacia arriba
    layers = [(eyes, -12 + lift), (mouth, 4)]
    if a >= 0.45:
        layers.append((CHEEKS, 1 + lift))
    return layers


def render_gem(f):
    """Colores de la gema en el fotograma f, relativos a su centro."""
    a = anguish(f)
    light = 0.25 + 0.75 * a
    if a > 0.9:
        light += 0.15 * ((f * 7) % 3 - 1)      # la luz titila en pleno grito

    # luz interior del alma, centrada en el rostro
    lv = {}
    for (x, y), base in GEM_LEVEL.items():
        gx = (x + 0.5 - FACE_DX) / 11.0
        gy = (y + 0.5 - FACE_DY - 1) / 15.0
        g = max(0.0, 1.0 - gx * gx - gy * gy)
        v = base + g * (1.0 + 2.2 * light)
        v += (BAYER4[y % 4][x % 4] / 16.0 - 0.47) * 0.35
        lv[(x, y)] = int(math.floor(v + 0.5))

    special = {}
    x0 = FACE_DX - FACE_W // 2
    for rows, ry in face_layers(f):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                p = (x0 + i, FACE_DY + ry + j)
                if ch == '.' or p not in lv or p in GEM_EDGE:
                    continue
                if ch == '#':
                    special[p] = 'v0'
                elif ch == 'o':
                    special[p] = 'g9' if a < 0.5 else 'v0'
                else:
                    lv[p] -= 2 if ch == '=' else 1

    # grietas: fisura oscura con canto claro; en el grito escapa la luz
    glow = a > 0.8
    crack = set(CRACKS)
    for (x, y) in CRACKS:
        n = (x + 1, y + 1)
        if n in lv and n not in crack and n not in GEM_EDGE:
            lv[n] += 3 if glow else 2
    for p in CRACKS:
        if p in lv:
            special[p] = 'g9' if glow else 'g0'

    out = {}
    for p in GEM_CELLS:
        if p in GEM_EDGE:
            out[p] = 'g0'
        elif p in special:
            out[p] = special[p]
        else:
            ramp = GEM_RAMP_OF[p]
            out[p] = ramp[max(0, min(len(ramp) - 1, lv[p]))]
    return out


# Destellos en los vértices de la gema: (fotograma, vértice)
GLINTS = [(3, 0), (13, 3), (57, 1)]


def draw_glints(cv, f, ox, oy):
    for start, vi in GLINTS:
        age = (f - start) % FRAMES
        if age > 4:
            continue
        x, y = OUTLINE[vi]
        x, y = ox + int(x), oy + int(y)
        size = (1, 2, 3, 2, 1)[age]
        cv.put(x, y, 'w')
        for dx, dy in N4:
            for k in range(1, size):
                cv.put(x + dx * k, y + dy * k, 'g9' if k == 1 else 'g7')


# ---------------------------------------------------------------------------
# Humo oscuro que se escapa por la punta y onda del grito mudo
# ---------------------------------------------------------------------------
WISPS = [(0, 0), (8, 2), (16, -1), (24, 1), (32, -2), (40, 0), (48, 2), (56, -1)]


def draw_wisps(cv, f, ox, oy):
    for i, (start, dx) in enumerate(WISPS):
        age = (f - start) % FRAMES
        if age >= 18:
            continue
        sway = round(math.sin(age * 0.45 + i * 1.7) * (0.5 + age * 0.12))
        x = ox + OUTLINE[0][0] + dx + sway
        y = oy + OUTLINE[0][1] - 2 - age
        c = 'g5' if age < 5 else ('g4' if age < 10 else ('g3' if age < 14 else 'g2'))
        cv.put(x, y, c)
        if age < 9 and (age + i) % 3 == 0:
            cv.put(x + (1 if i % 2 else -1), y + 1, darken(c, 1))


WAVES = [28, 35]


def draw_waves(cv, f, ox, oy):
    for start in WAVES:
        k = (f - start) % FRAMES
        if k >= 16:
            continue
        r = 25 + k * 2.0
        rx, ry = r * 0.82, r * 1.05
        col = ('g7', 'g6', 'g5', 'g4')[k // 4]
        for y in range(int(oy - ry - 2), int(oy + ry + 3)):
            for x in range(int(ox - rx - 2), int(ox + rx + 3)):
                d = math.hypot((x + 0.5 - ox) / rx, (y + 0.5 - oy) / ry)
                if abs(d - 1.0) * r > 0.6:
                    continue
                if k >= 4 and (x + y) % 2:
                    continue
                if k >= 8 and (x // 2 + y) % 2:
                    continue
                if k >= 12 and (x + y // 2) % 3:
                    continue
                cv.put(x, y, col)


# ---------------------------------------------------------------------------
# Sombra en el suelo
# ---------------------------------------------------------------------------
def draw_shadow(cv, f):
    lift = bob(f)                       # negativo = más alto
    hw = 12.5 + lift * 0.9
    hh = 2.4 + lift * 0.12
    for y in range(GROUND_Y - 4, GROUND_Y + 5):
        for x in range(W):
            nx = (x + 0.5 - GEM_X) / hw
            ny = (y + 0.5 - GROUND_Y) / hh
            d = nx * nx + ny * ny
            if d <= 0.55 or (d <= 1.0 and (x + y) % 2 == 0):
                cv.put(x, y, 'sh')


# ---------------------------------------------------------------------------
# Objetos en órbita: fragmentos de la gema y piedras-sello con runas
# ---------------------------------------------------------------------------
ORBIT_A, ORBIT_B = 33.0, 11.0
ORBIT_TILT = -0.15
ORBIT_DY = 8                # la órbita rodea la parte baja de la gema


def orbit_pos(theta, cx, cy, a=ORBIT_A, b=ORBIT_B):
    ex, ey = a * math.cos(theta), b * math.sin(theta)
    ct, st = math.cos(ORBIT_TILT), math.sin(ORBIT_TILT)
    return cx + ex * ct - ey * st, cy + ex * st + ey * ct, math.sin(theta)


STONES = {
    'A': dict(poly=[(-4, -2), (-2, -4), (2, -4.2), (4.5, -1), (4, 3), (1, 4.2), (-3, 3.8), (-4.6, 1)],
              rune=["r.r", ".r.", ".r."]),
    'B': dict(poly=[(-1, -5.2), (2.5, -3), (3.4, 2), (1, 5), (-2.6, 4), (-3.4, -1)],
              rune=[".r.", "r.r", ".r.", ".r."]),
    'C': dict(poly=[(-5.5, -1), (-3, -3.6), (3, -3.4), (5.6, 0), (4, 3.2), (-3.5, 3.4)],
              rune=["r..", ".r.", "..r"]),
}
STONE_RAMP = ('s1', 's2', 's3', 's4', 's5')


def draw_stone(cv, spec, x, y, rot, scale, dark, rune_col):
    ca, sa = math.cos(rot), math.sin(rot)
    pts = [(x + (px * ca - py * sa) * scale, y + (px * sa + py * ca) * scale)
           for px, py in spec['poly']]
    cells = raster_poly(pts)
    if not cells:
        return
    for (px, py) in outer_ring(cells):
        cv.put(px, py, darken('s0', dark))
    rx = max(abs(p[0] - x) for p in pts) or 1
    ry = max(abs(p[1] - y) for p in pts) or 1
    for (px, py) in cells:
        nx, ny = (px + 0.5 - x) / rx, (py + 0.5 - y) / ry
        v = 0.45 - (nx * 0.6 + ny * 0.8) * 0.45
        v += (BAYER4[py % 4][px % 4] / 16.0 - 0.47) * 0.12
        idx = max(0, min(len(STONE_RAMP) - 1, int(v * len(STONE_RAMP))))
        cv.put(px, py, darken(STONE_RAMP[idx], dark))
    rune = spec['rune']
    rx0 = int(round(x - len(rune[0]) / 2.0))
    ry0 = int(round(y - len(rune) / 2.0))
    for j, row in enumerate(rune):
        for i, ch in enumerate(row):
            if ch == 'r' and (rx0 + i, ry0 + j) in cells:
                cv.put(rx0 + i, ry0 + j, darken(rune_col, dark))


def draw_shard(cv, x, y, length, width, rot, tumble, dark):
    ux, uy = math.cos(rot), math.sin(rot)
    vx, vy = -uy, ux
    face = math.cos(tumble)
    w = max(1.25, width * abs(face))
    pts = [(x + ux * length * 0.6, y + uy * length * 0.6),
           (x + vx * w, y + vy * w),
           (x - ux * length * 0.4, y - uy * length * 0.4),
           (x - vx * w * 0.7, y - vy * w * 0.7)]
    cells = raster_poly(pts)
    if not cells:
        return
    for (px, py) in outer_ring(cells):
        cv.put(px, py, darken('g0', dark))
    light_side = 1 if face > 0 else -1
    for (px, py) in cells:
        s = (px + 0.5 - x) * vx + (py + 0.5 - y) * vy
        c = 'g8' if s * light_side > 0 else 'g5'
        cv.put(px, py, darken(c, dark))
    if abs(face) > 0.9:
        tx = int(math.floor(x + ux * length * 0.3))
        ty = int(math.floor(y + uy * length * 0.3))
        cv.put(tx, ty, darken('w', dark))


# (tipo, fase inicial en la órbita como fracción de vuelta, parámetros)
ORBITERS = [
    ('stone', 0.00, dict(key='A', spin=0.5)),
    ('shard', 0.17, dict(length=10, width=3.0, spin=-0.5, tumble=1)),
    ('stone', 0.34, dict(key='B', spin=-0.4)),
    ('shard', 0.50, dict(length=8, width=2.6, spin=1.0, tumble=2)),
    ('stone', 0.66, dict(key='C', spin=0.3)),
    ('shard', 0.83, dict(length=9, width=2.8, spin=-1.0, tumble=1)),
]

DUST = [(0.1, 0.9, 'g7'), (0.36, 1.1, 'g6'), (0.6, 0.86, 'g8'), (0.85, 1.08, 'g6')]


def draw_orbiters(cv, f, front):
    a_ = anguish(f)
    cx, cy = GEM_X, GEM_Y + ORBIT_DY + bob(f, lag=3.0)
    push = 2.5 * smoothstep(0.75, 1.0, a_)        # el grito empuja la órbita
    a, b = ORBIT_A + push, ORBIT_B + push * 0.3
    t = f / FRAMES
    items = []
    for kind, phase, p in ORBITERS:
        theta = tau(phase - t)
        x, y, z = orbit_pos(theta, cx, cy, a, b)
        y += math.sin(tau(t + phase * 2)) * 0.8
        if (z >= 0) == front:
            items.append((z, kind, x, y, theta, phase, p))
    items.sort(key=lambda it: it[0])

    # estela tenue
    for z, kind, x, y, theta, phase, p in items:
        col = 'g4' if kind == 'shard' else 'c1'
        for k in (1, 2):
            tx, ty, tz = orbit_pos(theta + 0.12 * (k + 1.4), cx, cy, a, b)
            if (tz >= 0) == front and (k == 1 or f % 2 == 0):
                cv.put(int(math.floor(tx)), int(math.floor(ty)), darken(col, 0 if tz >= 0 else 1))

    for z, kind, x, y, theta, phase, p in items:
        dark = 0 if z > -0.25 else (1 if z > -0.7 else 2)
        scale = 0.85 + 0.2 * (z + 1) / 2
        if kind == 'stone':
            rot = math.sin(tau(t + phase)) * 0.35 * p['spin']
            if a_ > 0.8:
                rune = 'w' if (f // 3) % 2 else 'c3'   # los sellos contienen el grito
            else:
                rune = 'c2' if ((f + int(phase * 16)) // 4) % 3 else 'c3'
            draw_stone(cv, STONES[p['key']], x, y, rot, scale, dark, rune)
        else:
            rot = tau(p['spin'] * t + phase)
            tumble = tau(p['tumble'] * t + phase)
            draw_shard(cv, x, y, p['length'] * scale, p['width'] * scale, rot, tumble, dark)

    for phase, rf, col in DUST:
        theta = tau(phase - 2 * t)
        x, y, z = orbit_pos(theta, cx, cy, a * rf, b * rf)
        if (z >= 0) == front and (f + int(phase * 10)) % 4:
            cv.put(int(math.floor(x)), int(math.floor(y)), darken(col, 0 if z >= 0 else 1))


# ---------------------------------------------------------------------------
# Fotograma completo
# ---------------------------------------------------------------------------
def render(f):
    cv = Canvas()
    ox = GEM_X + SHAKE.get(f, 0)
    oy = GEM_Y + round(bob(f))
    draw_shadow(cv, f)
    draw_orbiters(cv, f, front=False)
    draw_waves(cv, f, ox, oy)
    for (dx, dy), c in render_gem(f).items():
        cv.put(ox + dx, oy + dy, c)
    if anguish(f) < 0.5:
        draw_glints(cv, f, ox, oy)
    draw_orbiters(cv, f, front=True)
    draw_wisps(cv, f, ox, oy)
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
    gif[0].save(os.path.join(HERE, 'gema_sufriente.gif'), save_all=True,
                append_images=gif[1:], duration=FRAME_MS, loop=0,
                transparency=0, disposal=2, optimize=False)

    # vista previa ampliada con fondo
    bg = tuple(int(PREVIEW_BG[i:i + 2], 16) for i in (0, 2, 4))
    big = [paletted(cv, bg).resize((W * PREVIEW_SCALE, H * PREVIEW_SCALE), Image.NEAREST)
           for cv in frames]
    big[0].save(os.path.join(HERE, f'gema_sufriente_x{PREVIEW_SCALE}.gif'), save_all=True,
                append_images=big[1:], duration=FRAME_MS, loop=0, optimize=False)

    # tira de sprites RGBA
    sheet = Image.new('RGBA', (W * len(frames), H), (0, 0, 0, 0))
    for i, cv in enumerate(frames):
        img = Image.new('RGBA', (W, H))
        img.putdata([RGB[c] + (255,) if c else (0, 0, 0, 0) for row in cv.px for c in row])
        sheet.paste(img, (i * W, 0))
    sheet.save(os.path.join(HERE, 'gema_sufriente_spritesheet.png'))


def main():
    frames = [render(f) for f in range(FRAMES)]
    export(frames)
    print(f'{FRAMES} fotogramas de {W}x{H} px generados en {HERE}')


if __name__ == '__main__':
    main()
