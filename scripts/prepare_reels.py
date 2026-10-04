#!/usr/bin/env python3
"""
Prepares Instagram Reels from the "Idee Reel" tab of the ideas sheet.

Runs ONLY on the owner's Windows PC (double-click run-reels.bat), never in the
cloud routine: YouTube blocks cloud servers, and Whisper needs the local GPU.

For every new row of the sheet:
  1. checks the times and the video license (must be Creative Commons Attribution)
  2. downloads only the requested segment (yt-dlp)
  3. transcribes it with Whisper on the GPU (English only, otherwise the row is rejected)
  4. builds a 1080x1920 video: the clip cropped to 4:3 on a blurred background,
     with highlighted subtitles (espresso text on a hazel box) when someone speaks.
     No text on screen otherwise: the CC BY attribution goes in the caption
  5. saves everything in reels/<ID>-<slug>/ and, at the end, commits and pushes

The cloud routine (REELS.md) then writes the caption and publishes.

Disk: nothing is written to C:. Every cache, temp file, model and tool lives in
.venv/ and .reels/ inside the project folder (see redirect_everything_to_project).

Usage (from run-reels.bat, which passes the arguments through):
  run-reels.bat               process every new row, then commit + push
  run-reels.bat --dry-run     process, but don't commit or push
  run-reels.bat --only 3      process only the row with ID 3
  run-reels.bat --retry       also retry rows that were rejected before
  run-reels.bat --check       check the setup (no download, no changes)

Developer test options (no sheet, no YouTube):
  --local-video FILE --id N [--title T --channel C --url U] [--words-json FILE]
"""
import argparse
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".reels"          # everything local and heavy lives here (ignored by git)
REELS_DIR = ROOT / "reels"      # finished reels, committed to GitHub
FONTS = ROOT / "template" / "fonts"
STATE_FILE = WORK / "state.json"

# ---------------------------------------------------------------- disk safety

# The bat file saves the user's real APPDATA/LOCALAPPDATA before redirecting
# them; git must run with the real ones (credential manager), everything else
# with the redirected ones.
ORIGINAL_ENV = dict(os.environ)
for _k in ("APPDATA", "LOCALAPPDATA"):
    if os.environ.get(f"ORIG_{_k}"):
        ORIGINAL_ENV[_k] = os.environ[f"ORIG_{_k}"]


