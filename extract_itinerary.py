"""
Taj Reisen: Reiseverlauf-PDF -> erkannte Flüge -> überwachbare Watch(es).

Primär extrahiert Claude die Flüge (robust gegenüber unterschiedlichen
Reiseverlauf-Layouts). Ohne API-Key greift ein Regex-Fallback, der auf das
Taj-Reisen-Format ("TT.MM.JJJJ - Stadt nach Stadt - Abflug: HH:MM ...")
zugeschnitten ist.
"""

from __future__ import annotations
import os
import re
import json

import requests
from pypdf import PdfReader

from models import Flight, Watch, to_iso
from iata import city_iata, airline_iata

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Ligaturen, die pypdf/pdftotext manchmal liefern (z.B. "Abﬂug").
_LIGATURES = {"\ufb01": "fi", "\ufb02": "fl", "\ufb00": "ff",
              "\ufb03": "ffi", "\ufb04": "ffl"}


def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    for lig, repl in _LIGATURES.items():
        text = text.replace(lig, repl)
    return text


# ----------------------------------------------------------------------------
# Claude-Extraktion (primär)
# ----------------------------------------------------------------------------

_PROMPT = """Extrahiere ALLE Flüge aus diesem Reiseverlauf. Gib AUSSCHLIESSLICH
ein JSON-Array zurück, ohne Markdown, ohne Erklärung. Jeder Flug:
{{"date":"YYYY-MM-DD","from_iata":"XXX","to_iata":"XXX","carrier_iata":"XX",
"cabin":"economy|premium_economy|business","depart_time":"HH:MM","arrive_time":"HH:MM",
"checked_bag":true|false}}
Nutze offizielle IATA-Codes (Berlin=BER, München=MUC, Frankfurt=FRA, Delhi=DEL,
Mumbai=BOM, Udaipur=UDR, Chennai=MAA, Kochi=COK). checked_bag=true wenn Freigepäck
erwähnt ist oder die Airline/Kabine es üblicherweise enthält. Reiseverlauf:

{text}"""


def flights_via_claude(text: str) -> list[Flight]:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 1500,
              "messages": [{"role": "user",
                            "content": _PROMPT.format(text=text[:12000])}]},
        timeout=60,
    )
    resp.raise_for_status()
    blocks = resp.json().get("content", [])
    out = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    out = out.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    data = json.loads(out)
    flights = []
    for f in data:
        flights.append(Flight(
            date=f["date"], origin=f["from_iata"], destination=f["to_iata"],
            carrier=f.get("carrier_iata", ""), cabin=f.get("cabin", ""),
            depart_time=f.get("depart_time", ""), arrive_time=f.get("arrive_time", ""),
            checked_bag=f.get("checked_bag"),
        ))
    return flights


# ----------------------------------------------------------------------------
# Regex-Fallback (Taj-Reisen-Format)
# ----------------------------------------------------------------------------

_HEADER = re.compile(r"Flugverbindung mit (.+?) in der ([\w\- ]+?)(?:\s*\(([^)]*)\))?:",
                     re.IGNORECASE)
_LEG = re.compile(
    r"(\d{2}\.\d{2}\.\d{4})\s*-\s*(.+?)\s+nach\s+(.+?)\s*-\s*Abflug:\s*(\d{1,2}:\d{2})"
    r"\s*-\s*Ankunft:\s*(\d{1,2}:\d{2})", re.IGNORECASE)


def flights_via_regex(text: str) -> list[Flight]:
    lines = text.splitlines()
    flights: list[Flight] = []
    cur_airline, cur_cabin, cur_bag = "", "", None

    for line in lines:
        h = _HEADER.search(line)
        if h:
            cur_airline = airline_iata(h.group(1)) or h.group(1).strip()
            cur_cabin = ("premium_economy" if "premium" in h.group(2).lower()
                         else "business" if "business" in h.group(2).lower()
                         else "economy")
            cur_bag = True if h.group(3) and "gepäck" in h.group(3).lower() else None
            continue
        m = _LEG.search(line)
        if m:
            o = city_iata(m.group(2)) or m.group(2).strip()[:3].upper()
            d = city_iata(m.group(3)) or m.group(3).strip()[:3].upper()
            per_leg_cabin = "economy" if "(economy" in line.lower() else cur_cabin
            flights.append(Flight(
                date=to_iso(m.group(1)), origin=o, destination=d,
                carrier=cur_airline, cabin=per_leg_cabin or "economy",
                depart_time=m.group(4), arrive_time=m.group(5),
                checked_bag=cur_bag, raw=line.strip(),
            ))
    return flights


