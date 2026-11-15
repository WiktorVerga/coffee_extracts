#!/usr/bin/env python3
"""
Mood posts log: what was made and published, and what comes next.

mood-posts/log.json is the history. The post folders in mood-posts/posts/
are the source for the lines already used.

Usage:
    python mood-posts/scripts/mood_log.py recent [N]
        -> the last N entries (default 5): date | status | kind | theme, layout, art | line

    python mood-posts/scripts/mood_log.py lines
        -> every line already used (all post folders plus the log), one per row.
           A new post must not repeat or closely rewrite any of them.

    python mood-posts/scripts/mood_log.py retry
        -> folders whose latest entry is "error", with post.jpg and caption.txt,
           not published, and fewer than 3 errors. Oldest first.

    python mood-posts/scripts/mood_log.py queue [--include-previews]
        -> ready-made folders waiting to be published (post.jpg + caption.txt,
           no publication, never logged as published, skipped or error), oldest
           first. In preview mode add --include-previews so folders already
           previewed are left out and the runs move on; in publish mode leave
           it out, so previewed folders get published.

    python mood-posts/scripts/mood_log.py add --folder mood-posts/posts/<folder> \
        --status preview|published|skipped|error [--reason "..."] \
        [--media-id 123] [--permalink https://...]
        -> adds an entry; line, kind, theme, layout and art come from post.json
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent.parent      # mood-posts/
ROOT = BASE.parent
POSTS = BASE / "posts"
LOG = BASE / "log.json"
STATUSES = ("preview", "published", "skipped", "error")
MAX_ERRORS = 3


def load():
    return json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []


def save(entries):
    LOG.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plain(text):
    return " ".join(str(text or "").replace("*", "").split())


def rel(folder):
    """Folder path relative to the repository root, with forward slashes."""
    path = Path(folder)
    if not path.is_absolute():
        path = (ROOT / path) if (ROOT / path).exists() else path.resolve()
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(folder).as_posix()


def post_of(folder_rel):
    source = ROOT / folder_rel / "post.json"
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def add(folder, status, reason="", media_id="", permalink=""):
    folder_rel = rel(folder)
    post = post_of(folder_rel)
    entry = {
        "date": datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d %H:%M"),
        "folder": folder_rel,
        "text": plain(post.get("text")),
        "kind": post.get("kind", ""),
        "theme": post.get("theme", ""),
        "layout": post.get("layout", ""),
        "art": post.get("art") or "",
        "status": status,
        "reason": reason,
        "media_id": media_id,
        "permalink": permalink,
    }
    entries = load()
    entries.append(entry)
    save(entries)
    return entry


def folders():
    return sorted(p for p in POSTS.iterdir() if p.is_dir()) if POSTS.exists() else []


def is_published(folder):
    done = folder / "publication.json"
    try:
        return bool(json.loads(done.read_text(encoding="utf-8")).get("media_id"))
    except (OSError, json.JSONDecodeError):
        return False


def is_ready(folder):
    return (folder / "post.jpg").exists() and (folder / "caption.txt").exists() and not is_published(folder)


def statuses_by_folder():
    out = {}
    for e in load():
        out.setdefault(e.get("folder", ""), []).append(e.get("status"))
    return out


def retry_list():
    history = statuses_by_folder()
    out = []
    for folder in folders():
        seen = history.get(rel(folder), [])
        if seen and seen[-1] == "error" and seen.count("error") < MAX_ERRORS and is_ready(folder):
            out.append(rel(folder))
    return out


def queue_list(include_previews=False):
    history = statuses_by_folder()
    blocking = {"published", "skipped", "error"} | ({"preview"} if include_previews else set())
    return [rel(f) for f in folders() if is_ready(f) and not blocking & set(history.get(rel(f), []))]


def used_lines():
    lines = []
    for folder in folders():
        text = plain(post_of(rel(folder)).get("text"))
        if text:
            lines.append(text)
    lines += [e["text"] for e in load() if e.get("text")]
    return list(dict.fromkeys(line.lower() for line in lines))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("recent")
    r.add_argument("n", nargs="?", type=int, default=5)
    sub.add_parser("lines")
    sub.add_parser("retry")
    q = sub.add_parser("queue")
    q.add_argument("--include-previews", action="store_true")
    a = sub.add_parser("add")
    a.add_argument("--folder", required=True)
    a.add_argument("--status", required=True, choices=STATUSES)
    a.add_argument("--reason", default="")
    a.add_argument("--media-id", default="")
    a.add_argument("--permalink", default="")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.cmd == "recent":
        for e in load()[-args.n:]:
            look = ", ".join(x for x in (e.get("theme"), e.get("layout"), e.get("art") or "no art") if x)
            print(f'{e["date"]} | {e["status"]} | {e.get("kind") or "-"} | {look} | {e.get("text", "")}')
    elif args.cmd == "lines":
        print("\n".join(used_lines()))
    elif args.cmd == "retry":
        print("\n".join(retry_list()))
    elif args.cmd == "queue":
        print("\n".join(queue_list(args.include_previews)))
    elif args.cmd == "add":
        add(args.folder, args.status, args.reason, args.media_id, args.permalink)
        print("Logged.")


if __name__ == "__main__":
    main()
