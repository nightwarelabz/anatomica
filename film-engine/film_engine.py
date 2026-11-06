"""ANATOMICA film - animation/compositing engine (v5).

Renders the five acts from the production plates in prod/ (2560x1440)
into 1920x1080 act files in acts/. All motion is post work on the
plates: eased crop-window camera moves, layer crossfades, the x-ray
sweep, travelling pulse highlights, heart pulse scaling on the shared
ECG curve, HUD drawn at 2x and downscaled, drape composited last in
every frame, and the NIGHTWARE LABZ mark stamped on every frame
(via compose_still.stamp_mark).

One physiological script drives everything: hr_at(t) (heart rate),
phase_at(t) (cardiac phase) and resp_at(t) are shared by the heart
pulse, the HUD traces and (in sound_design.py) the monitor/ventilator
sound, so picture and sound can never drift apart.

Acts (24 fps, 10080 frames total):
  I   Intake          0:00-0:45   frames    0-1079
  II  X-Ray Sweep     0:45-1:40   frames 1080-2399
  III Layer Analysis  1:40-3:10   frames 2400-4559
  IV  The Procedure   3:10-5:40   frames 4560-8159
  V   Post-Op         5:40-7:00   frames 8160-10079

Run:  python3 film_engine.py [act_number ...]   (default: all)
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser(
    '~/workspace/anatomica-engine-stage/film-engine'))
from compose_still import stamp_mark  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.join(HERE, 'prod')
ACTS = os.path.join(HERE, 'acts')
FPS = 24
OUT_W, OUT_H = 1920, 1080
PLATE_W, PLATE_H = 2560, 1440

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

# ------------------------------------------------------------------
# physiology script (single source of truth for picture + sound)
# ------------------------------------------------------------------
# HR timeline (bpm): baseline 72; Act IV builds tension: incision
# ~210s, dip to 54 at 255s, recovery to 76 by 300s, settle 70.
_HR_KEYS = [(0, 72), (185, 72), (205, 84), (215, 88), (235, 66),
            (255, 54), (275, 62), (300, 76), (330, 72), (420, 70)]


def _lerp_keys(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            u = u * u * (3 - 2 * u)
            return v0 + (v1 - v0) * u
    return keys[-1][1]


def hr_at(t):
    return _lerp_keys(_HR_KEYS, t)


def _beat_times():
    """Integrate the HR curve into beat onset times (seconds)."""
    times = []
    phase = 0.0
    t = 0.0
    dt = 0.02
    while t < 420.0:
        phase += hr_at(t) / 60.0 * dt
        if phase >= 1.0:
            phase -= 1.0
            times.append(t)
        t += dt
    return times


BEATS = _beat_times()


def phase_at(t):
    """Cardiac phase 0..1 at time t (0 = R peak)."""
    import bisect
    i = bisect.bisect_right(BEATS, t)
    if i == 0:
        return 0.0
    prev = BEATS[i - 1]
    nxt = BEATS[i] if i < len(BEATS) else prev + 60.0 / hr_at(t)
    return (t - prev) / max(nxt - prev, 1e-6)


def ecg_value(phase):
    """The v4 ECG waveform shape, as a function of cardiac phase."""
    p = phase
    v = 2.0 * math.sin(p * math.pi * 2) * 0.4
    v += 3.0 * math.exp(-((p - 0.16) ** 2) / 0.0004)
    v += -7.0 * math.exp(-((p - 0.235) ** 2) / 0.00008)
    v += 34.0 * math.exp(-((p - 0.26) ** 2) / 0.00012)
    v += -9.0 * math.exp(-((p - 0.285) ** 2) / 0.00008)
    v += 6.0 * math.exp(-((p - 0.46) ** 2) / 0.0012)
    return -v / 34.0  # normalised: R peak = -1 (screen up)


def resp_at(t):
    """Respiration phase (12 breaths/min = 5 s period)."""
    return (t % 5.0) / 5.0


def spo2_at(t):
    return 98 if hr_at(t) > 60 else 96


def bp_at(t):
    hr = hr_at(t)
    sys_ = int(round(118 + (hr - 72) * 0.35))
    dia = int(round(76 + (hr - 72) * 0.22))
    return sys_, dia


# ------------------------------------------------------------------
# plate loading / compositing helpers
# ------------------------------------------------------------------
_CACHE = {}


def plate(cam, group):
    key = (cam, group)
    if key not in _CACHE:
        path = os.path.join(PROD, f'{cam}_{group}.png')
        _CACHE[key] = Image.open(path).convert('RGBA')
    return _CACHE[key]


def over(img, layer, alpha):
    if alpha <= 0.0:
        return img
    p = layer
    if alpha < 0.999:
        p = layer.copy()
        a = p.getchannel('A').point(lambda v: int(v * alpha))
        p.putalpha(a)
    img.alpha_composite(p)
    return img


def scaled_about(layer, cx, cy, s):
    """Scale a plate about a pivot point (heart pulse)."""
    if abs(s - 1.0) < 1e-4:
        return layer
    w, h = layer.size
    nw, nh = int(w * s), int(h * s)
    r = layer.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    canvas.alpha_composite(r, (int(cx - cx * s), int(cy - cy * s)))
    return canvas


# heart centroid on the main camera (measured from the heart plate
# alpha: plate-px bbox 1435-1537 x 500-596 -> centroid ~ (1486, 548))
HEART_MAIN = (1486, 548)
# surgery-camera heart centroid is measured when the surg plates land
HEART_SURG = (1280, 620)

CAPTIONS = [
    'I // INTAKE - PATIENT ON TABLE - VITALS LIVE',
    'II // X-RAY SWEEP - SKELETAL SURVEY',
    'III // LAYER ANALYSIS - MUSCLE / NERVE / VASCULAR',
    'IV // LIVE PROCEDURE - THORACIC FIELD OPEN',
    'V // CLOSE + POST-OP SCAN - VITALS STABLE',
]
BOTTOM = 'PURE KRELL // ANATOMICA - SIMULATED PATIENT - NO REAL PERSON'


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def crop_pan(img, cx, cy, scale, out_w=OUT_W, out_h=OUT_H):
    """Crop a window of the plate and resize to output size.
    (cx, cy) is the window centre in plate pixels; scale = plate
    pixels per output pixel (>1 zooms out, <1 zooms in)."""
    vw, vh = out_w * scale, out_h * scale
    x0 = max(0.0, min(PLATE_W - vw, cx - vw / 2))
    y0 = max(0.0, min(PLATE_H - vh, cy - vh / 2))
    box = (int(x0), int(y0), int(x0 + vw), int(y0 + vh))
    return img.crop(box).resize((out_w, out_h), Image.LANCZOS)


# ------------------------------------------------------------------
# HUD (drawn at 2x, downscaled)
# ------------------------------------------------------------------
def draw_hud(frame_img, t, act_idx, caption_alpha=1.0):
    S = 2
    hud = Image.new('RGBA', (OUT_W * S, OUT_H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(hud, 'RGBA')
    f_cap = ImageFont.truetype(FONTB, 21 * S)
    f_big = ImageFont.truetype(FONTB, 44 * S)
    f_med = ImageFont.truetype(FONT, 20 * S)
    f_small = ImageFont.truetype(FONT, 15 * S)
    ink = (200, 225, 235, 235)
    dim = (140, 170, 185, 200)
    ecg_c = (90, 235, 140, 255)
    spo2_c = (110, 200, 255, 255)
    resp_c = (240, 200, 120, 255)

    def tx(x, y, s, font, fill=ink):
        d.text((x * S, y * S), s, font=font, fill=fill)

    # caption top-left
    a = int(235 * caption_alpha)
    d.text((28 * S, 22 * S), CAPTIONS[act_idx], font=f_cap,
           fill=(200, 225, 235, a))
    tx(28, 52, BOTTOM, f_small, dim)

    # vitals panel (right side)
    px, py, pw = 1560, 84, 330
    d.rectangle([px * S, py * S, (px + pw) * S, (py + 356) * S],
                fill=(4, 10, 14, 150), outline=(70, 100, 115, 160),
                width=S)
    tx(px + 16, py + 12, 'VITALS - LIVE', f_med)
    hr = hr_at(t)
    # ECG trace: last 4 seconds of the shared curve
    ex, ey, ew, eh = px + 16, py + 52, pw - 32, 74
    pts = []
    for i in range(ew):
        tt = t - 4.0 + 4.0 * i / ew
        v = ecg_value(phase_at(tt))
        pts.append(((ex + i) * S, (ey + eh / 2 + v * eh * 0.42) * S))
    d.line(pts, fill=ecg_c, width=2 * S)
    tx(ex, ey + eh + 6, 'ECG  LEAD II', f_small, dim)
    tx(px + 190, py + 44, f'{int(round(hr))}', f_big, ecg_c)
    tx(px + 262, py + 78, 'BPM', f_small, dim)
    # SpO2 pleth
    sy = py + 168
    pts = []
    for i in range(ew):
        tt = t - 4.0 + 4.0 * i / ew
        ph = phase_at(tt)
        v = math.exp(-ph * 5.5) * (0.75 + 0.25 * math.cos(ph * 6.28))
        pts.append(((ex + i) * S, (sy + 44 - v * 40) * S))
    d.line(pts, fill=spo2_c, width=2 * S)
    tx(ex, sy + 50, 'SPO2  PLETH', f_small, dim)
    tx(px + 190, sy - 6, f'{spo2_at(t)}', f_big, spo2_c)
    tx(px + 262, sy + 28, '%', f_small, dim)
    # RESP
    ry = py + 262
    pts = []
    for i in range(ew):
        tt = t - 4.0 + 4.0 * i / ew
        v = math.sin(resp_at(tt) * math.pi * 2)
        pts.append(((ex + i) * S, (ry + 22 - v * 16) * S))
    d.line(pts, fill=resp_c, width=2 * S)
    tx(ex, ry + 30, 'RESP', f_small, dim)
    tx(px + 190, ry - 8, '12', f_big, resp_c)
    sys_, dia = bp_at(t)
    tx(px + 16, py + 322, f'BP  {sys_} / {dia}      TEMP  36.8 C',
       f_med)
    hud = hud.resize((OUT_W, OUT_H), Image.LANCZOS)
    frame_img.alpha_composite(hud)
    return frame_img


def finish_frame(img, t, act_idx, caption_alpha=1.0):
    img = img.convert('RGBA')
    img = draw_hud(img, t, act_idx, caption_alpha)
    img = img.convert('RGB')
    img = stamp_mark(img)
    return img


# ------------------------------------------------------------------
# per-act frame builders: each returns an RGBA plate-space composite
# ------------------------------------------------------------------
def build_main_base(layers):
    """layers: ordered list of (group, alpha) over the main base."""
    img = plate('main', 'base').copy()
    for g, a in layers:
        over(img, plate('main', g), a)
    over(img, plate('main', 'drapeonly'), 1.0)
    return img


def frame_act1(t, lt):
    """Intake: intact patient, slow push-in, layers ghost in late."""
    u = lt / 45.0
    img = plate('main', 'base').copy()
    over(img, plate('main', 'skin'), 1.0)
    over(img, plate('main', 'heart'),
         0.05 + 0.05 * math.sin(phase_at(t) * 6.283))
    ghost = ease((lt - 30.0) / 13.0) * 0.30
    if ghost > 0:
        over(img, plate('main', 'muscle'), ghost)
        over(img, plate('main', 'bone'), ghost * 0.8)
    over(img, plate('main', 'drapeonly'), 1.0)
    cx = 1280 + (1180 - 1280) * ease(u)
    cy = 700 + (640 - 700) * ease(u)
    sc = 1.333 + (1.02 - 1.333) * ease(u)
    return crop_pan(img, cx, cy, sc)


def frame_act2(t, lt):
    """X-ray sweep: a bright band travels head->feet; behind it the
    skeleton shows through the skin."""
    img = plate('main', 'base').copy()
    over(img, plate('main', 'skin'), 1.0)
    bone = plate('main', 'bone')
    W, H = PLATE_W, PLATE_H
    sweep_y = -100 + (H + 200) * ease(lt / 40.0) if lt < 40 else H + 200
    mask = Image.new('L', (W, H), 0)
    md = ImageDraw.Draw(mask)
    if lt < 40:
        md.rectangle([0, 0, W, int(sweep_y)], fill=235)
        band = Image.new('L', (W, H), 0)
        bd = ImageDraw.Draw(band)
        bd.rectangle([0, int(sweep_y) - 26, W, int(sweep_y) + 26],
                     fill=120)
        mask = Image.fromarray(np.maximum(np.array(mask),
                                          np.array(band)).astype('uint8'))
    else:
        mask = Image.new('L', (W, H), 235)
    bone_a = bone.copy()
    bone_a.putalpha(mask)
    img.alpha_composite(bone_a)
    over(img, plate('main', 'drapeonly'), 1.0)
    if lt > 46:  # hold the skeletal survey, slow drift
        pass
    return crop_pan(img, 1280, 690, 1.28)


def _pulse_mask(base_alpha, t, speed=0.55, width=0.16, cycles=1):
    """Brightened copy of a layer where a pulse band travels along
    the layer's own extent (top->bottom of its alpha bbox)."""
    a = np.array(base_alpha).astype(np.float32) / 255.0
    ys, xs = np.nonzero(a > 0.05)
    if len(ys) == 0:
        return None
    y0, y1 = ys.min(), ys.max()
    prog = (np.arange(a.shape[0])[:, None] - y0) / max(y1 - y0, 1)
    ph = (t * speed) % 1.0
    band = np.exp(-((prog - ph) ** 2) / (2 * width ** 2))
    band += np.exp(-((prog - ph - 1) ** 2) / (2 * width ** 2))
    band += np.exp(-((prog - ph + 1) ** 2) / (2 * width ** 2))
    glow = np.clip(a * band * 1.6, 0, 1)
    return glow


