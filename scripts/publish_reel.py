#!/usr/bin/env python3
"""
Publishes the reel in a reels/ folder to Instagram.

Requirements:
  - the folder contains clip.mp4 (made by prepare_reels.py on the owner's PC),
    source.json and caption.txt (written by the reels routine)
  - the folder is already committed and pushed to GitHub (PUBLIC repo):
    Instagram downloads the video from jsDelivr (files up to 20 MB), with
    raw.githubusercontent.com as fallback. See scripts/media_host.py

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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import media_host  # noqa: E402
import reels_log  # noqa: E402
from publish import CONFIG, USER, APIError, call  # noqa: E402  (same API helpers as the carousels)

ROOT = Path(__file__).resolve().parent.parent
MAX_MB = 20  # jsDelivr limit for files served from GitHub


def video_retryable(err):
    """A video container that fails to download or ends in ERROR is only a draft:
    creating it again is safe."""
    return media_host.is_download_error(err) or "in state ERROR" in str(err)


def create_video_container(rel_file, params, sha, log=print):
    """Creates the REELS container (download from jsDelivr, retried, raw as fallback)
    and waits until Instagram has processed it. Returns (container_id, url)."""
    def create(urls):
        container = call("POST", f"{USER}/media", dict(params, video_url=urls[0]))
        wait_for_container(container["id"])
        return container["id"]

    container_id, _host, urls = media_host.create_with_retry(
        create, [rel_file], "video", CONFIG["github_repo"], sha, CONFIG,
        retryable=video_retryable, log=log)
    return container_id, urls[0]


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

    rel_file = f"{rel}/clip.mp4"
    params = {
        "media_type": "REELS",
        "caption": caption,
        "share_to_feed": "true",
        "thumb_offset": "1000",
    }
    if args.dry_run:
        host = media_host.hosts_for("video", CONFIG)[0]
        url = media_host.url_for(host, CONFIG["github_repo"], args.sha, rel_file)
        status, detail = media_host.probe(url, "video")
        print(f"Video: {url}  [{status}: {detail}]")
        print("\n[dry-run] Caption:\n" + caption)
        print(f"\n[dry-run] Planned calls: 1 × POST {USER}/media (REELS, {size_mb:.1f} MB, retried on download errors), "
              f"wait for processing, 1 × POST {USER}/media_publish (never retried)")
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
        reels_log.add(rid, title, "error", rel, reason=str(e)[:300])
        sys.exit(3)

    result = {"media_id": media_id, "permalink": permalink, "video": url, "sha": args.sha}
    (folder / "publication.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    reels_log.add(rid, title, "published", rel, media_id=media_id, permalink=permalink)
    print(f"PUBLISHED: {permalink or media_id}")


if __name__ == "__main__":
    main()
