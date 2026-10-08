# Coffee Autopost

A system that automatically publishes Instagram carousels starting from one row in a Google Sheet.
You write the idea (in Italian), a Claude Code routine does the rest: English copy, design, publishing.

```
Google Sheet (ideas, in Italian) ──► Claude routine (Mon · Wed · Fri, evening)
                                       │  picks the idea, writes slides and caption in US English
                                       │  renders the slides (HTML template → JPEG)
                                       │  saves them to GitHub (public repo)
                                       └► Instagram API ──► carousel published
```

Cost: nothing beyond the Claude Pro subscription. Each run uses part of the plan's usage limits, like a regular session.

---

## What's in the folder

| Path | Contents |
|---|---|
| `guide/style-guide.md` | Voice, fact rules, carousel structure. **The most important file: edit it as much as you like.** |
| `template/carousel.html` | The design. Open it in a browser to preview; colors and sizes are variables at the top of the file. |
| `template/fonts/` | Archivo Black (titles) and Archivo Narrow (body text), OFL license, free for commercial use too. |
| `posts/example-moka/` | A complete example carousel: JSON, caption and images. |
| `scripts/render.py` | Turns `carousel.json` into 1080×1350 JPEG images. |
| `scripts/publish.py` | Publishes the carousel to Instagram. |
| `scripts/log.py` | Tracks which ideas have been used (`log.json`). |
| `scripts/refresh_token.py` | Refreshes the Instagram token (run it about every 50 days). |
| `CLAUDE.md` | The procedure Claude follows on every run. |
| `ROUTINE-PROMPT.txt` | The text to paste into the routine. |
| `setup-environment.sh` | The script to paste into the cloud environment. |
| `config.json` | Handle, mode (`preview` / `publish`), sheet ID, repo. |
| `highlights/highlights.json` | Text of the evergreen highlight stories (Start, Moka, Espresso, Gear, Q&A). |
| `template/story.html`, `template/highlight-cover.html` | Design of the stories (1080×1920) and of the highlight covers. |
| `scripts/render_highlights.py` | Turns `highlights.json` into PNG stories and covers in `highlights/out/`. |

