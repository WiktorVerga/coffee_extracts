# Variant B "Film" (A/B test)

Everything that makes variant B different lives **in this folder**. Variant A is the original project, untouched: `template/carousel.html`, `template/fonts/`, `template/reel/`, `REEL-ANIMATED.md`.

A post is B when its `carousel.json` has `"variant": "B"` (written by `scripts/ab.py assign`, see the A/B section of `README.md` at the root).

## What's in here

| File | What it is | Edit it to change… |
|---|---|---|
| `carousel.html` | the B carousel template (1080 × 1350) | the look of the B slides: colors, type, grain, the line-drawn cup |
| `fonts/` | Fraunces (titles) and Archivo Narrow (body), OFL licenses included | the fonts of B (carousel and reel) |
| `reel/reel.html` | the B reel template (1080 × 1920): sizes, safe zones, animation, transitions, flickering grain | the look and motion of the B reel |
| `reel/vendor/gsap.min.js` | animation library used by the reel (own copy) | nothing |
| `variant.json` | the paths above and the **B reel settings** (they override `config.json` → `reel_animated` only for B) | length (`target_seconds`, `min_seconds`), voice speed, word limits, pacing of the reveals, bitrate, which elements appear one by one (`reveals`) |
| `REEL-B.md` | how the routine writes the B narration: up to 60 s, full sentences that explain the why | the writing rules of the B reel |

## How B differs from A

| | A (original) | B "Film" |
|---|---|---|
| Carousel | dark/hazel, Archivo Black, filled cup, thick progress bar, handle and page numbers | light paper, Fraunces serif, line-drawn cup, hairlines, film grain; no frame, no handle, no small labels (cover kicker, "People say", "The tip"), no page numbers, "Swipe" only on the cover |
| Reel length | 15–30 s | 35–60 s |
| Voice | 1.1x, up to 1.25x | 1.0x, up to 1.08x |
| Narration | punchy: sentences ≤ 9 words, ≤ 20 words per scene, 45–65 words | explanatory: sentences ≤ 24 words, ≤ 50 per scene, 120–160 words (100–175 accepted) |
| Reveals | all items of a slide appear within ~1.6 s | items appear along the line, up to 3 s apart |

Content rules (guide, fact rules, slide types and word limits of the carousel) are **the same** for A and B.

## Try it by hand

```
python scripts/render.py posts/<folder> --variant B        # B slides of an existing post (carousel.json is not changed)
python scripts/reel_animated/build_reel.py posts/<folder>  # the reel follows "variant" in carousel.json
```
Open `carousel.html` in a browser to see the example slides.

## Rules for editing

- Keep the markers that `scripts/reel_animated/build_reel.py` cuts at (explained at the top of `carousel.html`).
- If you add or remove an element that the reel reveals, update `variant.json` → `reel.reveals`.
- Changing B never changes A, and the other way round. Only `scripts/` and the content rules are shared.
- To stop the test: `config.json` → `ab_test.enabled` = `false`. To keep B for good: `ab_test.default` = `"B"`.
