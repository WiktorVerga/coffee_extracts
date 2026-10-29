#!/usr/bin/env python3
"""
A/B test report: reads the Instagram insights of every published post (the
carousel and its reel) and compares variant A with variant B.
Main metrics (chosen by the owner): views and likes of carousel and reel, and
the average watch time of the reel. The others are shown as context.

Usage:
    python scripts/ab_report.py              # fetch new numbers, rewrite the report
    python scripts/ab_report.py --offline    # no API calls: rebuild the report from ab/metrics.json
    python scripts/ab_report.py --refresh-all  # fetch again even the posts already frozen

What it does:
  - takes from log.json every post whose latest entry is "published" (with a
    media_id), and its variant (posts before the test have none: they are
    shown apart, as "A before the test", for reference only)
  - for each post younger than config.json -> ab_test.measure_after_days (7)
    it stores the latest numbers; the first time a post is that old or older
    it FREEZES the numbers ("frozen"): the comparison only uses frozen numbers,
    so every post is measured at the same age. Frozen posts are not fetched again.
  - writes ab/metrics.json (data) and ab/report.md (the report, in Italian)

Never fails the routine: API errors (expired token, missing
instagram_business_manage_insights permission, metric not available...) are
written into the report and printed as WARNING, and the exit code is still 0.

Metrics (Instagram API with Instagram Login, graph.instagram.com):
  carousel: reach, views, likes, comments, saved, shares, total_interactions,
            follows, profile_visits
  reel:     reach, views, likes, comments, saved, shares, total_interactions,
            ig_reels_avg_watch_time
"""
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ab  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "log.json"
OUT_DIR = ROOT / "ab"
METRICS = OUT_DIR / "metrics.json"
REPORT = OUT_DIR / "report.md"
TZ = ZoneInfo("Europe/Rome")

POST_METRICS = ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions",
                "follows", "profile_visits"]
REEL_METRICS = ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions",
                "ig_reels_avg_watch_time"]
MIN_POSTS = 6   # per variant, before the report calls a trend


def now():
    return datetime.now(TZ)


def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    except (TypeError, ValueError):
        return None


def published_posts():
    """{folder: log entry} for posts whose latest entry is published with a media_id."""
    latest = {}
    for e in json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []:
        if e.get("folder"):
            latest[e["folder"]] = e
    return {f: e for f, e in latest.items() if e.get("status") == "published" and e.get("media_id")}


def read_value(item):
    if "total_value" in item:
        return item["total_value"].get("value")
    vals = item.get("values") or []
    return vals[0].get("value") if vals else None


def fetch(call, media_id, metrics):
    """All metrics in one call; if Instagram refuses the set, one by one (skipping the ones it refuses)."""
    out, errors = {}, []
    try:
        r = call("GET", f"{media_id}/insights", {"metric": ",".join(metrics)})
        for item in r.get("data", []):
            out[item["name"]] = read_value(item)
        return out, errors
    except Exception as e:  # noqa: BLE001
        first = str(e)
    if '"code":190' in first.replace(" ", "") or "access token" in first.lower():
        return out, [first[:300]]   # token problem: no point in trying metric by metric
    for m in metrics:
        try:
            r = call("GET", f"{media_id}/insights", {"metric": m})
            for item in r.get("data", []):
                out[item["name"]] = read_value(item)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{m}: {str(e)[:200]}")
    return out, errors


