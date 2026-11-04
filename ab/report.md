# Test A/B: variante A (originale) contro B (Film)

Aggiornato: 2026-11-04 19:53 · test attivo dal 2026-10-29 · numeri congelati a 7 giorni dalla pubblicazione.

Metriche principali: **visualizzazioni e like** del carosello e del reel, e per il reel il **tempo medio di visione**. Le altre metriche sono in fondo, solo come contesto.

## Com'è andata finora

**Troppo presto per un verdetto**: servono almeno 6 post congelati per variante (ora A = 0, B = 0). Con pochi post la differenza dipende più dall'argomento del singolo post che dal template.

Ancora nessun post congelato per entrambe le varianti.

## Metriche principali

### Carosello

| Metrica (media · mediana) | A (originale) (n=0) | B (Film) (n=0) | A prima del test (n=10) |
|---|---|---|---|
| Visualizzazioni | – | – | 54.8 · 52.5 |
| Like | – | – | 3.8 · 4 |
| Like ogni 100 visualizzazioni | – | – | 6.8 · 6.7 |

### Reel del post

| Metrica (media · mediana) | A (originale) (n=0) | B (Film) (n=0) | A prima del test (n=8) |
|---|---|---|---|
| Visualizzazioni | – | – | 99.9 · 102 |
| Like | – | – | 5.1 · 5 |
| Visione media | – | – | 3.8 s · 3.9 s |
| Visione media / durata del reel | – | – | 14.9% · 16.2% |

## Post del test

| Data | ID | Variante | Serie | Carosello: visual. | Carosello: like | Reel: visual. | Reel: like | Reel: visione media | Stato |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-04 | 19 | B | Inside the cup | 0 | 0 | 0 | 0 | – | in corso (0 gg) |
| 2026-11-02 | 13 | A | Common mistake | 51 | 3 | 53 | 5 | 4.8 s | in corso (2 gg) |
| 2026-10-30 | 12 | B | One word | 61 | 3 | 51 | 4 | 5.4 s | in corso (5 gg) |

In attesa dei 7 giorni: ID 12 (B), ID 13 (A), ID 19 (B).

## Altre metriche (contesto)

### Carosello: altre metriche

| Metrica (media · mediana) | A (originale) (n=0) | B (Film) (n=0) | A prima del test (n=10) |
|---|---|---|---|
| Reach | – | – | 28 · 28 |
| Salvataggi | – | – | 0 · 0 |
| Condivisioni | – | – | 0 · 0 |
| Interazioni / reach | – | – | 18.2% · 18.3% |
| Nuovi follower | – | – | 0 · 0 |

### Reel: altre metriche

| Metrica (media · mediana) | A (originale) (n=0) | B (Film) (n=0) | A prima del test (n=8) |
|---|---|---|---|
| Reach | – | – | 87.6 · 91.5 |
| Salvataggi | – | – | 0.1 · 0 |
| Condivisioni | – | – | 0.1 · 0 |
| Interazioni / reach | – | – | 10.0% · 8.5% |

## Come leggerlo

- Ogni nuovo post riceve A o B a turno (scripts/ab.py): così le due varianti escono negli stessi giorni e con argomenti misti.
- I numeri vengono congelati quando il post compie i giorni indicati sopra, così ogni post è misurato alla stessa età. "A prima del test" è solo un riferimento: quei post sono stati misurati più tardi e in un periodo diverso.
- Il reel B dura fino a 60 secondi, quello A fino a 30: la visione media in secondi favorisce naturalmente il video più lungo. Per confrontarli guarda anche "Visione media / durata".
- Visualizzazioni e like variano molto da post a post anche per l'argomento: controlla nella tabella dei post che A e B abbiano serie simili, e fidati delle mediane più che delle medie.

