# Your own sound effects

Drop your sound effect files **in this folder** (`sfx/custom/`). The routine reads each file's **name** to understand where to use it. Anything you cover here **replaces** the built-in synthesized effect for that role; roles you don't cover keep the built-in one (the effects in `sfx/`, made by `scripts/reel_animated/make_sfx.py`).

## Where each effect is used, and the words that tell it

A file name is matched **in this order**, the first role with a word in the name wins (upper/lower case doesn't matter, any other words are fine: `soft-whoosh-02.wav` → whoosh).

| Role | Where it plays | Words in the name |
|---|---|---|
| **riser** | builds up to the first cut, ends exactly on it | `riser`, `build`, `tension`, `rise`, `crescendo`, `sweep-up`, `salita` |
| **intro** | the very first moment of the reel (the hook) | `intro`, `opening`, `open`, `start`, `hook`, `cover`, `apertura`, `inizio` |
| **ding** | the call to action in the last scene | `ding`, `bell`, `chime`, `cta`, `success`, `final`, `end`, `outro`, `sparkle`, `campanell`, `chiusura`, `fine` |
| **hit** | lands the new scene, right on every cut | `hit`, `impact`, `thud`, `boom`, `slam`, `punch`, `bass`, `drop`, `colpo`, `impatto` |
| **tick** | every time a line of text appears (kept quiet) | `tick`, `click`, `type`, `typing`, `pop`, `blip`, `tap`, `snap`, `text`, `reveal`, `bubble`, `scatto` |
| **whoosh** | the swipe between two scenes | `whoosh`, `swoosh`, `swipe`, `swish`, `transition`, `transizione`, `wipe`, `slide`, `air`, `passaggio` |

Examples: `transition-whoosh-1.wav`, `transition-whoosh-2.wav`, `scene-impact-soft.wav`, `text-pop.wav`, `cta-chime.mp3`, `hook-intro-sting.wav`, `riser-short.wav`.

A name with an ambiguous mix goes to the first matching role of the table (`transition-hit.wav` is a **hit**). A file whose name matches nothing is **ignored**, and the run summary of the build prints a warning with its name.

## Good to know

- **Several files for one role are used in rotation** (the 1st cut gets the first whoosh, the 2nd cut the second one...). Great for variety: give 2 or 3 whooshes and 2 or 3 hits.
- **Format:** `.wav`, `.mp3`, `.m4a`, `.aac`, `.flac`, `.ogg` or `.opus`, any sample rate, mono or stereo. Short files: whoosh up to 1.3 s, hit 1.5 s, tick 0.5 s, ding 2.2 s, riser 1.6 s, intro 2 s (longer files are cut with a fade-out).
- **Alignment:** every effect is placed so its **loudest moment** falls on the cut (or on the text appearing), so you don't have to trim silence at the start.
- **Level:** you don't need to match loudness between files, each one is leveled automatically. The overall level of all effects is `sfx_level_db` in `config.json` → `reel_animated` (now `-14`; lower = quieter).
- Same licensing rule as the music: use only effects you may use commercially on Instagram.
- Commit and push the files to `main`: the next run uses them.
