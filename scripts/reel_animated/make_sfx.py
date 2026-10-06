#!/usr/bin/env python3
"""
Synthesizes the sound effects used by the animated reels (no external files,
no licenses). Writes WAV files (48 kHz, mono, 16 bit) into sfx/.

    python3 scripts/reel_animated/make_sfx.py

The result is deterministic (fixed random seed). The generated files are
committed, so the routine does not need to run this: run it only if you want to
tweak the sounds (edit the functions below) and regenerate them.
"""
import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path(__file__).resolve().parent.parent.parent / "sfx"
rng = np.random.default_rng(7)


def t(seconds):
    return np.arange(int(SR * seconds)) / SR


def lowpass(x, cutoff_curve):
    """One-pole low-pass whose cutoff (Hz) changes sample by sample."""
    y = np.zeros_like(x)
    prev = 0.0
    for i, (v, fc) in enumerate(zip(x, cutoff_curve)):
        a = 1 - np.exp(-2 * np.pi * fc / SR)
        prev += a * (v - prev)
        y[i] = prev
    return y


def fade(x, fin=0.005, fout=0.02):
    n = len(x)
    a, b = int(SR * fin), int(SR * fout)
    x = x.copy()
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def norm(x, peak=0.8):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def whoosh(dur=0.55):
    """Noise sweeping up in brightness then closing: a swipe."""
    x = t(dur)
    noise = rng.standard_normal(len(x))
    center = 300 * (24 ** (np.sin(np.pi * x / dur) ** 0.8))  # 300 Hz -> ~7 kHz -> back
    env = np.sin(np.pi * x / dur) ** 1.6
    return fade(norm(lowpass(noise, center) * env))


def hit(dur=0.45):
    """Soft low thump with a short click: lands the new scene."""
    x = t(dur)
    freq = 55 + 110 * np.exp(-x * 28)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-x * 9)
    click = rng.standard_normal(len(x)) * np.exp(-x * 220) * 0.35
    return fade(norm(body + click), 0.001, 0.05)


def pop(dur=0.14):
    x = t(dur)
    freq = 900 + 500 * np.exp(-x * 40)
    s = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-x * 34)
    return fade(norm(s, 0.7), 0.001, 0.02)


def tick(dur=0.08):
    x = t(dur)
    s = rng.standard_normal(len(x)) * np.exp(-x * 90)
    s = lowpass(s, np.full(len(x), 6000.0))
    return fade(norm(s, 0.6), 0.0005, 0.01)


def ding(dur=0.9):
    """Two bell partials: the call to action."""
    x = t(dur)
    s = (np.sin(2 * np.pi * 1318.5 * x) + 0.5 * np.sin(2 * np.pi * 1975.5 * x)
         + 0.25 * np.sin(2 * np.pi * 2637 * x)) * np.exp(-x * 5.5)
    return fade(norm(s, 0.7), 0.001, 0.1)


def riser(dur=0.9):
    """Tension before the first transition after the hook."""
    x = t(dur)
    noise = rng.standard_normal(len(x))
    center = 200 * (30 ** (x / dur))
    env = (x / dur) ** 2
    return fade(norm(lowpass(noise, center) * env), 0.01, 0.01)


def save(name, data):
    OUT.mkdir(exist_ok=True)
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"sfx/{name}.wav  {len(data) / SR:.2f}s")


if __name__ == "__main__":
    for name, fn in [("whoosh", whoosh), ("hit", hit), ("pop", pop), ("tick", tick),
                     ("ding", ding), ("riser", riser)]:
        save(name, fn())
