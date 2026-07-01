"""
Zentrale Konfiguration: globale Einstellungen + alle Samsara-Strecken.

Datumsangaben hier im Format TT.MM.JJJJ; Umwandlung nach ISO passiert automatisch.
Gästezahlen pro Reise NICHT hier, sondern in bookings.json (siehe bookings.py).
"""

from models import Watch
import bookings

# ----------------------------------------------------------------------------
# GLOBALE EINSTELLUNGEN
# ----------------------------------------------------------------------------

CURRENCY = "EUR"
DEFAULT_PAX = 2                  # Gäste, wenn eine Reise nicht in bookings.json steht
ALERT_DROP_PER_PERSON = 50.0     # Mail-Alert ab diesem Preisrückgang pro Person
HISTORY_DAYS_FOR_STATS = 90      # Zeitfenster für Statistik/Chart

# Ticketing-Erinnerung
TICKETING_LEAD_DAYS = 25         # Tickets müssen ~3,5 Wochen vor Abflug ausgestellt sein
REMINDER_WINDOW_DAYS = 4         # so viele Tage vor der Deadline beginnt die Erinnerung

# Aufgabegepäck-Fallback (Gebühr je Richtung/Person), falls Tarif kein Gepäck enthält.
BAG_FEES = {"LH": 0.0, "EK": 0.0, "QR": 0.0, "AI": 0.0, "_default": 30.0}


# ----------------------------------------------------------------------------
# SAMSARA-STRECKEN
# ----------------------------------------------------------------------------

# --- Gruppe A: LH DIREKT, FRA <-> DEL, mit Freigepäck ------------------------
LH_TRIPS = {
    "Rajasthan 16d": [
        ("29.10.2026", "13.11.2026"), ("12.11.2026", "27.11.2026"),
        ("03.12.2026", "18.12.2026"), ("20.12.2026", "04.01.2027"),
        ("04.02.2027", "19.02.2027"), ("18.02.2027", "05.03.2027"),
        ("04.03.2027", "19.03.2027"), ("18.03.2027", "02.04.2027"),
        ("25.03.2027", "09.04.2027"),
    ],
    "Rajasthan 18d": [
        ("06.11.2026", "23.11.2026"), ("18.12.2026", "04.01.2027"),
        ("29.01.2027", "15.02.2027"), ("26.02.2027", "15.03.2027"),
        ("12.03.2027", "29.03.2027"), ("26.03.2027", "12.04.2027"),
    ],
    "North India 14d": [
        ("09.11.2026", "22.11.2026"), ("07.12.2026", "20.12.2026"),
        ("01.02.2027", "14.02.2027"), ("15.02.2027", "28.02.2027"),
        ("15.03.2027", "28.03.2027"), ("29.03.2027", "11.04.2027"),
    ],
    "Safari 14d": [
        ("07.11.2026", "20.11.2026"), ("06.02.2027", "19.02.2027"),
        ("06.03.2027", "19.03.2027"), ("24.03.2027", "06.04.2027"),
        ("10.04.2027", "23.04.2027"), ("01.05.2027", "14.05.2027"),
    ],
}

# --- Gruppe B: SOUTH INDIA (FRA->MAA hin, COK->FRA zurück; EK via DXB / QR via DOH)
SOUTH_TRIPS = {
    "South India 16d": [
        ("07.11.2026", "22.11.2026"), ("19.12.2026", "03.01.2027"),
        ("09.01.2027", "24.01.2027"), ("13.02.2027", "28.02.2027"),
        ("27.02.2027", "14.03.2027"), ("13.03.2027", "28.03.2027"),
    ],
}


def _apply_booking(w: Watch) -> Watch:
    """Setzt Gästezahl + Buchungsstatus aus bookings.json."""
    w.adults = bookings.pax_for(w.label, DEFAULT_PAX)
    w.booked = bookings.is_booked(w.label)
    w.ticketed = bookings.is_ticketed(w.label)
    return w


def samsara_watches() -> list[Watch]:
    watches: list[Watch] = []

    for trip, dates in LH_TRIPS.items():
        for dep, ret in dates:
            watches.append(_apply_booking(Watch(
                company="Samsara", label=f"{trip} · {dep}",
                origin="FRA", destination="DEL",
                depart_date=dep, return_date=ret,
                carriers=["LH"], max_stops=0,
                cabin="economy", checked_bag=True)))

    for trip, dates in SOUTH_TRIPS.items():
        for dep, ret in dates:
            watches.append(_apply_booking(Watch(
                company="Samsara", label=f"{trip} · {dep}",
                origin="FRA", destination="MAA",
                depart_date=dep, return_date=ret, return_origin="COK",
                carriers=["EK", "QR"], max_stops=1,
                cabin="economy", checked_bag=True)))

    return watches
