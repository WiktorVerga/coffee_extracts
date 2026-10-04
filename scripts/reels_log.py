#!/usr/bin/env python3
"""
Reels log: keeps track of which reels in reels/ have already been used.
Separate from log.json (carousels): reel IDs come from the "Idee Reel" sheet tab.

reels-log.json lives in the repository root. A reel whose ID appears here as
"published" or "skipped" must not be used again.

Usage:
    python scripts/reels_log.py ready [--include-previews]
        → reel folders ready to publish (they have clip.mp4 and source.json and
          their ID is not used yet), lowest ID first, one per line: "<ID> <folder>"
          In preview mode add --include-previews, so test runs move through the list.

    python scripts/reels_log.py used [--include-previews]
        → IDs already used, one per line

    python scripts/reels_log.py recent [N]
        → the last N log entries (default 5)

    python scripts/reels_log.py add --id 3 --title "Video title" \
        --folder reels/003-slug --status preview|published|skipped|error \
        [--reason "..."] [--media-id 123] [--permalink https://...]
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "reels-log.json"
REELS = ROOT / "reels"
STATUSES = ("preview", "published", "skipped", "error")
FINAL = {"published", "skipped"}


def load():
    if LOG.exists():
        return json.loads(LOG.read_text(encoding="utf-8"))
    return []


def save(entries):
    LOG.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add(reel_id, title, status, folder="", reason="", media_id="", permalink=""):
    entries = load()
    entries.append({
        "date": datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d %H:%M"),
        "id": str(int(reel_id)),
        "title": title,
        "status": status,
        "folder": folder,
        "reason": reason,
        "media_id": media_id,
        "permalink": permalink,
    })
    save(entries)


def used(include_previews=False):
    return {e["id"] for e in load()
            if e["status"] in FINAL or (include_previews and e["status"] == "preview")}


def ready(include_previews=False):
    taken = used(include_previews)
    out = []
    for folder in sorted(REELS.glob("[0-9][0-9][0-9]-*")):
        if not ((folder / "clip.mp4").exists() and (folder / "source.json").exists()):
            continue
        rid = str(int(folder.name.split("-")[0]))
        if rid not in taken:
            out.append((int(rid), folder.relative_to(ROOT).as_posix()))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("ready", "used"):
        p = sub.add_parser(name)
        p.add_argument("--include-previews", action="store_true")
    r = sub.add_parser("recent")
    r.add_argument("n", nargs="?", type=int, default=5)
    a = sub.add_parser("add")
    a.add_argument("--id", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--status", required=True, choices=STATUSES)
    a.add_argument("--folder", default="")
    a.add_argument("--reason", default="")
    a.add_argument("--media-id", default="")
    a.add_argument("--permalink", default="")
    args = ap.parse_args()

    if args.cmd == "ready":
        for rid, folder in ready(args.include_previews):
            print(rid, folder)
    elif args.cmd == "used":
        for rid in sorted(used(args.include_previews), key=int):
            print(rid)
    elif args.cmd == "recent":
        for e in load()[-args.n:]:
            print(f'{e["date"]} | ID {e["id"]} | {e["status"]} | {e["title"]}')
    elif args.cmd == "add":
        add(args.id, args.title, args.status, args.folder, args.reason, args.media_id, args.permalink)
        print("Logged.")


if __name__ == "__main__":
    main()