def redirect_everything_to_project():
    """Points every cache/temp/config location used by our tools inside .reels/.
    Must run before importing faster_whisper / huggingface_hub."""
    dirs = {
        "TEMP": WORK / "tmp",
        "TMP": WORK / "tmp",
        "TMPDIR": WORK / "tmp",
        "HF_HOME": WORK / "hf",                 # Hugging Face (Whisper model download)
        "HF_HUB_CACHE": WORK / "models",
        "XDG_CACHE_HOME": WORK / "cache",
        "DENO_DIR": WORK / "deno",              # Deno cache (used by yt-dlp)
        "CUDA_CACHE_PATH": WORK / "cuda-cache", # NVIDIA JIT cache
        "APPDATA": WORK / "appdata" / "Roaming",
        "LOCALAPPDATA": WORK / "appdata" / "Local",
    }
    for key, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)
    os.environ["PIP_NO_CACHE_DIR"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["PYTHONUTF8"] = "1"
    tempfile.tempdir = str(WORK / "tmp")
    # the venv's Scripts folder holds deno.exe: yt-dlp finds it on PATH
    scripts_dir = Path(sys.executable).parent
    os.environ["PATH"] = str(scripts_dir) + os.pathsep + os.environ.get("PATH", "")


def on_drive_c(path):
    drive = os.path.splitdrive(str(Path(path).resolve()))[0]
    return drive.upper() == "C:"


# ---------------------------------------------------------------- config

DEFAULTS = {
    "mode": "preview",
    "sheet_name": "Idee Reel",
    "sheet_gid": "",
    "min_seconds": 5,
    "max_seconds": 90,
    "max_mb": 18,               # jsDelivr refuses files over 20 MB
    "whisper_model": "large-v3-turbo",
    "license_label": "CC BY 3.0",
}


def load_config():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    reels = dict(DEFAULTS)
    reels.update(cfg.get("reels", {}))
    cfg["reels"] = reels
    return cfg


# ---------------------------------------------------------------- small helpers

class Reject(Exception):
    """The row can't become a reel (reason shown to the owner)."""


def say(msg=""):
    print(msg, flush=True)


def slugify(text, max_len=40):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return (text[:max_len].rstrip("-")) or "clip"


def parse_time(value):
    """'2:15' → 135.0 · '1:02:15' → 3735.0 · '75' → 75.0"""
    s = (value or "").strip().replace(",", ".")
    if not s:
        raise ValueError("empty")
    parts = s.split(":")
    if len(parts) > 3:
        raise ValueError(s)
    total = 0.0
    for p in parts:
        if not re.fullmatch(r"\d+(\.\d+)?", p.strip()):
            raise ValueError(s)
        total = total * 60 + float(p)
    return total


def fmt_time(seconds):
    seconds = int(round(seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"rejected": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def existing_reel(rid):
    return next(iter(sorted(REELS_DIR.glob(f"{int(rid):03d}-*"))), None)


# ---------------------------------------------------------------- tools

def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001  (developer machines without the venv)
        exe = shutil.which("ffmpeg")
        if not exe:
            raise SystemExit("ffmpeg not found: run setup-reels.bat")
        return exe


def run(cmd, env=None, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if check and r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-12:]
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(map(str, cmd[:3]))} …\n" + "\n".join(tail))
    return r


def yt_dlp(args):
    base = [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-cache-dir", "--no-playlist",
            "--no-warnings"]
    return run(base + args, env=os.environ.copy())


def probe(path):
    import av
    with av.open(str(path)) as c:
        v = c.streams.video[0]
        w, h = v.codec_context.width, v.codec_context.height
        if c.duration:
            duration = float(c.duration / 1_000_000)
        else:
            duration = float(v.duration * v.time_base)
        has_audio = len(c.streams.audio) > 0
    return {"width": w, "height": h, "duration": duration, "audio": has_audio}


# ---------------------------------------------------------------- sheet

def read_sheet(cfg):
    sid = cfg["google_sheet_id"]
    r = cfg["reels"]
    if str(r.get("sheet_gid", "")).strip():
        url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={r['sheet_gid']}"
    else:
        url = (f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&headers=1&sheet="
               + urllib.parse.quote(r["sheet_name"]))
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            kind = resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise SystemExit(
            f"Can't read the sheet (HTTP {e.code}). In Google Sheets: Share → General access → "
            f"'Anyone with the link' → Viewer. Also check the tab is called '{r['sheet_name']}'.")
    if "html" in kind.lower() or body.lstrip().startswith("<"):
        raise SystemExit("The sheet isn't shared by link: Share → General access → 'Anyone with the link' → Viewer.")

    rows = list(csv.reader(io.StringIO(body)))
    if not rows:
        return []
    out = []
    for line in rows[1:]:
        line = (line + [""] * 6)[:6]
        rid, link, start, end, notes, status = (c.strip() for c in line)
        if not rid and not link:
            continue
        out.append({"id": rid, "link": link, "start": start, "end": end, "notes": notes, "status": status})
    return out


def normalize_id(raw):
    try:
        return int(float(raw))
    except ValueError:
        raise Reject(f"ID '{raw}' is not a number")


# ---------------------------------------------------------------- YouTube

def video_info(url):
    r = yt_dlp(["-J", "--skip-download", url])
    return json.loads(r.stdout)


def check_license_and_language(info):
    lic = (info.get("license") or "").strip()
    if "creative commons" not in lic.lower():
        raise Reject(f"license is '{lic or 'standard YouTube license'}', not Creative Commons Attribution")
    # the spoken language is checked later by Whisper, on the clip itself:
    # clips without speech are fine whatever the video's language
    return lic


def download_segment(url, start, end, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_tpl = str(dest_dir / "source.%(ext)s")
    yt_dlp([
        "-f", "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b",
        "--download-sections", f"*{start:.2f}-{end:.2f}",
        "--force-keyframes-at-cuts",
        "--merge-output-format", "mp4",
        "--ffmpeg-location", ffmpeg_exe(),
        "-o", out_tpl,
        url,
    ])
    files = [p for p in dest_dir.glob("source.*") if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
    if not files:
        raise RuntimeError("download finished but no video file was found")
    return files[0]


# ---------------------------------------------------------------- Whisper

def add_nvidia_dll_dirs():
    """The CUDA/cuDNN libraries come from pip packages (nvidia-*) inside .venv."""
    try:
        import nvidia  # noqa: F401
    except ImportError:
        return
    import nvidia as _nv
    for base in getattr(_nv, "__path__", []):
        for sub in Path(base).glob("*"):
            for libdir in (sub / "bin", sub / "lib"):
                if libdir.is_dir():
                    os.environ["PATH"] = str(libdir) + os.pathsep + os.environ["PATH"]
                    if hasattr(os, "add_dll_directory"):
                        try:
                            os.add_dll_directory(str(libdir))
                        except OSError:
                            pass


def gpu_works():
    """Loads Whisper on the GPU in a separate process: a missing CUDA library can
    crash the process instead of raising an error."""
    r = subprocess.run([sys.executable, str(Path(__file__)), "--gpu-probe"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-3:]


def load_whisper(model_name, device):
    add_nvidia_dll_dirs()
    from faster_whisper import WhisperModel
    compute = "float16" if device == "cuda" else "int8"
    return WhisperModel(model_name, device=device, compute_type=compute,
                        download_root=str(WORK / "models"))


def load_audio(path, sr=16000):
    """Decodes the audio with ffmpeg into 16 kHz mono float32. faster-whisper's own
    decoder calls PyAV with an option recent PyAV versions removed (the only ones
    available for Python 3.14), so we hand Whisper the samples directly."""
    import numpy as np
    r = subprocess.run([ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(path),
                        "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("audio decode failed: " + r.stderr.decode(errors="replace").strip()[-300:])
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe(path, model):
    audio = load_audio(path)
    if audio.size < 16000:
        raise Reject("the clip has no audio track")
    segments, info = model.transcribe(audio, word_timestamps=True, beam_size=5,
                                      vad_filter=True, condition_on_previous_text=False)
    words, text = [], []
    for seg in segments:
        text.append(seg.text.strip())
        for w in (seg.words or []):
            t = w.word.strip()
            if t:
                words.append({"start": float(w.start), "end": float(w.end), "text": t})
    return {"language": info.language, "probability": round(float(info.language_probability), 3),
            "words": words, "text": " ".join(text).strip()}


def has_speech(tr, min_words=6, min_probability=0.6):
    """Whisper can 'hear' a few words in music or ambient noise: a handful of
    words, or a language guessed with low confidence, means no real speech."""
    if len(tr["words"]) < min_words:
        return False
    if tr["language"] != "en" and tr["probability"] < min_probability:
        return False
    return True


# ---------------------------------------------------------------- subtitles

PUNCT_BREAK = (".", "?", "!", ";", ":")


def make_chunks(words, max_words=4, max_chars=24, gap=0.6):
    chunks, cur = [], []

    def flush():
        if cur:
            chunks.append({"start": cur[0]["start"], "end": cur[-1]["end"],
                           "text": " ".join(w["text"] for w in cur)})
            cur.clear()

    def ends_sentence(w):
        return w["text"].endswith(PUNCT_BREAK)

    for i, w in enumerate(words):
        if cur:
            joined = len(" ".join(x["text"] for x in cur + [w]))
            too_long = len(cur) >= max_words or joined > max_chars
            # don't leave a lonely last word: let it join if it closes the sentence
            if too_long and ends_sentence(w) and len(cur) <= max_words and joined <= max_chars + 8:
                too_long = False
            if too_long or w["start"] - cur[-1]["end"] > gap:
                flush()
        cur.append(w)
        if ends_sentence(w) or (w["text"].endswith(",") and len(cur) >= 2):
            flush()
    flush()

    for i, c in enumerate(chunks):  # close tiny gaps, keep every chunk readable
        nxt = chunks[i + 1]["start"] if i + 1 < len(chunks) else None
        if nxt is not None and nxt - c["end"] < 0.4:
            c["end"] = nxt
        if c["end"] - c["start"] < 0.35:
            c["end"] = c["start"] + 0.35 if nxt is None else min(c["start"] + 0.35, nxt)
        c["text"] = clean_caption(c["text"])
    return [c for c in chunks if c["text"]]


def clean_caption(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" ,.;:-–—\"“”")
    return text.upper()


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(chunks, path):
    lines = []
    for i, c in enumerate(chunks, 1):
        lines += [str(i), f"{srt_time(c['start'])} --> {srt_time(c['end'])}", c["text"], ""]
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- graphics

W, H = 1080, 1920
ESPRESSO = "#413125"
HAZEL = "#EFD6B4"
SIDE_MARGIN = 120          # keeps text clear of Instagram's right-side buttons
WINDOW_CENTER_Y = 800      # centre of the 4:3 video window
SAFE_BOTTOM = 1480         # Instagram's caption and buttons start below this


def font(name, size, bold=False):
    from PIL import ImageFont
    f = ImageFont.truetype(str(FONTS / name), size)
    if bold:
        try:
            f.set_variation_by_axes([700])
        except Exception:  # noqa: BLE001
            pass
    return f


def balanced_lines(draw, text, fnt):
    """Splits text in two lines of similar width (no lonely last word)."""
    words = text.split()
    if len(words) < 2:
        return [text]
    best = None
    for i in range(1, len(words)):
        l1, l2 = " ".join(words[:i]), " ".join(words[i:])
        widest = max(draw.textlength(l1, font=fnt), draw.textlength(l2, font=fnt))
        if best is None or widest < best[0]:
            best = (widest, [l1, l2])
    return best[1]


def highlight_png(text, path, size=72, single_min=58, pad_x=28, pad_y=16, radius=24, line_gap=12,
                  fg=ESPRESSO, bg=HAZEL, face="ArchivoBlack-Regular.ttf", max_lines=2, min_size=44,
                  max_w=None):
    """Text on a rounded 'highlighter' box, one box per line, transparent PNG.
    Prefers one line (shrinking down to single_min), then two balanced lines."""
    from PIL import Image, ImageDraw
    max_w = max_w or (W - 2 * SIDE_MARGIN - 2 * pad_x)
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines, fnt = None, None
    for s in range(size, single_min - 1, -2):
        f = font(face, s)
        if d0.textlength(text, font=f) <= max_w:
            lines, fnt = [text], f
            break
    if lines is None and max_lines >= 2:
        s = size - 6
        while True:
            f = font(face, s)
            cand = balanced_lines(d0, text, f)
            if all(d0.textlength(l, font=f) <= max_w for l in cand) or s <= min_size:
                lines, fnt = cand, f
                break
            s -= 2
    if lines is None:                       # one line only (credit): shrink, then cut
        s = single_min
        f = font(face, s)
        while d0.textlength(text, font=f) > max_w and len(text) > 8:
            text = text[:-2].rstrip() + "…"
        lines, fnt = [text], f
    asc, desc = fnt.getmetrics()
    box_h = asc + desc + 2 * pad_y
    widths = [d0.textlength(l, font=fnt) for l in lines]
    img_w = int(max(widths) + 2 * pad_x)
    img_h = int(len(lines) * box_h + (len(lines) - 1) * line_gap)
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (line, lw) in enumerate(zip(lines, widths)):
        x0 = (img_w - lw) / 2 - pad_x
        y0 = i * (box_h + line_gap)
        d.rounded_rectangle([x0, y0, x0 + lw + 2 * pad_x, y0 + box_h], radius=radius, fill=bg)
        d.text((x0 + pad_x, y0 + pad_y), line, font=fnt, fill=fg)
    img.save(path)
    return img.size


# ---------------------------------------------------------------- video

def layout(src_w, src_h):
    """Returns the crop of the source and where it goes in the 1080x1920 frame."""
    ar = src_w / src_h
    if ar < 0.9:                      # vertical source: fill the whole frame
        return {"full": True}
    if ar >= 4 / 3:                   # landscape: crop the centre to 4:3
        ch = src_h
        cw = int(round(src_h * 4 / 3))
    else:                             # squarish: keep it all
        cw, ch = src_w, src_h
    cw, ch = cw - cw % 2, ch - ch % 2
    win_h = int(round(W * ch / cw))
    win_h -= win_h % 2
    top = WINDOW_CENTER_Y - win_h // 2
    top -= top % 2
    return {"full": False, "crop_w": cw, "crop_h": ch,
            "crop_x": (src_w - cw) // 2, "crop_y": (src_h - ch) // 2,
            "win_h": win_h, "top": top}


def build_video(src, chunks, out_path, work, max_mb, log):
    info = probe(src)
    lay = layout(info["width"], info["height"])
    pngs = work / "png"
    pngs.mkdir(exist_ok=True)

    inputs = ["-i", str(src)]

    if lay["full"]:
        graph = [f"[0:v]fps=30,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[v0]"]
        sub_center_y = 1330
    else:
        graph = [
            "[0:v]fps=30,split=2[a][b]",
            f"[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
            f"boxblur=12:2,scale={W}:{H},eq=brightness=-0.07:saturation=0.85[bg]",
            f"[b]crop={lay['crop_w']}:{lay['crop_h']}:{lay['crop_x']}:{lay['crop_y']},"
            f"scale={W}:{lay['win_h']},setsar=1[fg]",
            f"[bg][fg]overlay=0:{lay['top']}[v0]",
        ]
        below = lay["top"] + lay["win_h"] + 48
        sub_center_y = below + 80 if below + 200 <= SAFE_BOTTOM else lay["top"] + lay["win_h"] - 140

    last = "v0"
    for i, c in enumerate(chunks):
        p = pngs / f"sub_{i:03d}.png"
        sw, sh = highlight_png(c["text"], p)
        inputs += ["-i", str(p)]
        nxt = f"v{i + 1}"
        graph.append(f"[{last}][{i + 1}:v]overlay={(W - sw) // 2}:{sub_center_y - sh // 2}:"
                     f"enable='between(t,{c['start']:.3f},{c['end']:.3f})'[{nxt}]")
        last = nxt
    graph.append(f"[{last}]format=yuv420p[vout]")
    script = work / "filter.txt"
    script.write_text(";\n".join(graph), encoding="utf-8")

    duration = info["duration"]
    budget_kbps = int(max_mb * 1024 * 1024 * 8 * 0.94 / 1000 / max(duration, 1))
    v_kbps = max(1200, min(6000, budget_kbps - 160))
    for attempt in range(4):
        cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", *inputs,
               "-filter_complex_script", str(script), "-map", "[vout]"]
        if info["audio"]:
            cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]
        cmd += ["-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-level", "4.1",
                "-b:v", f"{v_kbps}k", "-maxrate", f"{int(v_kbps * 1.4)}k", "-bufsize", f"{v_kbps * 2}k",
                "-g", "60", "-r", "30", "-movflags", "+faststart", str(out_path)]
        run(cmd)
        size_mb = out_path.stat().st_size / 1024 / 1024
        if size_mb <= max_mb:
            log(f"    video: {duration:.1f}s, {size_mb:.1f} MB, {v_kbps} kbps")
            return {"duration": round(duration, 2), "size_mb": round(size_mb, 2), "video_kbps": v_kbps,
                    "layout": "vertical-fill" if lay["full"] else "4:3 on blurred background"}
        v_kbps = int(v_kbps * 0.8)
    raise RuntimeError(f"can't get the video under {max_mb} MB")


def save_frames(video, folder, duration):
    for i, frac in enumerate((0.15, 0.5, 0.85), 1):
        run([ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{duration * frac:.2f}",
             "-i", str(video), "-frames:v", "1", "-vf", "scale=540:960", "-q:v", "4",
             str(folder / f"frame-{i}.jpg")])


# ---------------------------------------------------------------- one row

def process_row(row, cfg, model_getter, args, log):
    rcfg = cfg["reels"]
    rid = normalize_id(row["id"])
    if args.local_video:
        info = {"title": args.title, "channel": args.channel, "webpage_url": args.url,
                "license": "Creative Commons Attribution license (reuse allowed)", "id": "local-test",
                "duration": None}
    else:
        if not re.search(r"(youtube\.com|youtu\.be)/", row["link"]):
            raise Reject("the link is not a YouTube link")
        try:
            start, end = parse_time(row["start"]), parse_time(row["end"])
        except ValueError:
            raise Reject(f"start/end '{row['start']}' / '{row['end']}' are not times like 02:15 "
                         "(set columns C and D to Format → Number → Plain text)")
        if end <= start:
            raise Reject("the end comes before the start")
        length = end - start
        if not rcfg["min_seconds"] <= length <= rcfg["max_seconds"]:
            raise Reject(f"the clip lasts {length:.0f}s; allowed {rcfg['min_seconds']}–{rcfg['max_seconds']}s")
        log("    reading video info…")
        info = video_info(row["link"])
        lic = check_license_and_language(info)
        if info.get("duration") and end > info["duration"] + 1:
            raise Reject(f"the end ({fmt_time(end)}) is after the end of the video ({fmt_time(info['duration'])}); "
                         "if you wrote 02:15 and it became 2:15:00, set columns C and D to plain text")
        log(f"    \"{info.get('title')}\" — {info.get('channel') or info.get('uploader')} · {lic}")

    work = WORK / "jobs" / f"{rid:03d}"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    if args.local_video:
        src = Path(args.local_video)
        start, end = 0.0, probe(src)["duration"]
    else:
        log(f"    downloading {fmt_time(start)}–{fmt_time(end)}…")
        src = download_segment(row["link"], start, end, work)

    if args.words_json:
        tr = json.loads(Path(args.words_json).read_text(encoding="utf-8"))
    else:
        log("    transcribing…")
        model, device = model_getter()
        tr = transcribe(src, model)
        tr["device"] = device
    speech = has_speech(tr)
    if speech and tr["language"] != "en":
        raise Reject(f"Whisper hears '{tr['language']}' (p={tr['probability']}), not English")
    if speech:
        chunks = make_chunks(tr["words"])
    else:
        log("    no speech: the reel will have no subtitles")
        chunks, tr["text"] = [], ""
    title = info.get("title") or "clip"
    channel = info.get("channel") or info.get("uploader") or "Unknown"
    folder = REELS_DIR / f"{rid:03d}-{slugify(title)}"
    folder.mkdir(parents=True, exist_ok=True)

    log("    editing video…")
    clip = folder / "clip.mp4"
    meta = build_video(src, chunks, clip, work, rcfg["max_mb"], log)
    save_frames(clip, folder, meta["duration"])
    if speech:
        write_srt(chunks, folder / "subtitles.srt")
        (folder / "transcript.txt").write_text(tr["text"] + "\n", encoding="utf-8")
    else:
        (folder / "transcript.txt").write_text("(no speech: visual clip without subtitles)\n", encoding="utf-8")

    url = info.get("webpage_url") or row.get("link", "")
    source = {
        "id": rid,
        "sheet_row": {k: row.get(k, "") for k in ("link", "start", "end", "notes")},
        "video": {
            "youtube_id": info.get("id"),
            "title": title,
            "channel": channel,
            "channel_url": info.get("channel_url") or info.get("uploader_url") or "",
            "url": url,
            "license": info.get("license"),
            "duration": info.get("duration"),
            "upload_date": info.get("upload_date"),
        },
        "clip": {"start": fmt_time(start), "end": fmt_time(end), **meta},
        "attribution": (f'Clip from "{title}" by {channel} ({url.replace("https://", "").replace("www.", "")}), '
                        f"licensed under {rcfg['license_label']}. "
                        + ("Trimmed, reframed and subtitled." if speech else "Trimmed and reframed.")),
        "speech": speech,
        "language": tr["language"] if speech else None,
        "language_probability": tr["probability"],
        "whisper": {"model": rcfg["whisper_model"], "device": tr.get("device", "test")},
        "transcript": tr["text"],
        "prepared_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    (folder / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    return folder


# ---------------------------------------------------------------- git

def git(*args, check=True):
    return run(["git", "-C", str(ROOT), *args], env=ORIGINAL_ENV, check=check)


def sync_to_github(branch):
    """Commits every reel folder not yet on GitHub and pushes. Also picks up
    reels left behind by a previous run whose push failed."""
    git("add", "--", "reels")
    staged = git("diff", "--cached", "--quiet", "--", "reels", check=False).returncode == 1
    if staged:
        names = git("diff", "--cached", "--name-only", "--", "reels").stdout.split()
        ids = sorted({n.split("/")[1].split("-")[0].lstrip("0") for n in names if n.count("/") >= 2})
        git("commit", "-m", f"Reels ready: ID {', '.join(ids)}", "--", "reels")
    git("pull", "--rebase", "--autostash", "origin", branch)
    ahead = git("rev-list", "--count", f"origin/{branch}..HEAD").stdout.strip()
    if ahead and ahead != "0":
        git("push", "origin", f"HEAD:{branch}")
        return True
    return staged


# ---------------------------------------------------------------- check

def check_setup(cfg):
    ok = True

    def line(name, good, detail=""):
        nonlocal ok
        ok &= good
        say(f"  [{'ok' if good else '!!'}] {name}" + (f" — {detail}" if detail else ""))

    say("Checking the reels setup\n")
    line("project folder not on C:", not on_drive_c(ROOT), str(ROOT))
    line("Python", True, sys.version.split()[0] + f" ({sys.executable})")
    line("Python inside the project .venv", ".venv" in Path(sys.executable).parts, "")
    try:
        exe = ffmpeg_exe()
        enc = run([exe, "-hide_banner", "-encoders"]).stdout
        line("ffmpeg with libx264", "libx264" in enc, exe)
    except Exception as e:  # noqa: BLE001
        line("ffmpeg", False, str(e))
    deno = shutil.which("deno")
    line("Deno (for yt-dlp)", bool(deno), deno or "not found")
    try:
        v = yt_dlp(["--version"]).stdout.strip()
        line("yt-dlp", True, v)
    except Exception as e:  # noqa: BLE001
        line("yt-dlp", False, str(e).splitlines()[0])
    try:
        rows = read_sheet(cfg)
        line(f"sheet '{cfg['reels']['sheet_name']}'", True, f"{len(rows)} rows")
    except SystemExit as e:
        line("sheet", False, str(e))
    good, detail = gpu_works()
    line("Whisper on the GPU", good, " | ".join(detail) if not good else "CUDA ok")
    r = git("ls-remote", "--heads", "origin", check=False)
    line("GitHub access", r.returncode == 0, "" if r.returncode == 0 else r.stderr.strip()[:200])
    say("\nAll good." if ok else "\nSome checks failed: see the lines marked !!")
    return ok


def gpu_probe(cfg):
    import numpy as np
    model = load_whisper(cfg["reels"]["whisper_model"], "cuda")
    list(model.transcribe(np.zeros(16000, dtype=np.float32))[0])
    print("gpu ok")


# ---------------------------------------------------------------- main

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Prepare reels from the 'Idee Reel' sheet")
    ap.add_argument("--dry-run", action="store_true", help="don't commit or push")
    ap.add_argument("--only", type=int, help="process only this ID")
    ap.add_argument("--retry", action="store_true", help="retry rows rejected before")
    ap.add_argument("--check", action="store_true", help="check the setup and exit")
    ap.add_argument("--allow-c", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--gpu-probe", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--local-video", help=argparse.SUPPRESS)
    ap.add_argument("--words-json", help=argparse.SUPPRESS)
    ap.add_argument("--id", type=int, default=999, help=argparse.SUPPRESS)
    ap.add_argument("--title", default="Local test clip", help=argparse.SUPPRESS)
    ap.add_argument("--channel", default="Test Channel", help=argparse.SUPPRESS)
    ap.add_argument("--url", default="https://www.youtube.com/watch?v=TEST", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if on_drive_c(ROOT) and not args.allow_c:
        raise SystemExit(f"The project is on C: ({ROOT}). Move it to another drive: this script never writes to C:.")
    redirect_everything_to_project()
    cfg = load_config()

    if args.gpu_probe:
        gpu_probe(cfg)
        return
    if args.check:
        sys.exit(0 if check_setup(cfg) else 1)

    REELS_DIR.mkdir(exist_ok=True)
    state = load_state()

    if args.local_video:
        rows = [{"id": str(args.id), "link": args.url, "start": "", "end": "", "notes": "", "status": ""}]
    else:
        say("Reading the sheet…")
        rows = read_sheet(cfg)

    todo = []
    for row in rows:
        try:
            rid = normalize_id(row["id"])
        except Reject as e:
            say(f"  row '{row['id']}': {e}")
            continue
        if args.only is not None and rid != args.only:
            continue
        if row["status"].lower() == "salta":
            continue
        if existing_reel(rid) and not args.local_video:
            continue
        if str(rid) in state["rejected"] and not args.retry:
            continue
        todo.append(row)

    if not todo:
        say("No new rows to process.")
        finish([], args, cfg)
        return

    model_cache = {}

    def model_getter():
        if "m" not in model_cache:
            name = cfg["reels"]["whisper_model"]
            good, detail = gpu_works()
            device = "cuda" if good else "cpu"
            if not good:
                say("    GPU not available, using the CPU (slower): " + " | ".join(detail))
            say(f"    loading Whisper {name} on {device} (the first time it downloads ~1.6 GB into .reels\\models)…")
            model_cache["m"] = (load_whisper(name, device), device)
        return model_cache["m"]

    done, rejected, failed = [], [], []
    for row in todo:
        rid = row["id"]
        say(f"\nID {rid}: {row['link']}")
        t0 = time.time()
        try:
            folder = process_row(row, cfg, model_getter, args, say)
            done.append(folder)
            state["rejected"].pop(str(normalize_id(rid)), None)
            say(f"    ready: {folder.relative_to(ROOT).as_posix()} ({time.time() - t0:.0f}s)")
        except Reject as e:
            rejected.append((rid, str(e)))
            state["rejected"][str(normalize_id(rid))] = {"reason": str(e), "at": datetime.now().strftime("%Y-%m-%d %H:%M")}
            say(f"    REJECTED: {e}")
        except Exception as e:  # noqa: BLE001
            failed.append((rid, str(e)))
            say(f"    ERROR: {e}")
        save_state(state)

    say("\n" + "-" * 60)
    say(f"Ready: {len(done)}   Rejected: {len(rejected)}   Errors: {len(failed)}")
    for rid, why in rejected:
        say(f"  ID {rid} rejected: {why}   (write 'salta' in the sheet, or fix it and run with --retry)")
    for rid, why in failed:
        say(f"  ID {rid} error: {why.splitlines()[0]}   (it will be retried next time)")

    finish(done, args, cfg)


def finish(done, args, cfg):
    if args.dry_run or args.local_video:
        if done:
            say("\nDry run: nothing committed or pushed (the next normal run will push these reels).")
        return
    say("\nSyncing with GitHub…")
    try:
        if sync_to_github(cfg.get("branch", "main")):
            say("Pushed. The Tuesday/Thursday routine publishes them, lowest ID first.")
        else:
            say("Nothing new to push.")
    except RuntimeError as e:
        say(f"GitHub sync FAILED: {e}\nThe reels are saved locally: run again to retry.")
        sys.exit(3)


if __name__ == "__main__":
    main()
