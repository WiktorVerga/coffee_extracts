#!/usr/bin/env python3
"""
Builds the animated reel of a post: same content and same look as the carousel,
narrated, with sound effects and music, 9:16, 15 to 30 seconds, no dead air.

Usage:
    python3 scripts/reel_animated/build_reel.py posts/2026-10-05-bitter-espresso

Input (inside the post folder):
    carousel.json   the carousel (already written and checked)
    reel.json       the narration, one line per slide:  {"scenes": [{"say": "..."}, ...]}

Output (inside the post folder):
    reel.mp4        the video (H.264 + AAC, 1080x1920, <= max_mb)
    reel-meta.json  duration, scene timings, music used, sizes
Temporary files go to .reel-build/<post>/ (ignored by git). Frames to look at
before publishing: .reel-build/<post>/frames/scene-XX.jpg

Exit codes:
    0  reel ready
    2  content problem (script too long/short, text doesn't fit...): edit reel.json
       or carousel.json and run again
    3  technical error (TTS, browser, ffmpeg...)
"""
import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
CFG = {
    "mode": "preview",
    "voice": "af_heart",
    "target_seconds": 30.0,
    "min_seconds": 27.0,
    "max_speed": 1.25,
    "voice_speed": 1.1,      # base speed of the voice: a reel needs energy, 1.0 sounds sleepy
    "max_gap": 0,            # longest silence kept INSIDE a line (s); 0 = keep the voice's natural pauses
    "title_pause": 0.8,      # silence (s) between a scene's first sentence (its "title") and the rest of the scene; 0 = off
    "voice_pitch_semitones": 0.0,   # voice pitch shift (0 = natural voice); duration is unchanged
    "voice_reverb_wet": 0.08,       # light room reverb on the voice (0 = dry, 0.3 = very roomy)
    "voice_reverb_seconds": 0.45,   # reverb tail length (RT60): short = small room
    "voice_echo_wet": 0.12,         # very light echo: the early reflections of a small room (0 = off)
    "max_mb": 18,
    "fps": 30,
    "video_bitrate": "4M",
    "hyperframes_version": "0.8.137",
    "music_dir": "music",
    "music_level_db": 0.0,
    "sfx_level_db": -14.0,   # sound effects level (dB), 0 = old loud level
    **CONFIG.get("reel_animated", {}),
}
SR = 48000
LEAD = 0.12          # silence before each narration line (s)
PAD = 0.32           # silence after each narration line (s)
LAST_PAD = 1.1       # the last scene lingers on the call to action
MAX_SENTENCE_WORDS = 9   # short, punchy sentences: one beat each
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
AUDIO_EXT = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus"}


class ContentError(Exception):
    pass


class TechError(Exception):
    pass


def log(msg):
    print(msg, flush=True)


# ── helpers ──────────────────────────────────────────────────────────
def run(cmd, env=None, cwd=None, timeout=900, capture=True):
    try:
        p = subprocess.run(cmd, env=env, cwd=cwd, timeout=timeout, text=True,
                           stdout=subprocess.PIPE if capture else None,
                           stderr=subprocess.STDOUT if capture else None)
    except subprocess.TimeoutExpired:
        raise TechError(f"timeout running: {' '.join(map(str, cmd))[:200]}")
    return p


def hf_cmd():
    """The HyperFrames CLI: the installed one, otherwise npx with the pinned version."""
    exe = shutil.which("hyperframes")
    if exe:
        return [exe]
    return ["npx", "--yes", f"hyperframes@{CFG['hyperframes_version']}"]


def find_chrome():
    """Chrome/Chromium for the render. HyperFrames can't download its own from the
    cloud network, so reuse the one Playwright installed."""
    candidates = [os.environ.get("HYPERFRAMES_BROWSER_PATH", "")]
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            candidates.append(p.chromium.executable_path)
    except Exception:  # noqa: BLE001
        pass
    candidates += ["/opt/pw-browsers/chromium"]
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        candidates.append(shutil.which(name) or "")
    for c in candidates:
        if c and Path(c).exists():
            return c
    return ""


def decode(path, start=0.0, duration=None):
    """Any audio file -> float32 stereo array at 48 kHz (through ffmpeg)."""
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", str(path)]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise TechError(f"ffmpeg can't read {path}: {p.stderr.decode(errors='replace')[:300]}")
    return np.frombuffer(p.stdout, dtype="<f4").reshape(-1, 2).copy()


def words(text):
    return len(str(text or "").split())


