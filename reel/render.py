"""Frame renderer: cairo draw -> multi-sample motion blur -> lens/film finishing.

Usage:
  python3 render.py preview 0.5 3.9 7.2 ...   # write stills to out/preview/
  (the full video is driven by make.py)
"""
import math
import os
import sys

import cairo
import numpy as np

import scenes
from lib import BEAT, H, W

FPS = 60
SAMPLES = 8          # sub-frame samples per frame
SHUTTER = 0.5        # 180-degree shutter

_surface = None
_grain = None
_vignette = None


def _init():
    global _surface, _grain, _vignette
    if _surface is not None:
        return
    _surface = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    rng = np.random.default_rng(7)
    _grain = [rng.normal(0, 1, (H, W)).astype(np.float32) for _ in range(6)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2)
    _vignette = (1 - 0.22 * np.clip(d, 0, 1.2) ** 2.2).astype(np.float32)[..., None]


def render_raw(t):
    ctx = cairo.Context(_surface)
    ctx.set_antialias(cairo.ANTIALIAS_GOOD)
    scenes.draw(ctx, t, FPS)
    _surface.flush()
    buf = np.ndarray((H, W, 4), np.uint8, _surface.get_data())
    return buf[..., :3].astype(np.float32)   # BGR


def render_frame(index):
    """Return one finished frame as an (H, W, 3) uint8 RGB array."""
    _init()
    t = index / FPS
    acc = None
    # hard cuts land on every bar line: never blur across one
    cut = round(t / (4 * BEAT)) * 4 * BEAT
    for s in range(SAMPLES):
        ts = t + (s / SAMPLES - 0.5 + 0.5 / SAMPLES) * SHUTTER / FPS
        if t >= cut > ts:
            ts = cut
        elif t < cut <= ts:
            ts = cut - 1e-4
        img = render_raw(max(0.0, ts))
        acc = img if acc is None else acc + img
    img = acc / SAMPLES

    # chromatic aberration, stronger on beat impacts
    ca = int(round(scenes.aberration(t / BEAT)))
    if ca > 0:
        img[..., 2] = np.roll(img[..., 2], ca, axis=1)     # red right
        img[..., 0] = np.roll(img[..., 0], -ca, axis=1)    # blue left
    img *= _vignette
    img += _grain[index % len(_grain)][..., None] * 2.2
    out = np.clip(img, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(out[..., ::-1])            # BGR -> RGB


def preview(times, out_dir):
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    for tt in times:
        idx = int(round(float(tt) * FPS))
        Image.fromarray(render_frame(idx)).save(os.path.join(out_dir, "f_%05.2f.png" % float(tt)))


if __name__ == "__main__":
    if sys.argv[1] == "preview":
        preview(sys.argv[2:], os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "preview"))