def update(store, refresh_all=False, offline=False):
    s = ab.settings()
    days = float(s.get("measure_after_days", 7))
    started = s.get("started_on", "")
    posts = published_posts()
    warnings = []
    call = None
    if not offline:
        try:
            from publish import call as api_call   # same token handling as publishing
            call = api_call
        except Exception as e:  # noqa: BLE001
            warnings.append(f"API not available: {e}")
    t = now()
    for folder, e in posts.items():
        rec = store.setdefault(folder, {})
        pub = parse_date(e.get("date"))
        age = round((t - pub).total_seconds() / 86400, 2) if pub else None
        in_test = bool(e.get("variant")) and (not started or e.get("date", "") >= started)
        rec.update({
            "id": e.get("id"), "idea": e.get("idea"), "series": e.get("series", ""),
            "variant": e.get("variant") or "", "in_test": in_test,
            "published_at": e.get("date"), "permalink": e.get("permalink", ""), "age_days": age,
        })
        reel_pub = ROOT / folder / "reel-publication.json"
        reel_id = ""
        if reel_pub.exists():
            try:
                reel_id = json.loads(reel_pub.read_text(encoding="utf-8")).get("media_id", "")
            except json.JSONDecodeError:
                pass
        reel_meta = ROOT / folder / "reel-meta.json"
        if reel_id and reel_meta.exists():
            try:
                rec.setdefault("reel", {})["duration"] = json.loads(reel_meta.read_text(encoding="utf-8")).get("duration")
            except json.JSONDecodeError:
                pass
        for kind, media_id, metrics in (("post", e["media_id"], POST_METRICS), ("reel", reel_id, REEL_METRICS)):
            if not media_id:
                continue
            m = rec.setdefault(kind, {})
            m["media_id"] = media_id
            if call is None or (m.get("frozen") and not refresh_all):
                continue
            values, errors = fetch(call, media_id, metrics)
            if errors:
                m["errors"] = errors
                warnings.append(f"{folder} ({kind}): " + "; ".join(errors)[:300])
            else:
                m.pop("errors", None)
            if values:
                snap = {"fetched_at": t.strftime("%Y-%m-%d %H:%M"), "age_days": age, **values}
                m["latest"] = snap
                if age is not None and age >= days and not m.get("frozen"):
                    m["frozen"] = snap
    return warnings


# ── report ───────────────────────────────────────────────────────────
def rate(num, den):
    return num / den if den else None


def derived(snap, duration=None):
    reach = snap.get("reach") or 0
    views, likes = snap.get("views"), snap.get("likes")
    saved, shares = snap.get("saved") or 0, snap.get("shares") or 0
    inter = snap.get("total_interactions")
    if inter is None:
        inter = saved + shares + (likes or 0) + (snap.get("comments") or 0)
    watch = snap.get("ig_reels_avg_watch_time")
    watch = watch / 1000 if watch else None          # Instagram gives milliseconds
    return {
        "views": views, "likes": likes,
        "likes_per_100_views": rate((likes or 0) * 100, views) if views else None,
        "avg_watch_s": watch,
        "watch_share": rate(watch, duration) if watch and duration else None,
        "reach": reach, "saved": saved, "shares": shares,
        "engagement_rate": rate(inter, reach),
        "follows": snap.get("follows"),
    }