def reveal_count(slide):
    """How many elements appear one after the other on a slide.
    MUST match the REVEAL selectors in template/reel/reel.html."""
    t = slide.get("type")
    if t == "cover":
        return 1 + bool(slide.get("kicker")) + bool(slide.get("subtitle"))
    if t == "text":
        body = slide.get("body")
        bodies = body if isinstance(body, list) else [body]
        return 1 + len([b for b in bodies if b]) + bool(slide.get("highlight"))
    if t == "number":
        return bool(slide.get("title")) + 2
    if t == "steps":
        return 1 + len(slide.get("steps", []))
    if t == "compare":
        return 3
    if t == "myth":
        return 4
    if t == "tip":
        return 2
    if t == "closing":
        return 1 + bool(slide.get("body")) + bool(slide.get("cta"))
    return 1


# ── 1. load and validate ─────────────────────────────────────────────
def load_inputs(folder):
    cj, rj = folder / "carousel.json", folder / "reel.json"
    if not cj.exists():
        raise TechError("carousel.json is missing")
    if not rj.exists():
        raise ContentError("reel.json is missing: write the narration (one line per slide).")
    carousel = json.loads(cj.read_text(encoding="utf-8"))
    reel = json.loads(rj.read_text(encoding="utf-8"))
    slides = carousel["slides"]
    scenes = reel.get("scenes", [])
    errors = []
    if len(scenes) != len(slides):
        errors.append(f"reel.json has {len(scenes)} scenes, the carousel has {len(slides)} slides: they must match one to one.")
    total_words = 0
    for i, sc in enumerate(scenes, 1):
        say = str(sc.get("say", "")).strip()
        n = words(say)
        total_words += n
        if not say:
            errors.append(f"Scene {i}: empty 'say'.")
        if n > 20:
            errors.append(f"Scene {i}: {n} words, max 20 (one breath, it's a reel).")
        for sent in re.split(r"(?<=[.!?])\s+", say):
            if words(sent) > MAX_SENTENCE_WORDS:
                errors.append(f"Scene {i}: the sentence \"{sent}\" has {words(sent)} words, max {MAX_SENTENCE_WORDS}: split it.")
        if EMOJI.search(say):
            errors.append(f"Scene {i}: no emoji.")
        if "http" in say or "@" in say or "#" in say:
            errors.append(f"Scene {i}: no links, handles or hashtags in the narration.")
    if total_words > 80:
        errors.append(f"The narration has {total_words} words: too many for {CFG['target_seconds']:.0f} seconds (aim for 45-65).")
    if errors:
        raise ContentError("\n".join(errors))
    return carousel, [str(s["say"]).strip() for s in scenes]


# ── 2. voice ─────────────────────────────────────────────────────────
def tts_all(texts, workdir, speed):
    env = dict(os.environ)
    out = []
    for i, text in enumerate(texts):
        wav = workdir / f"voice-{i + 1:02d}.wav"
        title, rest = split_title(text) if i > 0 else (text, "")   # scene 1 is the hook: no split
        parts = [(wav, title)]
        if rest and float(CFG.get("title_pause") or 0) > 0:
            parts = [(workdir / f"voice-{i + 1:02d}a.wav", title), (workdir / f"voice-{i + 1:02d}b.wav", rest)]
        for w_, t_ in parts if len(parts) > 1 else [(wav, text)]:
            cmd = hf_cmd() + ["tts", t_, "--voice", CFG["voice"], "--speed", f"{speed:.3f}",
                              "--output", str(w_), "--json"]
            p = run(cmd, env=env, timeout=300)
            if p.returncode != 0 or not w_.exists():
                raise TechError(f"TTS failed on scene {i + 1}:\n{(p.stdout or '')[-600:]}")
            if float(CFG.get("max_gap") or 0) > 0:
                tighten(w_)
        if len(parts) > 1:
            join_with_pause(parts[0][0], parts[1][0], wav, float(CFG["title_pause"]))
        pitch_shift(wav, float(CFG.get("voice_pitch_semitones") or 0))
        out.append(wav)
    return out


def split_title(text):
    """The first sentence of a scene is its 'title'; returns (title, rest)."""
    m = re.match(r"(.+?[.!?])\s+(\S.*)$", text.strip(), re.S)
    return (m.group(1), m.group(2)) if m else (text.strip(), "")


