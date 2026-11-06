"""ANATOMICA film - Act IV: The Procedure (surgery camera).

Composites the surg plates with the procedure beats, all timed from
film_engine.ACT4 (absolute film seconds) so picture and sound share
one script:
  incision_t   cautery glow line opens over the chest field
  retractor_t  retractor arcs settle at the field edges
  suction      an instrument silhouette works the field
  dip_t        vitals dip (HR curve lives in film_engine)
  graft_t      graft highlight fades in at the heart
  suture_start stitches appear one by one; the field closes
  close_t      field closed; pull back to the Act V handoff

No gore: the procedure reads as light, instruments and motion over
the approved surgery composite. The drape plate is composited last,
as in every act.

Run:  python3 film_act4.py
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import film_engine as fe

A4 = fe.ACT4
_CENTROID = None


def heart_centroid():
    """Alpha-weighted centroid of the surg heart plate."""
    global _CENTROID
    if _CENTROID is None:
        a = np.array(fe.plate('surg', 'heart').getchannel('A'),
                     dtype=np.float32)
        ys, xs = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        w = a.sum() + 1e-6
        _CENTROID = (float((a * xs).sum() / w),
                     float((a * ys).sum() / w))
    return _CENTROID


def _ellipse_mask(size, cx, cy, rx, ry, blur=18):
    m = Image.new('L', size, 0)
    d = ImageDraw.Draw(m)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))


def frame_act4(t, lt):
    cx, cy = heart_centroid()
    img = fe.plate('surg', 'base').copy()
    fe.over(img, fe.plate('surg', 'skin'), 0.10)

    # incision opening 0..1 (opens at incision_t, closes by close_t)
    open_u = fe.ease((t - A4['incision_t']) / 8.0)
    if t > A4['suture_start']:
        open_u *= 1.0 - 0.85 * fe.ease(
            (t - A4['suture_start'])
            / (A4['close_t'] - A4['suture_start']))
    rx = 300 * open_u
    ry = 120 * open_u

    muscle = fe.plate('surg', 'muscle')
    fe.over(img, muscle, 0.25)
    if open_u > 0.01:
        # deepen the field inside the incision + warm rim glow
        mask = _ellipse_mask(img.size, cx, cy, rx, ry)
        dark = Image.new('RGBA', img.size, (30, 4, 4, 0))
        dark.putalpha(mask.point(lambda v: int(v * 0.45)))
        img.alpha_composite(dark)
        glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                   outline=(255, 170, 90, 200), width=7)
        glow = glow.filter(ImageFilter.GaussianBlur(9))
        img.alpha_composite(glow)

    # lungs with a whisper of breathing motion
    resp = math.sin(fe.resp_at(t) * math.pi * 2)
    lung = fe.scaled_about(fe.plate('surg', 'lung'), cx, cy,
                           1.0 + 0.008 * resp)
    fe.over(img, lung, 0.55)

    # heart, pulsing on the shared ECG curve
    pulse = 1.0 + 0.05 * max(0.0, -fe.ecg_value(fe.phase_at(t)))
    heart = fe.scaled_about(fe.plate('surg', 'heart'), cx, cy, pulse)
    fe.over(img, heart, 1.0)
    fe.over(img, fe.plate('surg', 'vessels'), 0.9)

    fx = Image.new('RGBA', img.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fx, 'RGBA')
    # retractors: two steel arcs at the field edges
    if t >= A4['retractor_t'] and open_u > 0.05:
        a_in = fe.ease((t - A4['retractor_t']) / 3.0)
        for sgn in (-1, 1):
            ex = cx + sgn * rx * 0.92
            fd.arc([ex - 60, cy - ry - 26, ex + 60, cy + ry + 26],
                   start=80 if sgn < 0 else 260,
                   end=280 if sgn < 0 else 100,
                   fill=(168, 178, 190, int(220 * a_in)), width=13)
            fd.line([ex, cy - ry - 30, ex + sgn * 130,
                     cy - ry - 120],
                    fill=(120, 130, 142, int(200 * a_in)), width=11)
    # instrument silhouette during suction: slow pass over the field
    s0, s1 = A4['suction']
    if s0 <= t <= s1:
        u = (t - s0) / (s1 - s0)
        ix = cx - 340 + 680 * u
        iy = cy - 190 + 60 * math.sin(u * math.pi)
        fd.line([ix, iy - 260, ix + 26, iy + 60],
                fill=(16, 20, 26, 235), width=30)
        fd.line([ix + 26, iy + 60, ix + 88, iy + 128],
                fill=(16, 20, 26, 235), width=13)
        fd.ellipse([ix + 70, iy + 112, ix + 112, iy + 148],
                   outline=(150, 160, 172, 220), width=6)
    # graft highlight: a warm arc settling at the heart
    if t >= A4['graft_t']:
        ga = fe.ease((t - A4['graft_t']) / 6.0) * 0.85
        fd.arc([cx - 120, cy - 90, cx + 130, cy + 110], start=300,
               end=70, fill=(255, 205, 150, int(230 * ga)), width=10)
    # sutures: ticks appear along the closing line
    if t >= A4['suture_start']:
        n = int(9 * fe.ease((t - A4['suture_start'])
                            / (A4['close_t'] - A4['suture_start'])))
        for i in range(n):
            u = (i + 0.5) / 9.0
            sx = cx - rx * 0.8 + 1.6 * rx * u
            sy = cy + (u - 0.5) * ry * 0.5
            fd.line([sx - 13, sy - 13, sx + 13, sy + 13],
                    fill=(225, 232, 238, 235), width=5)
            fd.line([sx - 13, sy + 13, sx + 13, sy - 13],
                    fill=(225, 232, 238, 235), width=5)
    fx = fx.filter(ImageFilter.GaussianBlur(1.2))
    img.alpha_composite(fx)

    fe.over(img, fe.plate('surg', 'drapeonly'), 1.0)
    # camera: near-full frame, slow push; a breath closer at the dip
    sc = 1.10 - 0.08 * fe.ease(lt / 150.0)
    if A4['dip_t'] - 12 <= t <= A4['dip_t'] + 18:
        sc -= 0.03 * math.sin(
            (t - (A4['dip_t'] - 12)) / 30.0 * math.pi)
    return fe.crop_pan(img, cx, cy - 40, sc)


def main():
    fe.render_act(4, 4560, 3600,
                  lambda t, lt: frame_act4(t, lt))


if __name__ == '__main__':
    main()