def extract_flights(pdf_path: str, prefer_claude: bool = True) -> list[Flight]:
    text = extract_text(pdf_path)
    if prefer_claude and ANTHROPIC_API_KEY:
        try:
            flights = flights_via_claude(text)
            if flights:
                return flights
        except Exception as e:
            print(f"[Taj] Claude-Extraktion fehlgeschlagen ({e}), nutze Regex.")
    return flights_via_regex(text)


# ----------------------------------------------------------------------------
# Watches aus Flügen ableiten
# ----------------------------------------------------------------------------

def build_watches(flights: list[Flight], adults: int = 2,
                  include_domestic: bool = False,
                  booked: bool = True, ticketed: bool = False) -> list[Watch]:
    """Leitet Watches aus den erkannten Flügen ab.

    Standard: die preisrelevante internationale Round-Trip. Heuristik: nach
    Reisetag gruppieren; erster Reisetag = Hinreise, letzter = Rückreise.
    Beispiel: 04.02 BER->MUC->DEL und 28.02 BOM->FRA->BER  =>  Watch BER<->BOM.

    include_domestic=True: zusätzlich je EINE One-Way-Watch pro Inlandsflug
    (z.B. UDR->BOM). Inlandsflüge werden über das Länder-Mapping erkannt.
    """
    from iata import is_domestic

    if not flights:
        return []
    by_day: dict[str, list[Flight]] = {}
    for f in sorted(flights, key=lambda x: (x.date, x.depart_time)):
        by_day.setdefault(f.date, []).append(f)

    days = sorted(by_day)
    out_day, ret_day = by_day[days[0]], by_day[days[-1]]

    origin = out_day[0].origin
    dest = out_day[-1].destination
    ret_origin = ret_day[0].origin
    carriers = sorted({f.carrier for f in out_day + ret_day if f.carrier})
    nonstop = (len(out_day) == 1 and len(ret_day) == 1)

    watches = [Watch(
        company="Taj Reisen",
        label=f"{origin}<->{dest} · {days[0]}",
        origin=origin, destination=dest,
        depart_date=days[0], return_date=days[-1], return_origin=ret_origin,
        carriers=carriers, max_stops=0 if nonstop else 1,
        cabin=out_day[-1].cabin or "economy", checked_bag=True,
        adults=adults, booked=booked, ticketed=ticketed, kind="roundtrip",
    )]

    if include_domestic:
        edge_days = {days[0], days[-1]}     # Hin-/Rücktag sind schon im Round-Trip
        for f in flights:
            if f.date in edge_days:
                continue
            if is_domestic(f.origin, f.destination):
                watches.append(Watch(
                    company="Taj Reisen",
                    label=f"Inland {f.origin}->{f.destination} · {f.date}",
                    origin=f.origin, destination=f.destination,
                    depart_date=f.date, return_date=None,
                    carriers=[f.carrier] if f.carrier else [],
                    max_stops=0, cabin=f.cabin or "economy",
                    checked_bag=bool(f.checked_bag), adults=adults,
                    booked=booked, ticketed=ticketed, kind="oneway-domestic",
                ))
    return watches


if __name__ == "__main__":
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    domestic = "--domestic" in sys.argv
    if not args:
        print("Nutzung: python extract_itinerary.py <reiseverlauf.pdf> [--domestic]")
        raise SystemExit(1)
    fl = extract_flights(args[0])
    print(f"\n{len(fl)} Flüge erkannt:")
    for f in fl:
        print(f"  {f.date} {f.origin}->{f.destination} {f.carrier or '?':<3} "
              f"{f.cabin:<16} {f.depart_time}-{f.arrive_time}")
    print(f"\nAbgeleitete Watch(es) (Inlandsflüge: {'an' if domestic else 'aus'}):")
    for w in build_watches(fl, include_domestic=domestic):
        print(f"  [{w.kind}] " + w.describe())
