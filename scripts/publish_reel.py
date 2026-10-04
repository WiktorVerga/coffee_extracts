#!/usr/bin/env python3
"""
Publishes the reel in a reels/ folder to Instagram.

Requirements:
  - the folder contains clip.mp4 (made by prepare_reels.py on the owner's PC),
    source.json and caption.txt (written by the reels routine)
  - the folder is already committed and pushed to GitHub (PUBLIC repo):
    Instagram downloads the video from jsDelivr, which serves files up to 20 MB

Usage:
    python scripts/publish_reel.py reels/003-pull-a-shot --sha <commit>

    --dry-run   show what it would do without calling Instagram

Token: same as scripts/publish.py (API credential on the cloud environment,
or IG_ACCESS_TOKEN for tests from your own computer).

Exit codes: 0 published, 2 content/URL error, 3 API error.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reels_log  # noqa: E402
from publish import CONFIG, USER, APIError, call  # noqa: E402  (same API helpers as the carousels)

ROOT = Path(__file__).resolve().parent.parent
MAX_MB = 20  # jsDelivr limit for files served from GitHub


def file_url(repo, sha, rel_file):
    return f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{rel_file}"


def check_url(url):
    """Checks the video is reachable and is an MP4. If the domain can't be reached
    from here (restricted network), says so and moves on."""
    try:
        req = urllib.request.Request(url, method="GET", headers={"Range": "bytes=0-1023"})
        with urllib.request.urlopen(req, timeout=30) as r:
            kind = r.headers.get("Content-Type", "")
            if not kind.startswith("video/"):
                return f"unexpected type '{kind}'"
            return None
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return f"can't verify from here ({e.__class__.__name__})"


def wait_for_container(container_id, max_seconds=900):
    """Video processing on Instagram's side takes longer than images."""
    start = time.time()
    while time.time() - start < max_seconds:
        state = call("GET", container_id, {"fields": "status_code,status"})
        code = state.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise APIError(f"Container {container_id} in state {code}: {state.get('status')}")
        time.sleep(10)
    raise APIError(f"Container {container_id} not ready after {max_seconds}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--sha", required=True, help="commit that contains clip.mp4 and caption.txt")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    folder = Path(args.folder).resolve()
    rel = folder.relative_to(ROOT).as_posix()
    clip = folder / "clip.mp4"
    caption_file = folder / "caption.txt"
    source_file = folder / "source.json"

    for f in (clip, caption_file, source_file):
        if not f.exists():
            print(f"ERROR: {f.name} is missing")
            sys.exit(2)
    source = json.loads(source_file.read_text(encoding="utf-8"))
    rid, title = source["id"], source["video"]["title"]

    size_mb = clip.stat().st_size / 1024 / 1024
    if size_mb > MAX_MB:
        print(f"ERROR: clip.mp4 is {size_mb:.1f} MB, jsDelivr serves at most {MAX_MB} MB")
        sys.exit(2)
    caption = caption_file.read_text(encoding="utf-8").strip()
    if len(caption) > 2200:
        print(f"ERROR: caption is {len(caption)} characters, Instagram's limit is 2200")
        sys.exit(2)
    if caption.count("#") > 30:
        print("ERROR: more than 30 hashtags")
        sys.exit(2)
    yt_id = source["video"].get("youtube_id") or ""
    if yt_id and yt_id not in caption:
        print("ERROR: the caption doesn't contain the link to the original video (required by CC BY)")
        sys.exit(2)

    url = file_url(CONFIG["github_repo"], args.sha, f"{rel}/clip.mp4")
    problem = check_url(url)
    print(f"Video: {url}" + (f"  [WARNING: {problem}]" if problem else "  [ok]"))
    if problem and problem.startswith(("HTTP", "unexpected")):
        print("ERROR: Instagram wouldn't be able to download the video. Is the repo public? Did the push succeed?")
        sys.exit(2)

    params = {
        "media_type": "REELS",
        "video_url": url,
        "caption": caption,
        "share_to_feed": "true",
        "thumb_offset": "1000",
    }
    if args.dry_run:
        print("\n[dry-run] Caption:\n" + caption)
        print(f"\n[dry-run] Planned calls: 1 × POST {USER}/media (REELS, {size_mb:.1f} MB), "
              f"wait for processing, 1 × POST {USER}/media_publish")
        return

    try:
        container = call("POST", f"{USER}/media", params)
        wait_for_container(container["id"])
        published = call("POST", f"{USER}/media_publish", {"creation_id": container["id"]})
        media_id = published["id"]
        try:
            permalink = call("GET", media_id, {"fields": "permalink"}).get("permalink", "")
        except APIError:
            permalink = ""
    except APIError as e:
        print("API ERROR:", e)
        reels_log.add(rid, title, "error", rel, reason=str(e)[:300])
        sys.exit(3)

    result = {"media_id": media_id, "permalink": permalink, "video": url, "sha": args.sha}
    (folder / "publication.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    reels_log.add(rid, title, "published", rel, media_id=media_id, permalink=permalink)
    print(f"PUBLISHED: {permalink or media_id}")


if __name__ == "__main__":
    main()
