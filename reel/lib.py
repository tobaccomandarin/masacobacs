"""Shared helpers: timeline constants, easing curves, colour, and glyph-outline typography.

Everything in the reel is drawn procedurally with cairo. Text is rendered from real
font outlines (fontTools -> cairo paths) so every glyph can be animated independently.
"""
import math
import os

import cairo
from fontTools.pens.cairoPen import CairoPen
from fontTools.ttLib import TTFont

# ---------------------------------------------------------------- timeline
W, H = 1080, 1920
BPM = 128.0
BEAT = 60.0 / BPM            # 0.46875 s
BARS = 8
DURATION = BARS * 4 * BEAT   # exactly 15.0 s

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

# ---------------------------------------------------------------- palette
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)

INK = hexc("0E0D0C")
PAPER = hexc("F3EEE5")
CORAL = hexc("E2683F")
BLUE = hexc("2F4BFF")
LIME = hexc("D6FF3D")
GRAPHITE = hexc("5B5750")


def with_alpha(c, a):
    return (c[0], c[1], c[2], c[3] * a)


def mix(c1, c2, p):
    return tuple(c1[i] + (c2[i] - c1[i]) * p for i in range(4))


def setc(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], c[3] * a)


# ---------------------------------------------------------------- math / easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, p):
    return a + (b - a) * p


def prog(x, a, b):
    """0..1 progress of x through the window [a, b]."""
    if b == a:
        return 1.0 if x >= b else 0.0
    return clamp((x - a) / (b - a))


def eo_expo(p):
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)


def ei_expo(p):
    return 0.0 if p <= 0 else 2 ** (10 * p - 10)


def eio_expo(p):
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    return 2 ** (20 * p - 10) / 2 if p < 0.5 else (2 - 2 ** (-20 * p + 10)) / 2


def eo_cubic(p):
    return 1 - (1 - p) ** 3


def ei_cubic(p):
    return p ** 3


def eio_cubic(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def eo_quint(p):
    return 1 - (1 - p) ** 5


def eo_back(p, s=1.70158):
    q = p - 1
    return 1 + (s + 1) * q ** 3 + s * q ** 2


def ei_back(p, s=1.70158):
    return (s + 1) * p ** 3 - s * p ** 2


def eio_back(p, s=1.70158):
    s2 = s * 1.525
    if p < 0.5:
        return ((2 * p) ** 2 * ((s2 + 1) * 2 * p - s2)) / 2
    return ((2 * p - 2) ** 2 * ((s2 + 1) * (p * 2 - 2) + s2) + 2) / 2


def spring(t, freq=18.0, damp=7.0):
    """Damped spring settling from 0 to 1; t in seconds."""
    if t <= 0:
        return 0.0
    return 1 - math.exp(-damp * t) * math.cos(freq * t)


def cubic_bezier(x1, y1, x2, y2):
    """CSS cubic-bezier timing function."""
    def bez(t, a, b):
        return 3 * a * (1 - t) ** 2 * t + 3 * b * (1 - t) * t ** 2 + t ** 3

    def f(x):
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if bez(mid, x1, x2) < x:
                lo = mid
            else:
                hi = mid
        return bez((lo + hi) / 2, y1, y2)
    return f


EXPO_OUT = cubic_bezier(0.16, 1.0, 0.3, 1.0)


def hash01(*args):
    """Deterministic pseudo-random 0..1 from integers."""
    h = 2166136261
    for a in args:
        h ^= int(a) & 0xFFFFFFFF
        h = (h * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    return (h & 0xFFFFFF) / float(0xFFFFFF)


# ---------------------------------------------------------------- typography
class Font:
    """A font whose glyph outlines are cached as cairo paths in font units."""

    def __init__(self, filename):
        self.tt = TTFont(os.path.join(FONT_DIR, filename))
        self.cmap = self.tt.getBestCmap()
        self.gs = self.tt.getGlyphSet()
        self.upm = self.tt["head"].unitsPerEm
        os2 = self.tt["OS/2"]
        self.cap = getattr(os2, "sCapHeight", 0) or int(self.upm * 0.7)
        self.xh = getattr(os2, "sxHeight", 0) or int(self.upm * 0.5)
        self.hmtx = self.tt["hmtx"]
        self._paths = {}
        self._scratch = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A8, 1, 1))
        self.kern = self._load_kerning()

    def _load_kerning(self):
        pairs = {}
        if "GPOS" not in self.tt:
            return pairs
        gpos = self.tt["GPOS"].table
        for lookup in gpos.LookupList.Lookup:
            subs = []
            for st in lookup.SubTable:
                if lookup.LookupType == 9:
                    st = st.ExtSubTable
                if getattr(st, "LookupType", lookup.LookupType) == 2:
                    subs.append(st)
            for st in subs:
                cov = st.Coverage.glyphs
                if st.Format == 1:
                    for i, first in enumerate(cov):
                        for rec in st.PairSet[i].PairValueRecord:
                            v = getattr(rec.Value1, "XAdvance", 0) if rec.Value1 else 0
                            if v:
                                pairs.setdefault((first, rec.SecondGlyph), v)
                elif st.Format == 2:
                    c1 = st.ClassDef1.classDefs
                    c2 = st.ClassDef2.classDefs
                    self._class_kern = getattr(self, "_class_kern", [])
                    self._class_kern.append((set(cov), c1, c2, st.Class1Record))
        return pairs

    def kerning(self, a, b):
        v = self.kern.get((a, b))
        if v is not None:
            return v
        for cov, c1, c2, recs in getattr(self, "_class_kern", []):
            if a in cov:
                r = recs[c1.get(a, 0)].Class2Record[c2.get(b, 0)]
                v = getattr(r.Value1, "XAdvance", 0) if r.Value1 else 0
                if v:
                    return v
        return 0

    def gname(self, ch):
        return self.cmap.get(ord(ch))

    def path(self, gname):
        p = self._paths.get(gname)
        if p is None:
            ctx = self._scratch
            ctx.new_path()
            self.gs[gname].draw(CairoPen(self.gs, ctx))
            p = ctx.copy_path()
            ctx.new_path()
            self._paths[gname] = p
        return p

    def layout(self, text, size, tracking=0.0):
        """Return ([(char, gname, x, advance_px)], total_width_px).

        tracking is in em/1000 like design tools."""
        s = size / self.upm
        out = []
        x = 0.0
        prev = None
        for ch in text:
            g = self.gname(ch)
            if g is None:
                g = self.gname(" ")
            if prev is not None:
                x += self.kerning(prev, g) * s
            adv = self.hmtx[g][0] * s
            out.append((ch, g, x, adv))
            x += adv + tracking / 1000.0 * size
            prev = g
        width = x - (tracking / 1000.0 * size if text else 0)
        return out, width

    def width(self, text, size, tracking=0.0):
        return self.layout(text, size, tracking)[1]

    def glyph(self, ctx, gname, x, y, size):
        """Append a glyph outline with its baseline origin at (x, y)."""
        s = size / self.upm
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(s, -s)
        ctx.append_path(self.path(gname))
        ctx.restore()

    def text(self, ctx, text, x, y, size, tracking=0.0, align="left"):
        glyphs, w = self.layout(text, size, tracking)
        if align == "center":
            x -= w / 2
        elif align == "right":
            x -= w
        for ch, g, gx, _ in glyphs:
            if ch != " ":
                self.glyph(ctx, g, x + gx, y, size)
        return w

    def cap_px(self, size):
        return self.cap / self.upm * size


