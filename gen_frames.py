#!/usr/bin/env python3
"""Day -> Night hero proof: programmatic frame-sequence generator.

Renders a flat-illustration desk scene parameterized by t in [0,1]
(0 = sales day, 1 = builder night) and exports WebP frames.
Desktop: 150 frames @1600x900. Mobile: 84 frames @960x540.
Poster: the dusk frame (t=0.62) as JPEG.
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.dirname(os.path.abspath(__file__))
SS = 2  # supersample factor for crisp edges

# Pillow 10.2 on this VM requires radius <= (min(w,h)-2)/2 in rounded_rectangle; clamp.
_orig_rr = ImageDraw.ImageDraw.rounded_rectangle
def _rr(self, xy, radius=0, *a, **kw):
    x0, y0, x1, y1 = xy
    maxr = max(0, int((min(x1 - x0, y1 - y0) - 2) // 2))
    return _orig_rr(self, xy, min(int(radius), maxr), *a, **kw)
ImageDraw.ImageDraw.rounded_rectangle = _rr

# ---------- helpers ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def sstep(a, b, x):
    t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t)
def ramp(stops, t):
    """stops: [(pos, (r,g,b)), ...] -> interpolated colour"""
    if t <= stops[0][0]: return stops[0][1]
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            f = (t - p0) / (p1 - p0)
            return tuple(round(lerp(c0[i], c1[i], f)) for i in range(3))
    return stops[-1][1]
def mix(c0, c1, t): return tuple(round(lerp(c0[i], c1[i], t)) for i in range(3))

SKY_TOP = [(0, (56, 138, 212)), (0.35, (62, 118, 198)), (0.55, (36, 58, 128)),
           (0.75, (15, 21, 60)), (1, (6, 9, 32))]
SKY_BOT = [(0, (178, 226, 246)), (0.35, (250, 206, 148)), (0.55, (255, 138, 78)),
           (0.75, (86, 62, 118)), (1, (36, 30, 72))]
WALL    = [(0, (240, 232, 218)), (0.5, (196, 164, 150)), (1, (22, 22, 42))]
DESK_TOP = [(0, (172, 124, 78)), (1, (58, 42, 62))]
DESK_FRONT = [(0, (128, 90, 56)), (1, (34, 26, 44))]
SKYLINE = [(0, (108, 150, 190)), (0.55, (70, 66, 110)), (1, (9, 13, 32))]

BUILDINGS = [(0, 150, 210), (140, 120, 300), (250, 170, 170), (405, 110, 340),
             (505, 190, 240), (680, 130, 380), (800, 180, 200)]
STARS = [(random.Random(7).random(), 0)]  # placeholder, real stars below
_rng = random.Random(42)
STARLIST = [(_rng.uniform(0, 980), _rng.uniform(0, 420), _rng.uniform(0.4, 1.0)) for _ in range(120)]

# static grain (same every frame so scrubbing doesn't shimmer)
def make_grain(w, h):
    r = np.random.RandomState(3)
    n = (r.rand(h, w) * 255).astype(np.uint8)
    img = Image.fromarray(np.dstack([n, n, n]), "RGB")
    return img

GRAIN = {}
VIG = {}
def vignette(w, h):
    if (w, h) in VIG: return VIG[(w, h)]
    y, x = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    d = np.sqrt(((x - cx) / (w * 0.72)) ** 2 + ((y - cy) / (h * 0.72)) ** 2)
    a = (clamp(0, 1) + np.clip((d - 0.55) * 190, 0, 165)).astype(np.uint8)
    img = Image.fromarray(np.dstack([np.zeros((h, w, 2), np.uint8), a]), "RGB")
    # build an RGBA black layer with that alpha
    black = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    black.putalpha(Image.fromarray(a, "L"))
    VIG[(w, h)] = black
    return black

def sky_gradient(w, h, t):
    top, bot = ramp(SKY_TOP, t), ramp(SKY_BOT, t)
    col = np.zeros((h, 1, 3), np.uint8)
    for i in range(h):
        f = i / (h - 1)
        col[i, 0] = mix(top, bot, f ** 1.15)
    return Image.fromarray(np.repeat(col, w, axis=1), "RGB").convert("RGBA")

# ---------- scene ----------
def draw_frame(t, W, H):
    # layout lives in a 1600x900 design space; scale uniformly to target size
    S = (W / 1600.0) * SS
    w, h = int(1600 * S), int(900 * S)
    def X(v): return v * S
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    d = ImageDraw.Draw(img, "RGBA")
    night = sstep(0.45, 0.85, t)          # nightfall factor
    dusk = sstep(0.3, 0.6, t)

    # wall
    d.rectangle([0, 0, w, h], fill=ramp(WALL, t) + (255,))
    # ---- window + sky (clipped) ----
    wx0, wy0, wx1, wy1 = X(60), X(50), X(1040), X(620)
    sky = sky_gradient(int(wx1 - wx0), int(wy1 - wy0), t)
    # sun glow
    sun_x = X(lerp(190, 760, t)); sun_y = X(lerp(150, 560, t * t * 0.9 + t * 0.1))
    glow = Image.new("RGBA", sky.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    sun_col = mix((255, 216, 84), (255, 116, 44), sstep(0.2, 0.7, t))
    for r, a in [(300, 26), (210, 40), (140, 60)]:
        gd.ellipse([sun_x - wx0 - X(r), sun_y - wy0 - X(r), sun_x - wx0 + X(r), sun_y - wy0 + X(r)],
                   fill=sun_col + (int(a * (1 - night * 0.85)),))
    sky = Image.alpha_composite(sky, glow)
    sd = ImageDraw.Draw(sky, "RGBA")
    # stars
    sa = sstep(0.52, 0.8, t)
    if sa > 0:
        for sx, sy, sb in STARLIST:
            a = int(230 * sa * sb)
            r = X(1.6 if sb < 0.8 else 2.4)
            sd.ellipse([X(sx) - r, X(sy) - r, X(sx) + r, X(sy) + r], fill=(235, 240, 255, a))
    # sun disc
    if t < 0.97:
        r = X(44)
        sd.ellipse([sun_x - wx0 - r, sun_y - wy0 - r, sun_x - wx0 + r, sun_y - wy0 + r], fill=sun_col + (255,))
    # moon (crescent, rises late)
    if t > 0.45:
        mf = sstep(0.45, 0.95, t)
        mx, my, mr = X(850), X(lerp(430, 140, mf)), X(38)
        moon = Image.new("RGBA", sky.size, (0, 0, 0, 0))
        md = ImageDraw.Draw(moon)
        md.ellipse([mx - wx0 - mr, my - wy0 - mr, mx - wx0 + mr, my - wy0 + mr], fill=(238, 240, 250, int(255 * mf)))
        moon.putalpha(Image.composite(moon.getchannel("A"), Image.new("L", sky.size, 0),
                                      Image.new("RGBA", sky.size, (0, 0, 0, 0)).split()[3]))  # noop keep
        cut = Image.new("RGBA", sky.size, (0, 0, 0, 0))
        cd = ImageDraw.Draw(cut)
        cd.ellipse([mx - wx0 - mr * 0.55, my - wy0 - mr * 1.15, mx - wx0 + mr * 1.25, my - wy0 + mr * 0.75],
                   fill=(0, 0, 0, 255))
        a = moon.getchannel("A")
        a = Image.composite(Image.new("L", sky.size, 0), a, cut.getchannel("A"))
        moon.putalpha(a)
        sky = Image.alpha_composite(sky, moon)
    # skyline
    sd = ImageDraw.Draw(sky, "RGBA")
    sc = ramp(SKYLINE, t)
    for bx, bw, bh in BUILDINGS:
        top = X(620 - 50) - X(bh) - wy0
        sd.rectangle([X(bx) + wx0 - wx0, top, X(bx + bw), wy1 - wy0], fill=sc + (255,))
        # windows lit at night
        cols = int(bw // 26); rows = int(bh // 30)
        for cx in range(cols):
            for cy in range(rows):
                hv = ((bx * 31 + cx * 17 + cy * 43) % 100) / 100.0
                if hv < night * 0.75:
                    px = X(bx + 8 + cx * 26); py = top + X(10 + cy * 30)
                    sd.rectangle([px, py, px + X(9), py + X(12)], fill=(255, 196, 92, 235))
    img.alpha_composite(sky, (int(wx0), int(wy0)))
    # window frame + mullions
    fc = mix((74, 62, 52), (10, 10, 20), night)
    d.rectangle([wx0 - X(14), wy0 - X(14), wx1 + X(14), wy0], fill=fc + (255,))
    d.rectangle([wx0 - X(14), wy1, wx1 + X(14), wy1 + X(14)], fill=fc + (255,))
    d.rectangle([wx0 - X(14), wy0, wx0, wy1], fill=fc + (255,))
    d.rectangle([wx1, wy0, wx1 + X(14), wy1], fill=fc + (255,))
    d.rectangle([X(545), wy0, X(555), wy1], fill=fc + (255,))
    d.rectangle([wx0, X(330), wx1, X(340)], fill=fc + (255,))

    # ---- poster on right wall: sales chart -> code mark (crossfade) ----
    px0, py0, px1, py1 = X(1160), X(110), X(1500), X(370)
    d.rectangle([px0 - X(8), py0 - X(8), px1 + X(8), py1 + X(8)], fill=fc + (255,))
    d.rectangle([px0, py0, px1, py1], fill=mix((255, 246, 220), (14, 18, 38), sstep(0.35, 0.65, t)) + (255,))
    day_a, night_a = 1 - sstep(0.4, 0.58, t), sstep(0.46, 0.62, t)
    if day_a > 0.02:
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        bars = [70, 110, 92, 150, 196]
        for i, bh in enumerate(bars):
            bx = X(1200 + i * 58)
            ld.rectangle([bx, py1 - X(30) - X(bh), bx + X(34), py1 - X(30)], fill=(37, 99, 235, int(255 * day_a)))
        ld.line([px0 + X(28), py1 - X(96), px0 + X(140), py1 - X(150), px0 + X(230), py1 - X(122), px0 + X(312), py1 - X(214)],
                fill=(220, 38, 38, int(255 * day_a)), width=int(X(6)))
        img.alpha_composite(layer); d = ImageDraw.Draw(img, "RGBA")
    if night_a > 0.02:
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        ld.text((px0 + X(70), py0 + X(60)), "</>", font_size=int(X(150)), fill=(94, 234, 212, int(255 * night_a)), anchor="mm",
                ) if False else None
        # code brackets drawn as strokes (font-free)
        cx, cy, s = px0 + X(170), py0 + X(130), X(58)
        for sx, flip in [(0, 1), (X(150), -1)]:
            ox = cx + sx
            pts = [(ox + flip * s * 0.6, cy - s), (ox, cy - s * 0.35), (ox, cy + s * 0.35), (ox + flip * s * 0.6, cy + s)] if flip == 1 else \
                  [(ox - s * 0.6, cy - s), (ox, cy - s * 0.35), (ox, cy + s * 0.35), (ox - s * 0.6, cy + s)]
            ld.line(pts, fill=(94, 234, 212, int(255 * night_a)), width=int(X(13)), joint="curve")
        ld.line([(cx + X(88), cy - s), (cx + X(62), cy + s)], fill=(240, 171, 252, int(255 * night_a)), width=int(X(13)))
        img.alpha_composite(layer); d = ImageDraw.Draw(img, "RGBA")

    # ---- desk ----
    d.rectangle([0, X(640), w, X(678)], fill=ramp(DESK_TOP, t) + (255,))
    d.rectangle([0, X(678), w, h], fill=ramp(DESK_FRONT, t) + (255,))
    d.rectangle([0, X(640), w, X(646)], fill=mix((210, 164, 110), (86, 64, 92), night) + (255,))

    # ---- monitor ----
    mx0, my0, mx1, my1 = X(700), X(326), X(1236), X(636)
    if night > 0.03:  # screen glow halo
        halo = Image.new("RGBA", (w, h), (0, 0, 0, 0)); hd = ImageDraw.Draw(halo)
        for pad, a in [(46, 14), (30, 22), (16, 30)]:
            hd.rounded_rectangle([mx0 - X(pad), my0 - X(pad), mx1 + X(pad), my1 + X(pad)], X(26), fill=(96, 165, 250, int(a * night)))
        img.alpha_composite(halo); d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([mx0, my0, mx1, my1], X(16), fill=(26, 28, 38, 255))
    sx0, sy0, sx1, sy1 = X(718), X(344), X(1218), X(600)
    # day screen
    day_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dl = ImageDraw.Draw(day_layer)
    dl.rounded_rectangle([sx0, sy0, sx1, sy1], X(8), fill=(228, 243, 252, 255))
    dl.rectangle([sx0, sy0, sx1, sy0 + X(34)], fill=(203, 228, 246, 255))
    for i, bh in enumerate([64, 104, 84, 138, 178]):
        bx = X(770 + i * 84)
        dl.rectangle([bx, sy1 - X(36) - X(bh), bx + X(48), sy1 - X(36)], fill=(59, 130, 246, 255))
    dl.line([X(748), sy1 - X(84), X(880), sy1 - X(140), X(990), sy1 - X(110), X(1150), sy1 - X(198)],
            fill=(220, 38, 38, 255), width=int(X(6)))
    dl.rectangle([sx0, sy1 - X(28), sx1, sy1], fill=(190, 216, 238, 255))
    if day_a := (1 - sstep(0.4, 0.58, t)):
        day_layer.putalpha(day_layer.getchannel("A").point(lambda a: int(a * day_a)))
        img.alpha_composite(day_layer)
    # night screen (code)
    night_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0)); nl = ImageDraw.Draw(night_layer)
    nl.rounded_rectangle([sx0, sy0, sx1, sy1], X(8), fill=(9, 14, 28, 255))
    nl.rectangle([sx0, sy0, sx1, sy0 + X(34)], fill=(17, 26, 46, 255))
    for i, c in enumerate([(248, 113, 113), (253, 224, 71), (74, 222, 128)]):
        nl.ellipse([sx0 + X(16 + i * 26), sy0 + X(11), sx0 + X(30 + i * 26), sy0 + X(25)], fill=c + (255,))
    code_rows = [
        [(0, 120, (125, 211, 252)), (130, 210, (148, 163, 184)), (350, 90, (240, 171, 252))],
        [(26, 180, (94, 234, 212)), (216, 140, (253, 224, 71))],
        [(26, 90, (148, 163, 184)), (126, 260, (125, 211, 252)), (396, 70, (240, 171, 252))],
        [(52, 220, (94, 234, 212)), (282, 120, (148, 163, 184))],
        [(52, 150, (253, 224, 71)), (212, 200, (125, 211, 252))],
        [(26, 110, (240, 171, 252)), (146, 170, (148, 163, 184))],
        [(0, 200, (125, 211, 252)), (210, 90, (94, 234, 212))],
    ]
    for ri, row in enumerate(code_rows):
        ry = sy0 + X(58 + ri * 30)
        for off, ln, c in row:
            nl.rounded_rectangle([sx0 + X(28 + off), ry, sx0 + X(28 + off + ln), ry + X(13)], X(6), fill=c + (255,))
    blink = 0.55 + 0.45 * math.sin(t * math.pi * 28)
    nl.rectangle([sx0 + X(330), sy0 + X(58 + 6 * 30), sx0 + X(340), sy0 + X(58 + 6 * 30) + X(16)], fill=(226, 232, 240, int(255 * blink)))
    na = sstep(0.46, 0.62, t)
    if na > 0.02:
        night_layer.putalpha(night_layer.getchannel("A").point(lambda a: int(a * na)))
        img.alpha_composite(night_layer)
    d = ImageDraw.Draw(img, "RGBA")
    # monitor stand
    d.rectangle([X(936), X(636), X(1000), X(664)], fill=(20, 22, 30, 255))
    d.rounded_rectangle([X(884), X(658), X(1052), X(672)], X(6), fill=(20, 22, 30, 255))

    # ---- plant (left of desk) ----
    d.rounded_rectangle([X(140), X(606), X(232), X(652)], X(8), fill=mix((194, 84, 52), (96, 46, 40), night) + (255,))
    leaf_c = mix((46, 140, 76), (16, 60, 40), night)
    for ang, ln in [(-50, 74), (-18, 92), (14, 84), (44, 66)]:
        a = math.radians(ang - 90)
        ex, ey = X(186) + X(ln) * math.cos(a), X(606) + X(ln) * math.sin(a)
        d.line([X(186), X(610), ex, ey], fill=leaf_c + (255,), width=int(X(9)))
        d.ellipse([ex - X(13), ey - X(8), ex + X(13), ey + X(8)], fill=leaf_c + (255,))
    # ---- books ----
    d.rounded_rectangle([X(452), X(622), X(600), X(652)], X(4), fill=mix((37, 99, 235), (22, 44, 92), night) + (255,))
    d.rounded_rectangle([X(466), X(594), X(586), X(622)], X(4), fill=mix((220, 38, 38), (96, 26, 34), night) + (255,))
    # ---- phone (sales day tool, dims at night) ----
    d.rounded_rectangle([X(252), X(648), X(404), X(676)], X(10), fill=(18, 20, 28, 255))
    ph = mix((125, 211, 252), (38, 48, 68), night)
    d.rounded_rectangle([X(262), X(654), X(394), X(670)], X(6), fill=ph + (255,))

    # ---- lamp ----
    lamp_on = sstep(0.55, 0.8, t)
    if lamp_on > 0.02:  # light cone + pool (under lamp head, over desk)
        cone = Image.new("RGBA", (w, h), (0, 0, 0, 0)); cd2 = ImageDraw.Draw(cone)
        cd2.polygon([X(1332), X(452), X(1150), X(676), X(1560), X(676)], fill=(255, 197, 94, int(52 * lamp_on)))
        cd2.ellipse([X(1150), X(640), X(1560), X(700)], fill=(255, 205, 110, int(66 * lamp_on)))
        img.alpha_composite(cone.filter(ImageFilter.GaussianBlur(X(6)))); d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([X(1352), X(640), X(1472), X(664)], fill=(24, 24, 34, 255))
    d.line([X(1412), X(646), X(1412), X(478)], fill=(24, 24, 34, 255), width=int(X(10)))
    d.line([X(1412), X(478), X(1348), X(440)], fill=(24, 24, 34, 255), width=int(X(10)))
    d.polygon([X(1304), X(452), X(1360), X(404), X(1404), X(436), X(1348), X(484)], fill=(24, 24, 34, 255))
    if lamp_on > 0.02:
        d.ellipse([X(1328), X(438), X(1368), X(466)], fill=(255, 214, 120, int(255 * lamp_on)))
    # ---- mug + steam ----
    d.rounded_rectangle([X(1258), X(602), X(1312), X(652)], X(7), fill=mix((214, 69, 56), (128, 40, 40), night) + (255,))
    d.arc([X(1300), X(610), X(1336), X(646)], -80, 90, fill=mix((214, 69, 56), (128, 40, 40), night) + (255,), width=int(X(6)))
    if night > 0.1:
        for k, xo in enumerate([1272, 1292]):
            pts = []
            for s_i in range(21):
                f = s_i / 20
                pts.append((X(xo + 6 * math.sin(f * 5 + k * 2 + t * 2)), X(596 - f * 44)))
            d.line(pts, fill=(226, 232, 240, int(90 * night)), width=int(X(3)))
    # ---- chair silhouette (foreground) ----
    ch = Image.new("RGBA", (w, h), (0, 0, 0, 0)); chd = ImageDraw.Draw(ch)
    chc = mix((52, 54, 68), (6, 6, 14), night)
    chd.rounded_rectangle([X(470), X(716), X(724), X(930)], X(46), fill=chc + (232,))
    img.alpha_composite(ch); d = ImageDraw.Draw(img, "RGBA")

    # ---- finish: grain + vignette ----
    img = img.convert("RGB")
    g = GRAIN.get((W, H))
    if g is None:
        g = make_grain(W, H); GRAIN[(W, H)] = g
    gbig = g.resize((w, h), Image.NEAREST).convert("L")
    img = Image.composite(Image.new("RGB", (w, h), (128, 128, 128)), img, gbig.point(lambda v: 8))
    vig = vignette(W, H).resize((w, h))
    va = vig.getchannel("A").point(lambda a: int(a * lerp(0.35, 0.8, night)))
    black = Image.new("RGBA", (w, h), (0, 0, 0, 255)); black.putalpha(va)
    img = Image.alpha_composite(img.convert("RGBA"), black).convert("RGB")
    return img.resize((W, H), Image.LANCZOS)

def main():
    jobs = [("frames", 150, 1600, 900), ("frames-m", 84, 960, 540)]
    if len(sys.argv) > 1 and sys.argv[1] == "mobile":
        jobs = [("frames-m", 84, 960, 540)]
    for sub, n, W, H in jobs:
        outdir = os.path.join(OUT, sub); os.makedirs(outdir, exist_ok=True)
        total = 0
        for i in range(n):
            t = i / (n - 1)
            frame = draw_frame(t, W, H)
            p = os.path.join(outdir, f"f{i:03d}.webp")
            frame.save(p, "WEBP", quality=78, method=4)
            total += os.path.getsize(p)
        print(f"{sub}: {n} frames {W}x{H} total {total/1024:.0f} KiB avg {total/n/1024:.1f} KiB")
    poster = draw_frame(0.62, 1600, 900)
    poster.save(os.path.join(OUT, "poster.jpg"), "JPEG", quality=86)
    print("poster.jpg", os.path.getsize(os.path.join(OUT, "poster.jpg")) // 1024, "KiB")

if __name__ == "__main__":
    main()
