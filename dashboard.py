"""
Schreibt data.json: pro Strecke aktueller Preis, Statistik, Marge, Verlauf und
Metadaten. Diese Datei liest das Bedienpanel (index.html) für die Übersicht.

  python dashboard.py
"""

from __future__ import annotations
import json
import datetime as dt

import config
import storage


def de(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return dt.date.fromisoformat(iso).strftime("%d.%m.%Y")
    except ValueError:
        return iso


def _ticket_state(booked, ticketed, deadline, days_left):
    if not booked:
        return "monitor", "nur beobachtet"
    if ticketed:
        return "ticketed", "Tickets ausgestellt"
    if days_left < 0:
        return "overdue", f"überfällig seit {abs(days_left)} T"
    if days_left <= config.REMINDER_WINDOW_DAYS:
        return "soon", f"Ticketing in {days_left} T"
    return "scheduled", f"Ticketing bis {deadline.strftime('%d.%m.')}"


def build(out_path: str = "data.json") -> str:
    today = dt.date.today()
    metas = {m["watch_key"]: m for m in storage.list_watches()}
    cards, booked_n, margins = [], 0, []
    next_deadline = None

    for r in storage.all_watch_keys():
        key = r["watch_key"]
        m = metas.get(key, {})
        st = storage.stats(key, config.HISTORY_DAYS_FOR_STATS)
        if not st:
            continue
        hist = storage.history(key, config.HISTORY_DAYS_FOR_STATS)
        depart = dt.date.fromisoformat(r["depart_date"])
        deadline = depart - dt.timedelta(days=config.TICKETING_LEAD_DAYS)
        days_left = (deadline - today).days
        booked = bool(m.get("booked"))
        ticketed = bool(m.get("ticketed"))
        state, state_label = _ticket_state(booked, ticketed, deadline, days_left)
        if booked:
            booked_n += 1
            if not ticketed and depart >= today and (
                    next_deadline is None or deadline < next_deadline[0]):
                next_deadline = (deadline, f"{r['company']} · {r['origin']}->{r['destination']}")
        calc = m.get("calc_price")
        margin = round(calc - st["current"], 2) if calc else None
        if margin is not None:
            margins.append(margin)
        vals = [p for _, p in hist]
        change_last = round(vals[-1] - vals[-2], 2) if len(vals) >= 2 else None
        trip = (r["label"] or "").split(" · ")[0]
        cards.append({
            "slug": f"{r['company']}|{r['label']}",
            "company": r["company"] or "", "trip": trip, "kind": m.get("kind", "roundtrip"),
            "route": f"{r['origin']} → {r['destination']}",
            "dep": de(r["depart_date"]), "ret": de(r["return_date"]), "dep_iso": r["depart_date"],
            "pax": int(m.get("adults") or 1),
            "state": state, "state_label": state_label, "days_left": days_left, "booked": booked,
            "current": st["current"], "avg": st["avg"], "min": st["min"], "max": st["max"],
            "n": st["count"], "vs_avg": st["vs_avg"], "calc": calc, "margin": margin,
            "change_last": change_last,
            "labels": [f"{ts[8:10]}.{ts[5:7]}." for ts, _ in hist], "values": vals,
        })

    avg_margin = round(sum(margins) / len(margins), 2) if margins else None
    out = {
        "generated": today.strftime("%d.%m.%Y"),
        "currency": config.CURRENCY,
        "summary": {
            "watched": len(cards), "booked": booked_n, "avg_margin": avg_margin,
            "next_deadline": de(next_deadline[0].isoformat()) if next_deadline else "—",
            "next_deadline_sub": next_deadline[1] if next_deadline else "keine gebuchte Reise",
        },
        "cards": cards,
    }
    with open(out_path, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"data.json geschrieben ({len(cards)} Strecken)")
    return out_path


if __name__ == "__main__":
    build()
