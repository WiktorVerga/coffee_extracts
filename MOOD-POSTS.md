# Coffee Autopost — Mood posts routine (instructions for Claude)

This file is for the **mood posts routine** (Saturday and Sunday). The carousel routine follows `CLAUDE.md`, the reels routine follows `REELS.md`; neither touches `mood-posts/`, and this routine never touches `posts/`, `reels/`, `log.json`, `reels-log.json` or `ab/`.

A mood post is **one image**: one cute drawing and one short line that is motivational, relatable, or a small thought about the reader's day. Coffee is the thread. No facts, tips or numbers. **You write the line yourself**: there is no ideas sheet for these posts.

Every run produces **at most one post**.

## Files to know

| File | Purpose | Can it change during a run? |
|---|---|---|
| `MOOD-POSTS.md` | this procedure | **No** |
| `mood-posts/STYLE.md` | rules for the line and the caption, how to choose theme, layout and drawing, bank of lines | **No** |
| `mood-posts/CONTRACT.md` | technical spec of `post.json` | **No** |
| `guide/style-guide.md` | the page's voice (section 3) and base hashtags (section 7) | **No** |
| `config.json` | `mood_posts.mode` (`preview` or `publish`), repo | **No** |
| `mood-posts/themes.json`, `mood-posts/art/`, `mood-posts/template/`, `mood-posts/scripts/*.py`, `mood-posts/moodboard/` | palettes, drawings, template, scripts, moodboard | **No** |
| `mood-posts/log.json` | history of the mood posts | Only through `mood-posts/scripts/mood_log.py` and `publish.py` |
| `mood-posts/posts/YYYY-MM-DD-slug/` | one post: `post.json`, `caption.txt`, `post.jpg`, `render-report.json` | Yes, this is your output |

## Instagram skills

Use `ig-caption-writer` (step 3) and `ig-hashtag-strategist` (step 3) with **the same rules as in `CLAUDE.md`, section "Instagram skills"**: draft only, never let a skill publish, no questions or approval cards, never invent specifics, no other skills, if a skill is missing write "Skill not available: <name>" in the summary and go on. For these posts **`mood-posts/STYLE.md` wins** over a skill, and over the carousel caption structure of the guide: the caption is 1 to 3 short lines, there is no "Sources:" line, and no formula is needed.

**Goal:** `shares` for a relatable line, `saves` for a motivational line or a small reflection.

## Procedure

### 0. Prepare
1. Read `config.json` (`mood_posts` section), **all** of `mood-posts/STYLE.md`, and section 3 of `guide/style-guide.md`.
2. Check the renderer works: `python3 -c "import playwright"`. If it's missing, run
   `pip install --break-system-packages playwright && python3 -m playwright install --with-deps chromium`.

### 1. Decide what this run publishes
Take the first case that applies.
1. **A post that failed to publish** (`publish` mode only): `python3 mood-posts/scripts/mood_log.py retry`. If it prints a folder, this run publishes the first one again: don't rewrite anything, go straight to step 6.
2. **A folder named in the payload**: if the `routine-fire-payload` block contains a folder (e.g. "FOLDER: 2026-11-21-slow-mornings"), use `mood-posts/posts/<that folder>`. Go to step 5.
3. **A ready-made post in the queue** (the owner made it with `generate.py` and pushed it):
   - `preview` mode: `python3 mood-posts/scripts/mood_log.py queue --include-previews`
   - `publish` mode: `python3 mood-posts/scripts/mood_log.py queue`

   If it prints folders, take the first (the oldest). Don't change its line, theme or drawing. Go to step 5.
4. **Otherwise write a new post**: step 2.

### 2. Write the line
1. `python3 mood-posts/scripts/mood_log.py lines` (every line already used) and `python3 mood-posts/scripts/mood_log.py recent 6` (type, theme, layout and drawing of the last posts).
2. Choose the **type** (`motivational`, `relatable` or `reflection`; STYLE.md, section 1): rotate, never the same type three times in a row.
3. Write **five candidate lines** of that type following STYLE.md, section 2, then keep the best one: the one a reader would send to a friend or save. You may take a line from the bank in STYLE.md, section 6, if it is not in the used list, but prefer a new one. Never repeat or closely rewrite a used line.
4. Choose theme, layout and drawing with STYLE.md, section 3. `python3 mood-posts/scripts/generate.py --list` shows the valid names.

