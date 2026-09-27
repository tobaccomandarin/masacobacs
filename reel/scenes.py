"""The eight scenes of the reel. One scene per bar at 128 BPM (1 bar = 1.875 s).

All timing is expressed in beats (bt = seconds / BEAT) so picture and sound share
one clock. Each scene demonstrates one motion-design principle:

  bar 1  SQUASH & STRETCH   bouncing ball, motion path, impact rings
  bar 2  KINETIC TYPE       masked, staggered, justified type
  bar 3  EASING             live graph editor: linear vs cubic-bezier, onion skin
  bar 4  STAGGER            60-cell grid morphing in a ripple from the centre
  bar 5  IMPACT             the drop: flash, 3D dot tunnel, glitch type
  bar 6  PARALLAX           depth-layered marquees + rotating text-on-path badge
  bar 7  CONSTRUCTION       geometry guides that resolve into the spark mark
  bar 8  SIGNATURE          end card, then an iris back to the opening dot (loops)
"""
import math

import cairo

from lib import (BEAT, BLUE, CORAL, GRAPHITE, H, INK, LIME, PAPER, W, clamp,
                 cubic_bezier, diamond, eio_cubic, eio_expo, ei_back,
                 ei_expo, eo_back, eo_cubic, eo_expo, font, hash01, lerp, mix,
                 prog, rounded_rect, setc, spark, spring, star4, with_alpha)

TAU = 2 * math.pi


def bg(ctx, c):
    setc(ctx, c)
    ctx.rectangle(-200, -200, W + 400, H + 400)
    ctx.fill()


def impulse(bt, beats, decay=12.0):
    """Sum of exponential decays (in seconds) triggered at the given beats."""
    v = 0.0
    for b in beats:
        dt = (bt - b) * BEAT
        if 0 <= dt < 1.0:
            v += math.exp(-dt * decay)
    return v


# ======================================================================= bar 1
DOT_R = 48
FLOOR = 1180
DOT_START = (540.0, 700.0)
IMPACTS = (1.0, 2.0, 3.0)


def _dot_xy(bt):
    xs = [(0.0, 540.0), (1.0, 612.0), (2.0, 690.0), (3.0, 616.0), (3.5, 540.0)]
    x = xs[-1][1]
    for (b0, x0), (b1, x1) in zip(xs, xs[1:]):
        if b0 <= bt <= b1:
            x = lerp(x0, x1, (bt - b0) / (b1 - b0))
            break
    fc = FLOOR - DOT_R
    if bt < 1:
        y = DOT_START[1] + (fc - DOT_START[1]) * bt ** 2
    elif bt < 2:
        u = bt - 1
        y = fc - 4 * 330 * u * (1 - u)
    elif bt < 3:
        u = bt - 2
        y = fc - 4 * 230 * u * (1 - u)
    elif bt < 3.5:
        u = (bt - 3) / 0.5
        y = fc - (fc - DOT_START[1]) * (1 - (1 - u) ** 2)
    else:
        y = DOT_START[1]
    return x, y


def scene_bounce(ctx, bt):
    bg(ctx, INK)
    fade_out = 1 - prog(bt, 3.4, 3.7)

    # floor line grows from the centre
    half = 330 * eo_expo(prog(bt, 0.15, 0.95))
    if half > 1:
        setc(ctx, PAPER, 0.28 * fade_out)
        ctx.set_line_width(3)
        ctx.move_to(540 - half, FLOOR)
        ctx.line_to(540 + half, FLOOR)
        ctx.stroke()

    # motion path (After Effects style dotted trajectory) with keyframe diamonds
    path_a = prog(bt, 0.25, 0.7) * fade_out
    if path_a > 0:
        setc(ctx, PAPER, 0.38 * path_a)
        s = 0.0
        while s <= min(bt, 3.5):
            x, y = _dot_xy(s)
            ctx.new_sub_path()
            ctx.arc(x, y, 2.6, 0, TAU)
            s += 0.045
        ctx.fill()
        for b in IMPACTS:
            if bt >= b:
                p = eo_back(prog(bt, b, b + 0.3), 3)
                x, _ = _dot_xy(b)
                setc(ctx, LIME, path_a)
                diamond(ctx, x, FLOOR + 34, 9 * p)
                ctx.fill()

    # impact rings
    for b in IMPACTS:
        p = prog(bt, b, b + 0.7)
        if 0 < p < 1:
            x, _ = _dot_xy(b)
            rx = 40 + 190 * eo_expo(p)
            ctx.save()
            ctx.translate(x, FLOOR)
            ctx.scale(1, 0.2)
            ctx.arc(0, 0, rx, 0, TAU)
            ctx.restore()
            setc(ctx, PAPER, 0.55 * (1 - p))
            ctx.set_line_width(3)
            ctx.stroke()

    x, y = _dot_xy(bt)
    # velocity-driven stretch
    vy = (_dot_xy(bt + 0.01)[1] - _dot_xy(bt - 0.01)[1]) / 0.02
    stretch = clamp(abs(vy) / 2600.0, 0, 0.36) if bt < 3.5 else 0.0
    sx, sy = 1 / (1 + stretch), 1 + stretch
    for b in IMPACTS:
        dt = (bt - b) * BEAT
        if 0 <= dt < 0.5:
            sq = 0.46 * math.exp(-dt * 15) * math.cos(dt * 36)
            sx *= 1 + sq
            sy *= 1 - sq
    # anticipation before the big reveal
    ant = math.sin(math.pi * prog(bt, 3.42, 3.62)) * 0.22
    sx *= 1 - ant
    sy *= 1 - ant

    # shadow
    h = clamp((FLOOR - DOT_R - y) / 480.0)
    if fade_out > 0:
        ctx.save()
        ctx.translate(x, FLOOR + 5)
        ctx.scale(1, 0.16)
        ctx.arc(0, 0, DOT_R * (1.25 - 0.55 * h), 0, TAU)
        ctx.restore()
        setc(ctx, PAPER, 0.16 * (1 - 0.7 * h) * fade_out * prog(bt, 0.1, 0.5))
        ctx.fill()

    # the dot; at the end of the bar it swells into the next scene's colour
    grow = ei_expo(prog(bt, 3.55, 4.0))
    r = DOT_R + (2300 - DOT_R) * grow
    col = mix(PAPER, CORAL, eo_cubic(prog(bt, 3.5, 3.78)))
    cy = min(y, FLOOR - DOT_R * sy) if bt < 3.5 else y
    ctx.save()
    ctx.translate(x, cy)
    ctx.scale(sx, sy)
    ctx.arc(0, 0, r, 0, TAU)
    ctx.restore()
    setc(ctx, col)
    ctx.fill()


