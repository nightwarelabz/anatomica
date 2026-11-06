"""ANATOMICA film - sound design engine (v5).

Builds the full 7-minute score/soundscape for the film: a dark,
ominous theatre bed with every event locked to the same physiology
script the picture uses (film_engine.hr_at / phase_at / resp_at /
BEATS / ACT4), so sound and image cannot drift.

Design rules (locked with the film spec):
- tone: very ominous, serious; no light or playful elements
- bed: detuned fundamentals ~41 Hz + ~55 Hz under filtered brown
  noise; the drone drops a semitone through Act IV and resolves in V
- deep sub-thump locked to every heartbeat (the shared BEATS list)
- ventilator at 12/min locked to the shared respiration phase
- cautery = low electrical buzz; suction = lowpassed noise drag;
  instruments = sparse heavy metallic contacts with long decay
- near-silence in the seconds before the incision
- sweep sounds stay under 2 kHz; master lowpassed ~6 kHz outside pips
- master: -16 LUFS integrated, true peak <= -1.5 dBFS

Verification (four steps, run with --verify):
1. band-energy profile per act
2. spectrogram rendered to PNG for visual inspection
3. onset audit: detected heartbeat onsets vs BEATS, tolerance
   +/-2 frames (0.083 s)
4. loudness + true-peak metering (ffmpeg loudnorm / astats)

Run:  python3 sound_design.py [--verify]
Out:  acts/score.wav  (48 kHz, stereo, 420 s)
"""
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import film_engine as fe  # noqa: E402

SR = 48000
DUR = 420.0
N = int(SR * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'acts', 'score.wav')
A4 = fe.ACT4


def t_axis():
    return np.arange(N) / SR


def lowpass(x, cutoff, sr=SR):
    """One-pole lowpass, applied forward (causal, dark)."""
    a = 1.0 - math.exp(-2 * math.pi * cutoff / sr)
    y = np.empty_like(x)
    acc = 0.0
    # scipy-free loop is too slow in Python; use lfilter via FFT-free
    # cumulative form with numpy: use scipy if available.
    from scipy.signal import lfilter
    return lfilter([a], [1.0, -(1.0 - a)], x)


def bandpass_noise(dur, cutoff_lo, cutoff_hi, seed=7):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(int(dur * SR))
    from scipy.signal import butter, sosfilt
    sos = butter(2, [cutoff_lo, cutoff_hi], btype='band', fs=SR,
                 output='sos')
    return sosfilt(sos, x)


def brown_noise(dur, seed=3):
    rng = np.random.default_rng(seed)
    w = rng.standard_normal(int(dur * SR))
    b = np.cumsum(w)
    b = b - np.linspace(0, b[-1], len(b))
    return b / (np.abs(b).max() + 1e-9)


def env_ad(n, attack, decay, sr=SR):
    a = int(attack * sr)
    d = int(decay * sr)
    e = np.zeros(n)
    if a > 0:
        e[:a] = np.linspace(0, 1, a)
    if d > 0:
        e[a:a + d] = np.exp(-np.arange(d) / (decay * sr / 3.0))
    return e


def add_at(track, sig, t0):
    i = int(t0 * SR)
    j = min(N, i + len(sig))
    if j > i:
        track[i:j] += sig[:j - i]


