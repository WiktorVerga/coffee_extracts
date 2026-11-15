# Mood posts

Single-image posts for @coffee_extracts: one cute drawing, one short line
(motivational, relatable, or a small thought about the day), a lot of empty
space. Separate from the carousels: nothing here is touched by the carousel
or reels routines, and nothing here touches `posts/`, `log.json` or `ab/`.

```
one line of text ──► generate.py ──► post.json ──► render.py ──► post.jpg (1080 × 1350)
                     picks theme,                  HTML template         │
                     layout, drawing               + SVG drawing         ▼
                                              git push ──► publish.py ──► Instagram Graph API
```

## What's in the folder

| Path | Contents |
|---|---|
| `moodboard/moodboard.html` | The moodboard: references, palette, type, drawings, layouts, mock posts. Open it in a browser. `moodboard/refs/` holds the inspiration images, on your PC only (not committed: they belong to other people). |
| `STYLE.md` | Rules for the lines and the captions, how to choose theme, layout and drawing, and a bank of ready lines. |
| `CONTRACT.md` | The technical spec: `post.json` fields, layouts, theme fields, rules for new drawings. |
| `themes.json` | The six palettes with their type style: `espresso`, `mocha`, `latte`, `oat`, `paper`, `caramel`. Edit colors here. |
| `art/*.svg`, `art/index.json` | The drawings, colored by the theme through CSS variables, and their tags. |
| `template/post.html` | The reusable template. Open it in a browser to preview every layout and theme. |
| `scripts/generate.py` | Line of text → post folder with `post.json`, then renders it. |
| `scripts/render.py` | `post.json` → `post.jpg`. |
| `scripts/publish.py` | `post.jpg` + `caption.txt` → Instagram (single image). |
| `scripts/mood_log.py` | The log: lines already used, queue of ready posts, posts to retry. |
| `posts/YYYY-MM-DD-slug/` | One post: `post.json`, `caption.txt`, `post.jpg`, `render-report.json`, and `publication.json` once published. |
| `log.json` | History of previews, publications and errors (written by `mood_log.py` and `publish.py`). |

## The routine

A cloud routine publishes one mood post on Saturday and one on Sunday, following
`MOOD-POSTS.md` in the repository root (prompt: `ROUTINE-MOOD-PROMPT.txt`).
It writes the line itself. `config.json` → `mood_posts.mode` decides whether it
only creates the post (`preview`) or also publishes it (`publish`).

A folder you make by hand and push (with `post.jpg` and `caption.txt`) goes
into the queue: the routine publishes the queue, oldest first, before writing
new posts. See the queue with `python mood-posts/scripts/mood_log.py queue`.

## Make a post

```
python mood-posts/scripts/generate.py --text "but first,|*coffee*" --caption "Your caption here"
```

- `|` forces a line break, `*word*` is the emphasis.
- Theme, layout and drawing are chosen automatically (least recently used
  theme, layout from the length of the line, drawing from its tags) and never
  repeat the previous post. Force any of them with `--theme`, `--layout`, `--art`
  (`--art none` for text only), `--format square`.
- `python mood-posts/scripts/generate.py --list` shows themes, layouts and drawings.
- `--batch ideas.json` makes many posts from a JSON list.

Then **look at `post.jpg`**. To change something, edit `post.json` and run

```
python mood-posts/scripts/render.py mood-posts/posts/<folder>
```

Exit codes of both scripts: `0` ok, `2` the text doesn't fit or a field is
wrong (shorten the line, the template is not the problem), `3` technical error.

## Publish

Instagram downloads the image from GitHub, so the folder must be pushed first.

```
git add mood-posts/posts/<folder>
git commit -m "Mood post: <line>"
git push origin HEAD:main
python mood-posts/scripts/publish.py mood-posts/posts/<folder> --sha <commit> --dry-run
python mood-posts/scripts/publish.py mood-posts/posts/<folder> --sha <commit>
```

`--dry-run` checks the image, the public URL and the caption without calling
Instagram. The token works as for the carousels (`IG_ACCESS_TOKEN` on your PC,
the environment's API credential in a cloud routine). After publishing, commit
`publication.json` and `mood-posts/log.json`. If the script fails, don't run
it twice in a row: it has already retried the download on its own.

## Add a drawing or a theme

- Drawing: add `art/<name>.svg` following "art/*.svg rules" in `CONTRACT.md`
  (colors only through `--art-line`, `--art-fill`, `--art-paper`), and a line
  in `art/index.json` with its tags.
- Theme: add an entry to `themes.json` with the same fields as the others.
