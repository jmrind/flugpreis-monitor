"""
Zentrale Konfiguration. Die ÜBERWACHTEN FLÜGE stehen jetzt in flights.json und
werden im Bedienpanel bearbeitet (hinzufügen/entfernen/ändern). Hier stehen nur
noch globale Einstellungen + ein Fallback, falls flights.json fehlt.
"""

from __future__ import annotations
import os
import json

from models import Watch

# ----------------------------------------------------------------------------
# GLOBALE EINSTELLUNGEN
# ----------------------------------------------------------------------------

CURRENCY = "EUR"
DEFAULT_PAX = 2
ALERT_DROP_PER_PERSON = 50.0
HISTORY_DAYS_FOR_STATS = 90
TICKETING_LEAD_DAYS = 25          # ~3,5 Wochen vor Abflug
REMINDER_WINDOW_DAYS = 4
BAG_FEES = {"LH": 0.0, "EK": 0.0, "QR": 0.0, "AI": 0.0, "_default": 30.0}

FLIGHTS_FILE = os.environ.get("FLIGHTS_FILE", "flights.json")

# Fallback-Definitionen, falls flights.json (noch) nicht existiert.
_FALLBACK = {
    "trips": [
        {"company": "Samsara", "name": "Rajasthan 16d", "origin": "FRA",
         "destination": "DEL", "return_origin": "DEL", "carriers": ["LH"],
         "max_stops": 0, "cabin": "economy", "checked_bag": True,
         "calc_price": 935, "dates": [{"depart": "29.10.2026", "return": "13.11.2026"}]},
    ]
}


def _load_flights() -> dict:
    if os.path.exists(FLIGHTS_FILE):
        try:
            with open(FLIGHTS_FILE) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[config] flights.json ist kein gültiges JSON: {e} — nutze Fallback.")
    return _FALLBACK


def samsara_watches() -> list[Watch]:
    data = _load_flights()
    watches: list[Watch] = []
    for t in data.get("trips", []):
        for row in t.get("dates", []):
            dep = row["depart"]
            watches.append(Watch(
                company=t.get("company", "Samsara"),
                label=f"{t['name']} · {dep}",
                origin=t["origin"], destination=t["destination"],
                depart_date=dep, return_date=row.get("return"),
                return_origin=t.get("return_origin") or t["destination"],
                carriers=t.get("carriers", []),
                max_stops=t.get("max_stops"),
                cabin=t.get("cabin", "economy"),
                checked_bag=t.get("checked_bag", True),
                adults=int(row.get("pax", DEFAULT_PAX)),
                booked=bool(row.get("booked", False)),
                ticketed=bool(row.get("ticketed", False)),
                calc_price=t.get("calc_price"),
            ))
    return watches
