#!/usr/bin/env python3
"""
Creates a mood post: one line of text -> a post folder with post.json and
the finished post.jpg (through render.py).

Usage:
    python mood-posts/scripts/generate.py --text "but first,|*coffee*"
    python mood-posts/scripts/generate.py --text "..." --theme espresso \
        --layout stack --art beans --format portrait --sub "small second line" \
        --kind motivational|relatable|reflection \
        --caption "Caption text for Instagram" --slug but-first-coffee
    python mood-posts/scripts/generate.py --batch ideas.json
    python mood-posts/scripts/generate.py --list

Text:
    "|" or "\\n" forces a line break, *word* marks the emphasis.

Anything you leave out is chosen for you:
    --theme   the theme used least recently
    --layout  from the length of the line (short -> stack/hero, long -> quiet)
    --art     the drawing whose tags match the words of the line, otherwise
              the one used least recently ("none" for no drawing)
The choice never repeats the theme, layout or drawing of the previous post
when there is an alternative.

--batch takes a JSON file with a list of objects using the same names as the
options ({"text": "...", "theme": "...", "caption": "..."}); one folder each.

Options:
    --date YYYY-MM-DD   folder date (default: today)
    --no-render         write post.json only
    --force             overwrite an existing folder with the same name

Exit codes: 0 ok, 2 content or layout problem, 3 technical error.
"""
import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent                      # mood-posts/
POSTS = BASE / "posts"
ART_INDEX = BASE / "art" / "index.json"
LAYOUTS = ("center", "stack", "hero", "side", "quiet")
KINDS = ("motivational", "relatable", "reflection")
FORMATS = ("portrait", "square")
MAX_WORDS, MAX_SUB_WORDS = 14, 8

sys.path.insert(0, str(HERE))
import render as renderer  # noqa: E402

# Words in a line -> tags of art/index.json. Only a nudge: the fallback is rotation.
HINTS = {
    "morning": ("morning", "alarm", "wake", "woke", "early", "sunrise", "snooze", "7am", "6am"),
    "tired": ("tired", "sleep", "sleepy", "nap", "awake", "exhausted", "yawn", "bed"),
    "monday": ("monday", "week", "meeting", "inbox", "email", "emails", "work", "deadline"),
    "cozy": ("cozy", "slow", "quiet", "rain", "sunday", "blanket", "home", "soft"),
    "comfort": ("okay", "ok", "fine", "enough", "gentle", "breathe", "kind", "rest"),
    "humor": ("people", "opinion", "talk", "personality", "need", "survive", "functioning"),
    "love": ("love", "heart", "favorite", "date", "together", "us"),
    "ritual": ("first", "ritual", "moka", "brew", "pour", "cup", "espresso", "sip"),
    "go": ("go", "run", "late", "busy", "commute", "walk", "start", "begin", "ideas"),
    "oops": ("spill", "spilled", "mess", "mistake", "oops", "again", "anyway"),
}


class GenerateError(Exception):
    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def plain(text):
    """The line without markup, on one row."""
    return " ".join(text.replace("*", "").split())


def words(text):
    return len(plain(text or "").split())


def slugify(text, limit=6):
    ascii_text = unicodedata.normalize("NFKD", plain(text)).encode("ascii", "ignore").decode()
    parts = re.findall(r"[a-z0-9]+", ascii_text.lower())
    return "-".join(parts[:limit]) or "post"


def history():
    """post.json of the existing posts, oldest first (folder names start with the date)."""
    out = []
    if POSTS.exists():
        for folder in sorted(p for p in POSTS.iterdir() if p.is_dir()):
            source = folder / "post.json"
            if source.exists():
                try:
                    out.append(json.loads(source.read_text(encoding="utf-8")))
                except json.JSONDecodeError:
                    pass
    return out


def least_recent(options, used, avoid=None):
    """The option used longest ago (never used wins); `avoid` only loses a tie-break
    when it is the single most recent one and there is an alternative."""
    options = list(options)
    if not options:
        return None
    last_seen = {o: -1 for o in options}
    for i, value in enumerate(used):
        if value in last_seen:
            last_seen[value] = i
    ranked = sorted(options, key=lambda o: (last_seen[o], options.index(o)))
    if avoid and ranked[0] == avoid and len(ranked) > 1:
        return ranked[1]
    return ranked[0]


def pick_layout(text, art, past):
    n = words(text)
    if art is None:
        choices = ["quiet", "stack"] if n > 4 else ["stack", "quiet"]
    elif n <= 4:
        choices = ["stack", "hero", "center"]
    elif n <= 8:
        choices = ["center", "side", "hero"]
    else:
        choices = ["center", "quiet", "side"]
    previous = past[-1].get("layout") if past else None
    return next((c for c in choices if c != previous), choices[0])


def pick_art(text, past):
    names = renderer.available_art()
    if not names:
        return None
    index = json.loads(ART_INDEX.read_text(encoding="utf-8")) if ART_INDEX.exists() else {}
    line = set(re.findall(r"[a-z0-9]+", plain(text).lower()))
    wanted = {tag for tag, triggers in HINTS.items() if line & set(triggers)}
    used = [p.get("art") for p in past]
    previous = used[-1] if used else None

    def score(name):
        meta = index.get(name, {})
        tags = set(meta.get("tags", [])) | set(name.split("-"))
        return len(tags & (wanted | line))

    best = max(score(n) for n in names)
    pool = [n for n in names if score(n) == best] if best else names
    return least_recent(pool, used, avoid=previous)