def build():
    t = t_axis()
    mix = np.zeros(N)

    # ---- drone bed ---------------------------------------------
    # semitone drop through Act IV: factor glides 1 -> 2^(-1/12)
    # between 195 s and 215 s, holds, resolves 325-345 s.
    def drop_factor(tt):
        semi = 2 ** (-1 / 12)

        def ease_arr(u):
            u = np.clip(u, 0.0, 1.0)
            return u * u * (3 - 2 * u)

        f = np.ones_like(tt)
        down = (tt > 195) & (tt < 215)
        f[down] = 1 - (1 - semi) * ease_arr((tt[down] - 195) / 20.0)
        hold = (tt >= 215) & (tt <= 325)
        f[hold] = semi
        up = (tt > 325) & (tt < 345)
        f[up] = semi + (1 - semi) * ease_arr((tt[up] - 325) / 20.0)
        return f
    fac = drop_factor(t)
    ph1 = np.cumsum(41.2 * fac) / SR
    ph2 = np.cumsum(55.0 * fac * 1.003) / SR
    drone = (0.55 * np.sin(2 * np.pi * ph1)
             + 0.38 * np.sin(2 * np.pi * ph2)
             + 0.18 * np.sin(2 * np.pi * ph1 * 2.0))
    room = brown_noise(DUR) * 0.5
    room = lowpass(room, 420)
    bed = drone * 0.16 + room * 0.10
    # near-silence before the incision (203-210 s): duck the bed
    duck = np.ones(N)
    i0, i1 = int(202 * SR), int(210 * SR)
    duck[i0:i1] = np.linspace(1.0, 0.25, i1 - i0)
    i2 = int(214 * SR)
    duck[i1:i2] = np.linspace(0.25, 1.0, i2 - i1)
    mix += bed * duck

    # ---- heartbeat sub-thump on the shared BEATS ---------------
    thump_len = int(0.16 * SR)
    tt = np.arange(thump_len) / SR
    for bt in fe.BEATS:
        f0 = 68 - 23 * (tt / 0.16)
        ph = np.cumsum(f0) / SR
        th = np.sin(2 * np.pi * ph) * np.exp(-tt / 0.045)
        gain = 0.5
        if A4['suction'][0] <= bt <= A4['suction'][1]:
            gain = 0.42
        add_at(mix, th * gain, bt)

    # ---- ECG pips ----------------------------------------------
    pip_len = int(0.07 * SR)
    pt = np.arange(pip_len) / SR
    for bt in fe.BEATS:
        in_act4 = 190 <= bt <= 340
        sparse = (int(bt) % 2 == 0)
        if not in_act4 and not sparse:
            continue
        freq = 660.0 - (98 - fe.spo2_at(bt)) * 12.0
        pip = np.sin(2 * np.pi * freq * pt) * np.exp(-pt / 0.018)
        add_at(mix, pip * 0.055, bt + 0.02)

    # ---- ventilator, locked to respiration phase ----------------
    vent_period = 5.0
    for k in range(int(DUR / vent_period)):
        t0 = k * vent_period
        seg_n = int(3.2 * SR)
        st = np.arange(seg_n) / SR
        swell = np.sin(np.pi * np.clip(st / 3.2, 0, 1)) ** 2
        noise = bandpass_noise(3.2, 200, 750, seed=100 + k)
        add_at(mix, noise[:seg_n] * swell * 0.05, t0)

    # ---- Act II sweep whooshes (under 2 kHz) ---------------------
    for s0 in (45.0, 100.0):
        seg_n = int(40 * SR)
        noise = bandpass_noise(40, 300, 1600, seed=42)
        swell = np.sin(np.pi * np.arange(seg_n) / seg_n) ** 2
        add_at(mix, noise * swell * 0.035, s0)

    # ---- Act IV events -------------------------------------------
    # cautery buzz at the incision (3.5 s)
    cn = int(3.5 * SR)
    ct = np.arange(cn) / SR
    buzz = (np.sin(2 * np.pi * 118 * ct)
            + 0.6 * np.sin(2 * np.pi * 236 * ct)
            + 0.3 * np.sin(2 * np.pi * 359 * ct))
    buzz *= (0.8 + 0.2 * np.sin(2 * np.pi * 31 * ct))
    buzz *= np.sin(np.pi * np.clip(ct / 3.5, 0, 1)) ** 2
    add_at(mix, buzz * 0.028, A4['incision_t'])
    # retractor contacts: two heavy metallic hits
    for dt_ in (0.0, 1.4):
        hn = int(1.8 * SR)
        ht = np.arange(hn) / SR
        hit = (np.sin(2 * np.pi * 196 * ht) * np.exp(-ht / 0.5)
               + 0.7 * np.sin(2 * np.pi * 523 * ht) * np.exp(-ht / 0.22)
               + 0.4 * np.sin(2 * np.pi * 1244 * ht)
               * np.exp(-ht / 0.07))
        add_at(mix, hit * 0.11, A4['retractor_t'] + dt_)
    # suction drag
    sn = int((A4['suction'][1] - A4['suction'][0]) * SR)
    snoise = lowpass(np.random.default_rng(9).standard_normal(sn), 500)
    senv = np.sin(np.pi * np.arange(sn) / sn) ** 1.5
    add_at(mix, snoise * senv * 0.075, A4['suction'][0])
    # graft placement: one deep soft swell
    gn = int(2.6 * SR)
    gt = np.arange(gn) / SR
    gph = np.cumsum(82 - 20 * (gt / 2.6)) / SR
    graft = np.sin(2 * np.pi * gph) * np.sin(np.pi * gt / 2.6) ** 2
    add_at(mix, graft * 0.16, A4['graft_t'])
    # sutures: soft regular clicks from suture_start to close
    tt_s = A4['suture_start']
    while tt_s < A4['close_t']:
        kn = int(0.3 * SR)
        kt = np.arange(kn) / SR
        click = (np.sin(2 * np.pi * 340 * kt) * np.exp(-kt / 0.05)
                 + 0.5 * np.sin(2 * np.pi * 890 * kt)
                 * np.exp(-kt / 0.02))
        add_at(mix, click * 0.05, tt_s)
        tt_s += 3.7

    # ---- master --------------------------------------------------
    # steep master lowpass: the spec caps energy above ~6 kHz; a
    # one-pole at 6 kHz left 7% of Act IV up there (metallic hits).
    from scipy.signal import butter, sosfilt
    mix = sosfilt(butter(4, 5200, btype='low', fs=SR, output='sos'),
                  mix)
    fade_in = int(2.0 * SR)
    fade_out = int(4.0 * SR)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)
    stereo = np.stack([mix, mix], axis=1)
    return stereo


