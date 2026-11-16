# Mood posts: style rules

Working rules for writing one mood post for @coffee_extracts. Technical spec:
`CONTRACT.md` (it wins if the two disagree). Visual target: `moodboard/moodboard.html`.
A mood post is one image: one cute drawing and one short line about the reader
and a small part of their day. Coffee is the thread. No facts, tips or numbers.

## 1. The three line types

| Type | What it does | The reader should feel |
|---|---|---|
| Motivational | gives permission to start small, or to start again | lighter, not pushed |
| Relatable | names a small true habit people recognize | "that's me", and want to send it to a friend |
| Small reflection | looks closely at one moment of the day | a one-second pause, then a small smile |

Rotate the types. Never post the same type three times in a row.

## 2. Hard rules for the line

- 1 to 14 words. Aim for 4 to 9. `sub` is optional, max 8 words, and rarely needed.
- Lowercase by default, including "i". Write lowercase for `oat` too: the theme uppercases it.
- US English. Simple punctuation: periods and commas. No exclamation marks, no ellipses.
- Mark one emphasis with `*word*` (one or two words). It is the word the line turns on.
- Use `\n` only where a pause helps. Break by meaning, never mid-phrase.
- No emoji, no hashtags, no handle and no brand or company names in the image.
- No health, energy or caffeine-dose claims. No "coffee makes you", no cups-per-day figures.
- No hustle-culture cliches: grind, rise and shine, crush the day, no days off, boss mode.
- No "addicted", "can't function", "don't talk to me", and no joke at someone else's expense.
- Never reuse a well-known quote, slogan or meme line, and never the reference lines
  ("but first, coffee", "coffee is my morning wine", "great ideas start with coffee",
  "i need a coffee not your opinion", the "me / coffee" drip) or close rewrites of them.
- Never reuse a line already in `posts/`.
- The line must work without the caption and without the drawing, except in `hero`.

## 3. Picking theme, layout and art

Theme by tone, layout by length, art by the noun in the line. Don't use the theme of the last 2 posts or the art of the last 3.

| If the line is... | Theme | Layout | Art |
|---|---|---|---|
| quiet, slow, evening-like, a reflection | `espresso` | `stack` (3 to 7 words) or `quiet` | `beans`, `steam-cup`, or none |
| loud, punchy, 5 words or fewer | `mocha` | `side` or `stack` | `moka`, `beans` |
| gentle, with one key word to shout | `latte` | `center` or `quiet` | `cat-cup`, `steam-cup`, `croissant` |
| a deadpan joke, flat delivery | `oat` | `stack` or `center` | `sleepy-mug`, `takeaway-cup`, `alarm-clock`, `spilled-cup` |
| only works with the character | `paper` | `hero` or `center` | `ghost-mug`, `cat-cup`, `drip-bag` |
| warm, affectionate, about other people | `caramel` | `center` or `side` | `heart-cup`, `croissant`, `moka` |

Layout by length:

- `hero`: 2 to 6 words that caption the drawing. The drawing carries the joke.
- `stack`: 3 to 7 words, one or two per line, 3 or 4 lines. Small art beside the text.
- `center`: 5 to 12 words in 2 or 3 lines under the art. The default when unsure.
- `side`: 2 to 5 words in short lines next to a tall drawing (`moka`, `takeaway-cup`, `drip-bag`).
- `quiet`: 6 to 14 words, small, `art: null` or a tiny one. At most one post in four.

Art:

- Use the object the line names. If it names none, match the mood: tired = `sleepy-mug`,
  rest = `cat-cup`, affection = `heart-cup`, rush = `takeaway-cup`, absence = `ghost-mug`.
- Only use names listed in `art/index.json`. If the motif does not exist yet, take the
  closest one or `null`. Never ask for a new drawing inside a run.
- One drawing per post. `format` stays `portrait` unless the owner asks for `square`.

## 4. Caption

