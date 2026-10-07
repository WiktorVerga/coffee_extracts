# Animated reel of the post (steps 5b and 7b of `CLAUDE.md`)

Every carousel gets its own reel: **same idea, same content, same look**, narrated, with sound effects and music, 9:16, 30 seconds. It is built with HyperFrames and published like the post, with no human in the loop.

This file is part of the carousel routine (`CLAUDE.md` points here). It is **not** the reels routine of `REELS.md` (YouTube clips, Tuesday and Thursday), which is untouched.

## Files

| File | Purpose | Can it change during a run? |
|---|---|---|
| `scripts/reel_animated/build_reel.py` | voice, timing, audio mix, layout check, render | **No** |
| `scripts/reel_animated/make_sfx.py`, `sfx/*.wav` | the sound effects (synthesized, no licenses) | **No** |
| `sfx/custom/` | the owner's own sound effects, role guessed from the file name (see `sfx/custom/README.md`); they replace the built-in effect of that role | **No** |
| `template/reel/reel.html`, `template/reel/vendor/gsap.min.js` | the 9:16 template (colors, fonts and slides come from `template/carousel.html`) | **No** |
| `music/` | the owner's tracks (see `music/README.md`) | **No** |
| `scripts/publish_post_reel.py` | publishes the reel | **No** |
| `reel-skill/viral-reel-generator/` | the script-writing skill of point 1 of step 5b (a copy, read from here) | **No** |
| `config.json` → `reel_animated` | `mode` (`preview`/`publish`), voice, target length | **No** |
| `posts/<folder>/reel.json` | the narration, one line per slide | Yes, your output |
| `posts/<folder>/reel-caption.txt` | the reel caption | Yes, your output |
| `posts/<folder>/reel.mp4`, `reel-meta.json` | made by `build_reel.py` | Only by running the script |
| `posts/<folder>/reel-publication.json` | made by `publish_post_reel.py` | Only by running the script |

## Step 5b. Make the reel (after the quality gate of step 5 has passed)

The carousel and its caption are final. The reel never changes them.

1. **Plan and write the script with `viral-reel-generator`.** Use it here, and not before. The skill lives in the repository: **read `reel-skill/viral-reel-generator/SKILL.md` with the Read tool** and the files of `reel-skill/viral-reel-generator/references/` that it names (`writing-styles.md` and `hook-patterns.md` always, the others if useful), and follow them. Don't depend on the plugin: if the Skill tool also offers `mcpmarket-me:viral-reel-generator` you may call it instead, but the repository copy is the reference. It is used for **the script and the organization of the reel**: the hook, how the scenes are ordered for retention, the pacing of each line, the ending, and its anti-AI-slop writing rules. Draft only. Give it: the finished `carousel.json` (slides in order, with their types), the caption, the series, the goal chosen in step 3 (`saves` or `shares`), the 30-second target, the voice (`af_sky`, about 2.8 words per second) and the constraints below. Ask it for the hook and for the scene-by-scene script, one scene per slide.
   Rules for using it (nobody is there to answer questions):
   - **The guide and this file win.** If the skill's advice contradicts `guide/style-guide.md`, `CLAUDE.md` or the rules below, follow those. Known cases: no emoji, no brands or company names, no figure or claim that is not on the slides, no personal story or result (the page has none), US English, no engagement bait, the word limits below, **one scene per slide in the slide order** (the skill may propose a different structure or scene count: keep its hook and pacing ideas, but map them onto the slides, never add or reorder scenes), and no on-screen text, B-roll, camera or editing directions (the template draws the reel).
   - **No questions, no approval step.** Skip its "Discovery Questions" / Interactive Mode: the idea, the notes and the carousel are the brief, so choose the angle yourself and report it in the final summary.
   - **Use only what the reel needs from it:** the style choice (Punchy or Deep Dive; pick by content, and a reel always fits 30 seconds), the hook patterns, the anti-slop rules and the flow patterns (connector words, contrast, mechanism). **Ignore** its output format with timecodes and visual cues, its metadata generation (caption hook, keywords, thumbnail text: the caption is already written), Roast Mode, and `visual-patterns.md` (the template draws the reel). The hook must be 12 words or less here, not 15.
   - **Never invent specifics.** If it asks for a figure, date, name or example you don't have, leave it out.
   - **Draft only.** Never let it publish, upload, schedule or generate media: the reel is built by `build_reel.py` and published by `publish_post_reel.py` only.
   - **If the files in `reel-skill/` can't be read**, write the narration from the rules below alone and write "Skill not available: viral-reel-generator" in the final summary. Don't stop the run.
   From the skill's output, keep only the spoken lines, and write them into `posts/<folder>/reel.json`: the narration, **one line per slide, in the same order** (same number of scenes as slides):
   ```json
   { "scenes": [ { "say": "Why does your espresso taste bitter? It's not the coffee." }, { "say": "..." } ] }
   ```
   Rules:
   - **Same content as the carousel, in spoken form.** Every fact must already be on the slides (or in the caption, with its source). Never add a figure, name or claim the carousel doesn't have. The guide's fact rules (section 4) apply word for word.
   - **Voice of the guide** (section 3): US English, "you", short sentences, no banned words, no emoji, no brands.
   - **Scene 1 is the hook**: a promise or a question that makes people stay, in 12 words or less if you can. The last scene recaps in one sentence and ends with one ask (save, share, or the same question as the caption).
   - **60 to 85 words in total, at most 26 per scene.** The voice (`af_sky`) speaks about 2.8 words per second, and the reel must fit 30 seconds (the script speeds the voice up to 1.2x if needed and refuses anything longer).
   - **Write for the ear:** spell numbers and units as they are spoken ("twenty-five to thirty seconds", "two hundred degrees Fahrenheit", "nine bar"). No symbols, no hashtags, no links, no handles.
   - **Italian words:** the English voice mispronounces them. Respell them for the ear only in `reel.json` (the slides keep the correct spelling): *moka* → "moh-ka", *caffè* → "caf-feh", *ristretto* → "ris-tret-toh", *macchiato* → "mak-kee-ah-toh", *al banco* → "al bahn-koh". If unsure, avoid the word in the narration.
   - Keep the slide and the sentence together: the line of scene N is heard while slide N is on screen.
