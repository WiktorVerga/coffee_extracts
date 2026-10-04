# Coffee Autopost — Reels routine (instructions for Claude)

This file is for the **reels routine** (Tuesday and Thursday). The carousel routine follows `CLAUDE.md` and never touches `reels/` or `reels-log.json`.

The reels are **clips of other creators' YouTube videos**, licensed **CC BY** (Creative Commons Attribution). The owner picks the moments in the "Idee Reel" sheet tab; his PC (`scripts/prepare_reels.py`) checks the license, cuts the clip, adds subtitles and a credit, and pushes `reels/<ID>-<slug>/` to GitHub. **Your job:** pick the next ready reel, check it, write the caption with the attribution, and publish it.

Every run produces **at most one reel**.

## Files to know

| File | Purpose | Can it change during a run? |
|---|---|---|
| `REELS.md` | this procedure | **No** |
| `guide/style-guide.md` | voice and fact rules (sections 3, 4, 7) | **No** |
| `config.json` | `reels.mode` (`preview` or `publish`), repo | **No** |
| `scripts/*.py` | `reels_log.py`, `publish_reel.py` | **No** |
| `reels-log.json` | history of used reels | Only through `scripts/reels_log.py` |
| `reels/<ID>-<slug>/clip.mp4`, `source.json`, `transcript.txt`, `subtitles.srt`, `frame-1..3.jpg` | made on the owner's PC | **No: never edit or re-encode the video** |
| `reels/<ID>-<slug>/caption.txt` | the caption | Yes, this is your output |

## Instagram skills

Use `ig-caption-writer` (step 3) and `ig-hashtag-strategist` (step 4) with **the same rules as in `CLAUDE.md`, section "Instagram skills"**: the guide wins, draft only, never let a skill publish, no questions or approval cards, never invent specifics, no other skills, if a skill is missing write "Skill not available: <name>" in the summary and go on.

**Goal:** `shares` (a reel is discovery content). **Formulas allowed:** IG2, IG3, IG5, IG7, IG8. Never IG1 (the page adds no numbers of its own), IG4 or IG6.

## Procedure

### 0. Prepare
Read `config.json` (`reels` section) and sections 3, 4 and 7 of `guide/style-guide.md`.

### 1. Pick the reel
1. If the `routine-fire-payload` block contains an ID (e.g. "ID: 3"), use the folder `reels/003-*` and jump to step 2.
2. Otherwise run:
   - `preview` mode: `python3 scripts/reels_log.py ready --include-previews`
   - `publish` mode: `python3 scripts/reels_log.py ready`
3. Take the first line (lowest ID). If the list is empty: **stop** without creating anything; the summary says "No reels ready: add rows to the Idee Reel sheet and run run-reels.bat".

### 2. Check the reel
Read `source.json`, `transcript.txt` and look at `frame-1.jpg`, `frame-2.jpg`, `frame-3.jpg` with the Read tool. Skip the reel if any of these is true:
- `source.json` → `video.license` does not say Creative Commons
- the clip makes **health claims** (guide, rule 6) or is mainly about a **brand or product** (an ad, a review, an unboxing)
- it states something as fact that is clearly wrong or controversial, and the page would be spreading it
- it doesn't make sense on its own (starts or ends mid-thought, refers to "what I showed you earlier")
- the frames show something unrelated to coffee, or anything you wouldn't put on the page

To skip: `python3 scripts/reels_log.py add --id <ID> --title "<video title>" --folder <folder> --status skipped --reason "<why>"`, then go back to step 1 with the next ready reel (at most 3 attempts per run).

### 3. Write the caption
Use **`ig-caption-writer`** (draft only) to write `caption.txt` in the reel folder, in **US English**, following the voice of the guide (section 3) and this structure:

1. **Hook** (first line, ≤ 125 characters): makes sense on its own, says what the viewer will get from the clip. It must not misquote the creator.
2. **Body:** 1–3 short sentences that add context for someone making coffee at home (why it matters, how it relates to the moka pot or home espresso, an Italian angle if it's real). Don't repeat the subtitles.
3. **One closing question**, specific to the topic (no "what do you think?", no engagement bait).
4. A blank line, then the **attribution line**, mandatory (license CC BY), taken from `source.json`:
   `Clip: "<video.title>" by <video.channel> (youtube.com/watch?v=<video.youtube_id>), CC BY 3.0. Trimmed, reframed and subtitled.`
5. Only if the hook or the body adds a fact that is **not** in the clip: a `Sources:` line as in the guide, section 7 (find it as in `CLAUDE.md` step 3b; if you can't, remove the fact).
6. A blank line, then the hashtags (step 4).

Rules:
- **Never imply the creator endorses the page** ("our friend", "as X told us", "in collaboration with"). The creator is credited, nothing more.
- The creator's name and channel are allowed in the attribution line and may be named in the body; any other brand or company: no (guide, rule 7).
- No emoji, none of the guide's banned words, no AI-sounding phrasing. About 900 characters max.

### 4. Choose the hashtags
Use **`ig-hashtag-strategist`** (draft only) on the finished caption: 3–5 hashtags, 2 from the guide's base list plus 1–3 specific ones, sized for a small account, at most one broad tag, all describing the actual clip. Don't repeat the specific tags of the last 3 `caption.txt` files in `reels/`. Add them as the last line.

### 5. Quality gate
- *Clip:* checked in step 2, the subtitles in `subtitles.srt` match what is said (if they are badly wrong, skip the reel with the reason "subtitles wrong").
- *Caption:* the hook stands alone in 125 characters; one idea; one specific question; no engagement bait; attribution line present and complete (title, channel, link with the video ID, CC BY 3.0, "Trimmed, reframed and subtitled").
- *Hashtags:* 3–5, on-topic, at most one broad, different from the last 3 reels.
Fix anything that fails before going on.

### 6. Save to GitHub
Work directly on `main`.
```
git add <folder>/caption.txt
git commit -m "Reel caption: <video title>"
git push origin HEAD:main
```

### 7. Publish (`reels.mode` = `publish` only)
- **`preview` mode:** don't publish. Run
  `python3 scripts/reels_log.py add --id <ID> --title "<video title>" --folder <folder> --status preview`,
  then commit and push `reels-log.json`. Done.
- **`publish` mode:**
  1. `SHA=$(git rev-parse HEAD)` (the commit with the caption, already pushed)
  2. `python3 scripts/publish_reel.py <folder> --sha $SHA` (it updates `reels-log.json` itself)
  3. Commit and push `reels-log.json` and `<folder>/publication.json`, even if it failed.
  4. If the script fails, **don't try again** in the same run: you could create a duplicate. Report the error in the summary.

### 8. Final summary
- reel used (ID, video title, channel, clip length)
- goal and formula, hashtag set with the size of each tag, any skill not available
- outcome: preview created / published (with link) / skipped (with reason) / error (with reason)
- how many reels are still ready (`python3 scripts/reels_log.py ready`); if 0 or 1: "Few reels left: add rows to the Idee Reel sheet and run run-reels.bat"
- if `token_refreshed_on` in `config.json` is older than 50 days or not filled in: **"WARNING: refresh the Instagram token"**

## Fixed rules
- Never print, save or commit tokens or keys.
- Never edit the guide, the scripts, `config.json`, or any file made by the PC (`clip.mp4`, `source.json`, `transcript.txt`, `subtitles.srt`, frames).
- Never publish more than one reel per run, never publish without the attribution line.
- Never try to download from YouTube: it doesn't work from the cloud and it isn't your job.
- When a skill and the guide disagree, the guide wins.