- 1 to 3 short lines. They add something the image does not say: where the line comes
  from, the small scene behind it, or the other side of it. Never repeat the line.
- Same voice as the image: lowercase is fine, warm, plain, no emoji, no brands, no claims.
- One closing question, specific to the line ("who made your first cup today?").
  Never "agree?", "thoughts?", "tag someone who".
- Last line: 3 to 5 hashtags, all about the actual content, at most one broad tag,
  different specific tags from the last 3 posts.
- No "Sources:" line: a mood post contains no facts. If the line needs a source, rewrite it.

## 5. Checklist

- [ ] The line is 1 to 14 words, lowercase, US English, with exactly one `*emphasis*`.
- [ ] It is clearly motivational, relatable or a small reflection, and not the third of its type in a row.
- [ ] No emoji, hashtag, brand, health claim, number of cups, hustle cliche or known quote.
- [ ] It is not already in `posts/` and not a reference line.
- [ ] Theme, layout and art follow the table; theme differs from the last 2 posts, art from the last 3.
      `theme` is a key of `themes.json`; `art` exists in `art/index.json` or is `null`.
- [ ] In the rendered image: text and art cover about a third of the canvas, nothing touches
      the edges, no orphan word on the last line, the drawing reads at phone size.
- [ ] The caption adds one thought, asks one specific question, ends with 3 to 5 hashtags.

## 6. Line bank

Thirty original lines, as models of the voice and for the owner to copy into the Notion database. The routine does not pick lines from here: it only uses rows of the database. Each: theme, layout, art.

### Motivational

1. `start *small*. start with a cup.` | latte, center, steam-cup
2. `small pot,\n*big* plans` | mocha, side, moka
3. `slow mornings\nare still\n*mornings*` | espresso, stack, beans
4. `the first cup doesn't have to be *perfect*. neither do you.` | caramel, center, heart-cup
5. `today can be *rebrewed*` | paper, hero, drip-bag
6. `good things take a *little heat*` | mocha, side, moka
7. `you showed up. the coffee is *proud* of you.` | paper, center, sleepy-mug
8. `refill,\nthen\n*try again*` | oat, stack, takeaway-cup
9. `nothing is urgent before the *first cup*` | espresso, quiet, null
10. `one sip, then the *next thing*` | latte, center, steam-cup

### Relatable

11. `my personality is still *brewing*` | oat, center, sleepy-mug
12. `here in spirit until the *first sip*` | paper, hero, ghost-mug
13. `i'll be nice in *one cup*` | oat, stack, sleepy-mug
14. `made coffee. forgot coffee. *reheated* coffee.` | oat, center, steam-cup
15. `to go.\nnot in\na *hurry*.` | oat, stack, takeaway-cup
16. `the alarm asked. the coffee *answered*.` | paper, center, alarm-clock
17. `my love language is someone *making the coffee*` | caramel, center, heart-cup
18. `croissant first. *questions* later.` | latte, center, croissant
19. `spilled a little. *kept* most of it.` | paper, hero, spilled-cup
20. `running on *crumbs* and good intentions` | caramel, side, croissant

### Small reflection

21. `drink it while it's *warm*. that goes for most things.` | caramel, center, heart-cup
22. `rest is also on the *menu*` | latte, center, cat-cup
23. `the best part of the day fits in a *small cup*` | espresso, quiet, null
24. `some mornings the only win is the *coffee*. that counts.` | paper, center, sleepy-mug
25. `who taught you how to make *your* coffee?` | espresso, stack, moka
26. `the kitchen is quietest right before the *moka* starts` | mocha, side, moka
27. `a cup tastes better when someone *else* pours it` | caramel, center, heart-cup
28. `you remember the *table*, not the coffee` | latte, quiet, null
29. `notice the *first* sip. the rest goes fast.` | espresso, stack, beans
30. `nobody rushes the *last sip*` | paper, hero, cat-cup
