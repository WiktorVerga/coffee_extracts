#!/usr/bin/env python3
"""
Publishes the animated reel of a post (posts/<folder>/reel.mp4) to Instagram.

Requirements:
  - posts/<folder>/ contains reel.mp4 and reel-meta.json (scripts/reel_animated/build_reel.py)
    and reel-caption.txt (written by the routine)
  - the folder is already committed and pushed to GitHub (PUBLIC repo):
    Instagram downloads the video from jsDelivr (files up to 20 MB), with
    raw.githubusercontent.com as fallback. See scripts/media_host.py

Usage:
    python3 scripts/publish_post_reel.py posts/2026-10-05-bitter-espresso --sha <commit>

    --dry-run   show what it would do without calling Instagram

Token: same as scripts/publish.py (API credential on the cloud environment,
or IG_ACCESS_TOKEN for tests from your own computer).

It writes posts/<folder>/reel-publication.json (also when it fails) and refuses to
publish twice. It never touches log.json or reels-log.json.

Exit codes: 0 published, 2 content/URL error, 3 API error.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish import CONFIG, USER, APIError, call  # noqa: E402
import media_host  # noqa: E402
from publish_reel import MAX_MB, create_video_container  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--sha", required=True, help="commit that contains reel.mp4 and reel-caption.txt")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    folder = Path(args.folder).resolve()
    rel = folder.relative_to(ROOT).as_posix()
    video, caption_file, meta_file = folder / "reel.mp4", folder / "reel-caption.txt", folder / "reel-meta.json"
    result_file = folder / "reel-publication.json"

    for f in (video, caption_file, meta_file):
        if not f.exists():
            print(f"ERROR: {f.name} is missing")
            sys.exit(2)
    if result_file.exists():
        prev = json.loads(result_file.read_text(encoding="utf-8"))
        if prev.get("media_id"):
            print(f"ERROR: this reel was already published ({prev.get('permalink') or prev['media_id']}). Not publishing twice.")
            sys.exit(2)

    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    if not 20 <= float(meta.get("duration", 0)) <= 91:
        print(f"ERROR: unexpected duration {meta.get('duration')}s")
        sys.exit(2)
    size_mb = video.stat().st_size / 1024 / 1024
    if size_mb > MAX_MB:
        print(f"ERROR: reel.mp4 is {size_mb:.1f} MB, jsDelivr serves at most {MAX_MB} MB")
        sys.exit(2)
    caption = caption_file.read_text(encoding="utf-8").strip()
    if not caption:
        print("ERROR: reel-caption.txt is empty")
        sys.exit(2)
    if len(caption) > 2200:
        print(f"ERROR: caption is {len(caption)} characters, Instagram's limit is 2200")
        sys.exit(2)
    if caption.count("#") > 30:
        print("ERROR: more than 30 hashtags")
        sys.exit(2)

    rel_file = f"{rel}/reel.mp4"
    params = {
        "media_type": "REELS",
        "caption": caption,
        "share_to_feed": "true",
        "thumb_offset": "1000",   # the cover title is on screen at 1 s
    }
    if args.dry_run:
        host = media_host.hosts_for("video", CONFIG)[0]
        url = media_host.url_for(host, CONFIG["github_repo"], args.sha, rel_file)
        status, detail = media_host.probe(url, "video")
        print(f"Video: {url}  [{status}: {detail}]")
        print("\n[dry-run] Caption:\n" + caption)
        print(f"\n[dry-run] Planned calls: 1 × POST {USER}/media (REELS, {size_mb:.1f} MB, {meta['duration']}s, "
              f"retried on download errors), wait for processing, 1 × POST {USER}/media_publish (never retried)")
        return

    url = ""
    try:
        container_id, url = create_video_container(rel_file, params, args.sha)
        # The only step that makes something public: never retried.
        published = call("POST", f"{USER}/media_publish", {"creation_id": container_id})
        media_id = published["id"]
        try:
            permalink = call("GET", media_id, {"fields": "permalink"}).get("permalink", "")
        except APIError:
            permalink = ""
    except Exception as e:  # noqa: BLE001
        print("API ERROR:", e)
        result_file.write_text(json.dumps({"error": str(e)[:400], "video": url, "sha": args.sha},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit(3)

    result_file.write_text(json.dumps({"media_id": media_id, "permalink": permalink, "video": url, "sha": args.sha},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PUBLISHED: {permalink or media_id}")


if __name__ == "__main__":
    main()