def join_with_pause(a_wav, b_wav, out_wav, pause):
    """Joins the title line and the rest of the scene with exactly `pause` seconds of
    silence between the last word of the title and the first word of the rest."""
    def load(path):
        with wave.open(str(path)) as w:
            params = w.getparams()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, params.nchannels)
        return params, x.astype(np.float32) / 32768

    def trim(x, sr):
        win = max(1, int(sr * 0.01))
        n = len(x) // win
        if n < 3:
            return x
        e = np.sqrt(np.mean(x[: n * win].reshape(n, win, -1) ** 2, axis=(1, 2)))
        idx = np.flatnonzero(e > max(10 ** (-42 / 20), e.max() * 10 ** (-38 / 20)))
        if idx.size == 0:
            return x
        return x[max(0, idx[0] - 2) * win: min(n, idx[-1] + 3) * win]

    params, a = load(a_wav)
    _, b = load(b_wav)
    sr = params.framerate
    gap = np.zeros((int(sr * pause), a.shape[1]), dtype=np.float32)
    lead = np.zeros((int(sr * 0.02), a.shape[1]), dtype=np.float32)
    y = np.concatenate([lead, trim(a, sr), gap, trim(b, sr), lead])
    with wave.open(str(out_wav), "wb") as w:
        w.setparams(params)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


_PITCH_FILTER = None


def pitch_shift(wav, semitones):
    """Raises (or lowers) the pitch of one voice line without changing its length.
    Uses ffmpeg's rubberband filter (clean, high quality); if this ffmpeg was built
    without it, falls back to resampling + tempo correction (same result, a bit rawer)."""
    global _PITCH_FILTER
    if abs(semitones) < 0.01:
        return
    ratio = 2 ** (semitones / 12)
    with wave.open(str(wav)) as w:
        sr = w.getframerate()
    tmp = Path(str(wav) + ".pitch.wav")
    rubber = f"rubberband=pitch={ratio:.5f}"
    resample = f"asetrate={sr * ratio:.0f},aresample={sr},atempo={1 / ratio:.5f}"
    for flt in ([_PITCH_FILTER] if _PITCH_FILTER else [rubber, resample]):
        p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-af", flt, "-ar", str(sr), str(tmp)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if p.returncode == 0 and tmp.exists():
            _PITCH_FILTER = flt
            tmp.replace(wav)
            return
    raise TechError(f"pitch shift failed on {wav.name}: {p.stderr[-400:]}")


def add_echo(bus, wet):
    """Very light echo: the first reflections of the walls of a small room (a few
    quiet copies of the voice 15-90 ms later, slightly different left and right),
    so it sounds recorded in a room rather than inside the computer."""
    if wet <= 0 or not np.any(bus):
        return bus
    taps = [  # (delay s left, delay s right, relative gain)
        (0.017, 0.021, 1.00),
        (0.029, 0.026, 0.75),
        (0.043, 0.047, 0.55),
        (0.061, 0.057, 0.40),
        (0.089, 0.083, 0.25),
    ]
    out = bus.copy()
    for dl, dr, g in taps:
        for c, d in ((0, dl), (1, dr)):
            k = int(SR * d)
            out[k:, c] += bus[:-k, c] * (wet * g)
    return out.astype(np.float32)


def add_reverb(bus, wet, seconds):
    """Light room reverb: the dry voice plus a soft, decaying, slightly delayed
    stereo tail (synthetic impulse response, always the same). Length unchanged."""
    if wet <= 0 or seconds <= 0 or not np.any(bus):
        return bus
    rng = np.random.default_rng(7)                 # fixed: the same room on every reel
    n = int(SR * seconds)
    t = np.arange(n) / SR
    decay = np.exp(-6.91 * t / seconds)            # -60 dB at `seconds`
    ir = rng.standard_normal((n, 2)) * decay[:, None]
    k = int(SR * 0.0015)                           # soften the highs: a warm room, not a tin can
    ir = np.stack([np.convolve(ir[:, c], np.ones(k) / k, mode="same") for c in range(2)], axis=1)
    pre = int(SR * 0.018)                          # pre-delay keeps the words clear
    ir = np.concatenate([np.zeros((pre, 2)), ir])
    ir /= np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True)) + 1e-12
    size = 1 << int(np.ceil(np.log2(len(bus) + len(ir))))
    tail = np.stack([np.fft.irfft(np.fft.rfft(bus[:, c], size) * np.fft.rfft(ir[:, c], size), size)[: len(bus)]
                     for c in range(2)], axis=1)
    tail *= np.sqrt(np.mean(bus ** 2)) / (np.sqrt(np.mean(tail ** 2)) + 1e-12)   # same loudness as the dry voice
    return (bus * (1 - wet * 0.5) + tail * wet).astype(np.float32)