**Ideas sheet:** [Autopost Caffè – Idee](https://docs.google.com/spreadsheets/d/1Osn--FyHY-qSU6iafApyH9PRawN3fmOYrlK0VaShaEE/edit). It already has 10 test ideas, in Italian.
Columns: `ID` (unique number, never reused), `Idea`, `Note e fonti` (optional notes and sources, they override what Claude "knows"), `Rubrica` (optional series, Italian names are mapped in the guide), `Stato` (empty = to do, `salta` = skip it).

---

## Setup, step by step

### 1. Adjust the design and the guide (optional but recommended)
- Open `template/carousel.html` in a browser: you'll see every slide of the example carousel.
- Change colors/sizes in the `:root` variables at the top of the file and reload the page.
- Reread `guide/style-guide.md` and fix anything that doesn't sound like you.

### 2. Create the GitHub repository (public)
The repo **must be public**: Instagram downloads the images from a public address (through jsDelivr, which serves files from public GitHub repos).
There are no secrets in the repo: the Instagram token never lives here.

```powershell
cd "D:\Lavoro\AI Related\Autopost\coffee-autopost"
git init -b main
git add .
git commit -m "First commit"
git remote add origin https://github.com/WiktorVerga/coffee_extracts.git
git push -u origin main
```
Then in `config.json` replace `YOUR-USERNAME/coffee-autopost` with your `user/repo` and `@yourpage` with the real handle.

### 3. Create the Instagram account
1. A new Instagram account for the test page.
2. Settings → Account type → switch to a **professional account** (Creator or Business).

### 4. Create the app on Meta for Developers and get the token
> Meta renames its menus often: if something doesn't match, look for the equivalent item.

1. Go to developers.facebook.com → **My Apps** → **Create App**.
2. Pick the use case for managing content/messages on **Instagram**.
3. In the Instagram product open **"API setup with Instagram login"** (no Facebook Page needed).
4. In **App roles → Roles** add your Instagram account as a **tester**, then accept the invite in the Instagram app (Settings → Website permissions / Apps and websites → Tester invites).
5. Back in the API setup, click **Generate token** next to your account. Grant the basic and **content publishing** permissions (`instagram_business_basic`, `instagram_business_content_publish`).
6. Copy the token and keep it somewhere safe. Write today's date in `config.json` → `token_refreshed_on`.

For posting to your own account only, Meta's app review shouldn't be needed, but **that's not guaranteed**: if calls fail because of permissions, the error message will say so.

**Quick token check** (PowerShell):
```powershell
Invoke-RestMethod "https://graph.instagram.com/v24.0/me?fields=user_id,username&access_token=YOUR-TOKEN"
```
It should return your username.

### 5. Test locally (recommended)
```powershell
pip install playwright
python -m playwright install chromium
python scripts/render.py posts/example-moka
$env:IG_ACCESS_TOKEN = "YOUR-TOKEN"
python scripts/publish.py posts/example-moka --sha (git rev-parse HEAD) --id 0 --idea "Example" --dry-run
```
`--dry-run` checks images and caption without publishing. If you want a first real post, drop `--dry-run` (it will be logged with ID 0).

### 6. Set up the cloud environment
On **claude.ai/code** → environment selector → create a new environment (e.g. `autopost`):
1. **Network access** → **Custom**, tick *Also include default list of common package managers* and add:
   ```
   cdn.jsdelivr.net
   cdn.playwright.dev
   playwright.download.prss.microsoft.com
   playwright.azureedge.net
   ```
   Instagram downloads the images from `raw.githubusercontent.com` (already in the default list) and the videos from `cdn.jsdelivr.net`; each one is the other's fallback. The logic is in `scripts/media_host.py`.
2. **Setup script**: paste the contents of `setup-environment.sh`.
3. Save, then reopen the environment for editing → **API credentials** → **Add credential**:
   - type **Bearer**, name `Instagram`, host `graph.instagram.com`, value = the token.
   Anthropic's proxy adds the token to requests going to Instagram: Claude and the scripts never see it.
4. **Check it:** start a session in that environment on your repo and ask Claude:
   *"Run `curl -s 'https://graph.instagram.com/v24.0/me?fields=username'` and tell me the response."*
   If it returns your username, you're set.
   If it says the token is missing, use plan B: add `IG_ACCESS_TOKEN=YOUR-TOKEN` to the environment's **Environment variables** (visible only to people using the environment, which is just you).

### 7. Create the routine
On **claude.ai/code/routines** → **New routine**:
- **Name:** Coffee Autopost
- **Prompt:** paste `ROUTINE-PROMPT.txt` (Sonnet is a good model choice, it uses less of your limits)
- **Repository:** your `coffee-autopost`
- **Environment:** `autopost`
- **Connectors:** keep **only Google Drive**, remove all the others
- **Trigger:** schedule. Monday, Wednesday and Friday at 6:37 PM (a few minutes past the hour starts more reliably).
  If the form doesn't let you pick days, create a daily routine and then from Claude Code (terminal) run `/schedule update` with the cron `37 18 * * 1,3,5`.

Hit **Run now** for a first test. The run page shows everything Claude did.
To publish a specific idea right away: **Run now** with the text `ID: 5`.

### 8. Preview mode → publishing
- At first `config.json` has `"mode": "preview"`: the routine creates the carousel in `posts/…` on GitHub but **doesn't publish**. Each run tries a new idea.
- When you're happy: change it to `"mode": "publish"`, commit and push. From the next run it publishes for real (including the ideas that were only previewed).

### 9. Maintenance
- **About every 50 days:** refresh the token with `scripts/refresh_token.py`, replace the API credential and update `token_refreshed_on`. The routine summary warns you when it's due.
- **Ideas:** add rows to the sheet with a new ID. No need to mark anything: the log already knows what's been used.
- **Design and voice:** edit `template/` and `guide/`, commit and push. Changes apply from the next post.

---

## Highlights (stories and covers, uploaded by hand)

The highlights are a fixed, evergreen set: you create them once and update them when something changes. They are **not** part of the routine and are **not** published automatically, so you can add Instagram stickers (link, poll, question) when you upload them.

**Make the images**
```powershell
python scripts/render_highlights.py            # every group
python scripts/render_highlights.py qa         # only one group (covers are always rebuilt)
```
Output in `highlights/out/`:
- `covers/01-start.png` … `05-qa.png`: one cover per group
- `01-start/story-01.png` …: the stories of each group, in order

**Edit the text** in `highlights/highlights.json` (US English, same rules as the guide). Each group has `id`, `name`, `icon` and a list of `frames`. Frame types and limits:

| Type | Fields | Limits |
|---|---|---|
| `cover` | kicker, title, subtitle | 4 / 8 / 14 words |
| `text` | title, body, source (optional) | 7 / 40 words |
| `number` | number, unit, body, source | number ≤ 6 characters, body 25 words |
| `list` | title, items (label + note), source (optional) | title 6 words, 2–5 items, label 4 / note 8 words |
| `steps` | title, steps | title 6 words, 3–5 steps of 12 words |
| `qa` | question, answer | 16 / 35 words |
| `tip` | body (label optional) | 25 words |
| `sticker` | title, body | 7 / 16 words, leaves an empty area for a sticker |
| `closing` | title, body, cta | 8 / 20 / 5 words |

To answer a new question, add a `qa` frame to the `qa` group and re-render only that group.
To change colors, fonts or icons, edit `template/story.html` and `template/highlight-cover.html` (open them in a browser to preview: the dashed lines show the areas Instagram covers and where the sticker goes; they don't appear in the images).

**Upload them (Instagram app)**
1. Post the stories of one group, in order. On the `sticker` frames, add the sticker in the empty area (poll, question or link).
2. Once posted, open your profile → **New** (the + under the bio) → select that group's stories → name it (Start, Moka, Espresso, Gear, Q&A) → **Edit cover** → pick the matching image from `covers/`.
3. Repeat for each group. To add stories to an existing highlight later: open the story → **Highlight** → pick the group.

## Animated reel of every post

Every carousel also gets a **30-second animated reel** with the same content and the same look: the slides animate in 9:16 with wipes between them, the voice `af_heart` (HyperFrames TTS, Kokoro) reads a short spoken version of each slide, every transition has a sound effect, and a track from `music/` plays under the voice. It is built and published by the **same routine** as the carousel (steps 5b and 7b of `CLAUDE.md`, details in `REEL-ANIMATED.md`), fully on its own. It is separate from the Tuesday/Thursday YouTube reels below, which stay as they are.

| File | What it is |
|---|---|
| `REEL-ANIMATED.md` | The procedure for the routine (narration rules, build, caption, publish). |
| `scripts/reel_animated/build_reel.py` | Voice, timing (fits 30 s), audio mix, layout check, HyperFrames render. |
| `scripts/reel_animated/make_sfx.py`, `sfx/` | The built-in sound effects, synthesized (no licenses). |
| `sfx/custom/` | **Your own sound effects.** Name each file after where it is used (`transition-whoosh-1.wav`, `scene-impact.wav`, `text-pop.wav`, `cta-chime.mp3`...): the routine reads the name. Rules in `sfx/custom/README.md`. |
| `template/reel/reel.html` | The 9:16 template. Colors, fonts and slide design come from `template/carousel.html`, so a change there changes both. |
| `music/` | **Your tracks.** Format and rules in `music/README.md`. |
| `scripts/publish_post_reel.py` | Publishes the reel (same Instagram API and token as the carousel). |
| `config.json` → `reel_animated` | `mode` (`preview` / `publish`), voice, length. |

**Setup (once):** paste the updated `setup-environment.sh` into the cloud environment (it installs the voice model, ffmpeg and HyperFrames), put some tracks in `music/` and push. `reel_animated.mode` starts as `preview`: the reel files are created on GitHub (`posts/<folder>/reel.mp4`) but not published. When the previews look right, change it to `"publish"`.

**Test on your PC:** write `reel.json` in a post folder (see `REEL-ANIMATED.md`) and run `python3 scripts/reel_animated/build_reel.py posts/<folder>` (needs Python with `numpy`, `playwright` and `kokoro-onnx`, Node 22, ffmpeg).

**Weight:** each `reel.mp4` is about 15 MB and stays in the repository (Instagram downloads it from GitHub through jsDelivr). Delete the `reel.mp4` of old posts from time to time if the repository grows too much.

## Reels (clips from YouTube, CC BY)

Short clips of other creators' YouTube videos, only with a **Creative Commons Attribution** license, always credited. Published on **Tuesday and Thursday** by a second routine.

```
"Idee Reel" sheet tab ──► run-reels.bat on your PC ──► reels/<ID>-<slug>/ on GitHub
 (link + start + end)      license check, download,         │
                           Whisper subtitles, 9:16 video     ▼
                                              Reels routine (Tue · Thu, evening)
                                              caption + attribution ──► Instagram
```

Why the PC: YouTube blocks cloud servers, and Whisper needs your GPU. The cloud routine never downloads anything.

| File | What it is |
|---|---|
| `REELS.md` | The reels routine procedure (like `CLAUDE.md` for carousels). |
| `scripts/prepare_reels.py` | Runs on your PC: sheet → license check → clip → subtitles → `reels/`. |
| `scripts/publish_reel.py` | Publishes one reel (used by the routine). |
| `scripts/reels_log.py` / `reels-log.json` | Which reels were used (separate from the carousel log). |
| `setup-reels.bat` | One-time setup of the tools in `.venv\` (about 3 GB). |
| `run-reels.bat` | Double-click after adding rows to the sheet. |
| `ROUTINE-REELS-PROMPT.txt` | The text to paste into the reels routine. |

**Disk:** everything stays in the project folder. Python packages (ffmpeg, Deno, Whisper, NVIDIA libraries) go in `.venv\`; temp files, caches and the Whisper model (~1.6 GB) in `.reels\`. Both are ignored by git. The bat files redirect TEMP, APPDATA and every cache, and the script refuses to run if the project is on C:.

### Setup (once)
1. In the Google Sheet, add a tab **Idee Reel** with columns `ID | Link YouTube | Inizio (mm:ss) | Fine (mm:ss) | Note (facoltative) | Stato`. Set columns C and D to **Format → Number → Plain text**.
2. Share the sheet: **Share → General access → Anyone with the link → Viewer** (the script reads it without logging in).
3. Double-click `setup-reels.bat`. At the end it runs a check: every line should say `[ok]`.
4. Create a second routine on claude.ai/code/routines: prompt = `ROUTINE-REELS-PROMPT.txt`, environment `autopost`, schedule Tuesday and Thursday at 6:37 PM (cron `37 18 * * 2,4`).

### Every week
1. Add rows to **Idee Reel** (one row per clip; a long video can have several rows). 5–90 seconds per clip. Clips with speech must be in English (they get subtitles); clips without speech get no subtitles: write in the notes what they show, the routine uses it for the caption.
2. Double-click `run-reels.bat`. Rejected rows are listed with the reason (not CC BY, not English, wrong times…).
3. The routine publishes the ready reels, lowest ID first. `reels.mode` in `config.json` starts as `preview`: switch it to `publish` when the previews look right.

Options: `run-reels.bat --dry-run` (no push), `--only 3`, `--retry` (retry rejected rows), `--check`.

**Watch out:** if the original video has music, Instagram may mute or block the reel even with a CC BY license. Prefer clips with speech only. Downloading from YouTube with external tools is against YouTube's terms of service (a contractual rule, not copyright).

## Limits and things to watch
- Routines are in *research preview*: behavior and limits may change.
- Rendering needs Chromium. If the download in the setup script fails, the script tries a system Chrome; if that fails too, the run stops with a clear error.
- If the sheet gets very long, the connector might read only part of it: the procedure checks for this and downloads the full CSV in that case. Moving old ideas to another tab now and then helps.
- Highlights can't be created or edited through the Instagram API: that part is always manual.
- No human review in `publish` mode: that's why the guide bans invented facts, health claims, brands and stereotypes.