_fonts = {}


def font(key):
    files = {
        "black": "inter-latin-900-normal.woff",
        "semi": "inter-latin-600-normal.woff",
        "mono": "jetbrains-mono-latin-500-normal.woff",
        "serif": "instrument-serif-latin-400-normal.woff",
        "italic": "instrument-serif-latin-400-italic.woff",
        "jp": "noto-sans-jp-japanese-700-normal.woff",
    }
    f = _fonts.get(key)
    if f is None:
        f = _fonts[key] = Font(files[key])
    return f


# ---------------------------------------------------------------- shapes
def rounded_rect(ctx, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def diamond(ctx, cx, cy, r):
    ctx.move_to(cx, cy - r)
    ctx.line_to(cx + r, cy)
    ctx.line_to(cx, cy + r)
    ctx.line_to(cx - r, cy)
    ctx.close_path()


def star4(ctx, cx, cy, r, pinch=0.28):
    """Four-pointed sparkle built from curved edges."""
    pts = [(0, -r), (r, 0), (0, r), (-r, 0)]
    ctx.move_to(cx + pts[0][0], cy + pts[0][1])
    for i in range(4):
        a = pts[i]
        b = pts[(i + 1) % 4]
        ctx.curve_to(cx + a[0] * pinch, cy + a[1] * pinch,
                     cx + b[0] * pinch, cy + b[1] * pinch,
                     cx + b[0], cy + b[1])
    ctx.close_path()


SPARK_RAYS = 12


def spark(ctx, cx, cy, radius, grow=None, rot=0.0, width=0.11):
    """The reel's signature mark: 12 tapered rays of alternating length.

    grow: optional callable(i) -> 0..1 growth per ray (for staggered builds)."""
    for i in range(SPARK_RAYS):
        g = 1.0 if grow is None else grow(i)
        if g <= 0.001:
            continue
        a = rot + i * 2 * math.pi / SPARK_RAYS
        length = radius * (1.0 if i % 2 == 0 else 0.72) * (0.94 + 0.06 * math.cos(i * 2.3)) * g
        base = radius * width
        tip = base * 0.42
        ca, sa = math.cos(a), math.sin(a)
        px, py = -sa, ca
        r0 = radius * 0.10
        x0, y0 = cx + ca * r0, cy + sa * r0
        x1, y1 = cx + ca * (r0 + length), cy + sa * (r0 + length)
        # one consistent winding per ray so overlapping rays never punch holes
        ctx.move_to(x0 + px * base / 2, y0 + py * base / 2)
        ctx.line_to(x1 + px * tip / 2, y1 + py * tip / 2)
        ctx.arc_negative(x1, y1, tip / 2, a + math.pi / 2, a - math.pi / 2)
        ctx.line_to(x0 - px * base / 2, y0 - py * base / 2)
        ctx.arc_negative(x0, y0, base / 2, a - math.pi / 2, a - 3 * math.pi / 2)
        ctx.close_path()
    core = radius * 0.16 * (1.0 if grow is None else clamp(grow(0) * 1.5))
    if core > 0.5:
        ctx.new_sub_path()
        ctx.arc_negative(cx, cy, core, 2 * math.pi, 0)
