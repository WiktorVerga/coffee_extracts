#!/usr/bin/env python3
"""
Builds the JPEG images of a carousel from its carousel.json.

Usage:
    python scripts/render.py posts/2026-10-05-fill-a-moka

The post folder must contain carousel.json. The script writes
slide-01.jpg, slide-02.jpg, ... and render-report.json into the same folder.

Exit codes:
    0  all good
    2  layout or structure problems (see messages): fix the JSON
    3  technical error (browser won't start, missing files)
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template" / "carousel.html"
CONFIG = ROOT / "config.json"

# Word limits per field, taken from the style guide (section 5).
LIMITS = {
    "cover": {"kicker": 4, "title": 8, "subtitle": 14},
    "text": {"title": 7, "body": 45, "highlight": 12},
    "number": {"title": 7, "caption": 25},
    "steps": {"title": 7},
    "compare": {"title": 6},
    "myth": {"myth": 14, "truth": 35},
    "tip": {"body": 30},
    "closing": {"title": 8, "body": 20, "cta": 6},
}


def words(value):
    if isinstance(value, list):
        value = " ".join(value)
    return len(str(value or "").split())


def check_structure(data):
    """Blocking errors and warnings about the carousel structure."""
    errors, warnings = [], []
    slides = data.get("slides", [])
    if not 5 <= len(slides) <= 10:
        errors.append(f"The carousel has {len(slides)} slides: it needs 5 to 10.")
    if slides and slides[0].get("type") != "cover":
        errors.append("The first slide must be of type 'cover'.")
    if slides and slides[-1].get("type") != "closing":
        errors.append("The last slide must be of type 'closing'.")
    middle = {s.get("type") for s in slides[1:-1]}
    if len(middle) < 2:
        warnings.append("Only one slide type between cover and closing: the guide asks for at least 2.")
    if sum(1 for s in slides if s.get("type") == "tip") > 1:
        errors.append("More than one 'tip' slide: one per carousel at most.")

    for i, s in enumerate(slides, 1):
        kind = s.get("type")
        if kind not in LIMITS:
            errors.append(f"Slide {i}: type '{kind}' doesn't exist.")
            continue
        for field, maximum in LIMITS[kind].items():
            n = words(s.get(field))
            if n > maximum:
                errors.append(f"Slide {i} ({kind}): '{field}' has {n} words, max {maximum}.")
        if kind == "myth" and str(s.get("verdict", "")).lower() not in ("true", "false"):
            errors.append(f"Slide {i}: a 'myth' slide needs \"verdict\": \"true\" or \"false\".")
        if kind == "number" and len(str(s.get("number", ""))) > 6:
            errors.append(f"Slide {i}: the number '{s.get('number')}' is longer than 6 characters.")
        if kind == "steps":
            steps = s.get("steps", [])
            if not 3 <= len(steps) <= 5:
                errors.append(f"Slide {i}: needs 3 to 5 steps (has {len(steps)}).")
            for j, p in enumerate(steps, 1):
                if words(p) > 14:
                    errors.append(f"Slide {i}: step {j} has {words(p)} words, max 14.")
        if kind == "compare":
            for side in ("left", "right"):
                col = s.get(side) or {}
                points = col.get("points", [])
                if not col.get("label"):
                    errors.append(f"Slide {i}: the {side} column has no label.")
                if not 2 <= len(points) <= 4:
                    errors.append(f"Slide {i}: the {side} column needs 2 to 4 points.")
                for p in points:
                    if words(p) > 8:
                        errors.append(f"Slide {i}: the point '{p[:30]}…' is longer than 8 words.")
    return errors, warnings


def launch_browser(p):
    """Tries Playwright's Chromium first, then a system Chrome."""
    attempts = [
        lambda: p.chromium.launch(),
        lambda: p.chromium.launch(channel="chrome"),
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


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(3)
    folder = Path(sys.argv[1]).resolve()
    source = folder / "carousel.json"
    if not source.exists():
        print(f"Missing {source}")
        sys.exit(3)

    data = json.loads(source.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    data.setdefault("handle", config.get("handle", ""))

    errors, warnings = check_structure(data)
    for w in warnings:
        print("WARNING:", w)
    if errors:
        for e in errors:
            print("ERROR:", e)
        sys.exit(2)

    html = TEMPLATE.read_text(encoding="utf-8")
    start = html.index('<script id="data" type="application/json">')
    start = html.index(">", start) + 1
    end = html.index("</script>", start)
    safe_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = html[:start] + "\n" + safe_json + "\n" + html[end:]
    html = html.replace('data-mode="preview"', 'data-mode="render"', 1)
    temp = TEMPLATE.parent / ".render-temp.html"
    temp.write_text(html, encoding="utf-8")

    from playwright.sync_api import sync_playwright

    for old in folder.glob("slide-*.jpg"):
        old.unlink()

    try:
        with sync_playwright() as p:
            browser = launch_browser(p)
            page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
            page.goto(temp.as_uri())
            page.wait_for_selector("html[data-ready='1']", timeout=20000)
            report = page.evaluate("window.__REPORT")
            created = []
            for i, el in enumerate(page.query_selector_all(".slide"), 1):
                target = folder / f"slide-{i:02d}.jpg"
                el.screenshot(path=str(target), type="jpeg", quality=92)
                created.append(target.name)
            browser.close()
    except Exception as e:  # noqa: BLE001
        print("TECHNICAL ERROR:", e)
        sys.exit(3)
    finally:
        temp.unlink(missing_ok=True)

    report["files"] = created
    report["warnings"] = warnings
    (folder / "render-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if not report["ok"]:
        for problem in report["problems"]:
            print("LAYOUT:", problem)
        sys.exit(2)
    print(f"OK: {len(created)} slides created in {folder}")


if __name__ == "__main__":
    main()