def frame_act3(t, lt):
    """Layer analysis: muscle, then vascular pulse, then nerves,
    then organs/brain — each with a travelling signal."""
    img = plate('main', 'base').copy()
    over(img, plate('main', 'skin'), 0.10)
    segs = [(0, 22, 'muscle'), (22, 45, 'vessels'),
            (45, 68, 'nerve'), (68, 90, 'organs')]
    cur = None
    fade = 0.0
    for s0, s1, name in segs:
        if s0 <= lt < s1:
            cur, fade = name, ease((lt - s0) / 3.0)
    if cur == 'muscle':
        over(img, plate('main', 'muscle'), 0.85 * fade)
        over(img, plate('main', 'bone'), 0.25 * fade)
    elif cur == 'vessels':
        over(img, plate('main', 'muscle'), 0.18)
        ves = plate('main', 'vessels')
        over(img, ves, 0.95 * fade)
        glow = _pulse_mask(ves.getchannel('A'), t)
        if glow is not None:
            g = Image.new('RGBA', ves.size, (255, 90, 70, 0))
            g.putalpha(Image.fromarray((glow * 255).astype('uint8')))
            img.alpha_composite(g)
        over(img, plate('main', 'heart'), fade)
    elif cur == 'nerve':
        over(img, plate('main', 'bone'), 0.15)
        ner = plate('main', 'nerve')
        over(img, ner, 0.95 * fade)
        glow = _pulse_mask(ner.getchannel('A'), t, speed=0.4)
        if glow is not None:
            g = Image.new('RGBA', ner.size, (255, 230, 150, 0))
            g.putalpha(Image.fromarray((glow * 255).astype('uint8')))
            img.alpha_composite(g)
        over(img, plate('main', 'brain'), 0.9 * fade)
    elif cur == 'organs':
        over(img, plate('main', 'lung'), 0.9 * fade)
        over(img, plate('main', 'organliver'), 0.9 * fade)
        over(img, plate('main', 'heart'), fade)
        over(img, plate('main', 'brain'), 0.9 * fade)
    over(img, plate('main', 'drapeonly'), 1.0)
    return crop_pan(img, 1280, 690, 1.26)


