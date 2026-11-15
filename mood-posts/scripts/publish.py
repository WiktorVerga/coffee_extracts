#!/usr/bin/env python3
"""
Publishes a mood post (one image) to Instagram through the Graph API.

Requirements:
  - post.jpg exists in the folder (scripts/render.py or generate.py)
  - caption.txt exists in the folder
  - the folder is committed and pushed to GitHub (public repo): Instagram
    downloads the image from a public URL. Hosts and retries are the same as
    the carousels' (scripts/media_host.py in the repository root)

Usage:
    python mood-posts/scripts/publish.py mood-posts/posts/<folder> --sha <commit>
    python mood-posts/scripts/publish.py mood-posts/posts/<folder> --sha <commit> --dry-run

Token: same as the carousels. In the cloud routine the proxy adds it for
graph.instagram.com; on your own computer set IG_ACCESS_TOKEN.

Only the draft container is retried when Instagram can't download the image;
media_publish, the one call that makes the post public, is never retried.
The result goes to <folder>/publication.json and mood-posts/log.json
(through mood_log.py), also when it fails.

Exit codes: 0 published (or dry run), 2 content error, 3 API error.
"""
import argparse
import json
import os
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent                 # mood-posts/
ROOT = BASE.parent                 # repository root
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(ROOT / "scripts"))
import media_host  # noqa: E402  (repository root: scripts/media_host.py)
import mood_log  # noqa: E402

CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
IG = CONFIG["instagram"]
API = f'{IG["api_host"].rstrip("/")}/{IG["api_version"]}'
USER = IG.get("user_id") or "me"
LOCAL_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
MAX_BYTES = 8 * 1024 * 1024        # Instagram's limit for an image
RATIO_MIN, RATIO_MAX = 0.8, 1.91   # 4:5 to 1.91:1


class APIError(Exception):
    pass


def call(method, path, params=None):
    params = dict(params or {})
    if LOCAL_TOKEN:
        params["access_token"] = LOCAL_TOKEN
    url = f"{API}/{path.lstrip('/')}"
    body = None
    if method == "GET":
        if params:
            url += "?" + urllib.parse.urlencode(params)
    else:
        body = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=body, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise APIError(f"{method} {path} -> HTTP {e.code}: {detail}") from None


def wait_for_container(container_id, max_seconds=180):
    start = time.time()
    while time.time() - start < max_seconds:
        state = call("GET", container_id, {"fields": "status_code,status"})
        code = state.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise APIError(f"Container {container_id} in state {code}: {state.get('status')}")
        time.sleep(5)
    raise APIError(f"Container {container_id} not ready after {max_seconds}s")


def jpeg_size(path):
    """(width, height) of a JPEG, read from its header."""
    with open(path, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            raise ValueError("not a JPEG file")
        while True:
            marker = f.read(2)
            if len(marker) < 2 or marker[0] != 0xFF:
                raise ValueError("unreadable JPEG header")
            if marker[1] in (0xC0, 0xC1, 0xC2):
                f.read(3)
                height, width = struct.unpack(">HH", f.read(4))
                return width, height
            (length,) = struct.unpack(">H", f.read(2))
            f.seek(length - 2, 1)


def stop(message, code=2):
    print("ERROR:", message)
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--sha", required=True, help="pushed commit that contains post.jpg")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    folder = Path(args.folder).resolve()
    try:
        rel = folder.relative_to(ROOT).as_posix()
    except ValueError:
        stop("the folder must be inside the repository (Instagram downloads the image from GitHub)")
    image = folder / "post.jpg"
    caption_file = folder / "caption.txt"
    done = folder / "publication.json"

    if done.exists() and json.loads(done.read_text(encoding="utf-8")).get("media_id"):
        stop("this post was already published (publication.json). Not publishing twice.")
    if not image.exists():
        stop("post.jpg is missing: run generate.py or render.py first")
    if not caption_file.exists():
        stop("caption.txt is missing")
    try:
        width, height = jpeg_size(image)
    except ValueError as e:
        stop(f"post.jpg: {e}")
    if not RATIO_MIN <= width / height <= RATIO_MAX:
        stop(f"post.jpg is {width}x{height}: Instagram accepts ratios from 4:5 to 1.91:1")
    if image.stat().st_size > MAX_BYTES:
        stop(f"post.jpg is {image.stat().st_size} bytes, Instagram's limit is 8 MB")
    caption = caption_file.read_text(encoding="utf-8").strip()
    if not caption:
        stop("caption.txt is empty")
    if len(caption) > 2200:
        stop(f"caption is {len(caption)} characters, Instagram's limit is 2200")
    if caption.count("#") > 30:
        stop("more than 30 hashtags")

    rel_image = f"{rel}/{image.name}"
    hosts = media_host.hosts_for("image", CONFIG)

    if args.dry_run:
        url = media_host.url_for(hosts[0], CONFIG["github_repo"], args.sha, rel_image)
        status, detail = media_host.probe(url, "image", image.stat().st_size)
        print(f"Image: {width}x{height}, {image.stat().st_size} bytes")
        print(f"  {url}  [{status}: {detail}]")
        print("\n[dry-run] Caption:\n" + caption)
        print(f"\n[dry-run] Hosts, in order: {', '.join(hosts)}. Planned calls: 1 x POST {USER}/media "
              f"(image_url + caption, retried on download errors), wait for status, "
              f"1 x POST {USER}/media_publish (never retried)")
        return

    def create_container(urls):
        """A draft container: nothing is public until media_publish."""
        r = call("POST", f"{USER}/media", {"image_url": urls[0], "caption": caption})
        wait_for_container(r["id"])
        return r["id"]

    try:
        container, host, urls, _attempts = media_host.create_with_retry(
            create_container, [rel_image], "image", CONFIG["github_repo"], args.sha, CONFIG, root=ROOT,
            retryable=lambda e: media_host.is_download_error(e) or "in state ERROR" in str(e))
        # The only step that makes something public: never retried.
        published = call("POST", f"{USER}/media_publish", {"creation_id": container})
        media_id = published["id"]
        try:
            permalink = call("GET", media_id, {"fields": "permalink"}).get("permalink", "")
        except APIError:
            permalink = ""
    except Exception as e:  # noqa: BLE001
        print("API ERROR:", e)
        mood_log.add(rel, "error", reason=str(e)[:300])
        sys.exit(3)

    result = {"media_id": media_id, "permalink": permalink, "host": host, "image": urls[0], "sha": args.sha}
    done.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mood_log.add(rel, "published", media_id=media_id, permalink=permalink)
    print(f"PUBLISHED: {permalink or media_id}")


if __name__ == "__main__":
    main()
