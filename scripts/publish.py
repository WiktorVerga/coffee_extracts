#!/usr/bin/env python3
"""
Publishes the carousel in a post folder to Instagram.

Requirements:
  - the slide-XX.jpg images already exist (scripts/render.py)
  - the images are already committed and pushed to GitHub (PUBLIC repo),
    because Instagram downloads them from a public URL
  - the folder contains caption.txt

Usage:
    python scripts/publish.py posts/2026-10-05-fill-a-moka --sha <commit> \
        --id 7 --idea "Caricare la moka" --series "How-to"

    --dry-run   show what it would do without calling Instagram

Token:
  - In the cloud routine the token is NOT in the code: it is stored as an
    "API credential" on the environment for the host graph.instagram.com,
    and the proxy adds it to requests automatically.
  - To test from your own computer: set the IG_ACCESS_TOKEN environment
    variable to your token.

Exit codes: 0 published, 2 content/URL error, 3 API error.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import log  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
IG = CONFIG["instagram"]
BASE = f'{IG["api_host"].rstrip("/")}/{IG["api_version"]}'
USER = IG.get("user_id") or "me"
LOCAL_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()


class APIError(Exception):
    pass


def call(method, path, params=None):
    params = dict(params or {})
    if LOCAL_TOKEN:
        params["access_token"] = LOCAL_TOKEN
    url = f"{BASE}/{path.lstrip('/')}"
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
        raise APIError(f"{method} {path} → HTTP {e.code}: {detail}") from None


def image_url(repo, sha, rel_file):
    return f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{rel_file}"


def check_url(url):
    """Checks the image is reachable and is a JPEG.
    If the domain can't be reached from here (restricted network), says so and moves on."""
    try:
        req = urllib.request.Request(url, method="GET", headers={"Range": "bytes=0-1023"})
        with urllib.request.urlopen(req, timeout=30) as r:
            kind = r.headers.get("Content-Type", "")
            if "jpeg" not in kind:
                return f"unexpected type '{kind}'"
            return None
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return f"can't verify from here ({e.__class__.__name__})"


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--sha", required=True, help="commit that contains the images")
    ap.add_argument("--id", required=True)
    ap.add_argument("--idea", required=True)
    ap.add_argument("--series", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    folder = Path(args.folder).resolve()
    rel = folder.relative_to(ROOT).as_posix()
    images = sorted(folder.glob("slide-*.jpg"))
    caption_file = folder / "caption.txt"

    if not 2 <= len(images) <= 10:
        print(f"ERROR: need 2 to 10 images, found {len(images)}")
        sys.exit(2)
    if not caption_file.exists():
        print("ERROR: caption.txt is missing")
        sys.exit(2)
    caption = caption_file.read_text(encoding="utf-8").strip()
    if len(caption) > 2200:
        print(f"ERROR: caption is {len(caption)} characters, Instagram's limit is 2200")
        sys.exit(2)
    if caption.count("#") > 30:
        print("ERROR: more than 30 hashtags")
        sys.exit(2)

    urls = [image_url(CONFIG["github_repo"], args.sha, f"{rel}/{f.name}") for f in images]

    print("Images:")
    for u in urls:
        problem = check_url(u)
        print(f"  {u}" + (f"  [WARNING: {problem}]" if problem else "  [ok]"))
        if problem and problem.startswith(("HTTP", "unexpected")):
            print("ERROR: Instagram wouldn't be able to download this image. Is the repo public? Did the push succeed?")
            sys.exit(2)

    if args.dry_run:
        print("\n[dry-run] Caption:\n" + caption)
        print(f"\n[dry-run] Planned calls: {len(urls)} × POST {USER}/media (is_carousel_item), "
              f"1 × POST {USER}/media (CAROUSEL), wait for status, 1 × POST {USER}/media_publish")
        return

    try:
        children = []
        for u in urls:
            r = call("POST", f"{USER}/media", {"image_url": u, "is_carousel_item": "true"})
            children.append(r["id"])
        for c in children:
            wait_for_container(c)

        carousel = call("POST", f"{USER}/media", {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
        })
        wait_for_container(carousel["id"])

        published = call("POST", f"{USER}/media_publish", {"creation_id": carousel["id"]})
        media_id = published["id"]
        try:
            permalink = call("GET", media_id, {"fields": "permalink"}).get("permalink", "")
        except APIError:
            permalink = ""
    except APIError as e:
        print("API ERROR:", e)
        log.add(args.id, args.idea, "error", rel, args.series, reason=str(e)[:300])
        sys.exit(3)

    result = {"media_id": media_id, "permalink": permalink, "images": urls, "sha": args.sha}
    (folder / "publication.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log.add(args.id, args.idea, "published", rel, args.series, media_id=media_id, permalink=permalink)
    print(f"PUBLISHED: {permalink or media_id}")


if __name__ == "__main__":
    main()
