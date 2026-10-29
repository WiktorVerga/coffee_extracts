#!/usr/bin/env python3
"""
A/B test of the carousel templates.

Every new post gets a variant ("A" or "B"), written once into its
carousel.json as "variant". The variant decides everything that looks or
sounds different: the carousel template (scripts/render.py), the reel template,
fonts and reel rules (scripts/reel_animated/build_reel.py). It is copied into
log.json with every log entry, so scripts/ab_report.py can compare the two.

Where each variant lives (config.json -> ab_test.variants):
    "base"        = the original project files: template/carousel.html,
                    template/fonts/, template/reel/, REEL-ANIMATED.md (variant A)
    "<folder>"    = a self-contained folder with a variant.json that names its
                    files and its reel settings (variant B: variant-b/)

Settings in config.json -> "ab_test":
    enabled            false = every new post uses "default"
    started_on         posts logged before this date don't count for the balance
    variants           {"A": "base", "B": "variant-b"}
    default            the variant of posts without "variant" (all posts before the test)
    measure_after_days the age at which the report freezes a post's metrics

Assignment: alternating and self-balancing. The variant with fewer posts in
the test gets the next post; on a tie, the opposite of the most recent one.
A post that failed and is retried keeps its variant (it is already in its
carousel.json).

Usage:
    python scripts/ab.py assign posts/<folder> [--include-previews]
        -> writes "variant" into carousel.json if it has none, prints it.
           In preview mode add --include-previews (as with log.py used).
    python scripts/ab.py next [--include-previews]   -> prints the next variant, changes nothing
    python scripts/ab.py status                      -> posts per variant in the test
    python scripts/ab.py rules posts/<folder>         -> the reel rules file of the post's variant
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"
LOG = ROOT / "log.json"
DEFAULTS = {
    "enabled": False,
    "started_on": "",
    "variants": {"A": "base"},
    "default": "A",
    "measure_after_days": 7,
}


class ABError(Exception):
    pass


def settings():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    out = dict(DEFAULTS)
    out.update(cfg.get("ab_test") or {})
    return out


BASE = {   # variant A: the original files of the project
    "name": "A - original",
    "carousel_template": "template/carousel.html",
    "fonts": "template/fonts",
    "reel_template": "template/reel/reel.html",
    "reel_vendor": "template/reel/vendor",
    "reel_rules": "REEL-ANIMATED.md",
    "reel": {},
}
PATH_KEYS = ("carousel_template", "fonts", "reel_template", "reel_vendor", "reel_rules")


def profile(variant):
    """Everything that defines a variant, with absolute paths:
    carousel_template, fonts, reel_template, reel_vendor, reel_rules (Paths),
    reel (dict: overrides of config.json -> reel_animated), name, folder."""
    where = settings()["variants"].get(variant)
    if not where:
        raise ABError(f"variant '{variant}' is not in config.json -> ab_test.variants")
    if where == "base":
        prof, base_dir = dict(BASE), ROOT
    else:
        base_dir = ROOT / where
        vj = base_dir / "variant.json"
        if not vj.exists():
            raise ABError(f"variant '{variant}': {where}/variant.json is missing")
        prof = json.loads(vj.read_text(encoding="utf-8"))
        for k in PATH_KEYS:
            if not prof.get(k):
                raise ABError(f"variant '{variant}': '{k}' is missing in {where}/variant.json")
    out = {"name": prof.get("name", variant), "folder": base_dir, "reel": dict(prof.get("reel") or {})}
    for k in PATH_KEYS:
        path = (base_dir / prof[k]).resolve()
        if not path.exists():
            raise ABError(f"variant '{variant}': {k} not found ({path.relative_to(ROOT) if ROOT in path.parents else path})")
        out[k] = path
    return out


def template_for(variant):
    return profile(variant)["carousel_template"]


def variant_of(carousel, override=None):
    """The variant of a post: --variant override, then carousel.json, then the default."""
    v = override or (carousel or {}).get("variant") or settings()["default"]
    if v not in settings()["variants"]:
        raise ABError(f"variant '{v}' is not in config.json -> ab_test.variants")
    return v


def variant_of_folder(folder):
    cj = Path(folder) / "carousel.json"
    if not cj.exists():
        return ""
    try:
        return variant_of(json.loads(cj.read_text(encoding="utf-8")))
    except (ABError, json.JSONDecodeError):
        return ""


def _log():
    return json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []


def test_posts(include_previews=False):
    """{folder: (variant, position in the log)} of the posts that count in the test (latest entry per folder)."""
    s = settings()
    ok = {"published"} | ({"preview"} if include_previews else set())
    latest = {}
    for n, e in enumerate(_log()):
        if e.get("folder"):
            latest[e["folder"]] = (n, e)
    out = {}
    for folder, (n, e) in latest.items():
        if e.get("status") not in ok or not e.get("variant"):
            continue
        if s["started_on"] and e.get("date", "") < s["started_on"]:
            continue
        out[folder] = (e["variant"], n)   # n = position in log.json: later = more recent
    return out


def next_variant(include_previews=False):
    s = settings()
    names = list(s["variants"])
    if not s["enabled"] or len(names) < 2:
        return s["default"]
    posts = test_posts(include_previews)
    counts = {v: 0 for v in names}
    for v, _ in posts.values():
        if v in counts:
            counts[v] += 1
    low = min(counts.values())
    candidates = [v for v in names if counts[v] == low]
    if len(candidates) == 1:
        return candidates[0]
    if not posts:   # first post of the test: the new design (the old one has the history)
        others = [v for v in candidates if v != s["default"]]
        return others[0] if others else candidates[0]
    last = max(posts.values(), key=lambda t: t[1])[0]
    others = [v for v in candidates if v != last]
    return others[0] if others else candidates[0]


def assign(folder, include_previews=False):
    cj = Path(folder) / "carousel.json"
    if not cj.exists():
        raise ABError(f"{cj} is missing: write carousel.json first")
    text = cj.read_text(encoding="utf-8")
    data = json.loads(text)
    if data.get("variant"):
        variant_of(data)   # validates it
        return data["variant"], False
    v = next_variant(include_previews)
    # insert the field at the top, keeping the file's own formatting
    new = re.sub(r"^\s*\{\s*", '{\n  "variant": "%s",\n  ' % v, text, count=1)
    json.loads(new)
    cj.write_text(new, encoding="utf-8")
    return v, True


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    prev = "--include-previews" in args
    try:
        if args[0] == "assign" and len(args) >= 2:
            v, new = assign(args[1], prev)
            print(v)
            pr = profile(v)
            print(("assigned" if new else "already set") + f": variant {v} ({pr['name']}); reel rules: "
                  f"{pr['reel_rules'].relative_to(ROOT).as_posix()}", file=sys.stderr)
        elif args[0] == "rules" and len(args) >= 2:
            v = variant_of_folder(args[1]) or settings()["default"]
            print(profile(v)["reel_rules"].relative_to(ROOT).as_posix())
        elif args[0] == "next":
            print(next_variant(prev))
        elif args[0] == "status":
            s = settings()
            print(f"A/B test {'ON' if s['enabled'] else 'OFF'} since {s['started_on'] or '-'}")
            posts = test_posts(prev)
            for v, where in s["variants"].items():
                n = sum(1 for x, _ in posts.values() if x == v)
                pr = profile(v)
                print(f"  {v}: {n} posts  {pr['name']}  ({'original files' if where == 'base' else where + '/'})")
            print(f"  next: {next_variant(prev)}")
        else:
            print(__doc__)
            sys.exit(2)
    except ABError as e:
        print("ERROR:", e)
        sys.exit(3)


if __name__ == "__main__":
    main()