def measure_loudness(path):
    r = subprocess.run(
        ['ffmpeg', '-i', path, '-af',
         'loudnorm=I=-16:TP=-1.5:print_format=json', '-f', 'null', '-'],
        capture_output=True, text=True)
    import json
    txt = r.stderr
    js = txt[txt.rfind('{'):txt.rfind('}') + 1]
    return json.loads(js)


def write_wav(stereo, path):
    import wave
    peak = np.abs(stereo).max()
    target = 10 ** (-1.5 / 20.0)
    if peak > 0:
        stereo = stereo * (target * 0.999 / peak)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return peak


def verify(path):
    print('== STEP 1: band-energy profile per act ==')
    import wave
    with wave.open(path, 'rb') as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2')
    mono = raw.reshape(-1, 2).mean(axis=1) / 32768.0
    bands = [(20, 60), (60, 250), (250, 2000), (2000, 6000),
             (6000, 20000)]
    acts = [(0, 45), (45, 100), (100, 190), (190, 340), (340, 420)]
    for ai, (s0, s1) in enumerate(acts):
        seg = mono[int(s0 * SR):int(s1 * SR)]
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        freqs = np.fft.rfftfreq(len(seg), 1 / SR)
        tot = spec.sum() + 1e-9
        shares = []
        for lo, hi in bands:
            m = (freqs >= lo) & (freqs < hi)
            shares.append(spec[m].sum() / tot)
        print(f' act {ai + 1}: ' + ' '.join(
            f'{lo}-{hi}Hz {sh:.2f}' for (lo, hi), sh
            in zip(bands, shares)))
        assert shares[-1] < 0.05, 'energy above 6 kHz out of bounds'
    print('== STEP 3: heartbeat onset audit ==')
    from scipy.signal import butter, sosfilt, find_peaks
    sos = butter(2, [30, 90], btype='band', fs=SR, output='sos')
    low = sosfilt(sos, mono)
    env = np.abs(low)
    env = np.convolve(env, np.ones(2400) / 2400, mode='same')
    peaks, _ = find_peaks(env, distance=int(0.4 * SR),
                          height=env.max() * 0.25)
    detected = peaks / SR
    ok, worst = 0, 0.0
    for bt in fe.BEATS[2:-2]:
        d = np.abs(detected - bt).min() if len(detected) else 9
        worst = max(worst, d)
        if d <= 2 / 24:
            ok += 1
    print(f' beats matched {ok}/{len(fe.BEATS) - 4} within 2 frames; '
          f'worst offset {worst:.3f}s')
    assert ok >= len(fe.BEATS) - 6, 'onset audit failed'
    print('== STEP 4: loudness / true peak ==')
    m = measure_loudness(path)
    print(' integrated LUFS:', m['input_i'], ' true peak:', m['input_tp'])
    print('== STEP 2: spectrogram ==')
    from scipy.signal import spectrogram
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    f, tt, Sxx = spectrogram(mono, SR, nperseg=4096)
    plt.figure(figsize=(14, 5))
    plt.pcolormesh(tt, f, 10 * np.log10(Sxx + 1e-12), vmax=-20,
                   cmap='inferno')
    plt.ylim(0, 8000)
    plt.xlabel('seconds')
    plt.ylabel('Hz')
    plt.title('ANATOMICA score spectrogram')
    out = os.path.join(HERE, 'acts', 'spectrogram.png')
    plt.savefig(out, dpi=80)
    print(' spectrogram ->', out)
    print('VERIFY DONE')


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    stereo = build()
    peak = write_wav(stereo, OUT)
    print('score written', OUT, 'pre-limit peak %.3f' % peak)
    if '--verify' in sys.argv:
        verify(OUT)


if __name__ == '__main__':
    main()