2. **Build it:** `python3 scripts/reel_animated/build_reel.py posts/<folder>`
   - exit **0**: the reel is ready (`reel.mp4`, `reel-meta.json`). Frames to look at: `.reel-build/<folder>/frames/scene-XX.jpg`.
   - exit **2** (content problem: too long, too short, text that doesn't fit): read the message, fix `reel.json` and run again. If a slide's text doesn't fit, shorten `carousel.json` **only if** you then also re-render the images (step 4) and redo the checks of step 5. 3 attempts max.
   - exit **3**, or 3 failed attempts: **skip the reel, not the post.** Don't stop the run: the carousel goes on. In the final summary write "Reel: not made (<reason>)" and don't do step 7b.
   - If it prints `WARNING: music/ has no tracks`, the reel has voice and sound effects only: that is allowed, mention it in the summary.
3. **Look at the frames** with the Read tool (all `scene-XX.jpg`): text readable, nothing cut off, nothing over the cup that hides the words. The bottom 430 px and top 250 px are Instagram's interface: nothing important lives there (the template already respects this).
4. **Quality gate of the reel:**
   - `reel-meta.json`: `duration` between 27 and 30.5 seconds, `size_mb` ≤ 18.
   - The narration says nothing the slides don't say; no banned words; hook in scene 1; one ask at the end.
5. **Write `posts/<folder>/reel-caption.txt`**: start from `caption.txt` and adapt it to someone *watching* instead of swiping: hook (first line, ≤ 125 characters) that makes sense on its own, 1 or 2 short lines, the same closing question (or a new specific one), the **same `Sources:` line**, the **same hashtags** as the post. No emoji, at most 900 characters, nothing that refers to a swipe ("swipe", "slide 3"). Don't call extra skills for this (the viral-reel-generator is used only for the script in point 1).

Add the reel files to the commit of step 6 (`git add posts/<folder>`): `reel.json`, `reel.mp4`, `reel-meta.json`, `reel-caption.txt`.

## Step 7b. Publish the reel (after step 7)

- **`reel_animated.mode` = `preview`**: don't publish. Done (the files are on GitHub).
- **`reel_animated.mode` = `publish`**, and only if **the carousel was published in this run** (never a reel without its post):
  1. `SHA=$(git rev-parse HEAD)` (the commit that contains `reel.mp4`, already pushed)
  2. No cache warm-up with `curl`: the script checks that the video is served (jsDelivr, with `raw.githubusercontent.com` as fallback) and retries by itself when Instagram can't download it.
  3. `python3 scripts/publish_post_reel.py posts/<folder> --sha $SHA`
  4. Commit and push `posts/<folder>/reel-publication.json`, even if it failed.
  5. If the script fails, **don't run it again** in the same run: it has already retried on its own, and running it twice could create a duplicate. Report the error.

## Summary lines to add (step 8)

- reel: made / not made (reason); duration, size, music file used (or "no music"); hook and structure chosen with `viral-reel-generator` (or "Skill not available")
- reel outcome: preview / published (with link) / error (with reason)