def tighten(wav, edge=0.02):
    """Cuts the dead air out of one TTS line: trims the silence at both ends and
    shortens every pause inside the line to at most max_gap seconds. This is what
    keeps the narration punchy (Kokoro leaves ~0.3-0.5 s after every period)."""
    with wave.open(str(wav)) as w:
        params = w.getparams()
        raw = w.readframes(w.getnframes())
    if params.sampwidth != 2:
        return
    x = np.frombuffer(raw, dtype="<i2").reshape(-1, params.nchannels).astype(np.float32) / 32768
    sr = params.framerate
    win = max(1, int(sr * 0.01))
    nwin = len(x) // win
    if nwin < 3:
        return
    energy = np.sqrt(np.mean(x[: nwin * win].reshape(nwin, win, -1) ** 2, axis=(1, 2)))
    loud = energy > max(10 ** (-42 / 20), energy.max() * 10 ** (-38 / 20))
    idx = np.flatnonzero(loud)
    if idx.size == 0:
        return
    keep_gap = int(round(float(CFG["max_gap"]) / 0.01))
    pieces, run_start, prev = [], idx[0], idx[0]
    for k in idx[1:]:
        if k - prev - 1 > keep_gap:          # a long pause: close the voiced run
            pieces.append((run_start, prev + 1))
            run_start = k
        prev = k
    pieces.append((run_start, prev + 1))
    e = int(edge / 0.01)
    out = []
    for j, (a, b) in enumerate(pieces):
        a2 = max(0, a - e) if j == 0 else a
        b2 = min(nwin, b + (e if j == len(pieces) - 1 else keep_gap // 2))
        if j > 0:
            out.append(np.zeros((win * (keep_gap - keep_gap // 2), x.shape[1]), dtype=np.float32))
        out.append(x[a2 * win: b2 * win])
    y = np.concatenate(out)
    f = min(len(y) // 4, int(sr * 0.008))    # tiny fades: no clicks at the cuts
    if f > 1:
        y[:f] *= np.linspace(0, 1, f)[:, None]
        y[-f:] *= np.linspace(1, 0, f)[:, None]
    with wave.open(str(wav), "wb") as w:
        w.setparams(params)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def duration_of(wav):
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


# ── 3. timing ────────────────────────────────────────────────────────
def plan_timing(texts, workdir, n_items):
    """Voice at normal speed first; if it doesn't fit in the target, speed it up
    (never beyond max_speed). Returns voice files, speed, scene timings."""
    target = float(CFG["target_seconds"])
    speed = float(CFG["voice_speed"])
    voices = tts_all(texts, workdir, speed)
    durs = [duration_of(v) for v in voices]
    n = len(texts)
    pads = [LEAD + PAD] * (n - 1) + [LEAD + LAST_PAD]
    natural = sum(durs) + sum(pads)
    log(f"Narration at {speed:.2f}x: {sum(durs):.1f}s of speech, {natural:.1f}s with pauses (max {target:.0f}s)")

    if natural > target:
        speed = speed * sum(durs) / (target - sum(pads))
        if speed > CFG["max_speed"]:
            raise ContentError(
                f"The narration is too long: it would need {speed:.2f}x speed to fit {target:.0f}s "
                f"(max {CFG['max_speed']}x). Cut about {int((natural - target) * 2.6) + 3} words from reel.json.")
        speed = round(speed + 0.005, 3)
        log(f"Too long: re-recording at {speed:.2f}x")
        voices = tts_all(texts, workdir, speed)
        durs = [duration_of(v) for v in voices]
        natural = sum(durs) + sum(pads)
        while natural > target and speed < CFG["max_speed"]:   # rounding safety
            speed = round(speed + 0.01, 3)
            voices = tts_all(texts, workdir, speed)
            durs = [duration_of(v) for v in voices]
            natural = sum(durs) + sum(pads)
        if natural > target + 0.05:
            raise ContentError(f"Still {natural:.1f}s after speeding up. Shorten reel.json.")

    # target_seconds is a MAXIMUM, not a length to fill: spare time is never turned
    # into silence (dead air is what makes people swipe away)
    extra = 0.0
    if natural < CFG["min_seconds"]:
        raise ContentError(
            f"The narration is too short: {natural:.1f}s, the reel must be at least {CFG['min_seconds']:.0f}s. "
            f"Add about {int((CFG['min_seconds'] - natural) * 2.6) + 2} words to reel.json (keep it natural, no padding).")
    add = [0.0] * n

    scenes, t = [], 0.0
    for i in range(n):
        dur = durs[i] + pads[i] + add[i]
        first = 0.0 if i == 0 else 0.06
        avail = min(dur * 0.5, 1.6)
        step = max(0.15, min(0.32, avail / max(n_items[i] - 1, 1)))
        scenes.append({"start": round(t, 3), "dur": round(dur, 3), "first": first, "step": round(step, 3),
                       "voice_start": round(t + LEAD, 3), "voice_dur": round(durs[i], 3)})
        t += dur
    return voices, speed, scenes, round(t, 3)


# ── 4. music ─────────────────────────────────────────────────────────
def pick_music():
    """A random track of music/ that still has to take its turn (None if the folder has
    no tracks). Shuffle-bag rotation: the pick is random, but only among the tracks
    used the fewest times so far, so every track plays before any repeats. A track can
    come back right after itself only when a new round starts (never 3 times in a row)."""
    mdir = ROOT / CFG["music_dir"]
    tracks = sorted(p for p in mdir.glob("*") if p.suffix.lower() in AUDIO_EXT) if mdir.exists() else []
    if not tracks:
        return None, {}
    meta = {}
    mj = mdir / "tracks.json"
    if mj.exists():
        try:
            meta = json.loads(mj.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log("WARNING: music/tracks.json is not valid JSON, ignored")
    history = []   # oldest first
    for f in sorted((ROOT / "posts").glob("*/reel-meta.json")):
        try:
            history.append((json.loads(f.read_text(encoding="utf-8")).get("music") or {}).get("file"))
        except Exception:  # noqa: BLE001
            pass

    uses = {p.name: history.count(p.name) for p in tracks}
    fewest = min(uses.values())
    candidates = [p for p in tracks if uses[p.name] == fewest]
    best = random.SystemRandom().choice(candidates)   # not seeded: a real random pick
    log(f"Music pick: random among {[p.name for p in candidates]} (uses so far: {uses})")
    return best, meta.get(best.name, {})


# ── 5. audio mix ─────────────────────────────────────────────────────
def mono_to_stereo(x):
    return np.stack([x, x], axis=1) if x.ndim == 1 else x


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def place(buf, clip, at, gain=1.0):
    i = int(at * SR)
    if i < 0:
        clip = clip[-i:]
        i = 0
    j = min(len(buf), i + len(clip))
    if j > i:
        buf[i:j] += clip[: j - i] * gain



# ── custom sound effects (sfx/custom/) ───────────────────────────────
# The owner drops files with descriptive names in sfx/custom/; the role of each
# one is guessed from its name (first role in this order whose word appears).
SFX_ROLES = [
    ("riser", ["riser", "build", "tension", "rise", "crescendo", "sweep-up", "sweepup", "salita"]),
    ("intro", ["intro", "opening", "open", "start", "hook", "cover", "apertura", "inizio"]),
    ("ding", ["ding", "bell", "chime", "cta", "success", "final", "end", "outro", "sparkle", "campanell", "chiusura", "fine"]),
    ("hit", ["hit", "impact", "thud", "boom", "slam", "punch", "bass", "drop", "colpo", "impatto"]),
    ("tick", ["tick", "click", "type", "typing", "pop", "blip", "tap", "snap", "text", "reveal", "bubble", "scatto"]),
    ("whoosh", ["whoosh", "swoosh", "swipe", "swish", "transition", "transizione", "wipe", "slide", "air", "passaggio"]),
]
SFX_MAX_SECONDS = {"riser": 1.6, "intro": 2.0, "ding": 2.2, "hit": 1.5, "tick": 0.5, "whoosh": 1.3}


def sfx_role(filename):
    name = filename.lower()
    for role, keys in SFX_ROLES:
        if any(k in name for k in keys):
            return role
    return None


def load_sfx():
    """role -> list of mono-to-stereo arrays. The synthesized effects of sfx/ are the
    defaults; every role the owner covers in sfx/custom/ replaces them (several
    files of one role are used in rotation)."""
    defaults = {p.stem: [decode(p)] for p in (ROOT / "sfx").glob("*.wav")}
    custom = {}
    cdir = ROOT / "sfx" / "custom"
    if cdir.exists():
        for f in sorted(cdir.glob("*")):
            if f.suffix.lower() not in AUDIO_EXT:
                continue
            role = sfx_role(f.name)
            if role is None:
                log(f"WARNING: sfx/custom/{f.name}: can't tell where it is used from the name, ignored (see sfx/custom/README.md)")
                continue
            clip = decode(f, duration=SFX_MAX_SECONDS[role] + 0.5)[: int(SR * SFX_MAX_SECONDS[role])].copy()
            if len(clip) < SR * 0.02:
                continue
            fo = min(len(clip) // 4, int(SR * 0.05))
            clip[-fo:] *= np.linspace(1, 0, fo)[:, None]
            clip *= 0.8 / (np.max(np.abs(clip)) + 1e-9)       # every custom file starts at the same peak
            custom.setdefault(role, []).append(clip)
    used = {r: len(v) for r, v in custom.items()}
    if used:
        log(f"Custom sound effects: {used}")
    out = {}
    for role in ("riser", "intro", "ding", "hit", "tick", "whoosh"):
        out[role] = custom.get(role) or defaults.get(role) or []
    return out


def place_peak(buf, clip, at, gain=1.0):
    """Places a clip so its loudest moment falls on `at` (a cut, a reveal)."""
    win = int(SR * 0.02)
    env = np.convolve(np.max(np.abs(clip), axis=1), np.ones(win) / win, mode="same")
    peak_t = int(np.argmax(env)) / SR
    place(buf, clip, at - peak_t, gain)


def pick(variants, i):
    return variants[i % len(variants)]


def build_audio(voices, scenes, items, total, speed, music, music_meta, out_wav):
    n = int(total * SR) + SR // 2
    voice_bus = np.zeros((n, 2), dtype=np.float32)
    sfx_bus = np.zeros((n, 2), dtype=np.float32)

    # voice
    for v, sc in zip(voices, scenes):
        place(voice_bus, decode(v), sc["voice_start"])
    voice_bus = add_echo(voice_bus, float(CFG.get("voice_echo_wet") or 0))
    voice_bus = add_reverb(voice_bus, float(CFG.get("voice_reverb_wet") or 0), float(CFG.get("voice_reverb_seconds") or 0))
    peak = np.max(np.abs(voice_bus)) + 1e-9
    voice_bus *= min(0.85 / peak, 4.0)
    voice_bus *= 10 ** ((-17 - rms_db(voice_bus[np.abs(voice_bus[:, 0]) > 0.01])) / 20) \
        if np.any(np.abs(voice_bus[:, 0]) > 0.01) else 1.0
    peak = np.max(np.abs(voice_bus))
    if peak > 0.9:
        voice_bus *= 0.9 / peak

    # sound effects: one set per transition, quiet ticks on every reveal
    sfx = load_sfx()
    missing = [r for r, v in sfx.items() if r != "intro" and not v]
    if missing:
        raise TechError(f"missing sound effects for {missing}: sfx/ must contain the synthesized ones "
                        "(run scripts/reel_animated/make_sfx.py)")
    k = 0
    for i, sc in enumerate(scenes):
        if i == 0:
            first = sfx["intro"] or sfx["hit"]
            place_peak(sfx_bus, first[0], 0.05, 0.9)
        else:
            if i == 1 and scenes[0]["dur"] >= 1.5:
                place_peak(sfx_bus, pick(sfx["riser"], 0), sc["start"], 0.45)
            place_peak(sfx_bus, pick(sfx["whoosh"], i - 1), sc["start"], 0.75)
            place_peak(sfx_bus, pick(sfx["hit"], i - 1), sc["start"], 0.8)
        for j in range(1, items[i]):
            place_peak(sfx_bus, pick(sfx["tick"], k), sc["start"] + sc["first"] + j * sc["step"], 0.28)
            k += 1
    last = scenes[-1]
    place_peak(sfx_bus, sfx["ding"][0], last["start"] + last["first"] + max(items[-1] - 1, 0) * last["step"], 0.55)

    # music: loop if needed, level, fade, duck under the voice
    mus_bus = np.zeros((n, 2), dtype=np.float32)
    if music is not None:
        start = float(music_meta.get("start", 0))
        raw = decode(music, start=start, duration=600)
        if len(raw) < SR * 2:
            raise TechError(f"the music track {music.name} is too short or unreadable")
        need = n
        if len(raw) < need:      # loop with a short crossfade
            xf = int(SR * 0.4)
            parts = [raw]
            length = len(raw)
            while length < need:
                nxt = raw
                a, b = parts[-1], nxt
                ramp = np.linspace(0, 1, xf)[:, None]
                a = a.copy()
                a[-xf:] = a[-xf:] * (1 - ramp) + b[:xf] * ramp
                parts[-1] = a
                parts.append(b[xf:])
                length += len(b) - xf
            raw = np.concatenate(parts)
        mus = raw[:need].astype(np.float32)
        gain_db = -22 + float(CFG["music_level_db"]) + float(music_meta.get("gain_db", 0)) - rms_db(mus)
        mus *= 10 ** (gain_db / 20)
        fin, fout = int(SR * 0.6), int(SR * 1.6)
        end = int(total * SR)
        mus[:fin] *= np.linspace(0, 1, fin)[:, None]
        mus[end - fout:end] *= np.linspace(1, 0, fout)[:, None]
        mus[end:] = 0
        # sidechain: smoothed envelope of the voice lowers the music by up to 9 dB
        env = np.abs(voice_bus[:, 0])
        win = int(SR * 0.05)
        env = np.convolve(env, np.ones(win) / win, mode="same")
        env = np.clip(env / 0.12, 0, 1)
        k = int(SR * 0.25)
        env = np.convolve(env, np.ones(k) / k, mode="same")
        duck = 1 - env * (1 - 10 ** (-9 / 20))
        mus_bus = mus * duck[:, None].astype(np.float32)

    mix = voice_bus + sfx_bus * (10 ** (float(CFG["sfx_level_db"]) / 20)) + mus_bus
    mix = mix[: int(total * SR)]
    # the last 0.25 s: tiny fade so there is no click at the end
    f = int(SR * 0.25)
    mix[-f:] *= np.linspace(1, 0, f)[:, None]
    mix = np.tanh(mix * 0.95) / np.tanh(0.95) if np.max(np.abs(mix)) > 0.95 else mix
    pk = np.max(np.abs(mix))
    if pk > 0.95:
        mix *= 0.95 / pk
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return {"voice_rms_db": round(rms_db(voice_bus), 1), "music": None if music is None else music.name}


# ── 6. HyperFrames project ───────────────────────────────────────────
def extract_between(text, start_marker, end_marker, what):
    a = text.find(start_marker)
    b = text.find(end_marker, a + 1)
    if a < 0 or b < 0:
        raise TechError(f"template/carousel.html changed: can't find the {what} block "
                        f"(markers: {start_marker!r} .. {end_marker!r}). Update build_reel.py.")
    return text[a:b]


def write_project(workdir, carousel, scenes, total):
    car = (ROOT / "template" / "carousel.html").read_text(encoding="utf-8")
    css = extract_between(car, "@font-face", "</style>", "CSS")
    types_js = extract_between(car, "const esc =", "const problems = [];", "slide markup (esc/arrow/types)")
    fit_js = extract_between(car, "// Auto-fit:", "(document.fonts && document.fonts.ready", "auto-fit")
    # the carousel rules for the 4:5 preview grid and fixed 1350px slides must not apply
    css = re.sub(r"html\[data-mode=\"preview\"\][^{]*\{[^}]*\}", "", css)

    plan = {"handle": CONFIG.get("handle", ""), "slides": carousel["slides"], "scenes": scenes, "duration": total}
    plan_json = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
    html = (ROOT / "template" / "reel" / "reel.html").read_text(encoding="utf-8")
    for token, value in {
        "{{CAROUSEL_CSS}}": css,
        "{{CAROUSEL_JS_TYPES}}": types_js,
        "{{CAROUSEL_JS_FIT}}": fit_js,
        "{{PLAN_JSON}}": plan_json,
        "{{DURATION}}": f"{total:.2f}",
    }.items():
        html = html.replace(token, value)
    (workdir / "index.html").write_text(html, encoding="utf-8")
    shutil.copy(ROOT / "template" / "reel" / "vendor" / "gsap.min.js", workdir / "gsap.min.js")
    shutil.copytree(ROOT / "template" / "fonts", workdir / "fonts", dirs_exist_ok=True)
    (workdir / "meta.json").write_text(json.dumps({"id": "reel", "name": "reel"}), encoding="utf-8")
    (workdir / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
    }), encoding="utf-8")


def check_layout_and_frames(workdir, scenes, chrome):
    """Opens the page in a browser: reports text that doesn't fit and saves one frame per scene."""
    from playwright.sync_api import sync_playwright
    frames = workdir / "frames"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir()
    problems = []
    with sync_playwright() as p:
        launch_args = ["--no-sandbox", "--allow-file-access-from-files"]
        try:   # Playwright's own browser first (it is the one the setup script installs)
            browser = p.chromium.launch(args=launch_args, timeout=30000)
        except Exception:  # noqa: BLE001
            if not chrome:
                raise TechError("no browser available for the layout check")
            browser = p.chromium.launch(args=launch_args, executable_path=chrome, timeout=30000)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto((workdir / "index.html").as_uri())
        page.wait_for_function("window.__REPORT && window.__REPORT.timeline === true", timeout=30000)
        report = page.evaluate("window.__REPORT")
        problems += report.get("problems", [])
        problems += [f"page error: {e}" for e in errors]
        for i, sc in enumerate(scenes, 1):
            t = sc["start"] + min(sc["dur"] * 0.8, sc["first"] + 2.4)
            page.evaluate("t => { window.__timelines.main.seek(t); }", t)   # (never return the timeline: it is not serializable)
            page.screenshot(path=str(frames / f"scene-{i:02d}.jpg"), type="jpeg", quality=80)
        browser.close()
    return problems


def render(workdir, out_mp4, chrome):
    env = dict(os.environ)
    if chrome:
        env["HYPERFRAMES_BROWSER_PATH"] = chrome
    base = hf_cmd()
    lint = run(base + ["lint"], env=env, cwd=workdir, timeout=300)
    if lint.returncode != 0:
        raise TechError("hyperframes lint failed:\n" + (lint.stdout or "")[-1500:])
    cmd = base + ["render", "--fps", str(CFG["fps"]), "--quality", "standard",
                  "--video-bitrate", str(CFG["video_bitrate"]), "-o", str(out_mp4)]
    log("Rendering (about 1-3 minutes)...")
    p = run(cmd, env=env, cwd=workdir, timeout=1500)
    if p.returncode != 0 or not out_mp4.exists():
        raise TechError("hyperframes render failed:\n" + (p.stdout or "")[-2500:])


def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height,r_frame_rate,pix_fmt",
                        "-of", "json", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return json.loads(p.stdout)


def finalize(raw_mp4, final_mp4, total):
    """Instagram-friendly file: H.264 yuv420p + AAC, faststart, under max_mb."""
    info = probe(raw_mp4)
    vcodec = next((s["codec_name"] for s in info["streams"] if s.get("width")), "")
    acodec = next((s["codec_name"] for s in info["streams"] if not s.get("width")), "")
    size_mb = int(info["format"]["size"]) / 1024 / 1024
    if vcodec == "h264" and acodec == "aac" and size_mb <= CFG["max_mb"]:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(raw_mp4), "-c", "copy", "-movflags", "+faststart", str(final_mp4)]
    else:
        # budget in kbit/s so the file fits (audio 128k)
        vb = int((CFG["max_mb"] * 0.92 * 8192) / total - 128)
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(raw_mp4), "-c:v", "libx264", "-preset", "slow",
               "-b:v", f"{vb}k", "-maxrate", f"{int(vb * 1.4)}k", "-bufsize", f"{vb * 2}k",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(final_mp4)]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise TechError("ffmpeg failed: " + p.stderr[-800:])


# ── main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--no-render", action="store_true", help="voice, audio, layout check and frames only (fast)")
    args = ap.parse_args()

    folder = Path(args.folder).resolve()
    work = ROOT / ".reel-build" / folder.name
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    try:
        carousel, texts = load_inputs(folder)
        items = [reveal_count(s) for s in carousel["slides"]]
        voices, speed, scenes, total = plan_timing(texts, work, items)
        log(f"Timing OK: {total:.1f}s, {len(scenes)} scenes, voice speed {speed:.2f}x")

        music, music_meta = pick_music()
        if music is None:
            log("WARNING: music/ has no tracks: the reel will have voice and sound effects only")
        else:
            log(f"Music: {music.name}")
        info = build_audio(voices, scenes, items, total, speed, music, music_meta, work / "mix.wav")

        write_project(work, carousel, scenes, total)
        chrome = find_chrome()
        problems = check_layout_and_frames(work, scenes, chrome)
        if problems:
            raise ContentError("Layout problems in the reel (shorten the text in carousel.json, "
                               "which also changes the carousel, or fix it in the template):\n- " + "\n- ".join(problems))
        log(f"Layout OK. Frames to inspect: {work / 'frames'}/scene-XX.jpg")
        if args.no_render:
            return 0

        raw = work / "raw.mp4"
        render(work, raw, chrome)
        final = folder / "reel.mp4"
        finalize(raw, final, total)

        pr = probe(final)
        dur = float(pr["format"]["duration"])
        size_mb = int(pr["format"]["size"]) / 1024 / 1024
        v = next(s for s in pr["streams"] if s.get("width"))
        if not (CFG["min_seconds"] - 1 <= dur <= CFG["target_seconds"] + 1.0):
            raise TechError(f"unexpected duration: {dur:.1f}s")
        if size_mb > CFG["max_mb"] + 0.01:
            raise TechError(f"reel.mp4 is {size_mb:.1f} MB (max {CFG['max_mb']})")
        if (v["width"], v["height"]) != (1080, 1920):
            raise TechError(f"unexpected size {v['width']}x{v['height']}")
        meta = {
            "duration": round(dur, 2), "size_mb": round(size_mb, 2), "voice": CFG["voice"], "voice_speed": speed,
            "music": {"file": music.name if music else None, **({} if not music else music_meta)},
            "scenes": scenes, "hyperframes": CFG["hyperframes_version"],
        }
        (folder / "reel-meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"DONE: {final.relative_to(ROOT)}  {dur:.1f}s  {size_mb:.1f} MB  music={meta['music']['file']}")
        return 0
    except ContentError as e:
        print("CONTENT ERROR:\n" + str(e))
        return 2
    except TechError as e:
        print("TECHNICAL ERROR:\n" + str(e))
        return 3


if __name__ == "__main__":
    sys.exit(main())
