#!/usr/bin/env python3
"""
Refreshes your Instagram token (run it on YOUR computer, about every 50 days).

Instagram long-lived tokens expire after about 60 days. This script asks
Instagram for a new token based on the current one.

Usage (Windows PowerShell):
    $env:IG_ACCESS_TOKEN = "your-current-token"
    python scripts/refresh_token.py

Then:
  1. copy the new token printed on screen
  2. on claude.ai/code → environment settings → API credentials:
     delete the Instagram credential and add it again with the new token
  3. update "token_refreshed_on" in config.json
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ.get("IG_ACCESS_TOKEN", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else "")
if not token:
    print(__doc__)
    sys.exit(1)

url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode({
    "grant_type": "ig_refresh_token",
    "access_token": token,
})
try:
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read().decode())
except urllib.error.HTTPError as e:
    print("Error:", e.code, e.read().decode(errors="replace"))
    sys.exit(2)

days = int(data.get("expires_in", 0)) // 86400
print("New token (don't share it):\n")
print(data["access_token"])
print(f"\nExpires in about {days} days.")