# ======================================================================= bar 2
TYPE_LINES = ["I THINK", "IN KEY", "FRAMES"]
TYPE_STARTS = [4.0, 4.6, 5.2]
LETTER_STAGGER = 0.035
DIAMOND_T = 5.9
PAYOFF_T = 6.2


def _type_layout():
    f = font("black")
    margin = 72
    rows = []
    for i, text in enumerate(TYPE_LINES):
        extra = 0.62 if i == 2 else 0.0  # room for the keyframe diamond
        w1 = f.width(text, 100, tracking=-20) + extra * f.cap_px(100)
        size = (W - 2 * margin) / w1 * 100
        rows.append([text, size])
    cap_total = sum(f.cap_px(s) for _, s in rows)
    gap = 34
    block = cap_total + gap * (len(rows) - 1)
    y = 930 - block / 2
    out = []
    for text, size in rows:
        y += f.cap_px(size)
        out.append((text, size, y))
        y += gap
    return margin, out


def scene_type(ctx, bt):
    bg(ctx, CORAL)
    f = font("black")
    margin, rows = _type_layout()

    panel = eio_expo(prog(bt, 7.45, 8.0))
    push = -panel * 520
    bump = 1 + 0.012 * impulse(bt, [4], 9)

    ctx.save()
    ctx.translate(540, 960 + push)
    ctx.scale(bump, bump)
    ctx.translate(-540, -960)
    for li, (text, size, base) in enumerate(rows):
        start = TYPE_STARTS[li]
        if bt < start:
            continue
        cap = f.cap_px(size)
        glyphs, width = f.layout(text, size, tracking=-20)
        ctx.save()
        ctx.rectangle(0, base - cap - 14, W, cap + 30)
        ctx.clip()
        for gi, (ch, g, gx, adv) in enumerate(glyphs):
            if ch == " ":
                continue
            p = eo_expo(prog(bt, start + gi * LETTER_STAGGER, start + gi * LETTER_STAGGER + 0.85))
            dy = (1 - p) * cap * 1.2
            ctx.save()
            ctx.translate(margin + gx, base + dy)
            ctx.rotate((1 - p) * 0.12)
            f.glyph(ctx, g, 0, 0, size)
            ctx.restore()
            outline = li == 1 and gi >= 3
            setc(ctx, INK)
            if outline:
                ctx.set_line_width(5)
                ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                ctx.stroke()
            else:
                ctx.fill()
        ctx.restore()
        if li == 2:
            p = eo_back(prog(bt, DIAMOND_T, DIAMOND_T + 0.5), 2.2)
            if p > 0:
                dx = margin + width + cap * 0.36
                ctx.save()
                ctx.translate(dx, base - cap * 0.3)
                ctx.rotate((1 - p) * math.pi)
                diamond(ctx, 0, 0, cap * 0.28 * p)
                ctx.restore()
                setc(ctx, PAPER)
                ctx.fill()

    # the payoff line in an italic serif
    base = rows[-1][2] + 150
    it = font("italic")
    words = "every frame, on purpose.".split(" ")
    x = margin
    for wi, wd in enumerate(words):
        p = eo_expo(prog(bt, PAYOFF_T + wi * 0.12, PAYOFF_T + 0.9 + wi * 0.12))
        w = it.width(wd + " ", 76)
        if p > 0:
            ctx.save()
            ctx.rectangle(0, base - 90, W, 120)
            ctx.clip()
            it.text(ctx, wd, x, base + (1 - p) * 80, 76)
            setc(ctx, INK)
            ctx.fill()
            ctx.restore()
        x += w
    ctx.restore()

    # ink panel wipes up; its lime edge leads into the graph editor
    if panel > 0:
        top = H + 20 - (H + 60) * panel
        setc(ctx, INK)
        ctx.rectangle(-200, top, W + 400, H + 400)
        ctx.fill()
        setc(ctx, LIME)
        ctx.rectangle(-200, top - 6, W + 400, 6)
        ctx.fill()


# ======================================================================= bar 3
GX0, GX1, GY0, GY1 = 160.0, 920.0, 610.0, 1370.0
TRACK1, TRACK2 = 1470.0, 1550.0
BEZIER_TXT = "cubic-bezier(0.16, 1, 0.3, 1)"
BEZIER_T = (10.35, 11.05)
LIN_MOVES = [(9.0, 0, 1), (10.0, 1, 0), (11.0, 0, 1)]
EASE_MOVES = [(10.0, 1, 0), (11.0, 0, 1)]
MOVE_LEN = 0.86


def typed_char_times(text, window):
    a, b = window
    return [a + (b - a) * i / len(text) for i in range(len(text))]


