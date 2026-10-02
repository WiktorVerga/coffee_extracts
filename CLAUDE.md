# Coffee Autopost — instructions for Claude

This repository publishes Instagram carousels about Italian coffee, in US English, automatically.
Every routine run follows the procedure below **exactly** and produces **at most one post**.

## Files to know

| File | Purpose | Can it change during a run? |
|---|---|---|
| `guide/style-guide.md` | voice, fact rules, carousel structure | **No** |
| `config.json` | handle, mode (`preview` or `publish`), sheet ID, repo | **No** |
| `template/carousel.html` | slide design | **No** |
| `scripts/*.py` | render, publish, log | **No** |
| `log.json` | history of used ideas | Only through `scripts/log.py` |
| `posts/YYYY-MM-DD-slug/` | one post: `carousel.json`, `caption.txt`, `slide-XX.jpg` | Yes, this is your output |

Full example of a valid post: `posts/example-moka/`.

## The ideas sheet is in Italian

The owner writes ideas **in Italian**. Columns: `ID`, `Idea`, `Note e fonti (facoltative)` (notes and sources, optional), `Rubrica (facoltativa)` (series, optional, Italian names mapped in the guide, section 6), `Stato` (status: empty = to do, `salta` = skip it).
Read the idea and notes as a brief, then write the post in **US English** following the guide. Never translate word for word.

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

### 3. Write the post
1. Create the folder `posts/<today YYYY-MM-DD>-<short English slug>/`.
2. Write `carousel.json` in this shape (slide types and word limits are in the guide, section 5):

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
3. Write `caption.txt` following section 7 of the guide, including the "Sources:" line.

### 3b. Find the sources
Every figure or fact in the slides and caption needs a source (guide, section 4).
1. Use the sources in the sheet's notes column first.
2. Otherwise search the web for a reliable source (specialty coffee associations, manufacturers' manuals, universities, established coffee publications). Avoid forums and anonymous blogs.
3. If you can't find a reliable source for something, remove it from the post. If the post doesn't hold up without it, skip the idea (step 2).

### 4. Render the images
`python3 scripts/render.py posts/<folder>`
- exit **0**: continue
- exit **2**: read the messages, **shorten the text** in `carousel.json` (don't touch the template) and try again. 3 attempts max.
- exit **3**, or 3 failed attempts: log `--status error` with the reason, commit and push, stop.

### 5. Check the result
1. Look at **every** `slide-XX.jpg` with the Read tool: readable text, no awkward line breaks, no overlaps.
2. Go through the guide's checklist (section 8) for the slides and the caption.
3. If anything is off, fix it and go back to step 4.

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
- outcome: preview created / published (with link) / skipped / error (with reason)
- if `token_refreshed_on` in `config.json` is older than 50 days or not filled in: **"WARNING: refresh the Instagram token"**

## Fixed rules
- Never print, save or commit tokens or keys.
- Never edit the guide, the template, the scripts or `config.json`.
- Never publish more than one post per run.
- Never publish if a check in steps 4–5 didn't pass.