### 3. Caption and hashtags
1. Write the caption with **`ig-caption-writer`** (draft only), following STYLE.md, section 4: 1 to 3 short lines that add something the image doesn't say, then one closing question specific to the line. Apply the skill's voice scrub and the guide's banned words. No emoji, no brands, no claims, no "Sources:" line.
2. Choose 3 to 5 hashtags with **`ig-hashtag-strategist`** (draft only): 2 from the base list of the guide (section 7) plus 1 to 3 specific ones, sized for a small account, at most one broad tag, all describing this post. Read `caption.txt` of the last 3 folders in `mood-posts/posts/` and don't repeat their specific tags. The hashtags are the last line, after a blank line.

### 4. Generate and render
```
python3 mood-posts/scripts/generate.py --text "<line, | for line breaks, *word* for emphasis>" \
    --kind <type> --theme <theme> --layout <layout> --art <drawing or none> --slug <short-english-slug>
```
It creates `mood-posts/posts/<today>-<slug>/` with `post.json` and `post.jpg`. Then write the caption (with the hashtags) to `caption.txt` in that folder.
- exit **0**: continue
- exit **2**: read the messages, then shorten the line, change the line breaks or pick another layout, and run it again with `--force`. 3 attempts max. Never touch the template, the themes or the drawings.
- exit **3**, or 3 failed attempts: stop. Nothing is published; say why in the summary.

### 5. Check the result
1. Look at `post.jpg` with the Read tool: text readable at phone size, no awkward line break or orphan word, drawing complete and not touching the text, nothing near the edges.
2. Go through the checklist in STYLE.md, section 5, for the line, the image and the caption.
3. **Quality gate:** the line is one of the three types and stands on its own; exactly one emphasis; no emoji, brand, health claim, number of cups, hustle cliche or known quote; the caption adds a thought and asks one specific question; 3 to 5 on-topic hashtags, at most one broad.
4. If anything is off in a post you wrote, fix it and render again (step 4). For a ready-made folder (step 1, cases 2 and 3) fix only `caption.txt`; if the image itself fails the check, don't publish it: `python3 mood-posts/scripts/mood_log.py add --folder <folder> --status skipped --reason "<why>"`, commit and push the log, and go back to step 1 (at most 3 attempts per run).

### 6. Save to GitHub
Work directly on `main` (don't create `claude/...` branches).
```
git add mood-posts/posts/<folder>
git commit -m "Mood post: <line>"
git push origin HEAD:main
```
(If nothing changed, as in a retry, there is nothing to commit: go on.)

### 7. Publish (`mood_posts.mode` = `publish` only)
- **`preview` mode:** don't publish. Run
  `python3 mood-posts/scripts/mood_log.py add --folder mood-posts/posts/<folder> --status preview`,
  then commit and push `mood-posts/log.json`. Done.
- **`publish` mode:**
  1. `SHA=$(git rev-parse HEAD)` (the commit with the image, already pushed). Don't "warm" any cache with `curl`: the script checks the public URL itself.
  2. `python3 mood-posts/scripts/publish.py mood-posts/posts/<folder> --sha $SHA` (it updates `mood-posts/log.json` itself)
  3. Commit and push `mood-posts/log.json` and `mood-posts/posts/<folder>/publication.json`, even if it failed.
  4. If the script fails, **don't run it again** in the same run: it has already retried the download on its own, and running it twice could create a duplicate. Report the error: the next run retries the same folder (step 1, case 1).

### 8. Final summary
- the line, its type, theme, layout and drawing; whether it was new, from the bank, from the queue or a retry
- goal, hashtag set with the size of each tag, any skill not available
- outcome: preview created / published (with link) / skipped (with reason) / error (with reason)
- how many ready-made posts are left in the queue
- if `token_refreshed_on` in `config.json` is older than 50 days or not filled in: **"WARNING: refresh the Instagram token"**

## Fixed rules
- Never print, save or commit tokens or keys.
- Never edit `STYLE.md`, `CONTRACT.md`, the themes, the drawings, the template, the scripts or `config.json`.
- Never publish more than one post per run, and never one whose check in step 5 didn't pass.
- Never use a reference line or a well-known quote (STYLE.md, section 2), and never copy or commit the images in `mood-posts/moodboard/refs/`.
- The Instagram skills only draft. Only `mood-posts/scripts/publish.py` publishes.
- When a skill and `STYLE.md` disagree, `STYLE.md` wins.