def _gp(u, v):
    return GX0 + u * (GX1 - GX0), GY1 - v * (GY1 - GY0)


def _morph(bt):
    dt = (bt - 10.0) * BEAT
    return spring(dt, 17, 6.5) if dt > 0 else 0.0


def _ctrl(bt):
    m = _morph(bt)
    p1 = (lerp(1 / 3, 0.16, m), lerp(1 / 3, 1.0, m))
    p2 = (lerp(2 / 3, 0.30, m), lerp(2 / 3, 1.0, m))
    return p1, p2


def _bez(p1, p2, s):
    u = 3 * p1[0] * (1 - s) ** 2 * s + 3 * p2[0] * (1 - s) * s ** 2 + s ** 3
    v = 3 * p1[1] * (1 - s) ** 2 * s + 3 * p2[1] * (1 - s) * s ** 2 + s ** 3
    return u, v


def _ball_u(bt, moves, ease):
    u = moves[0][1]
    for start, a, b in moves:
        if bt >= start:
            p = prog(bt, start, start + MOVE_LEN)
            u = lerp(a, b, ease(p))
    return u


def _typed(ctx, text, window, bt, x, y, size, col, align="left"):
    f = font("mono")
    n = int(len(text) * prog(bt, *window) + 0.0001)
    shown = text[:n]
    w_full = f.width(text, size)
    x0 = x - w_full / 2 if align == "center" else x
    w = f.text(ctx, shown, x0, y, size) if shown else 0.0
    setc(ctx, col)
    ctx.fill()
    if (bt * 4) % 2 < 1.3 or n < len(text):
        setc(ctx, col, 0.9)
        ctx.rectangle(x0 + w + 4, y - size * 0.8, size * 0.55, size * 0.95)
        ctx.fill()


def scene_ease(ctx, bt):
    bg(ctx, INK)
    exit_p = prog(bt, 11.55, 11.8)
    a = 1 - exit_p
    ease_fn = cubic_bezier(0.16, 1, 0.3, 1)
    m = _morph(bt)

    if a > 0:
        # grid
        for i in range(9):
            u = i / 8
            p = eo_expo(prog(bt, 8.0 + i * 0.03, 8.55 + i * 0.03))
            setc(ctx, PAPER, (0.45 if i == 0 else 0.09) * a)
            ctx.set_line_width(2.5 if i == 0 else 1.5)
            x, _ = _gp(u, 0)
            ctx.move_to(x, GY1)
            ctx.line_to(x, GY1 - (GY1 - GY0) * p)
            ctx.stroke()
            _, y = _gp(0, u)
            ctx.move_to(GX0, y)
            ctx.line_to(GX0 + (GX1 - GX0) * p, y)
            ctx.stroke()
        mono = font("mono")
        la = prog(bt, 8.35, 8.7) * a
        mono.text(ctx, "TIME", GX1, GY1 + 42, 22, tracking=200, align="right")
        setc(ctx, PAPER, 0.5 * la)
        ctx.fill()
        ctx.save()
        ctx.translate(GX0 - 22, GY0)
        ctx.rotate(-math.pi / 2)
        mono.text(ctx, "VALUE", 0, 0, 22, tracking=200, align="right")
        ctx.restore()
        ctx.fill()

        # the curve
        p1, p2 = _ctrl(bt)
        draw_p = eo_cubic(prog(bt, 8.45, 9.1))
        col = mix(with_alpha(PAPER, 0.55), LIME, clamp(m))
        if draw_p > 0:
            n = 90
            for k in range(n + 1):
                s = draw_p * k / n
                x, y = _gp(*_bez(p1, p2, s))
                (ctx.move_to if k == 0 else ctx.line_to)(x, y)
            setc(ctx, col, a)
            ctx.set_line_width(6)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()

        # bezier handles
        ha = prog(bt, 9.0, 9.3) * a
        if ha > 0:
            for (hx, hy), anchor, t0 in ((p1, (0, 0), 10.0), (p2, (1, 1), 10.12)):
                ax, ay = _gp(*anchor)
                x, y = _gp(hx, hy)
                setc(ctx, PAPER, 0.5 * ha)
                ctx.set_line_width(2)
                ctx.move_to(ax, ay)
                ctx.line_to(x, y)
                ctx.stroke()
                pop = eo_back(prog(bt, t0, t0 + 0.35), 3.5)
                r = 9 + 7 * pop
                ctx.arc(x, y, r, 0, TAU)
                setc(ctx, INK)
                ctx.fill_preserve()
                setc(ctx, mix(PAPER, LIME, pop), ha)
                ctx.set_line_width(3)
                ctx.stroke()
                ctx.rectangle(ax - 7, ay - 7, 14, 14)
                setc(ctx, PAPER, ha)
                ctx.fill()

        # playhead + value dot on the curve
        if bt >= 9.0:
            if bt >= 10.0:
                moves, fn = EASE_MOVES, ease_fn
            else:
                moves, fn = LIN_MOVES, (lambda q: q)
            start = max(s for s, _, _ in moves if bt >= s) if bt >= moves[0][0] else moves[0][0]
            p = prog(bt, start, start + MOVE_LEN)
            v = fn(p)
            x, _ = _gp(p, 0)
            _, y = _gp(0, v)
            setc(ctx, LIME if bt >= 10 else PAPER, 0.35 * a)
            ctx.set_line_width(2)
            ctx.move_to(x, GY0 - 10)
            ctx.line_to(x, GY1)
            ctx.stroke()
            ctx.arc(x, y, 9, 0, TAU)
            setc(ctx, LIME if bt >= 10 else PAPER, a)
            ctx.fill()

        # tracks
        for ty, on in ((TRACK1, 8.8), (TRACK2, 9.9)):
            ta = prog(bt, on, on + 0.3) * a
            setc(ctx, PAPER, 0.16 * ta)
            ctx.set_line_width(2)
            ctx.move_to(GX0, ty)
            ctx.line_to(GX1, ty)
            ctx.stroke()
        mono.text(ctx, "linear", GX0, TRACK1 - 34, 20)
        setc(ctx, PAPER, 0.45 * prog(bt, 8.8, 9.1) * a)
        ctx.fill()
        mono.text(ctx, "ease-out", GX0, TRACK2 - 34, 20)
        setc(ctx, LIME, 0.8 * prog(bt, 9.9, 10.2) * a)
        ctx.fill()

        # onion-skinned balls
        def ball(ty, moves, fn, col, appear):
            s_app = eo_back(prog(bt, appear, appear + 0.35), 2.5)
            if s_app <= 0:
                return
            for k in range(8, -1, -1):
                u = _ball_u(bt - k * 0.035, moves, fn)
                x = lerp(GX0, GX1, u)
                al = (1.0 if k == 0 else 0.28 * (1 - k / 9)) * a
                ctx.arc(x, ty, 20 * s_app, 0, TAU)
                setc(ctx, col, al)
                ctx.fill()

        ball(TRACK1, LIN_MOVES, lambda q: q, with_alpha(PAPER, 0.7), 8.8)
        ball(TRACK2, EASE_MOVES, ease_fn, LIME, 9.85)

        # headings
        if bt >= 10:
            it = font("italic")
            glyphs, w = it.layout("Ease is emotion.", 118)
            x0 = 540 - w / 2
            ctx.save()
            ctx.rectangle(0, 330, W, 150)
            ctx.clip()
            for gi, (ch, g, gx, _) in enumerate(glyphs):
                p = eo_expo(prog(bt, 10.0 + gi * 0.025, 10.5 + gi * 0.025))
                it.glyph(ctx, g, x0 + gx, 445 + (1 - p) * 120, 118)
            setc(ctx, PAPER, a)
            ctx.fill()
            ctx.restore()
            _typed(ctx, BEZIER_TXT, BEZIER_T, bt, 540, 530, 28, with_alpha(LIME, a), align="center")

    # exit: the eased ball becomes the next scene
    if bt >= 11.55:
        u = _ball_u(bt, EASE_MOVES, ease_fn)
        bx, by = lerp(GX0, GX1, u), TRACK2
        mv = eio_cubic(prog(bt, 11.55, 11.82))
        x, y = lerp(bx, 540, mv), lerp(by, 960, mv)
        r = lerp(20, 2300, ei_expo(prog(bt, 11.68, 12.0)))
        ctx.arc(x, y, r, 0, TAU)
        setc(ctx, mix(LIME, BLUE, prog(bt, 11.7, 11.88)))
        ctx.fill()


