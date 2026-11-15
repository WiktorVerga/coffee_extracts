# Mood posts: shared contract

Single-image Instagram posts for @coffee_extracts: an "aesthetic", instantly
recognizable image with one cute element and one short line that is
motivational, relatable, or makes the reader think about a small part of
their day. Everything lives in `mood-posts/`; nothing outside it changes.

## Folder layout

```
mood-posts/
  themes.json            palettes + type styles (fixed, see below)
  art/<name>.svg         library of cute elements
  art/index.json         { "<name>": { "title": "...", "tags": [...], "ratio": w/h } }
  template/post.html     the reusable template (data injected by render.py)
  template/fonts/        Fraunces (roman + italic, variable), Archivo Black, Archivo Narrow
  scripts/render.py      post.json -> post.jpg
  scripts/generate.py    idea/text -> post folder with post.json (+ render)
  scripts/publish.py     post.jpg -> Instagram Graph API (single image)
  posts/YYYY-MM-DD-slug/ post.json, caption.txt, post.jpg, render-report.json
  moodboard/             moodboard.html, refs/ (local only, gitignored)
  STYLE.md               visual + copy rules
```

## post.json

```json
{
  "text": "but first,\n*coffee*",
  "theme": "espresso",
  "layout": "stack",
  "art": "beans",
  "format": "portrait",
  "sub": "optional tiny second line"
}
```

- `text`: 1 to 14 words. `\n` forces a line break. `*word*` marks the emphasis
  (how it looks depends on the theme's `emphasis`).
- `theme`: a key of `themes.json`.
- `layout`: one of
  - `center`: art on top, text centered below it (default)
  - `stack`: big left-aligned text filling the canvas, small art tucked beside/after the text
  - `hero`: the drawing is the post (about 60% of the canvas), short text as a caption under it
  - `side`: art on the left, text on the right, vertically centered together
  - `quiet`: small text centered in a lot of empty space, no art or a tiny one above it
- `art`: file name in `art/` without `.svg`, or `null`.
- `format`: `portrait` (1080 x 1350, default) or `square` (1080 x 1080).
- `sub`: optional small line (max 8 words).
- The handle (`@coffee_extracts`, from the root `config.json`) is drawn small
  and low-contrast at the bottom.

## themes.json (already written, do not change keys)

Each theme: `bg`, `ink` (text), `accent` (emphasis), `art.line`, `art.fill`,
`art.paper`, `font`, `weight`, `case` (`lower` | `upper` | `as-is`),
`tracking`, `emphasis` (`italic` | `accent` | `bold-caps`).

Font keys:
- `serif`: Fraunces, crisp (SOFT 0), high optical size
- `serif-soft`: Fraunces with SOFT 100, WONK 1 (round, friendly, fat at 900)
- `narrow`: Archivo Narrow
- `display`: Archivo Black

Emphasis:
- `italic`: Fraunces Italic in the `accent` color
- `accent`: same face, `accent` color
- `bold-caps`: uppercase, weight 900, `accent` color

## art/*.svg rules

- One root `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H">`, no
  `width`/`height` attributes, no XML prolog, no comments before the root.
- Colors ONLY through these CSS custom properties, each with a fallback:
  - `var(--art-line, #15110e)`: outlines
  - `var(--art-fill, #d2a369)`: the coffee / warm fill
  - `var(--art-paper, #ffffff)`: bodies, cups, anything "white"
  - a darker coffee shade is allowed only as `var(--art-fill)` with
    `opacity`/a `var(--art-line)` overlay at low opacity
- No `<text>`, no fonts, no `<image>`, no external references, no `<script>`,
  no `<style>` blocks. Presentation attributes or inline `style` only.
- Every `id` (gradients, clip paths) starts with the file name, e.g. `ghost-mug-clip`.
- Round caps and joins, stroke width 6 to 9 on a ~400 px box, slightly
  imperfect hand-drawn curves. Drawings must stay readable at 250 px wide.
- The drawing fills its viewBox with about 4% padding and no background rectangle.