def frame_act5(t, lt):
    """Post-op: layers recombine to the intact patient, confirmation
    sweep, slow pull-back to the wide."""
    u = lt / 80.0
    img = plate('main', 'base').copy()
    k = ease(lt / 25.0)
    over(img, plate('main', 'bone'), 0.55 * (1 - k))
    over(img, plate('main', 'muscle'), 0.45 * (1 - k))
    over(img, plate('main', 'vessels'), 0.8 * (1 - k))
    over(img, plate('main', 'nerve'), 0.8 * (1 - k))
    over(img, plate('main', 'heart'), 1.0)
    over(img, plate('main', 'skin'), 0.14 + 0.86 * k)
    over(img, plate('main', 'drapeonly'), 1.0)
    sc = 1.05 + (1.333 - 1.05) * ease((lt - 40.0) / 38.0)
    return crop_pan(img, 1240, 670, sc)


# Act IV event timeline (absolute film seconds; Act IV spans
# 190-340). film_act4.py and sound_design.py both read these, so
# picture and sound share one script.
ACT4 = dict(incision_t=210.0, retractor_t=226.0, suction=(240.0, 258.0),
            dip_t=255.0, graft_t=266.0, suture_start=302.0,
            close_t=332.0)

# Act IV lives in film_act4.py (needs the surg plates + sprites).

