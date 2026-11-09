# Test A/B: variante A (originale) contro B (Film)

Aggiornato: 2026-11-09 19:50 · test attivo dal 2026-10-29 · numeri congelati a 7 giorni dalla pubblicazione.

Metriche principali: **visualizzazioni e like** del carosello e del reel, e per il reel il **tempo medio di visione**. Le altre metriche sono in fondo, solo come contesto.

## Com'è andata finora

**Troppo presto per un verdetto**: servono almeno 6 post congelati per variante (ora A = 1, B = 1). Con pochi post la differenza dipende più dall'argomento del singolo post che dal template.

Tendenze (medie dei post congelati):
- visualizzazioni del carosello: A 57, B 62 (+9% per B)
- like del carosello: A 3, B 3 (+0% per B)
- visualizzazioni del reel: A 66, B 53 (-20% per B)
- like del reel: A 9, B 4 (-56% per B)
- visione media del reel: A 4.8 s, B 5.2 s (+8% per B)

## Metriche principali

### Carosello

| Metrica (media · mediana) | A (originale) (n=1) | B (Film) (n=1) | A prima del test (n=10) |
|---|---|---|---|
| Visualizzazioni | 57 · 57 | 62 · 62 | 54.8 · 52.5 |
| Like | 3 · 3 | 3 · 3 | 3.8 · 4 |
| Like ogni 100 visualizzazioni | 5.3 · 5.3 | 4.8 · 4.8 | 6.8 · 6.7 |

### Reel del post

| Metrica (media · mediana) | A (originale) (n=1) | B (Film) (n=1) | A prima del test (n=8) |
|---|---|---|---|
| Visualizzazioni | 66 · 66 | 53 · 53 | 99.9 · 102 |
| Like | 9 · 9 | 4 · 4 | 5.1 · 5 |
| Visione media | 4.8 s · 4.8 s | 5.2 s · 5.2 s | 3.8 s · 3.9 s |
| Visione media / durata del reel | 21.3% · 21.3% | 11.2% · 11.2% | 14.9% · 16.2% |

## Post del test

| Data | ID | Variante | Serie | Carosello: visual. | Carosello: like | Reel: visual. | Reel: like | Reel: visione media | Stato |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-09 | 22 | B | One word | 0 | 0 | 0 | 0 | – | in corso (0 gg) |
| 2026-11-06 | 21 | A | Side by side | 72 | 4 | 242 | 9 | 4.6 s | in corso (3 gg) |
| 2026-11-04 | 19 | B | Inside the cup | 95 | 4 | 151 | 3 | 5.5 s | in corso (5 gg) |
| 2026-11-02 | 13 | A | Common mistake | 57 | 3 | 66 | 9 | 4.8 s | congelato |
| 2026-10-30 | 12 | B | One word | 62 | 3 | 53 | 4 | 5.2 s | congelato |

In attesa dei 7 giorni: ID 19 (B), ID 21 (A), ID 22 (B).

## Altre metriche (contesto)

### Carosello: altre metriche

| Metrica (media · mediana) | A (originale) (n=1) | B (Film) (n=1) | A prima del test (n=10) |
|---|---|---|---|
| Reach | 24 · 24 | 25 · 25 | 28 · 28 |
| Salvataggi | 0 · 0 | 0 · 0 | 0 · 0 |
| Condivisioni | 0 · 0 | 0 · 0 | 0 · 0 |
| Interazioni / reach | 16.7% · 16.7% | 20.0% · 20.0% | 18.2% · 18.3% |
| Nuovi follower | 0 · 0 | 0 · 0 | 0 · 0 |

### Reel: altre metriche

| Metrica (media · mediana) | A (originale) (n=1) | B (Film) (n=1) | A prima del test (n=8) |
|---|---|---|---|
| Reach | 57 · 57 | 38 · 38 | 87.6 · 91.5 |
| Salvataggi | 0 · 0 | 0 · 0 | 0.1 · 0 |
| Condivisioni | 0 · 0 | 0 · 0 | 0.1 · 0 |
| Interazioni / reach | 17.5% · 17.5% | 13.2% · 13.2% | 10.0% · 8.5% |

## Come leggerlo

- Ogni nuovo post riceve A o B a turno (scripts/ab.py): così le due varianti escono negli stessi giorni e con argomenti misti.
- I numeri vengono congelati quando il post compie i giorni indicati sopra, così ogni post è misurato alla stessa età. "A prima del test" è solo un riferimento: quei post sono stati misurati più tardi e in un periodo diverso.
- Il reel B dura fino a 60 secondi, quello A fino a 30: la visione media in secondi favorisce naturalmente il video più lungo. Per confrontarli guarda anche "Visione media / durata".
- Visualizzazioni e like variano molto da post a post anche per l'argomento: controlla nella tabella dei post che A e B abbiano serie simili, e fidati delle mediane più che delle medie.

