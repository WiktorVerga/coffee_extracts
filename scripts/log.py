#!/usr/bin/env python3
"""
Post log: keeps track of which ideas from the sheet have already been used.

log.json lives in the repository root. It is the source of truth for which
idea comes next: an idea whose ID appears here as "published" or "skipped"
must not be used again.

Usage:
    python scripts/log.py used [--include-previews]
        → prints the IDs already used (published or skipped), one per line.
          In preview mode add --include-previews, so test runs move through
          the list instead of repeating the same idea. When you switch to
          "publish" mode, ideas that were only previewed become available again.

    python scripts/log.py recent [N]
        → prints the last N posts (default 5), useful to avoid repeating a series

    python scripts/log.py add --id 7 --idea "Caricare la moka" \
        --series "How-to" --folder posts/2026-10-05-fill-a-moka \
        --status preview|published|skipped|error [--reason "..."] \
        [--media-id 123] [--permalink https://...] [--variant A|B]

Every entry also records the post's A/B template variant ("variant"): taken
from --variant, or else from the folder's carousel.json (see scripts/ab.py).
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "log.json"
STATUSES = ("preview", "published", "skipped", "error")
FINAL = {"published", "skipped"}


def load():
    if LOG.exists():
        return json.loads(LOG.read_text(encoding="utf-8"))
    return []


def save(entries):
    LOG.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def variant_for(folder):
    if not folder:
        return ""
    try:
        import ab
        return ab.variant_of_folder(ROOT / folder)
    except Exception:  # noqa: BLE001  (the log must never fail because of the A/B test)
        return ""


def add(idea_id, idea, status, folder="", series="", reason="", media_id="", permalink="", variant=""):
    entries = load()
    entries.append({
        "date": datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d %H:%M"),
        "id": str(idea_id),
        "idea": idea,
        "series": series,
        "status": status,
        "folder": folder,
        "reason": reason,
        "media_id": media_id,
        "permalink": permalink,
        "variant": variant or variant_for(folder),
    })
    save(entries)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("used")
    u.add_argument("--include-previews", action="store_true")
    r = sub.add_parser("recent")
    r.add_argument("n", nargs="?", type=int, default=5)
    a = sub.add_parser("add")
    a.add_argument("--id", required=True)
    a.add_argument("--idea", required=True)
    a.add_argument("--status", required=True, choices=STATUSES)
    a.add_argument("--series", default="")
    a.add_argument("--folder", default="")
    a.add_argument("--reason", default="")
    a.add_argument("--media-id", default="")
    a.add_argument("--permalink", default="")
    a.add_argument("--variant", default="")
    args = ap.parse_args()

    if args.cmd == "used":
        for e in load():
            if e["status"] in FINAL or (args.include_previews and e["status"] == "preview"):
                print(e["id"])
    elif args.cmd == "recent":
        for e in load()[-args.n:]:
            v = f' | variant {e["variant"]}' if e.get("variant") else ""
            print(f'{e["date"]} | ID {e["id"]} | {e["status"]} | {e.get("series", "")} | {e["idea"]}{v}')
    elif args.cmd == "add":
        add(args.id, args.idea, args.status, args.folder, args.series, args.reason, args.media_id, args.permalink,
            args.variant)
        print("Logged.")


if __name__ == "__main__":
    main()
