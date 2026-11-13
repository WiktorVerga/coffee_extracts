# Test A/B: variante A (originale) contro B (Film)

Aggiornato: 2026-11-13 19:46 · test attivo dal 2026-10-29 · numeri congelati a 7 giorni dalla pubblicazione.

Metriche principali: **visualizzazioni e like** del carosello e del reel, e per il reel il **tempo medio di visione**. Le altre metriche sono in fondo, solo come contesto.

## Com'è andata finora

**Troppo presto per un verdetto**: servono almeno 6 post congelati per variante (ora A = 2, B = 2). Con pochi post la differenza dipende più dall'argomento del singolo post che dal template.

Tendenze (medie dei post congelati):
- visualizzazioni del carosello: A 86, B 90 (+5% per B)
- like del carosello: A 4, B 4 (+0% per B)
- visualizzazioni del reel: A 162, B 108 (-33% per B)
- like del reel: A 9.5, B 4 (-58% per B)
- visione media del reel: A 4.7 s, B 5.5 s (+17% per B)

## Metriche principali

### Carosello

| Metrica (media · mediana) | A (originale) (n=2) | B (Film) (n=2) | A prima del test (n=10) |
|---|---|---|---|
| Visualizzazioni | 86 · 86 | 90 · 90 | 54.8 · 52.5 |
| Like | 4 · 4 | 4 · 4 | 3.8 · 4 |
| Like ogni 100 visualizzazioni | 4.8 · 4.8 | 4.5 · 4.5 | 6.8 · 6.7 |

### Reel del post

| Metrica (media · mediana) | A (originale) (n=2) | B (Film) (n=2) | A prima del test (n=8) |
|---|---|---|---|
| Visualizzazioni | 162 · 162 | 108 · 108 | 99.9 · 102 |
| Like | 9.5 · 9.5 | 4 · 4 | 5.1 · 5 |
| Visione media | 4.7 s · 4.7 s | 5.5 s · 5.5 s | 3.8 s · 3.9 s |
| Visione media / durata del reel | 21.0% · 21.0% | 10.5% · 10.5% | 14.9% · 16.2% |

## Post del test

| Data | ID | Variante | Serie | Carosello: visual. | Carosello: like | Reel: visual. | Reel: like | Reel: visione media | Stato |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-13 | 23 | A | Common mistake | 0 | 0 | 0 | 0 | – | in corso (0 gg) |
| 2026-11-09 | 22 | B | One word | 101 | 7 | 662 | 20 | 11.0 s | in corso (4 gg) |
| 2026-11-06 | 21 | A | Side by side | 115 | 5 | 257 | 10 | 4.7 s | congelato |
| 2026-11-04 | 19 | B | Inside the cup | 118 | 5 | 164 | 4 | 5.9 s | congelato |
| 2026-11-02 | 13 | A | Common mistake | 57 | 3 | 66 | 9 | 4.8 s | congelato |
| 2026-10-30 | 12 | B | One word | 62 | 3 | 53 | 4 | 5.2 s | congelato |

In attesa dei 7 giorni: ID 22 (B), ID 23 (A).

## Altre metriche (contesto)

### Carosello: altre metriche

| Metrica (media · mediana) | A (originale) (n=2) | B (Film) (n=2) | A prima del test (n=10) |
|---|---|---|---|
| Reach | 38 · 38 | 39 · 39 | 28 · 28 |
| Salvataggi | 0 · 0 | 0 · 0 | 0 · 0 |
| Condivisioni | 0.5 · 0.5 | 0 · 0 | 0 · 0 |
| Interazioni / reach | 15.1% · 15.1% | 16.6% · 16.6% | 18.2% · 18.3% |
| Nuovi follower | 0 · 0 | 0 · 0 | 0 · 0 |

### Reel: altre metriche

| Metrica (media · mediana) | A (originale) (n=2) | B (Film) (n=2) | A prima del test (n=8) |
|---|---|---|---|
| Reach | 142 · 142 | 91.5 · 91.5 | 87.6 · 91.5 |
| Salvataggi | 1.5 · 1.5 | 0 · 0 | 0.1 · 0 |
| Condivisioni | 0.5 · 0.5 | 0 · 0 | 0.1 · 0 |
| Interazioni / reach | 11.9% · 11.9% | 8.6% · 8.6% | 10.0% · 8.5% |

## Come leggerlo

- Ogni nuovo post riceve A o B a turno (scripts/ab.py): così le due varianti escono negli stessi giorni e con argomenti misti.
- I numeri vengono congelati quando il post compie i giorni indicati sopra, così ogni post è misurato alla stessa età. "A prima del test" è solo un riferimento: quei post sono stati misurati più tardi e in un periodo diverso.
- Il reel B dura fino a 60 secondi, quello A fino a 30: la visione media in secondi favorisce naturalmente il video più lungo. Per confrontarli guarda anche "Visione media / durata".
- Visualizzazioni e like variano molto da post a post anche per l'argomento: controlla nella tabella dei post che A e B abbiano serie simili, e fidati delle mediane più che delle medie.