# ======================================================================= bar 4
COLS, ROWS, CELL = 6, 8, 160
GRID_BEATS = (12.0, 13.2, 14.4)
GRID_STATES = (1, 2, 4)
GRID_X0 = (W - COLS * CELL) / 2
GRID_Y0 = 960 - ROWS * CELL / 2


def _grid_state(k, i, j):
    """Shape state k for cell (i, j): size, roundness, rotation, colour."""
    checker = (i + j) % 2
    d = math.hypot(i - 2.5, j - 3.5)
    if k == 0:
        return 0.0, 1.0, 0.0, PAPER
    if k == 1:
        return 100.0, 1.0, 0.0, PAPER
    if k == 2:
        return 90.0, 0.14, math.pi / 4, LIME if checker else PAPER
    if k == 3:
        return 58.0, 0.18, math.pi, LIME if int(d * 1.4) % 3 == 0 else PAPER
    return 118.0, 1.0, math.pi, INK if checker else PAPER


def scene_grid(ctx, bt):
    bg(ctx, BLUE)
    implode_t = 15.5
    for j in range(ROWS):
        for i in range(COLS):
            d = math.hypot(i - 2.5, j - 3.5)
            size, rnd, rot, col = _grid_state(0, i, j)
            for k, b in enumerate(GRID_BEATS):
                t0 = b + d * 0.065
                p = prog(bt, t0, t0 + 0.8)
                if p <= 0:
                    break
                e = eo_back(p, 1.3)
                s2, r2, rot2, c2 = _grid_state(GRID_STATES[k], i, j)
                size = lerp(size, s2, e)
                rnd = lerp(rnd, r2, clamp(e))
                rot = lerp(rot, rot2, e)
                col = mix(col, c2, clamp(p * 1.6))
            cx = GRID_X0 + CELL / 2 + CELL * i
            cy = GRID_Y0 + CELL / 2 + CELL * j
            cy += 6 * math.sin(bt * math.pi * 0.5 + d * 0.9)
            size *= 1 + 0.04 * impulse(bt, [12], 9)
            # implode toward the centre: anticipation first, then suck in
            ip = prog(bt, implode_t + (4.3 - d) * 0.03, 15.97)
            if ip > 0:
                e = ei_back(ip, 2.2)
                cx = lerp(cx, 540, e)
                cy = lerp(cy, 960, e)
                size = lerp(size, 10, clamp(e))
            if size <= 0.5:
                continue
            ctx.save()
            ctx.translate(cx, cy)
            ctx.rotate(rot)
            rounded_rect(ctx, -size / 2, -size / 2, size, size, rnd * size / 2)
            ctx.restore()
            setc(ctx, col)
            ctx.fill()


