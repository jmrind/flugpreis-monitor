"""
Gäste/Buchungen pro Reise — die zentrale Stelle, an der du einstellst, wie viele
Passagiere an einer Verbindung interessiert / gebucht sind.

Bearbeite dazu die Datei bookings.json (kein Code-Eingriff nötig). Format:

    {
      "Rajasthan 16d · 29.10.2026": {"pax": 4, "ticketed": false},
      "South India 16d · 07.11.2026": {"pax": 2, "ticketed": true}
    }

- Der Schlüssel ist exakt das Watch-Label (Reise · Hinflugdatum).
- "pax"      = Anzahl gebuchter/interessierter Gäste (steuert Preisrechnung + Ticketing).
- "ticketed" = true, sobald die Tickets ausgestellt sind (stoppt die Erinnerung).

Reisen, die NICHT in bookings.json stehen, werden nur beobachtet (mit DEFAULT_PAX)
und lösen keine Ticketing-Erinnerung aus.
"""

from __future__ import annotations
import os
import json

_PATH = os.environ.get("BOOKINGS_FILE", "bookings.json")


def load() -> dict:
    if not os.path.exists(_PATH):
        return {}
    try:
        with open(_PATH) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[bookings] bookings.json ist kein gültiges JSON: {e}")
        return {}


def pax_for(label: str, default: int) -> int:
    entry = load().get(label)
    return int(entry.get("pax", default)) if entry else default


def is_booked(label: str) -> bool:
    return label in load()


def is_ticketed(label: str) -> bool:
    entry = load().get(label)
    return bool(entry and entry.get("ticketed"))