def agg(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None, None
    return statistics.mean(vals), statistics.median(vals)


def fmt(v, kind="n"):
    if v is None:
        return "–"
    if kind == "%":
        return f"{v * 100:.1f}%"
    if kind == "s":
        return f"{v:.1f} s"
    return f"{v:,.0f}".replace(",", ".") if v >= 100 else f"{v:.1f}".rstrip("0").rstrip(".")


def group_of(rec):
    if rec.get("in_test"):
        return rec.get("variant") or "A"
    return "A0"


GROUP_NAME = {"A": "A (originale)", "B": "B (Film)", "A0": "A prima del test"}
GROUPS = ("A", "B", "A0")
# (label, key, format): the main metrics first, chosen by the owner
POST_MAIN = [("Visualizzazioni", "views", "n"), ("Like", "likes", "n"),
             ("Like ogni 100 visualizzazioni", "likes_per_100_views", "n")]
REEL_MAIN = [("Visualizzazioni", "views", "n"), ("Like", "likes", "n"),
             ("Visione media", "avg_watch_s", "s"), ("Visione media / durata del reel", "watch_share", "%")]
POST_MORE = [("Reach", "reach", "n"), ("Salvataggi", "saved", "n"), ("Condivisioni", "shares", "n"),
             ("Interazioni / reach", "engagement_rate", "%"), ("Nuovi follower", "follows", "n")]
REEL_MORE = [("Reach", "reach", "n"), ("Salvataggi", "saved", "n"), ("Condivisioni", "shares", "n"),
             ("Interazioni / reach", "engagement_rate", "%")]


def frozen(rec, kind):
    m = rec.get(kind) or {}
    return derived(m["frozen"], m.get("duration")) if m.get("frozen") else None


def build_report(store, warnings):
    s = ab.settings()
    days = s.get("measure_after_days", 7)
    lines = [
        "# Test A/B: variante A (originale) contro B (Film)",
        "",
        f"Aggiornato: {now().strftime('%Y-%m-%d %H:%M')} · test {'attivo' if s.get('enabled') else 'spento'}"
        f" dal {s.get('started_on') or '–'} · numeri congelati a {days} giorni dalla pubblicazione.",
        "",
        "Metriche principali: **visualizzazioni e like** del carosello e del reel, e per il reel il"
        " **tempo medio di visione**. Le altre metriche sono in fondo, solo come contesto.",
        "",
    ]
    groups = {g: [] for g in GROUPS}
    pending = []
    for folder, rec in sorted(store.items(), key=lambda kv: kv[1].get("published_at") or ""):
        g = group_of(rec)
        if (rec.get("post") or {}).get("frozen"):
            groups[g].append(rec)
        elif g != "A0":
            pending.append(rec)

    means = {}

    def table(kind, cols, title):
        n = {g: sum(1 for r in groups[g] if frozen(r, kind)) for g in GROUPS}
        out = [f"### {title}", "", "| Metrica (media · mediana) | " +
               " | ".join(f"{GROUP_NAME[g]} (n={n[g]})" for g in GROUPS) + " |", "|---|" + "---|" * len(GROUPS)]
        for label, key, k in cols:
            cells = []
            for g in GROUPS:
                mean, med = agg([d[key] for d in (frozen(r, kind) for r in groups[g]) if d])
                means[(kind, g, key)] = mean
                cells.append("–" if mean is None else f"{fmt(mean, k)} · {fmt(med, k)}")
            out.append(f"| {label} | " + " | ".join(cells) + " |")
        return out

    post_main = table("post", POST_MAIN, "Carosello")
    reel_main = table("reel", REEL_MAIN, "Reel del post")
    post_more = table("post", POST_MORE, "Carosello: altre metriche")
    reel_more = table("reel", REEL_MORE, "Reel: altre metriche")

    na, nb = len(groups["A"]), len(groups["B"])
    lines += ["## Com'è andata finora", ""]
    if na < MIN_POSTS or nb < MIN_POSTS:
        lines += [f"**Troppo presto per un verdetto**: servono almeno {MIN_POSTS} post congelati per variante"
                  f" (ora A = {na}, B = {nb}). Con pochi post la differenza dipende più dall'argomento"
                  " del singolo post che dal template.", ""]
    trend = []
    for kind, key, label, k in (("post", "views", "visualizzazioni del carosello", "n"),
                                ("post", "likes", "like del carosello", "n"),
                                ("reel", "views", "visualizzazioni del reel", "n"),
                                ("reel", "likes", "like del reel", "n"),
                                ("reel", "avg_watch_s", "visione media del reel", "s")):
        a, b = means.get((kind, "A", key)), means.get((kind, "B", key))
        if a is None or b is None:
            continue
        diff = f"{(b - a) / a * 100:+.0f}% per B" if a else "A a zero"
        trend.append(f"- {label}: A {fmt(a, k)}, B {fmt(b, k)} ({diff})")
    lines += (["Tendenze (medie dei post congelati):"] + trend) if trend else ["Ancora nessun post congelato per entrambe le varianti."]
    lines += ["", "## Metriche principali", ""] + post_main + [""] + reel_main + [""]

    lines += ["## Post del test", "",
              "| Data | ID | Variante | Serie | Carosello: visual. | Carosello: like | Reel: visual. | Reel: like |"
              " Reel: visione media | Stato |", "|---|---|---|---|---|---|---|---|---|---|"]
    for rec in sorted(store.values(), key=lambda r: r.get("published_at") or "", reverse=True):
        if not rec.get("in_test"):
            continue
        post, reel = rec.get("post") or {}, rec.get("reel") or {}
        ps, rs = post.get("frozen") or post.get("latest"), reel.get("frozen") or reel.get("latest")
        d = derived(ps) if ps else {}
        r = derived(rs, reel.get("duration")) if rs else {}
        state = "congelato" if post.get("frozen") else (
            f"in corso ({fmt(rec.get('age_days'))} gg)" if ps else "nessun dato ancora")
        if post.get("errors") or reel.get("errors"):
            state += " · errore API"
        lines.append(f"| {(rec.get('published_at') or '')[:10]} | {rec.get('id')} | {rec.get('variant')} |"
                     f" {rec.get('series', '')} | {fmt(d.get('views'))} | {fmt(d.get('likes'))} |"
                     f" {fmt(r.get('views'))} | {fmt(r.get('likes'))} | {fmt(r.get('avg_watch_s'), 's')} | {state} |")
    if pending:
        lines += ["", f"In attesa dei {days} giorni: " + ", ".join(
            f"ID {r.get('id')} ({r.get('variant')})" for r in pending) + "."]
    lines += ["", "## Altre metriche (contesto)", ""] + post_more + [""] + reel_more + [""]
    lines += ["## Come leggerlo", "",
              "- Ogni nuovo post riceve A o B a turno (scripts/ab.py): così le due varianti escono negli stessi"
              " giorni e con argomenti misti.",
              "- I numeri vengono congelati quando il post compie i giorni indicati sopra, così ogni post è"
              " misurato alla stessa età. \"A prima del test\" è solo un riferimento: quei post sono stati"
              " misurati più tardi e in un periodo diverso.",
              "- Il reel B dura fino a 60 secondi, quello A fino a 30: la visione media in secondi favorisce"
              " naturalmente il video più lungo. Per confrontarli guarda anche \"Visione media / durata\".",
              "- Visualizzazioni e like variano molto da post a post anche per l'argomento: controlla nella"
              " tabella dei post che A e B abbiano serie simili, e fidati delle mediane più che delle medie.",
              ""]
    if warnings:
        lines += ["## Avvisi dell'ultimo aggiornamento", ""] + [f"- {w}" for w in warnings] + [""]
        if any("manage_insights" in w or "permission" in w.lower() or "(#10)" in w for w in warnings):
            lines += ["Il token Instagram potrebbe non avere il permesso `instagram_business_manage_insights`:"
                      " va aggiunto all'app e il token va rigenerato.", ""]
    return "\n".join(lines), {"A": na, "B": nb, "pending": len(pending), "means": means}


def main():
    offline = "--offline" in sys.argv
    refresh_all = "--refresh-all" in sys.argv
    OUT_DIR.mkdir(exist_ok=True)
    store = json.loads(METRICS.read_text(encoding="utf-8")) if METRICS.exists() else {}
    warnings = update(store, refresh_all=refresh_all, offline=offline)
    METRICS.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    text, summary = build_report(store, warnings)
    REPORT.write_text(text + "\n", encoding="utf-8")
    for w in warnings:
        print("WARNING:", w)
    m = summary["means"]
    pv = lambda g: fmt(m.get(("post", g, "views")))
    rw = lambda g: fmt(m.get(("reel", g, "avg_watch_s")), "s")
    print(f"A/B report: frozen posts A={summary['A']} B={summary['B']}, waiting={summary['pending']}; "
          f"carousel views A={pv('A')} B={pv('B')}; reel avg watch A={rw('A')} B={rw('B')} -> ab/report.md")


if __name__ == "__main__":
    main()
