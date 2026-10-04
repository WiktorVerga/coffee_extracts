# Coffee Autopost — instructions for Claude

This repository publishes Instagram carousels about Italian coffee, in US English, automatically.
Every routine run follows the procedure below **exactly** and produces **at most one post**.

> **Reels:** the reels routine (Tuesday and Thursday) follows `REELS.md` instead of this procedure. The carousel routine described here never touches `reels/`, `reels-log.json` or the reels scripts.

## Files to know

| File | Purpose | Can it change during a run? |
|---|---|---|
| `guide/style-guide.md` | voice, fact rules, carousel structure | **No** |
| `config.json` | handle, mode (`preview` or `publish`), sheet ID, repo | **No** |
| `template/carousel.html` | slide design | **No** |
| `scripts/*.py` | render, publish, log | **No** |
| `log.json` | history of used ideas | Only through `scripts/log.py` |
| `posts/YYYY-MM-DD-slug/` | one post: `carousel.json`, `caption.txt`, `slide-XX.jpg` | Yes, this is your output |
| `highlights/`, `template/story.html`, `template/highlight-cover.html`, `scripts/render_highlights.py` | evergreen highlight stories, made and uploaded by hand by the owner | **No: the routine never touches them** |
| `REELS.md`, `reels/`, `reels-log.json`, `scripts/prepare_reels.py`, `scripts/publish_reel.py`, `scripts/reels_log.py`, `*.bat` | reels (clips from YouTube), handled by the reels routine and the owner's PC | **No: the carousel routine never touches them** |

Full example of a valid post: `posts/example-moka/`.

## The ideas sheet is in Italian

The owner writes ideas **in Italian**. Columns: `ID`, `Idea`, `Note e fonti (facoltative)` (notes and sources, optional), `Rubrica (facoltativa)` (series, optional, Italian names mapped in the guide, section 6), `Stato` (status: empty = to do, `salta` = skip it).
The sheet has two tabs: use **only "Idee Post"**. Ignore "Idee Reel" (it belongs to the reels routine); if the connector returns both tables, read the one whose columns are the ones above.
Read the idea and notes as a brief, then write the post in **US English** following the guide. Never translate word for word.

## Instagram skills (used in steps 3, 3c, 3d and 5)

Three skills raise the quality of the post. Call each one with the Skill tool, at the step that names it, and not before.

| Skill | Step | What it does for this project |
|---|---|---|
| `ig-carousel-planner` | 3 | plans the carousel: formula, slide order, what goes on each slide |
| `ig-caption-writer` | 3c | writes the caption: hook, body, call to action, voice scrub |
| `ig-hashtag-strategist` | 3d | picks the hashtag set, sized and matched to the content |

Rules for using them in a routine run (nobody is there to answer questions):

1. **The guide wins.** If a skill's advice contradicts `guide/style-guide.md` or this file, follow the guide. Known cases: no emoji, no brands or company names (even as the "named entity" a skill asks for), a number only if it is widely accepted and sourced, the caption structure and "Sources:" line (guide, section 7), the slide types and word limits (guide, section 5), the base hashtag list.
2. **Draft only. Never let a skill publish.** Do not run their publishing steps: `lib.publish`, Publora, media upload, scheduling, `lib.illustrate`. Publishing happens only in step 7, through `scripts/publish.py`.
3. **No questions, no approval card.** Skip the skills' "gather inputs" questions and "approval card" steps. Choose the goal and the formula yourself (below) and report them in the final summary.
4. **Never invent specifics.** If a skill asks for a figure, date or example you don't have from the sheet or a reliable source, leave it out.
5. Don't call any other skill (for example `ig-humanizer`), and ignore a skill's suggestion to fill in a voice profile.
6. **If a skill is missing or fails**, continue with the guide alone and write "Skill not available: <name>" in the final summary. Don't stop the run.