def build(spec, past):
    """Validates one request and fills in what is missing. Returns (post, caption, slug)."""
    text = str(spec.get("text") or "").replace("\\n", "\n").replace("|", "\n")
    text = "\n".join(" ".join(row.split()) for row in text.split("\n") if row.strip())
    if not text:
        raise GenerateError("the post needs a text")
    if words(text) > MAX_WORDS:
        raise GenerateError(f"the line has {words(text)} words, max {MAX_WORDS}: shorten it")
    if text.count("*") % 2:
        raise GenerateError("unbalanced '*': mark the emphasis as *word*")
    sub = " ".join(str(spec.get("sub") or "").split())
    if words(sub) > MAX_SUB_WORDS:
        raise GenerateError(f"'sub' has {words(sub)} words, max {MAX_SUB_WORDS}")

    themes = renderer.load_themes()
    theme = spec.get("theme")
    if theme and theme not in themes:
        raise GenerateError(f"unknown theme '{theme}'. Available: {', '.join(themes)}")
    if not theme:
        theme = least_recent(themes, [p.get("theme") for p in past],
                             avoid=past[-1].get("theme") if past else None)

    art = spec.get("art")
    if art in ("none", "", False):
        art = None
    elif art:
        if art not in renderer.available_art():
            raise GenerateError(f"unknown art '{art}'. Available: {', '.join(renderer.available_art())}")
    elif spec.get("layout") != "quiet":
        art = pick_art(text, past)

    layout = spec.get("layout")
    if layout and layout not in LAYOUTS:
        raise GenerateError(f"unknown layout '{layout}'. Available: {', '.join(LAYOUTS)}")
    if not layout:
        layout = pick_layout(text, art, past)
    if layout == "hero" and art is None:
        raise GenerateError("the 'hero' layout needs a drawing (--art)")

    fmt = spec.get("format") or "portrait"
    if fmt not in FORMATS:
        raise GenerateError(f"unknown format '{fmt}'. Available: {', '.join(FORMATS)}")

    kind = spec.get("kind")
    if kind and kind not in KINDS:
        raise GenerateError(f"unknown kind '{kind}'. Available: {', '.join(KINDS)}")

    post = {"text": text, "theme": theme, "layout": layout, "art": art, "format": fmt}
    if kind:
        post["kind"] = kind
    if sub:
        post["sub"] = sub
    return post, (spec.get("caption") or "").strip(), spec.get("slug") or slugify(text)


def create(spec, day, do_render=True, force=False):
    past = history()
    post, caption, slug = build(spec, past)
    folder = POSTS / f"{day}-{slug}"
    if folder.exists() and not force:
        if (folder / "publication.json").exists():
            raise GenerateError(f"{folder.name} is already published: choose another --slug")
        raise GenerateError(f"{folder.name} already exists: use --force or another --slug")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if caption:
        (folder / "caption.txt").write_text(caption + "\n", encoding="utf-8")
    shown = folder.relative_to(BASE.parent).as_posix()
    print(f"{shown}: theme={post['theme']} layout={post['layout']} art={post['art']} format={post['format']}")
    if do_render:
        try:
            renderer.render(folder)
        except renderer.RenderError as e:
            raise GenerateError(f"{shown}: render failed\n{e}", getattr(e, "code", 3)) from None
        print(f"OK: {shown}/post.jpg")
    return folder


def show_lists():
    themes = renderer.load_themes()
    index = json.loads(ART_INDEX.read_text(encoding="utf-8")) if ART_INDEX.exists() else {}
    print("Themes:")
    for name, t in themes.items():
        print(f"  {name:<10} {t.get('label', '')}")
    print("Layouts:\n  " + ", ".join(LAYOUTS))
    print("Formats:\n  " + ", ".join(FORMATS))
    print("Art:")
    for name in renderer.available_art():
        meta = index.get(name, {})
        print(f"  {name:<14} {meta.get('title', '')}  [{', '.join(meta.get('tags', []))}]")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text")
    ap.add_argument("--theme")
    ap.add_argument("--layout")
    ap.add_argument("--art")
    ap.add_argument("--format", dest="format")
    ap.add_argument("--sub")
    ap.add_argument("--kind", choices=KINDS, help="type of line (STYLE.md, section 1); kept in post.json and in the log")
    ap.add_argument("--caption")
    ap.add_argument("--slug")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--batch")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.list:
        show_lists()
        return
    if args.batch:
        specs = json.loads(Path(args.batch).read_text(encoding="utf-8"))
        if not isinstance(specs, list):
            print("ERROR: the batch file must contain a JSON list")
            sys.exit(2)
    elif args.text:
        specs = [{k: getattr(args, k) for k in ("text", "theme", "layout", "art", "format", "sub", "kind", "caption", "slug")}]
    else:
        ap.print_usage()
        sys.exit(3)

    worst = 0
    for spec in specs:
        try:
            create(spec, spec.get("date") or args.date, not args.no_render, args.force)
        except GenerateError as e:
            print("ERROR:", e)
            worst = max(worst, e.code)
    sys.exit(worst)


if __name__ == "__main__":
    main()
