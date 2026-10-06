#!/usr/bin/env python3
"""
Public URLs for the media Instagram downloads, and the logic that makes those
downloads reliable. Used by publish.py, publish_reel.py and publish_post_reel.py.

Why this exists
---------------
Instagram does not receive our files: it downloads them from a public URL.
With jsDelivr, the first request for a file of a brand-new commit can get a
transient 403 that jsDelivr then caches for about 60 seconds. If Instagram
asks in that window (or through a different CDN node), it fails with error
2207052 "Media download has failed". A curl "warm-up" from the routine's
sandbox only warms the nodes the sandbox reaches, not the ones Meta uses.

What it does
------------
1. Two hosts for the same file of the same commit:
     raw       https://raw.githubusercontent.com/<repo>/<sha>/<path>
               no CDN cache to warm, answers right away; serves .jpg as
               image/jpeg, but .mp4 as application/octet-stream
     jsdelivr  https://cdn.jsdelivr.net/gh/<repo>@<sha>/<path>
               serves .mp4 as video/mp4, but needs time on a new commit
   Images try raw first, videos try jsDelivr first. Override with
   config.json → "media_hosts": {"image": [...], "video": [...]}.
2. Before Instagram is called, every URL must answer 200 with the right
   content type twice in a row, a few seconds apart (a cached 403 doesn't
   pass this check).
3. If Instagram still fails to download (2207052 and similar), the media
   container is created again after a pause, then with the other host.
   Retrying a container is safe: containers are drafts, nothing is posted
   until media_publish, which is never retried.
"""
import time
import urllib.error
import urllib.request

DEFAULT_HOSTS = {"image": ["raw", "jsdelivr"], "video": ["jsdelivr", "raw"]}
EXPECTED_TYPE = {"image": "image/jpeg", "video": "video/"}

# Instagram error subcodes that mean "I couldn't download the media".
# 2207052: media download failed / URI doesn't meet requirements
# 2207003: download took too long
DOWNLOAD_ERRORS = ("2207052", "2207003", "Media download has failed", "media download")


def url_for(host, repo, sha, rel_file):
    if host == "raw":
        return f"https://raw.githubusercontent.com/{repo}/{sha}/{rel_file}"
    if host == "jsdelivr":
        return f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{rel_file}"
    raise ValueError(f"unknown media host '{host}'")


def hosts_for(kind, config):
    custom = (config.get("media_hosts") or {}).get(kind)
    return list(custom) if custom else list(DEFAULT_HOSTS[kind])


def probe(url, kind):
    """Returns (status, detail): status is 'ok', 'bad' (Instagram would fail too)
    or 'unknown' (can't be checked from this network)."""
    try:
        req = urllib.request.Request(url, method="GET", headers={
            "Range": "bytes=0-1023",
            "Cache-Control": "no-cache",
            "User-Agent": "coffee-autopost-check/1.0",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            ctype = r.headers.get("Content-Type", "")
            if r.status not in (200, 206):
                return "bad", f"HTTP {r.status}"
            if not ctype.startswith(EXPECTED_TYPE[kind]):
                return "bad", f"content type '{ctype}'"
            return "ok", ctype
    except urllib.error.HTTPError as e:
        return "bad", f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return "unknown", f"can't verify from here ({e.__class__.__name__})"


def wait_until_ready(urls, kind, rounds=2, pause=10, max_seconds=240, log=print):
    """Waits until every URL answers 'ok' for `rounds` checks in a row.
    Returns 'ok', 'unknown' (network can't reach the host: go ahead and let
    Instagram try) or 'bad' (still failing after max_seconds)."""
    start = time.time()
    streak = 0
    while True:
        results = [probe(u, kind) for u in urls]
        states = {s for s, _ in results}
        if states == {"unknown"}:
            log(f"  can't check {urls[0].split('/')[2]} from here: going ahead")
            return "unknown"
        if states <= {"ok", "unknown"}:
            streak += 1
            if streak >= rounds:
                return "ok"
        else:
            streak = 0
            bad = [(u.rsplit('/', 1)[-1], d) for u, (s, d) in zip(urls, results) if s == "bad"]
            log(f"  not ready yet: {', '.join(f'{n} {d}' for n, d in bad)}")
        if time.time() - start > max_seconds:
            return "bad"
        time.sleep(pause if streak else 30)


def is_download_error(err):
    text = str(err)
    return any(code in text for code in DOWNLOAD_ERRORS)


def create_with_retry(create, files, kind, repo, sha, config, log=print,
                      pauses=(0, 60, 0, 90), retryable=None):
    """Runs create(urls) until Instagram accepts the media, where `urls` are the
    public URLs of `files` (paths relative to the repo) on one host.

    Attempt plan with two hosts A and B: A, A after 60 s, B, B after 90 s.
    Only download errors are retried (or what `retryable(err)` accepts); any
    other error is raised at once.
    Returns (result, host, urls)."""
    hosts = hosts_for(kind, config)
    plan = []
    for h in hosts:
        plan += [h, h]
    last_err = None
    checked = {}
    for attempt, (host, pause) in enumerate(zip(plan, pauses * len(hosts)), 1):
        urls = [url_for(host, repo, sha, f) for f in files]
        if host not in checked:
            log(f"Checking {host} ({len(urls)} file{'s' if len(urls) > 1 else ''})…")
            checked[host] = wait_until_ready(urls, kind, log=log)
            if checked[host] == "bad":
                log(f"  {host} is not serving the files: skipping it")
                last_err = last_err or RuntimeError(f"{host} not serving the files")
                continue
        elif checked[host] == "bad":
            continue
        if pause:
            log(f"  waiting {pause} s before trying again…")
            time.sleep(pause)
        try:
            log(f"Attempt {attempt}: Instagram downloads from {host}")
            return create(urls), host, urls
        except Exception as e:  # noqa: BLE001
            if not (retryable or is_download_error)(e):
                raise
            last_err = e
            log(f"  Instagram couldn't download the media from {host} (attempt {attempt})")
    raise last_err
