#!/usr/bin/env python3
"""
Builds the highlight images: the stories of every group and the covers.

Usage:
    python scripts/render_highlights.py            → every group
    python scripts/render_highlights.py moka gear  → only these groups (covers always)

Reads  highlights/highlights.json
Writes highlights/out/<NN>-<group>/story-01.png, story-02.png, ...
       highlights/out/covers/<NN>-<group>.png

These images are NOT published automatically: upload them by hand from the
Instagram app (see README, section "Highlights").

Exit codes: 0 all good, 2 text too long or invalid frame (fix the JSON), 3 technical error.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import launch_browser  # noqa: E402  (same browser fallback as the carousels)

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "highlights" / "highlights.json"
OUT = ROOT / "highlights" / "out"
STORY = ROOT / "template" / "story.html"
COVER = ROOT / "template" / "highlight-cover.html"
CONFIG = ROOT / "config.json"

# Word limits per field
LIMITS = {
    "cover": {"kicker": 4, "title": 8, "subtitle": 14},
    "text": {"title": 7, "body": 40},
    "number": {"title": 7, "body": 25},
    "list": {"title": 6},
    "steps": {"title": 6},
    "qa": {"question": 16, "answer": 35},
    "tip": {"label": 4, "body": 25},
    "sticker": {"title": 7, "body": 16},
    "closing": {"title": 8, "body": 20, "cta": 5},
}


def words(value):
    if isinstance(value, list):
        value = " ".join(value)
    return len(str(value or "").split())


def check_group(g):
    errors = []
    name = g.get("id", "?")
    frames = g.get("frames", [])
    if not frames:
        errors.append(f"[{name}] no frames.")
    if len(frames) > 15:
        errors.append(f"[{name}] {len(frames)} frames: keep it to 15 at most, people stop tapping.")
    for i, f in enumerate(frames, 1):
        kind = f.get("type")
        if kind not in LIMITS:
            errors.append(f"[{name}] frame {i}: type '{kind}' doesn't exist.")
            continue
        for field, maximum in LIMITS[kind].items():
            n = words(f.get(field))
            if n > maximum:
                errors.append(f"[{name}] frame {i} ({kind}): '{field}' has {n} words, max {maximum}.")
        if kind == "list":
            items = f.get("items", [])
            if not 2 <= len(items) <= 5:
                errors.append(f"[{name}] frame {i}: a list needs 2 to 5 items.")
            for it in items:
                if words(it.get("label")) > 4 or words(it.get("note")) > 8:
                    errors.append(f"[{name}] frame {i}: item '{it.get('label')}' too long (label ≤ 4 words, note ≤ 8).")
        if kind == "steps":
            steps = f.get("steps", [])
            if not 3 <= len(steps) <= 5:
                errors.append(f"[{name}] frame {i}: needs 3 to 5 steps.")
            for s in steps:
                if words(s) > 12:
                    errors.append(f"[{name}] frame {i}: step '{s[:30]}…' longer than 12 words.")
        if kind == "number" and len(str(f.get("number", ""))) > 6:
            errors.append(f"[{name}] frame {i}: number longer than 6 characters.")
    return errors


def inject(template, payload):
    html = template.read_text(encoding="utf-8")
    start = html.index('<script id="data" type="application/json">')
    start = html.index(">", start) + 1
    end = html.index("</script>", start)
    safe = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = html[:start] + "\n" + safe + "\n" + html[end:]
    html = html.replace('data-mode="preview"', 'data-mode="render"', 1)
    temp = template.parent / f".render-{template.stem}.html"
    temp.write_text(html, encoding="utf-8")
    return temp


def shoot(browser, temp, selector, targets, size):
    page = browser.new_page(viewport={"width": size[0], "height": size[1]}, device_scale_factor=1)
    page.goto(temp.as_uri())
    page.wait_for_selector("html[data-ready='1']", timeout=20000)
    report = page.evaluate("window.__REPORT")
    if report["ok"]:
        for el, target in zip(page.query_selector_all(selector), targets):
            target.parent.mkdir(parents=True, exist_ok=True)
            el.screenshot(path=str(target), type="png")
    page.close()
    return report


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    groups = data["groups"]
    wanted = set(sys.argv[1:])
    unknown = wanted - {g["id"] for g in groups}
    if unknown:
        print("ERROR: unknown groups:", ", ".join(sorted(unknown)))
        sys.exit(2)

    errors = [e for g in groups if not wanted or g["id"] in wanted for e in check_group(g)]
    if errors:
        for e in errors:
            print("ERROR:", e)
        sys.exit(2)

    from playwright.sync_api import sync_playwright

    problems = []
    temps = []
    try:
        with sync_playwright() as p:
            browser = launch_browser(p)

            # covers
            covers = [{"id": g["id"], "icon": g["icon"]} for g in groups]
            temp = inject(COVER, {"covers": covers}); temps.append(temp)
            targets = [OUT / "covers" / f"{i:02d}-{g['id']}.png" for i, g in enumerate(groups, 1)]
            rep = shoot(browser, temp, ".cover", targets, (1080, 1920))
            problems += [f"[covers] {x}" for x in rep["problems"]]

            # stories
            for i, g in enumerate(groups, 1):
                if wanted and g["id"] not in wanted:
                    continue
                folder = OUT / f"{i:02d}-{g['id']}"
                if folder.exists():
                    for old in folder.glob("story-*.png"):
                        old.unlink()
                temp = inject(STORY, {"handle": config.get("handle", ""), "frames": g["frames"]}); temps.append(temp)
                targets = [folder / f"story-{n:02d}.png" for n in range(1, len(g["frames"]) + 1)]
                rep = shoot(browser, temp, ".story", targets, (1080, 1920))
                problems += [f"[{g['id']}] {x}" for x in rep["problems"]]
                if rep["ok"]:
                    print(f"OK: {g['name']}: {len(targets)} stories in {folder.relative_to(ROOT)}")
            browser.close()
    except Exception as e:  # noqa: BLE001
        print("TECHNICAL ERROR:", e)
        sys.exit(3)
    finally:
        for t in temps:
            t.unlink(missing_ok=True)

    if problems:
        for x in problems:
            print("LAYOUT:", x)
        sys.exit(2)
    print(f"OK: {len(groups)} covers in {(OUT / 'covers').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