# ======================================================================= bar 5
DROP_CARDS = [["EVERY", "FRAME"], ["ON", "BEAT."]]
DROP_BEATS = [16.0, 18.0]


def _tunnel(ctx, bt):
    f = 560.0
    spacing = 240.0
    n_rings = 18
    travel = 1000 * (bt - 16) + sum(900 * eo_expo(prog(bt, b, b + 1.2)) for b in DROP_BEATS)
    total = spacing * n_rings
    for k in range(n_rings):
        z = (k * spacing - travel) % total + 90
        depth_a = clamp(1 - z / total) * clamp((z - 90) / 160)
        if depth_a <= 0.01:
            continue
        rot = z * 0.0012 + (bt - 16) * 0.35
        col = CORAL if k % 4 == 0 else PAPER
        rr = 9.5 * f / z
        R = 520 * f / z
        for j in range(22):
            ang = rot + j * TAU / 22
            ctx.new_sub_path()
            ctx.arc(540 + math.cos(ang) * R, 960 + math.sin(ang) * R, rr, 0, TAU)
        setc(ctx, col, depth_a * 0.9)
        ctx.fill()


def _speedlines(ctx, bt):
    for b in DROP_BEATS:
        p = prog(bt, b, b + 0.8)
        if not 0 < p < 1:
            continue
        for i in range(40):
            ang = hash01(int(b), i) * TAU
            r0 = 160 + 1500 * eo_expo(p) * (0.6 + 0.4 * hash01(i, 7))
            ln = 380 * (1 - p)
            ctx.move_to(540 + math.cos(ang) * r0, 960 + math.sin(ang) * r0)
            ctx.line_to(540 + math.cos(ang) * (r0 + ln), 960 + math.sin(ang) * (r0 + ln))
        setc(ctx, PAPER, 0.5 * (1 - p))
        ctx.set_line_width(3)
        ctx.stroke()


def _drop_card(ctx, bt, idx):
    f = font("black")
    lines = DROP_CARDS[idx]
    b = DROP_BEATS[idx]
    p = eo_expo(prog(bt, b, b + 0.7))
    s = 1.3 - 0.3 * p
    styles = [[(PAPER, False), (LIME, True)], [(LIME, False), (PAPER, False)]][idx]
    sizes = [min(330.0, 930.0 / f.width(w, 100, tracking=-30) * 100) for w in lines]
    caps = [f.cap_px(z) for z in sizes]
    gap = 50
    total = sum(caps) + gap
    y = 960 - total / 2
    ctx.save()
    ctx.translate(540, 960)
    ctx.scale(s, s)
    ctx.translate(-540, -960)
    for li, (word, size, cap) in enumerate(zip(lines, sizes, caps)):
        y += cap
        lp_ = eo_expo(prog(bt, b + li * 0.25, b + li * 0.25 + 0.8))
        if lp_ > 0:
            ctx.save()
            ctx.rectangle(-200, y - cap - 12, W + 400, cap + 24)
            ctx.clip()
            f.text(ctx, word, 540, y + (1 - lp_) * cap * 1.1, size, tracking=-30, align="center")
            col, stroke = styles[li]
            setc(ctx, col)
            if stroke:
                ctx.set_line_width(6)
                ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                ctx.stroke()
            else:
                ctx.fill()
            ctx.restore()
        y += gap
    ctx.restore()


def scene_drop(ctx, bt):
    bg(ctx, INK)
    _tunnel(ctx, bt)
    _speedlines(ctx, bt)
    idx = max(i for i, b in enumerate(DROP_BEATS) if bt >= b)
    _drop_card(ctx, bt, idx)
    fl = 1 - prog(bt, 16.0, 16.45)
    if fl > 0:
        setc(ctx, LIME, fl * 0.85)
        ctx.paint()


# ======================================================================= bar 6
ROW_DEPTH = ["far", "near", "mid", "far", "near", "mid", "far", "mid", "near", "far", "mid", "near", "far"]
DEPTH = {"near": (200.0, 1.0), "mid": (130.0, 0.8), "far": (78.0, 0.55)}
MARQUEE = ["MOTION", "*", "DESIGN", "*"]
MARQUEE_BEATS = (20, 22)
BADGE_TEXT = "CLAUDE • MOTION DESIGN • MADE IN CODE • "


def _marquee_row(ctx, y, depth, direction, travel):
    f = font("black")
    size, amp = DEPTH[depth]
    parts = []
    x = 0.0
    for tok in MARQUEE:
        if tok == "*":
            parts.append(("*", x))
            x += size * 0.95
        else:
            parts.append((tok, x))
            x += f.width(tok, size, tracking=-20) + size * 0.15
    unit = x
    off = (direction * travel * size * 2.4) % unit
    start = -1300 - off
    cap = f.cap_px(size)
    xx = start
    while xx < 1300:
        for tok, px in parts:
            if tok == "*":
                star4(ctx, xx + px + size * 0.4, y - cap / 2, size * 0.34)
            else:
                f.text(ctx, tok, xx + px, y, size, tracking=-20)
        xx += unit
    if depth == "near":
        setc(ctx, INK)
        ctx.fill()
    elif depth == "mid":
        setc(ctx, INK)
        ctx.set_line_width(3)
        ctx.stroke()
    else:
        setc(ctx, PAPER, 0.65)
        ctx.fill()


