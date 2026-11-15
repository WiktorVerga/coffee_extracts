#!/usr/bin/env python3
"""
Builds the JPEG of a single-image "mood" post from its post.json.

Usage:
    python mood-posts/scripts/render.py mood-posts/posts/2026-11-15-slug [--out name.jpg] [--art-dir DIR]

The post folder must contain post.json (see mood-posts/CONTRACT.md). The
script writes post.jpg (1080 x 1350 or 1080 x 1080) and render-report.json
into the same folder. The folder can be anywhere, also outside the repo.

--out      file name of the image inside the folder (default post.jpg)
--art-dir  folder to read the drawings from instead of mood-posts/art
           (for tests)

When the layout check fails, no post.jpg is left in the folder: the image
is saved as post.rejected.jpg, to look at what went wrong.

Exit codes:
    0  all good
    2  content or layout problem (see the ERROR: / LAYOUT: lines): fix post.json
    3  technical error (browser won't start, missing files)

From another script:
    from render import render, available_art, load_themes, RenderError
    report = render(Path("mood-posts/posts/..."))      # raises RenderError (.code 2 or 3)
"""
import argparse
import json
import os
import re
import shutil
import struct
import sys
from pathlib import Path

MOOD = Path(__file__).resolve().parent.parent          # mood-posts/
ROOT = MOOD.parent                                     # repository root
CONFIG = ROOT / "config.json"
THEMES = MOOD / "themes.json"
ART_DIR = MOOD / "art"
TEMPLATE = MOOD / "template" / "post.html"

LAYOUTS = ("center", "stack", "hero", "side", "quiet")
FORMATS = {"portrait": (1080, 1350), "square": (1080, 1080)}
MAX_WORDS = 14
MAX_SUB_WORDS = 8
DEFAULT_HANDLE = "@coffee_extracts"
JPEG_QUALITY = 92

# Things an art file must not contain (CONTRACT.md, "art/*.svg rules").
FORBIDDEN_IN_ART = (
    (r"<script\b", "<script>"),
    (r"<image\b", "<image>"),
    (r"<text\b", "<text>"),
    (r"<foreignObject\b", "<foreignObject>"),
    (r"\son[a-z]+\s*=", "an event handler attribute (on...=)"),
    (r"(?:href|src)\s*=\s*[\"']\s*(?!#)[^\"']", "an external reference (href/src that is not #id)"),
    (r"url\(\s*[\"']?\s*(?!#)[a-z]+:", "an external url(...)"),
)


class RenderError(Exception):
    """code 2: content or layout problem. code 3: technical error."""

    def __init__(self, code, messages, kind="ERROR", report=None):
        if isinstance(messages, str):
            messages = [messages]
        super().__init__("; ".join(messages))
        self.code = code
        self.messages = list(messages)
        self.kind = kind            # "ERROR" or "LAYOUT": the prefix main() prints
        self.report = report


def words(value):
    """Number of words; the * of the emphasis marks don't count."""
    return len(str(value or "").replace("*", " ").split())


