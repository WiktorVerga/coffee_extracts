# Test A/B: variante A (originale) contro B (Film)

Aggiornato: 2026-11-20 19:50 · test attivo dal 2026-10-29 · numeri congelati a 7 giorni dalla pubblicazione.

Metriche principali: **visualizzazioni e like** del carosello e del reel, e per il reel il **tempo medio di visione**. Le altre metriche sono in fondo, solo come contesto.

## Com'è andata finora

**Troppo presto per un verdetto**: servono almeno 6 post congelati per variante (ora A = 3, B = 3). Con pochi post la differenza dipende più dall'argomento del singolo post che dal template.

Tendenze (medie dei post congelati):
- visualizzazioni del carosello: A 89.7, B 95.7 (+7% per B)
- like del carosello: A 4.7, B 5 (+7% per B)
- visualizzazioni del reel: A 157, B 295 (+87% per B)
- like del reel: A 7.3, B 9.7 (+32% per B)
- visione media del reel: A 5.1 s, B 7.3 s (+44% per B)

## Metriche principali

### Carosello

| Metrica (media · mediana) | A (originale) (n=3) | B (Film) (n=3) | A prima del test (n=10) |
|---|---|---|---|
| Visualizzazioni | 89.7 · 97 | 95.7 · 107 | 54.8 · 52.5 |
| Like | 4.7 · 5 | 5 · 5 | 3.8 · 4 |
| Like ogni 100 visualizzazioni | 5.3 · 5.3 | 5.2 · 4.8 | 6.8 · 6.7 |

### Reel del post

| Metrica (media · mediana) | A (originale) (n=3) | B (Film) (n=3) | A prima del test (n=8) |
|---|---|---|---|
| Visualizzazioni | 157 · 149 | 295 · 164 | 99.9 · 102 |
| Like | 7.3 · 9 | 9.7 · 4 | 5.1 · 5 |
| Visione media | 5.1 s · 4.8 s | 7.3 s · 5.9 s | 3.8 s · 3.9 s |
| Visione media / durata del reel | 21.4% · 21.3% | 14.2% · 11.2% | 14.9% · 16.2% |

## Post del test

| Data | ID | Variante | Serie | Carosello: visual. | Carosello: like | Reel: visual. | Reel: like | Reel: visione media | Stato |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-20 | 26 | B | Inside the cup | 0 | 0 | 0 | 0 | – | in corso (0 gg) |
| 2026-11-18 | 25 | A | How-to | 48 | 3 | 111 | 5 | 4.9 s | in corso (2 gg) |
| 2026-11-16 | 24 | B | Myth or fact | 79 | 5 | 158 | 5 | 5.9 s | in corso (4 gg) |
| 2026-11-13 | 23 | A | Common mistake | 97 | 6 | 149 | 3 | 5.8 s | congelato |
| 2026-11-09 | 22 | B | One word | 107 | 7 | 667 | 21 | 11.0 s | congelato |
| 2026-11-06 | 21 | A | Side by side | 115 | 5 | 257 | 10 | 4.7 s | congelato |
| 2026-11-04 | 19 | B | Inside the cup | 118 | 5 | 164 | 4 | 5.9 s | congelato |
| 2026-11-02 | 13 | A | Common mistake | 57 | 3 | 66 | 9 | 4.8 s | congelato |
| 2026-10-30 | 12 | B | One word | 62 | 3 | 53 | 4 | 5.2 s | congelato |

In attesa dei 7 giorni: ID 24 (B), ID 25 (A), ID 26 (B).

## Altre metriche (contesto)

### Carosello: altre metriche

| Metrica (media · mediana) | A (originale) (n=3) | B (Film) (n=3) | A prima del test (n=10) |
|---|---|---|---|
| Reach | 38.3 · 39 | 41.3 · 46 | 28 · 28 |
| Salvataggi | 0 · 0 | 0 · 0 | 0 · 0 |
| Condivisioni | 0.3 · 0 | 0 · 0 | 0 · 0 |
| Interazioni / reach | 16.0% · 16.7% | 18.3% · 20.0% | 18.2% · 18.3% |
| Nuovi follower | 0 · 0 | 0 · 0 | 0 · 0 |

### Reel: altre metriche

| Metrica (media · mediana) | A (originale) (n=3) | B (Film) (n=3) | A prima del test (n=8) |
|---|---|---|---|
| Reach | 138 · 131 | 253 · 145 | 87.6 · 91.5 |
| Salvataggi | 1 · 0 | 1.3 · 0 | 0.1 · 0 |
| Condivisioni | 0.3 · 0 | 0.7 · 0 | 0.1 · 0 |
| Interazioni / reach | 8.7% · 6.2% | 7.4% · 5.0% | 10.0% · 8.5% |

## Come leggerlo

- Ogni nuovo post riceve A o B a turno (scripts/ab.py): così le due varianti escono negli stessi giorni e con argomenti misti.
- I numeri vengono congelati quando il post compie i giorni indicati sopra, così ogni post è misurato alla stessa età. "A prima del test" è solo un riferimento: quei post sono stati misurati più tardi e in un periodo diverso.
- Il reel B dura fino a 60 secondi, quello A fino a 30: la visione media in secondi favorisce naturalmente il video più lungo. Per confrontarli guarda anche "Visione media / durata".
- Visualizzazioni e like variano molto da post a post anche per l'argomento: controlla nella tabella dei post che A e B abbiano serie simili, e fidati delle mediane più che delle medie.