def _badge(ctx, bt, cx, cy, scale, spark_alpha=1.0):
    if scale <= 0:
        return
    rot = (bt - 20) * 0.3 + 0.5 * eo_expo(prog(bt, 22, 23))
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(scale, scale)
    ctx.arc(0, 0, 205, 0, TAU)
    setc(ctx, PAPER)
    ctx.fill()
    ctx.arc(0, 0, 188, 0, TAU)
    setc(ctx, INK, 0.9)
    ctx.set_line_width(2.5)
    ctx.stroke()
    mono = font("mono")
    radius = 150
    size = 29
    natural = mono.width(BADGE_TEXT, size)
    tracking = (TAU * radius - natural) / len(BADGE_TEXT) / size * 1000
    glyphs, _ = mono.layout(BADGE_TEXT, size, tracking)
    for ch, g, gx, adv in glyphs:
        if ch == " ":
            continue
        a = rot + (gx + adv / 2) / radius
        ctx.save()
        ctx.rotate(a)
        ctx.translate(0, -radius)
        mono.glyph(ctx, g, -adv / 2, size * 0.36, size)
        ctx.restore()
    setc(ctx, INK)
    ctx.fill()
    if spark_alpha > 0:
        spark(ctx, 0, 0, 84, rot=-rot * 1.6)
        setc(ctx, CORAL, spark_alpha)
        ctx.fill()
    ctx.restore()


def scene_marquee(ctx, bt):
    bg(ctx, CORAL)
    zoom = 1 + 34 * ei_expo(prog(bt, 23.4, 24.0))
    ctx.save()
    ctx.translate(540, 960)
    ctx.scale(zoom, zoom)
    ctx.translate(-540, -960)

    travel = (bt - 20) * 0.16 + sum(0.55 * eo_expo(prog(bt, b, b + 1.2)) for b in MARQUEE_BEATS)
    ctx.save()
    ctx.translate(540, 960)
    ctx.rotate(-0.21)
    y = -1180.0
    for r, depth in enumerate(ROW_DEPTH):
        size = DEPTH[depth][0]
        y += font("black").cap_px(size) + 46
        _marquee_row(ctx, y, depth, 1 if r % 2 == 0 else -1, travel * DEPTH[depth][1])
    ctx.restore()

    s = eo_back(prog(bt, 20.6, 21.1), 2.2)
    _badge(ctx, bt, 540, 960, s * 1.05, spark_alpha=1 - prog(bt, 23.55, 23.8))
    ctx.restore()


# ======================================================================= bars 7-8
C = (540.0, 760.0)
JP_T = 29.0
CIRCLES = [110, 200, 290, 380]
SPARK_R = 290.0
END_DOT = DOT_START


def _construction(ctx, bt, alpha):
    if alpha <= 0:
        return
    cx, cy = C
    ctx.set_line_width(2)
    # crosshair
    for k, (dx, dy, t0) in enumerate(((1, 0, 24.05), (0, 1, 24.15))):
        p = eo_expo(prog(bt, t0, t0 + 0.7))
        L = 1200 * p
        ctx.move_to(cx - dx * L, cy - dy * L)
        ctx.line_to(cx + dx * L, cy + dy * L)
    setc(ctx, INK, 0.28 * alpha)
    ctx.stroke()
    # concentric circles
    for k, r in enumerate(CIRCLES):
        p = eo_cubic(prog(bt, 24.3 + k * 0.14, 25.0 + k * 0.14))
        if p <= 0:
            continue
        ctx.new_path()
        ctx.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + TAU * p)
        if k % 2:
            ctx.set_dash([10, 10])
        setc(ctx, INK, 0.34 * alpha)
        ctx.stroke()
        ctx.set_dash([])
    # radial guides every 30 degrees
    for i in range(12):
        p = eo_expo(prog(bt, 24.9 + i * 0.04, 25.35 + i * 0.04))
        if p <= 0:
            continue
        a = -math.pi / 2 + i * TAU / 12
        ctx.move_to(cx, cy)
        ctx.line_to(cx + math.cos(a) * 430 * p, cy + math.sin(a) * 430 * p)
    setc(ctx, INK, 0.2 * alpha)
    ctx.stroke()
    # anchor points where guides meet the construction circle
    for i in range(12):
        p = eo_back(prog(bt, 25.45 + i * 0.03, 25.75 + i * 0.03), 3)
        if p <= 0:
            continue
        a = -math.pi / 2 + i * TAU / 12
        x, y = cx + math.cos(a) * 290, cy + math.sin(a) * 290
        ctx.rectangle(x - 6 * p, y - 6 * p, 12 * p, 12 * p)
    setc(ctx, INK, 0.7 * alpha)
    ctx.set_line_width(2)
    ctx.stroke()
    # measurement labels
    mono = font("mono")
    for k, r in enumerate(CIRCLES):
        p = prog(bt, 25.1 + k * 0.1, 25.35 + k * 0.1)
        if p <= 0:
            continue
        a = -math.pi / 4
        mono.text(ctx, "r%d" % r, cx + math.cos(a) * r + 10, cy + math.sin(a) * r - 8, 20)
        setc(ctx, GRAPHITE, p * alpha)
        ctx.fill()
    p = prog(bt, 25.5, 25.8)
    if p > 0:
        ctx.arc(cx, cy, 64, -math.pi / 2, -math.pi / 2 + TAU / 12)
        setc(ctx, CORAL, p * alpha)
        ctx.set_line_width(2.5)
        ctx.stroke()
        mono.text(ctx, "30°", cx + 30, cy - 80, 20)
        ctx.fill()
        mono.text(ctx, "Ø 760 / 12 rays", cx, cy + 425, 20, align="center")
        setc(ctx, GRAPHITE, p * alpha)
        ctx.fill()


