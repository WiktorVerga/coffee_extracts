#!/usr/bin/env python3
"""
Public URLs for the media Instagram downloads, and the logic that makes those
downloads reliable. Used by publish.py, publish_reel.py and publish_post_reel.py.

Why this exists
---------------
Instagram does not receive our files: it downloads them from a public URL.
- jsDelivr, on a brand-new commit, can answer 403 or 503 until it has fetched
  the whole file from GitHub, and it can serve the first bytes of a file
  (a range request) while the full file still fails. Instagram downloads the
  full file, so a check on the first kilobyte proves nothing.
- raw.githubusercontent.com answers at once, but serves .mp4 files as
  application/octet-stream.

What it does
------------
1. Hosts for the same file of the same commit:
     raw       https://raw.githubusercontent.com/<repo>/<sha>/<path>
     jsdelivr  https://cdn.jsdelivr.net/gh/<repo>@<sha>/<path>
     pages     https://<owner>.github.io/<repo>/<path>   (only if GitHub Pages
               is turned on for the repo; serves .mp4 as video/mp4)
   Images try raw, then jsDelivr. Videos try jsDelivr, then raw.
   Override with config.json → "media_hosts": {"image": [...], "video": [...]}.
2. Before Instagram is called, every file is downloaded IN FULL from that
   host, twice in a row, and must come back with status 200, an acceptable
   content type and exactly the size of the local file. This also forces
   jsDelivr to fetch and cache the whole file.
3. If Instagram still fails (download error 2207052, or a video container
   ending in ERROR), the draft container is created again after a pause,
   then from the next host. Retrying a container is safe: containers are
   drafts, nothing is posted until media_publish, which is never retried.
"""
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_HOSTS = {"image": ["raw", "jsdelivr"], "video": ["jsdelivr", "raw"]}
PAUSES = {"image": (0, 60), "video": (0, 120)}          # per host: 1st try, 2nd try
READY_TIMEOUT = {"image": 240, "video": 420}             # seconds to wait for a host

# Instagram error subcodes that mean "I couldn't download the media".
# 2207052: media download failed / URI doesn't meet requirements
# 2207003: download took too long
DOWNLOAD_ERRORS = ("2207052", "2207003", "Media download has failed", "media download")


class PublishFailed(Exception):
    """Raised when every attempt failed. `attempts` lists what was tried."""

    def __init__(self, message, attempts, last_url=""):
        super().__init__(message)
        self.attempts = attempts
        self.last_url = last_url


def url_for(host, repo, sha, rel_file):
    if host == "raw":
        return f"https://raw.githubusercontent.com/{repo}/{sha}/{rel_file}"
    if host == "jsdelivr":
        return f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{rel_file}"
    if host == "pages":
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/{rel_file}"
    raise ValueError(f"unknown media host '{host}'")


def hosts_for(kind, config):
    custom = (config.get("media_hosts") or {}).get(kind)
    return list(custom) if custom else list(DEFAULT_HOSTS[kind])


def type_ok(kind, url, ctype):
    if kind == "image":
        return ctype.startswith("image/jpeg")
    if ctype.startswith("video/"):
        return True
    # raw.githubusercontent.com only knows .mp4 as a generic binary
    return "raw.githubusercontent.com" in url and ctype.startswith("application/octet-stream")


def probe(url, kind, expected_size=None, timeout=180):
    """Downloads the whole file once. Returns (status, detail): status is 'ok',
    'bad' (Instagram would fail too) or 'unknown' (can't be checked from here)."""
    try:
        req = urllib.request.Request(url, method="GET", headers={
            "Cache-Control": "no-cache",
            "User-Agent": "coffee-autopost-check/1.1",
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = r.headers.get("Content-Type", "")
            if r.status != 200:
                return "bad", f"HTTP {r.status}"
            size = 0
            while True:
                chunk = r.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
            if not type_ok(kind, url, ctype):
                return "bad", f"content type '{ctype}'"
            if expected_size is not None and size != expected_size:
                return "bad", f"{size} bytes instead of {expected_size}"
            return "ok", f"{ctype}, {size} bytes"
    except urllib.error.HTTPError as e:
        return "bad", f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return "unknown", f"can't verify from here ({e.__class__.__name__})"


def wait_until_ready(urls, kind, sizes=None, rounds=2, pause=15, max_seconds=None, log=print):
    """Waits until every URL is downloaded in full, correctly, `rounds` times in
    a row. Returns 'ok', 'unknown' (this network can't reach the host: go ahead
    and let Instagram try) or 'bad' (still failing after max_seconds)."""
    max_seconds = max_seconds or READY_TIMEOUT[kind]
    sizes = sizes or [None] * len(urls)
    start = time.time()
    streak = 0
    while True:
        results = [probe(u, kind, s) for u, s in zip(urls, sizes)]
        states = {st for st, _ in results}
        if states == {"unknown"}:
            log(f"  can't check {urls[0].split('/')[2]} from here: going ahead")
            return "unknown"
        if states <= {"ok", "unknown"}:
            streak += 1
            if streak >= rounds:
                return "ok"
        else:
            streak = 0
            bad = [(u.rsplit('/', 1)[-1], d) for u, (st, d) in zip(urls, results) if st == "bad"]
            log(f"  not ready yet: {', '.join(f'{n} {d}' for n, d in bad)}")
        if time.time() - start > max_seconds:
            return "bad"
        time.sleep(pause if streak else 30)


def is_download_error(err):
    text = str(err)
    return any(code in text for code in DOWNLOAD_ERRORS)


def create_with_retry(create, files, kind, repo, sha, config, root=None, log=print, retryable=None):
    """Runs create(urls) until Instagram accepts the media. `urls` are the public
    URLs of `files` (paths relative to the repo root `root`) on one host.

    For each host in order: check it serves the files (see wait_until_ready),
    try, wait (60 s for images, 120 s for videos), try again, then go to the
    next host. Only download errors are retried (or what `retryable(err)`
    accepts); any other error is raised at once.
    Returns (result, host, urls, attempts). Raises PublishFailed if all fail."""
    sizes = [Path(root, f).stat().st_size for f in files] if root else None
    attempts = []
    last_url = ""
    for host in hosts_for(kind, config):
        urls = [url_for(host, repo, sha, f) for f in files]
        last_url = urls[0]
        log(f"Checking {host} ({len(urls)} file{'s' if len(urls) > 1 else ''}, full download)…")
        ready = wait_until_ready(urls, kind, sizes, log=log)
        if ready == "bad":
            log(f"  {host} is not serving the files correctly: next host")
            attempts.append({"host": host, "result": "not served correctly"})
            continue
        for pause in PAUSES[kind]:
            if pause:
                log(f"  waiting {pause} s before trying again…")
                time.sleep(pause)
            log(f"Attempt {len(attempts) + 1}: Instagram downloads from {host}")
            try:
                result = create(urls)
                attempts.append({"host": host, "result": "ok"})
                return result, host, urls, attempts
            except Exception as e:  # noqa: BLE001
                if not (retryable or is_download_error)(e):
                    raise
                attempts.append({"host": host, "result": str(e)[:160]})
                log(f"  Instagram couldn't use the media from {host}: {str(e)[:120]}")
    summary = "; ".join(f"{a['host']}: {a['result']}" for a in attempts)
    raise PublishFailed(f"all hosts failed ({summary})", attempts, last_url)