def load_themes():
    """The themes of mood-posts/themes.json, as a dict."""
    try:
        return json.loads(THEMES.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RenderError(3, f"Missing {THEMES}")
    except ValueError as e:
        raise RenderError(3, f"{THEMES} is not valid JSON: {e}")


def available_art(art_dir=None):
    """Names (without .svg) of the drawings in mood-posts/art, sorted."""
    folder = Path(art_dir) if art_dir else ART_DIR
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.svg"))


def load_handle():
    """Only the handle is read from the root config.json."""
    try:
        handle = json.loads(CONFIG.read_text(encoding="utf-8")).get("handle")
    except (OSError, ValueError):
        handle = None
    return handle or DEFAULT_HANDLE


def sanitize_svg(markup):
    """Keeps only the root <svg>...</svg>: no BOM, prolog, doctype or comments."""
    markup = markup.lstrip("﻿")
    markup = re.sub(r"<!--.*?-->", "", markup, flags=re.S)
    markup = re.sub(r"<\?.*?\?>", "", markup, flags=re.S)
    markup = re.sub(r"<!DOCTYPE[^>\[]*(\[[^\]]*\])?[^>]*>", "", markup, flags=re.S | re.I)
    start = re.search(r"<svg\b", markup)
    end = markup.rfind("</svg>")
    if not start or end < start.start():
        return ""
    return markup[start.start():end + len("</svg>")].strip()


def check_art(name, markup):
    """Problems of an (already sanitized) art file against the contract."""
    if not markup:
        return [f"art '{name}': no root <svg> element found."]
    errors = []
    for pattern, label in FORBIDDEN_IN_ART:
        if re.search(pattern, markup, flags=re.I):
            errors.append(f"art '{name}': contains {label}, which the contract forbids.")
    root_tag = markup[:markup.index(">") + 1] if ">" in markup else markup
    box = re.search(r"viewBox\s*=\s*[\"']([^\"']+)[\"']", root_tag)
    numbers = re.split(r"[\s,]+", box.group(1).strip()) if box else []
    try:
        ok = len(numbers) == 4 and float(numbers[2]) > 0 and float(numbers[3]) > 0
    except ValueError:
        ok = False
    if not ok:
        errors.append(f"art '{name}': the root <svg> needs a viewBox=\"0 0 W H\".")
    return errors


def validate(post, themes, art_dir=None):
    """Blocking content errors of a post.json (checked before the browser starts)."""
    errors = []
    if not isinstance(post, dict):
        return ["post.json must be a JSON object."]
    text = post.get("text")
    if not isinstance(text, str) or not text.replace("*", "").strip():
        errors.append("'text' is missing or empty.")
    else:
        n = words(text)
        if n > MAX_WORDS:
            errors.append(f"'text' has {n} words, max {MAX_WORDS}.")
        if text.count("*") % 2:
            errors.append("'text' has an unpaired '*': the emphasis is written *word*.")
    sub = post.get("sub")
    if sub is not None and not isinstance(sub, str):
        errors.append("'sub' must be a string.")
    elif sub and words(sub) > MAX_SUB_WORDS:
        errors.append(f"'sub' has {words(sub)} words, max {MAX_SUB_WORDS}.")

    theme = post.get("theme")
    if not theme:
        errors.append(f"'theme' is missing. Themes: {', '.join(themes)}.")
    elif theme not in themes:
        errors.append(f"theme '{theme}' doesn't exist. Themes: {', '.join(themes)}.")
    layout = post.get("layout") or "center"
    if layout not in LAYOUTS:
        errors.append(f"layout '{layout}' doesn't exist. Layouts: {', '.join(LAYOUTS)}.")
    fmt = post.get("format") or "portrait"
    if fmt not in FORMATS:
        errors.append(f"format '{fmt}' doesn't exist. Formats: {', '.join(FORMATS)}.")

    art = post.get("art")
    if art is not None and (not isinstance(art, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", art)):
        errors.append("'art' must be null or a file name of the art folder without '.svg' (letters, digits, - and _).")
    elif art:
        folder = Path(art_dir) if art_dir else ART_DIR
        if not (folder / f"{art}.svg").is_file():
            names = available_art(art_dir)
            errors.append(f"art '{art}' not found in {folder}. Available: {', '.join(names) if names else '(none)'}.")
    elif layout == "hero":
        errors.append("layout 'hero' needs a drawing: set 'art'.")
    return errors


def launch_browser(p):
    """Tries Playwright's Chromium first, then a system Chrome."""
    attempts = [
        lambda: p.chromium.launch(),
        lambda: p.chromium.launch(channel="chrome"),
        lambda: p.chromium.launch(channel="msedge"),
    ]
    for name in (os.environ.get("CHROME_PATH"), "google-chrome", "chromium", "chromium-browser"):
        if name:
            path = shutil.which(name) or (name if Path(name).exists() else None)
            if path:
                attempts.append(lambda path=path: p.chromium.launch(executable_path=path))
    last = None
    for attempt in attempts:
        try:
            return attempt()
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(f"Could not start a browser: {last}")


def jpeg_size(path):
    """(width, height) of a JPEG file, read from its header."""
    with open(path, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            return None
        while True:
            byte = f.read(1)
            if not byte:
                return None
            if byte != b"\xff":
                continue
            marker = f.read(1)
            while marker == b"\xff":
                marker = f.read(1)
            if not marker:
                return None
            m = marker[0]
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                continue
            length = f.read(2)
            if len(length) < 2:
                return None
            size = struct.unpack(">H", length)[0]
            if m in (0xC0, 0xC1, 0xC2):
                data = f.read(5)
                height, width = struct.unpack(">HH", data[1:5])
                return width, height
            f.seek(size - 2, 1)


def build_html(payload):
    """The template with the data block replaced and render mode switched on."""
    try:
        html = TEMPLATE.read_text(encoding="utf-8")
        start = html.index('<script id="data" type="application/json">')
        start = html.index(">", start) + 1
        end = html.index("</script>", start)
    except FileNotFoundError:
        raise RenderError(3, f"Missing {TEMPLATE}")
    except ValueError:
        raise RenderError(3, f"{TEMPLATE} has no <script id=\"data\"> block.")
    safe_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = html[:start] + "\n" + safe_json + "\n" + html[end:]
    if 'data-mode="preview"' not in html:
        raise RenderError(3, f"{TEMPLATE} has no data-mode=\"preview\" attribute.")
    return html.replace('data-mode="preview"', 'data-mode="render"', 1)


def render(folder: Path, out_name: str = "post.jpg", art_dir=None) -> dict:
    """
    Renders <folder>/post.json to <folder>/<out_name> and writes
    <folder>/render-report.json. Returns the report.
    Raises RenderError: .code 2 (content or layout), .code 3 (technical).
    """
    folder = Path(folder).resolve()
    source = folder / "post.json"
    if not source.is_file():
        raise RenderError(3, f"Missing {source}")
    if Path(out_name).name != out_name or not out_name.lower().endswith((".jpg", ".jpeg")):
        raise RenderError(3, f"--out must be a plain .jpg file name, got '{out_name}'.")
    try:
        post = json.loads(source.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        raise RenderError(2, f"{source.name} is not valid JSON: {e}")

    themes = load_themes()
    errors = validate(post, themes, art_dir)

    art_svg = None
    art = post.get("art") if isinstance(post, dict) else None
    if not errors and art:
        art_file = (Path(art_dir) if art_dir else ART_DIR) / f"{art}.svg"
        try:
            art_svg = sanitize_svg(art_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as e:
            raise RenderError(3, f"Could not read {art_file}: {e}")
        errors += check_art(art, art_svg)
    if errors:
        raise RenderError(2, errors)

    fmt = post.get("format") or "portrait"
    width, height = FORMATS[fmt]
    item = dict(post)
    item["layout"] = post.get("layout") or "center"
    item["format"] = fmt
    item["art"] = art or None
    item["art_svg"] = art_svg
    payload = {"posts": [item], "themes": themes, "handle": load_handle()}

    html = build_html(payload)
    temp = TEMPLATE.parent / f".render-temp-{os.getpid()}.html"
    target = folder / out_name
    rejected = target.with_name(target.stem + ".rejected.jpg")
    shot = target.with_name(target.stem + ".tmp.jpg")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RenderError(3, "Playwright is not installed: pip install playwright && python -m playwright install chromium")

    try:
        temp.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            browser = launch_browser(p)
            try:
                page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                page.goto(temp.as_uri())
                page.wait_for_selector("html[data-ready='1']", state="attached", timeout=30000)
                report = page.evaluate("window.__REPORT")
                page.locator(".post").first.screenshot(path=str(shot), type="jpeg", quality=JPEG_QUALITY)
            finally:
                browser.close()
    except RenderError:
        raise
    except Exception as e:  # noqa: BLE001
        shot.unlink(missing_ok=True)
        raise RenderError(3, f"TECHNICAL ERROR: {e}")
    finally:
        temp.unlink(missing_ok=True)

    size = jpeg_size(shot)
    if size != (width, height):
        shot.unlink(missing_ok=True)
        raise RenderError(3, f"The image came out {size}, expected {(width, height)}.")

    detail = (report.get("posts") or [None])[0] or {}
    ok = bool(report.get("ok"))
    target.unlink(missing_ok=True)
    rejected.unlink(missing_ok=True)
    final = target if ok else rejected
    shot.replace(final)

    result = {
        "ok": ok,
        "problems": list(report.get("problems") or []),
        "file": final.name,
        "width": width,
        "height": height,
        "theme": post.get("theme"),
        "layout": item["layout"],
        "format": fmt,
        "art": item["art"],
        "font_size": detail.get("font_size"),
        "lines": detail.get("lines"),
        "art_box": detail.get("art_box"),
    }
    (folder / "render-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not ok:
        raise RenderError(2, result["problems"] or ["layout check failed"], kind="LAYOUT", report=result)
    return result


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Render a mood post (post.json -> post.jpg).")
    parser.add_argument("folder", help="post folder containing post.json")
    parser.add_argument("--out", default="post.jpg", help="image file name inside the folder (default post.jpg)")
    parser.add_argument("--art-dir", default=None, help="read drawings from this folder instead of mood-posts/art")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 3

    folder = Path(args.folder).resolve()
    try:
        report = render(folder, args.out, art_dir=args.art_dir)
    except RenderError as e:
        if e.code == 2 and e.kind != "LAYOUT":
            # content errors never reach the browser: leave a report and no stale image
            try:
                (folder / args.out).unlink(missing_ok=True)
                (folder / "render-report.json").write_text(
                    json.dumps({"ok": False, "problems": e.messages, "file": None}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
            except OSError:
                pass
        for message in e.messages:
            print(message if message.startswith("TECHNICAL ERROR:") else f"{e.kind}: {message}")
        return e.code
    print(f"OK: {folder / report['file']} ({report['width']}x{report['height']}, "
          f"{report['layout']}, {report['theme']}, text {report['font_size']}px)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