def _reveal_line(ctx, fnt, text, cx, base, size, t0, stagger, col, clip_h, tracking=0.0, rise=1.0):
    glyphs, w = fnt.layout(text, size, tracking)
    x0 = cx - w / 2
    ctx.save()
    ctx.rectangle(0, base - clip_h, W, clip_h * 1.45)
    ctx.clip()
    for gi, (ch, g, gx, _) in enumerate(glyphs):
        if ch == " ":
            continue
        p = eo_back(prog(t0[0], t0[1] + gi * stagger, t0[1] + gi * stagger + 0.55), 1.4)
        if p <= 0:
            continue
        fnt.glyph(ctx, g, x0 + gx, base + (1 - p) * clip_h * rise, size)
    setc(ctx, col)
    ctx.fill()
    ctx.restore()


def scene_finale(ctx, bt):
    bg(ctx, PAPER)
    cx, cy = C
    construct_a = 1 - 0.8 * prog(bt, 27.6, 28.3)
    _construction(ctx, bt, construct_a)

    # "built from first principles." caption during construction
    if bt < 28:
        it = font("italic")
        ca = 1 - prog(bt, 27.45, 27.7)
        words = "built from first principles.".split(" ")
        total = it.width(" ".join(words), 70)
        x = 540 - total / 2
        for wi, wd in enumerate(words):
            p = eo_expo(prog(bt, 25.3 + wi * 0.12, 25.9 + wi * 0.12))
            if p > 0:
                ctx.save()
                ctx.rectangle(0, 1330 - 80, W, 110)
                ctx.clip()
                it.text(ctx, wd, x, 1330 + (1 - p) * 70, 70)
                setc(ctx, INK, ca)
                ctx.fill()
                ctx.restore()
            x += it.width(wd + " ", 70)

    # spark: builds ray by ray, anticipates, then snaps into the logo lock-up
    if bt >= 26.0:
        dt28 = (bt - 28.0) * BEAT
        if bt < 28:
            scale = 1 - 0.14 * eio_cubic(prog(bt, 27.5, 27.97))
            rot = -0.9 * (1 - eo_expo(prog(bt, 26.0, 27.5))) - 0.22 * eio_cubic(prog(bt, 27.5, 27.97))
        else:
            scale = 0.6 + 0.5 * math.exp(-dt28 * 9) * math.cos(dt28 * 19)
            rot = -0.22 + (0.22 + TAU / 12) * eo_expo(prog(bt, 28.0, 28.9)) + max(0, bt - 28.9) * 0.06
            scale *= 1 + 0.04 * impulse(bt, [29, 30], 10)

        def grow(i):
            return eo_back(prog(bt, 26.0 + i * 0.065, 26.5 + i * 0.065), 1.8)

        spark(ctx, cx, cy, SPARK_R * scale, grow=grow, rot=rot)
        setc(ctx, CORAL)
        ctx.fill()

    if bt >= 28:
        # shockwave ring
        p = prog(bt, 28.0, 28.9)
        if p < 1:
            ctx.arc(cx, cy, 200 + 700 * eo_expo(p), 0, TAU)
            setc(ctx, CORAL, 0.6 * (1 - p))
            ctx.set_line_width(6 * (1 - p) + 1)
            ctx.stroke()
        serif = font("serif")
        _reveal_line(ctx, serif, "Claude", 540, 1215, 300, (bt, 28.12), 0.055, INK, 230)
        # rule
        rp = eo_expo(prog(bt, 28.9, 29.5))
        if rp > 0:
            setc(ctx, INK, 0.8)
            ctx.rectangle(540 - 170 * rp, 1276, 340 * rp, 2)
            ctx.fill()
        mono = font("mono")
        tp = eo_expo(prog(bt, 28.55, 29.7))
        track = lerp(900, 330, tp)
        mono.text(ctx, "MOTION DESIGNER", 540, 1352, 38, tracking=track, align="center")
        setc(ctx, INK, prog(bt, 28.55, 28.9))
        ctx.fill()
        _reveal_line(ctx, font("jp"), "動きで、語る。", 540, 1478, 70,
                     (bt, JP_T), 0.07, CORAL, 80, tracking=60)
        cp = prog(bt, 29.5, 29.9)
        if cp > 0:
            mono.text(ctx, "picture + sound: 100% generated in code", 540, 1566, 21, align="center")
            setc(ctx, GRAPHITE, cp)
            ctx.fill()


def iris(ctx, bt):
    """Close back down to the opening dot so the reel loops seamlessly."""
    p = eio_expo(prog(bt, 30.9, 31.55))
    if p <= 0:
        return
    x, y = END_DOT
    r = lerp(1500, DOT_R, p)
    ctx.save()
    ctx.rectangle(-200, -200, W + 400, H + 400)
    ctx.new_sub_path()
    ctx.arc_negative(x, y, r, TAU, 0)
    setc(ctx, INK)
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.fill()
    ctx.restore()
    solid = prog(bt, 31.2, 31.5)
    if solid > 0:
        ctx.arc(x, y, r, 0, TAU)
        setc(ctx, PAPER, solid)
        ctx.fill()


# ======================================================================= HUD
CHAPTERS = ["SQUASH & STRETCH", "KINETIC TYPE", "EASING", "STAGGER",
            "IMPACT", "PARALLAX", "CONSTRUCTION", "SIGNATURE"]
HUD_ON_DARK = [True, False, True, True, True, False, False, False]
GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/#_+"