**Goal:** `saves` for How-to, Side by side, Inside the cup, One word; `shares` for Myth or fact and Common mistake. If there is no series, pick by content.
**Formulas allowed:** IG1 (only with a sourced number), IG2, IG3, IG5, IG7, IG8. **Never** IG4 and IG6: they need a personal story or result, and the page has none. Pick the one that fits the series (e.g. Myth or fact → IG7, How-to → IG5 or IG8).

## Procedure

### 0. Prepare
1. Read `config.json` and **all** of `guide/style-guide.md`.
2. Check the renderer works: `python3 -c "import playwright"`. If it's missing, run
   `pip install --break-system-packages playwright && python3 -m playwright install --with-deps chromium`.

### 1. Pick the idea
1. If the `routine-fire-payload` block contains an ID (e.g. "ID: 7"), use that idea and jump to step 2.
2. Read the Google Sheet with the Google Drive connector (`read_file_content`, ID in `config.json` → `google_sheet_id`).
   Check that the number of rows you read matches the "Table Range": if only part of the sheet came back, download it as CSV with `download_file_content` and use that.
3. Get the IDs already used:
   - `preview` mode: `python3 scripts/log.py used --include-previews`
   - `publish` mode: `python3 scripts/log.py used`
4. Candidates = rows with an empty *Stato* column and an ID not already used, in ascending ID order.
5. Look at `python3 scripts/log.py recent 3`: if the first candidate has the same series as the last post and one of the next two candidates has a different series, use that one.
6. If there are no candidates: **stop** without creating anything. In the final summary write "No ideas available in the sheet".

### 2. Evaluate the idea
Reread section 4 of the guide ("Fact rules"). If the idea can't be covered while following them:
`python3 scripts/log.py add --id <ID> --idea "<text>" --status skipped --reason "<why>"`
and go back to step 1 with the next candidate (at most 3 attempts per run).

### 3. Plan and write the carousel
1. Create the folder `posts/<today YYYY-MM-DD>-<short English slug>/`.
2. **Plan with `ig-carousel-planner`** (draft only, see "Instagram skills"). Give it the idea translated into English, the sheet's notes, the series, the goal and the formula. Ask for the slide-by-slide outline, and map every slide to one of the guide's slide types. The plan must respect:
   - slide 1 is a promise with an open loop, never a bare title (cover title ≤ 8 words)
   - the strongest point sits on slide 2 or 3, one point per slide, readable in 2 seconds
   - the number of slides matches the real content (guide, section 5): never pad
   - the last slide recaps in one sentence and has a single ask
3. Write `carousel.json` from the plan, in this shape (slide types and word limits are in the guide, section 5):

```json
{
  "series": "How-to",
  "slides": [
    { "type": "cover", "kicker": "...", "title": "...", "subtitle": "..." },
    { "type": "text", "title": "...", "body": "...", "highlight": "..." },
    { "type": "number", "number": "1.5", "unit": "bar", "caption": "..." },
    { "type": "steps", "title": "...", "steps": ["...", "...", "..."] },
    { "type": "compare", "title": "...", "left": { "label": "...", "points": ["...", "..."] }, "right": { "label": "...", "points": ["...", "..."] } },
    { "type": "myth", "myth": "...", "verdict": "false", "truth": "..." },
    { "type": "tip", "label": "The tip", "body": "..." },
    { "type": "closing", "title": "...", "body": "...", "cta": "..." }
  ]
}
```
   Optional fields: `kicker`, `subtitle`, `highlight`, `unit`, the `title` of `number`, `body` and `cta` of `closing`.

