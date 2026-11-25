# Test A/B: variante A (originale) contro B (Film)

Aggiornato: 2026-11-25 19:48 · test attivo dal 2026-10-29 · numeri congelati a 7 giorni dalla pubblicazione.

Metriche principali: **visualizzazioni e like** del carosello e del reel, e per il reel il **tempo medio di visione**. Le altre metriche sono in fondo, solo come contesto.

## Com'è andata finora

**Troppo presto per un verdetto**: servono almeno 6 post congelati per variante (ora A = 4, B = 4). Con pochi post la differenza dipende più dall'argomento del singolo post che dal template.

Tendenze (medie dei post congelati):
- visualizzazioni del carosello: A 80.8, B 92 (+14% per B)
- like del carosello: A 4.2, B 5 (+18% per B)
- visualizzazioni del reel: A 148, B 261 (+77% per B)
- like del reel: A 7, B 8.5 (+21% per B)
- visione media del reel: A 5.1 s, B 7.0 s (+38% per B)

## Metriche principali

### Carosello

| Metrica (media · mediana) | A (originale) (n=4) | B (Film) (n=4) | A prima del test (n=10) |
|---|---|---|---|
| Visualizzazioni | 80.8 · 77 | 92 · 94 | 54.8 · 52.5 |
| Like | 4.2 · 4 | 5 · 5 | 3.8 · 4 |
| Like ogni 100 visualizzazioni | 5.3 · 5.4 | 5.4 · 5.5 | 6.8 · 6.7 |

### Reel del post

| Metrica (media · mediana) | A (originale) (n=4) | B (Film) (n=4) | A prima del test (n=8) |
|---|---|---|---|
| Visualizzazioni | 148 · 134 | 261 · 162 | 99.9 · 102 |
| Like | 7 · 7.5 | 8.5 · 4.5 | 5.1 · 5 |
| Visione media | 5.1 s · 4.9 s | 7.0 s · 5.9 s | 3.8 s · 3.9 s |
| Visione media / durata del reel | 21.5% · 21.4% | 13.1% · 10.6% | 14.9% · 16.2% |

## Post del test

| Data | ID | Variante | Serie | Carosello: visual. | Carosello: like | Reel: visual. | Reel: like | Reel: visione media | Stato |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-25 | 28 | B | One word | 0 | 0 | 0 | 0 | – | in corso (0 gg) |
| 2026-11-23 | 27 | A | Myth or fact | 105 | 3 | 202 | 5 | 5.2 s | in corso (1.9 gg) |
| 2026-11-20 | 26 | B | Inside the cup | 56 | 4 | 140 | 8 | 6.4 s | in corso (5 gg) |
| 2026-11-18 | 25 | A | How-to | 54 | 3 | 119 | 6 | 5.0 s | congelato |
| 2026-11-16 | 24 | B | Myth or fact | 81 | 5 | 160 | 5 | 5.9 s | congelato |
| 2026-11-13 | 23 | A | Common mistake | 97 | 6 | 149 | 3 | 5.8 s | congelato |
| 2026-11-09 | 22 | B | One word | 107 | 7 | 667 | 21 | 11.0 s | congelato |
| 2026-11-06 | 21 | A | Side by side | 115 | 5 | 257 | 10 | 4.7 s | congelato |
| 2026-11-04 | 19 | B | Inside the cup | 118 | 5 | 164 | 4 | 5.9 s | congelato |
| 2026-11-02 | 13 | A | Common mistake | 57 | 3 | 66 | 9 | 4.8 s | congelato |
| 2026-10-30 | 12 | B | One word | 62 | 3 | 53 | 4 | 5.2 s | congelato |

In attesa dei 7 giorni: ID 26 (B), ID 27 (A), ID 28 (B).

## Altre metriche (contesto)

### Carosello: altre metriche

| Metrica (media · mediana) | A (originale) (n=4) | B (Film) (n=4) | A prima del test (n=10) |
|---|---|---|---|
| Reach | 33.8 · 31.5 | 38.5 · 38 | 28 · 28 |
| Salvataggi | 0 · 0 | 0 · 0 | 0 · 0 |
| Condivisioni | 0.2 · 0 | 0 · 0 | 0 · 0 |
| Interazioni / reach | 15.8% · 15.8% | 18.7% · 20.0% | 18.2% · 18.3% |
| Nuovi follower | 0 · 0 | 0 · 0 | 0 · 0 |

### Reel: altre metriche

| Metrica (media · mediana) | A (originale) (n=4) | B (Film) (n=4) | A prima del test (n=8) |
|---|---|---|---|
| Reach | 128 · 115 | 224 · 140 | 87.6 · 91.5 |
| Salvataggi | 0.8 · 0 | 1 · 0 | 0.1 · 0 |
| Condivisioni | 0.2 · 0 | 0.5 · 0 | 0.1 · 0 |
| Interazioni / reach | 8.3% · 6.6% | 6.7% · 4.7% | 10.0% · 8.5% |

## Come leggerlo

- Ogni nuovo post riceve A o B a turno (scripts/ab.py): così le due varianti escono negli stessi giorni e con argomenti misti.
- I numeri vengono congelati quando il post compie i giorni indicati sopra, così ogni post è misurato alla stessa età. "A prima del test" è solo un riferimento: quei post sono stati misurati più tardi e in un periodo diverso.
- Il reel B dura fino a 60 secondi, quello A fino a 30: la visione media in secondi favorisce naturalmente il video più lungo. Per confrontarli guarda anche "Visione media / durata".
- Visualizzazioni e like variano molto da post a post anche per l'argomento: controlla nella tabella dei post che A e B abbiano serie simili, e fidati delle mediane più che delle medie.