def hud(ctx, t, bt, fps):
    a = prog(bt, 0.45, 1.1) * (1 - prog(bt, 30.55, 31.1))
    if a <= 0:
        return
    bar = min(7, int(bt // 4))
    col = PAPER if HUD_ON_DARK[bar] else INK
    mono = font("mono")
    size = 26
    if bar == 5 and bt >= 20.3:
        # the marquee is busy: give the HUD solid chips so it stays legible
        chip = 1 - prog(bt, 23.4, 23.6)
        setc(ctx, CORAL, a * chip)
        rounded_rect(ctx, 44, 136, 460, 56, 10)
        rounded_rect(ctx, W - 44 - 460, 136, 460, 56, 10)
        rounded_rect(ctx, 44, H - 300, W - 88, 130, 14)
        ctx.fill()

    # chapter label with a decode/scramble transition
    label = CHAPTERS[bar]
    sp = prog(bt, bar * 4, bar * 4 + 0.45)
    shown = []
    for i, ch in enumerate(label):
        if ch == " " or i / len(label) < sp:
            shown.append(ch)
        else:
            shown.append(GLYPHS[int(hash01(i, int(bt * 24)) * len(GLYPHS))])
    mono.text(ctx, "%02d" % (bar + 1), 64, 176, size)
    setc(ctx, col, a)
    ctx.fill()
    mono.text(ctx, "".join(shown), 124, 176, size, tracking=60)
    setc(ctx, col, 0.75 * a)
    ctx.fill()
    mono.text(ctx, "CLAUDE / MOTION REEL", W - 64, 176, size, tracking=60, align="right")
    setc(ctx, col, 0.55 * a)
    ctx.fill()

    # timeline with a keyframe per chapter
    y = H - 262
    x0, x1 = 64.0, W - 64.0
    pos = lerp(x0, x1, clamp(t / (32 * BEAT)))
    setc(ctx, col, 0.22 * a)
    ctx.rectangle(x0, y - 1, x1 - x0, 2)
    ctx.fill()
    setc(ctx, col, 0.9 * a)
    ctx.rectangle(x0, y - 1.5, pos - x0, 3)
    ctx.fill()
    for k in range(9):
        kx = lerp(x0, x1, k / 8)
        passed = bt >= k * 4
        pop = 1 + 0.6 * impulse(bt, [k * 4], 10)
        diamond(ctx, kx, y, 8 * pop)
        if passed:
            setc(ctx, col, a)
            ctx.fill()
        else:
            setc(ctx, col, 0.5 * a)
            ctx.set_line_width(2)
            ctx.stroke()
    ctx.rectangle(pos - 1.5, y - 20, 3, 40)
    setc(ctx, LIME if HUD_ON_DARK[bar] else CORAL, a)
    ctx.fill()

    # timecode + beat counter
    f = int(round(t * fps))
    tc = "%02d:%02d:%02d" % (0, int(t) // 60, int(t) % 60) + ":%02d" % (f % fps)
    mono.text(ctx, "TC " + tc, 64, y + 64, size)
    setc(ctx, col, 0.75 * a)
    ctx.fill()
    mono.text(ctx, "128 BPM", W - 64 - 4 * 26 - 24, y + 64, size, align="right")
    setc(ctx, col, 0.55 * a)
    ctx.fill()
    cur = int(bt) % 4
    for k in range(4):
        bx = W - 64 - (3 - k) * 26 - 16
        ctx.rectangle(bx, y + 64 - 16, 16, 16)
        if k == cur:
            setc(ctx, col, a * (0.45 + 0.55 * impulse(bt, [math.floor(bt)], 6)))
            ctx.fill()
        else:
            setc(ctx, col, 0.4 * a)
            ctx.set_line_width(1.5)
            ctx.stroke()


# ======================================================================= camera
SHAKES = [(1, 3), (2, 3), (3, 3), (4, 6), (8, 4), (12, 5), (16, 22), (18, 10),
          (20, 6), (28, 14)]


def camera(bt):
    x = y = 0.0
    for b, amp in SHAKES:
        dt = (bt - b) * BEAT
        if 0 <= dt < 0.6:
            e = amp * math.exp(-dt * 13)
            x += e * math.sin(dt * 71 + b)
            y += e * math.cos(dt * 57 + b * 2)
    return x, y


def aberration(bt):
    v = 1.2
    for b, amp in SHAKES:
        dt = (bt - b) * BEAT
        if 0 <= dt < 0.6:
            v += amp * 0.22 * math.exp(-dt * 10)
    return v


def draw(ctx, t, fps):
    bt = t / BEAT
    sx, sy = camera(bt)
    ctx.save()
    ctx.translate(sx, sy)
    if bt < 4:
        scene_bounce(ctx, bt)
    elif bt < 8:
        scene_type(ctx, bt)
    elif bt < 12:
        scene_ease(ctx, bt)
    elif bt < 16:
        scene_grid(ctx, bt)
    elif bt < 20:
        scene_drop(ctx, bt)
        # slice transition: strips of the next scene slide in on the last 16th
        if bt >= 19.72:
            _slices(ctx, bt)
    elif bt < 24:
        if bt < 20.3:
            scene_drop(ctx, 19.99)
            _slices(ctx, bt)
        else:
            scene_marquee(ctx, bt)
    else:
        scene_finale(ctx, bt)
        iris(ctx, bt)
    ctx.restore()
    hud(ctx, t, bt, fps)


def _slices(ctx, bt):
    n = 12
    hgt = H / n
    for k in range(n):
        t0 = 19.72 + (k % 6) * 0.018 + (k // 6) * 0.01
        p = eo_expo(prog(bt, t0, t0 + 0.42))
        if p <= 0:
            continue
        d = 1 if k % 2 == 0 else -1
        off = d * (1 - p) * (W + 200)
        ctx.save()
        ctx.rectangle(off - 100, k * hgt - 1, W + 200, hgt + 2)
        ctx.clip()
        ctx.translate(off, 0)
        scene_marquee(ctx, max(bt, 20.0))
        ctx.restore()
