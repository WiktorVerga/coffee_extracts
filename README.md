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

## Limits and things to watch
- Routines are in *research preview*: behavior and limits may change.
- Rendering needs Chromium. If the download in the setup script fails, the script tries a system Chrome; if that fails too, the run stops with a clear error.
- If the sheet gets very long, the connector might read only part of it: the procedure checks for this and downloads the full CSV in that case. Moving old ideas to another tab now and then helps.
- No human review in `publish` mode: that's why the guide bans invented facts, health claims, brands and stereotypes.
