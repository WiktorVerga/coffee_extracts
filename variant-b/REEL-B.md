# Animated reel of a variant B post (step 5b of `CLAUDE.md`)

**Only for posts whose `carousel.json` has `"variant": "B"`.** Posts with variant A follow `REEL-ANIMATED.md`, unchanged.

The B reel has the same idea, the same content and the same look as its B carousel, narrated, with sound effects and music, 9:16. It differs from the A reel in one thing: **it explains**. Up to **60 seconds**, calm and clear, with full sentences that give the reason behind each point, never a string of telegram-style fragments, never rushed.

Everything else (publishing, retries, the reel caption, the summary lines) works exactly as in `REEL-ANIMATED.md`.

## Files of variant B

| File | Purpose | Can it change during a run? |
|---|---|---|
| `variant-b/variant.json` → `reel` | the B reel settings: up to 60 s, voice at 1.0x, word limits, pacing of the reveals, bitrate | **No** |
| `variant-b/reel/reel.html`, `variant-b/reel/vendor/` | the B 9:16 template (look and slides come from `variant-b/carousel.html`) | **No** |
| `scripts/reel_animated/build_reel.py` | the same builder as A: it reads the post's variant and loads the B files and settings | **No** |
| `posts/<folder>/reel.json`, `reel-caption.txt` | your output, as for A | Yes |

## Step 5b for variant B (after the quality gate of step 5 has passed)

The carousel and its caption are final. The reel never changes them.

1. **Plan and write the script with `viral-reel-generator`**, read from `reel-skill/viral-reel-generator/` exactly as `REEL-ANIMATED.md` step 5b point 1 describes (same "the guide wins", no questions, draft only, never invent specifics, same fallback if the files can't be read). Differences for B:
   - Use the skill's **Style B, "The Deep Dive"** (`writing-styles.md`), not The Punchy, toned for this page: a friendly expert explaining at the counter, not someone roasting lazy solutions. Keep its anti-slop rules and its flow patterns (mechanism, cause and effect, contrast).
   - Tell it: a reel of **up to 60 seconds**, voice `af_heart` at **1.0x** (about 3 words per second), **120 to 160 words in total**, one scene per slide in the slide order.
   - Its hook patterns still apply, with the B hook limit below.
   Write the spoken lines into `posts/<folder>/reel.json`, one scene per slide, in the same order, same format as A (`"say"`, optional `"title"`).

   **Rules of the B narration:**
   - **Same content as the carousel, in spoken form.** Every fact must already be on the slides (or in the caption, with its source). Never add a figure, name or claim the carousel doesn't have. The guide's fact rules (section 4) apply word for word, and so does the voice of the guide (US English, "you", no banned words, no emoji, no brands).
   - **Explain, don't list.** Each scene says its point **and why it is so**: the cause, the mechanism, or what it means in your kitchen. Use the words that carry the logic: "because", "so", "which is why", "that means", "the reason is", "in practice". The listener should understand the idea, not just hear it.
   - **Full, well-built sentences.** Every sentence has a subject and a verb. Mix lengths: mostly 8 to 18 words, some shorter for emphasis, **never more than 24 words**. No staccato chains of fragments ("Less water. More body. Sweeter."): join them into one clear sentence ("With less water, the shot comes out thicker and usually sweeter.").
   - **Clear, precise words.** Prefer the concrete everyday word to the vague one ("the water runs through faster", not "the process changes"). Explain every Italian word the first time, as the slides do. One image per scene when the slide gives one.
   - **Direct, with no padding.** Every sentence adds a fact or a reason. No warm-up, no filler: "basically", "actually", "literally", "you might be wondering", "let's dive in", "in this video", "stick around", "the secret is". Don't repeat the slide title word for word.
   - **Scene 1 is the hook:** a clear question or claim of **14 words or less** in its first sentence, heard in the first second, that tells the viewer what they will understand by the end. The scene can go on with one sentence that sets up the problem.
   - **The last scene** sums up the idea in one sentence and ends with **one** ask (save, share, or the caption's question).
   - **At most 50 words per scene**, **120 to 160 words in total** (the script refuses fewer than 100 or more than 175). The reel lasts as long as the narration, **35 to 60 seconds**; spare time is never filled with silence. If the narration runs slightly over 60 seconds, the script speeds the voice up to 1.08x at most, otherwise it asks you to cut.
   - **Write for the ear**, as for A: numbers and units spelled as spoken, no symbols, hashtags, links or handles, and the same respelling of Italian words (*moka* → "moh-ka", *caffè* → "caf-feh", *ristretto* → "ris-tret-toh", *macchiato* → "mak-kee-ah-toh", *al banco* → "al bahn-koh"). If unsure, avoid the word in the narration.
   - **Spoken titles (optional)**, as for A, up to 6 words ("The tip.", "Why it turns bitter."). Scene 1 never has one.
   - Keep the slide and the line together: the line of scene N is heard while slide N is on screen, and the slide's elements appear one by one while you speak, so follow the slide's order inside the line.
2. **Build it:** `python3 scripts/reel_animated/build_reel.py posts/<folder>` (it prints `Variant B ...` and loads the B settings). Exit codes and what to do are the same as in `REEL-ANIMATED.md` step 5b point 2.
3. **Look at the frames** with the Read tool (all `scene-XX.jpg` in `.reel-build/<folder>/frames/`): text readable, nothing cut off, nothing covered by Instagram's interface (top 250 px, bottom 430 px).
4. **Quality gate of the B reel:**
   - `reel-meta.json`: `"variant": "B"`, `duration` between 35 and 61 seconds, `size_mb` ≤ 18.
   - The narration says nothing the slides don't say; no banned words; hook of 14 words or less; no sentence over 24 words; every scene gives a reason, not just a statement; no telegram-style fragments; one ask at the end.
5. **Write `posts/<folder>/reel-caption.txt`** exactly as in `REEL-ANIMATED.md` step 5b point 5.

Then step 7b (publishing) is the one in `REEL-ANIMATED.md`, unchanged.

## Summary lines (step 8)

As in `REEL-ANIMATED.md`, plus: "Reel rules: variant B (`variant-b/REEL-B.md`)", and the total number of words of the narration.