### 3b. Find the sources
Every figure or fact in the slides and caption needs a source (guide, section 4).
1. Use the sources in the sheet's notes column first.
2. Otherwise search the web for a reliable source (specialty coffee associations, manufacturers' manuals, universities, established coffee publications). Avoid forums and anonymous blogs.
3. If you can't find a reliable source for something, remove it from the post (and from `carousel.json`). If the post doesn't hold up without it, skip the idea (step 2).

### 3c. Write the caption
Use **`ig-caption-writer`** (draft only, see "Instagram skills") to write `caption.txt`, in the structure of guide section 7:
- the hook (first line, ≤ 125 characters) must make sense on its own and promise something specific, different from the cover title
- body: one idea, short lines, adds something the slides don't say
- one closing question, specific to the topic, as the only call to action (not "what do you think?", no engagement bait)
- apply the skill's voice scrub (no cluster of AI-sounding words, few em dashes, no "The result?" or "Here's the thing" style reveals) together with the guide's banned words
- "Sources:" line as in the guide, using only sources found in step 3b

### 3d. Choose the hashtags
Use **`ig-hashtag-strategist`** (draft only) on the finished caption. Keep guide section 7's frame: 3–5 hashtags, 2 from the base list plus 1–3 specific ones.
- the strategist chooses which base tags and which specific ones, sized for a small account: prefer niche and mid-size tags, at most one broad tag in total
- every tag must describe the actual content; no engagement-farm tags
- vary them: read `caption.txt` of the last 3 folders in `posts/` (skip `example-moka`) and don't repeat the same specific tags
- add them as the last line of `caption.txt`

### 4. Render the images
`python3 scripts/render.py posts/<folder>`
- exit **0**: continue
- exit **2**: read the messages, **shorten the text** in `carousel.json` (don't touch the template) and try again. 3 attempts max.
- exit **3**, or 3 failed attempts: log `--status error` with the reason, commit and push, stop.

### 5. Check the result
1. Look at **every** `slide-XX.jpg` with the Read tool: readable text, no awkward line breaks, no overlaps.
2. Go through the guide's checklist (section 8) for the slides and the caption.
3. **Quality gate** (this is the last check before saving and before any publishing). Reread the carousel, caption and hashtags once more with the three skills' criteria:
   - *Carousel:* slide 1 is a promise with an open loop; the best point is early; one idea per slide; no padding; the last slide has a recap and a single ask.
   - *Caption:* the hook stands alone in 125 characters; one idea; one specific call to action; no engagement bait; no AI-sounding phrasing.
   - *Hashtags:* 3–5, all on-topic, at most one broad, different from the last 3 posts.
4. If anything is off, fix it and go back to step 4 (re-render if the slides changed). Don't go on while a point of the quality gate fails.

### 6. Save to GitHub
Work directly on `main` (don't create `claude/...` branches).
```
git add posts/<folder>
git commit -m "Post: <cover title>"
git push origin HEAD:main
```

### 7. Publish (`publish` mode only)
- **`preview` mode**: don't publish. Run
  `python3 scripts/log.py add --id <ID> --idea "<text>" --series "<series>" --folder posts/<folder> --status preview`,
  then commit and push `log.json`. Done.
- **`publish` mode**:
  1. `SHA=$(git rev-parse HEAD)` (the commit with the images, already pushed)
  2. `python3 scripts/publish.py posts/<folder> --sha $SHA --id <ID> --idea "<text>" --series "<series>"`
     (the script updates `log.json` itself)
  3. Commit and push `log.json` and `posts/<folder>/publication.json`, even if it failed.
  4. If the script fails, **don't try to publish again** in the same run: you could create a duplicate. Report the error in the summary.

### 8. Final summary
End the run with a short summary:
- idea used (ID and text), series, number of slides
- goal and formula chosen (e.g. "saves, IG5"), hashtag set with the size of each tag, and any skill that was not available
- outcome: preview created / published (with link) / skipped / error (with reason)
- if `token_refreshed_on` in `config.json` is older than 50 days or not filled in: **"WARNING: refresh the Instagram token"**

## Fixed rules
- Never print, save or commit tokens or keys.
- Never edit the guide, the template, the scripts or `config.json`.
- Never publish more than one post per run.
- Never publish if a check in steps 4–5 (quality gate included) didn't pass.
- The Instagram skills only plan and draft. Never use their publishing features (Publora, `lib.publish`, `lib.illustrate`): only `scripts/publish.py` publishes.
- When a skill and the guide disagree, the guide wins.