ACTS_SPEC = [
    (1, 0, 1080, frame_act1),
    (2, 1080, 1320, frame_act2),
    (3, 2400, 2160, frame_act3),
    (5, 8160, 1920, frame_act5),
]


def render_act(act_idx, start, count, fn):
    os.makedirs(ACTS, exist_ok=True)
    out = os.path.join(ACTS, f'act{act_idx}.mp4')
    cmd = ['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{OUT_W}x{OUT_H}', '-r', str(FPS), '-i', '-',
           '-an', '-c:v', 'libx264', '-crf', '15', '-preset', 'medium',
           '-pix_fmt', 'yuv420p', out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    for i in range(count):
        f = start + i
        t = f / FPS
        img = fn(t, i / FPS)
        img = finish_frame(img, t, act_idx - 1)
        proc.stdin.write(img.tobytes())
        if i % 240 == 0:
            print(f'act{act_idx} frame {i}/{count}', flush=True)
    proc.stdin.close()
    proc.wait()
    print('ACT DONE', out)


def main():
    wanted = [int(x) for x in sys.argv[1:]] or [1, 2, 3, 5]
    for act_idx, start, count, fn in ACTS_SPEC:
        if act_idx in wanted:
            render_act(act_idx, start, count, fn)


if __name__ == '__main__':
    main()
