"""Datenmodelle, gemeinsam von Samsara und Taj Reisen genutzt."""

from __future__ import annotations
import datetime as dt
import hashlib
from dataclasses import dataclass, field


def to_iso(d: str) -> str:
    """'29.10.2026' -> '2026-10-29'. Lässt ISO-Strings unverändert."""
    if "-" in d and d[:4].isdigit():
        return d
    return dt.datetime.strptime(d, "%d.%m.%Y").strftime("%Y-%m-%d")


@dataclass
class Flight:
    """Ein einzelner Flug-Leg, z.B. aus einem Reiseverlauf extrahiert."""
    date: str                 # ISO
    origin: str               # IATA
    destination: str          # IATA
    carrier: str = ""         # IATA-Airline-Code, z.B. "LH"
    cabin: str = ""
    depart_time: str = ""
    arrive_time: str = ""
    checked_bag: bool | None = None
    raw: str = ""


@dataclass
class Watch:
    """Eine überwachte Verbindung (Round-Trip oder One-Way)."""
    company: str
    label: str
    origin: str
    destination: str
    depart_date: str                     # TT.MM.JJJJ oder ISO
    return_date: str | None = None
    return_origin: str | None = None
    carriers: list[str] = field(default_factory=list)
    max_stops: int | None = None
    cabin: str = "economy"
    checked_bag: bool = True
    adults: int = 1                      # = Anzahl interessierter/gebuchter Gäste
    booked: bool = False                 # echte Buchung -> Ticketing-Erinnerung
    ticketed: bool = False               # Tickets bereits ausgestellt?
    kind: str = "roundtrip"              # "roundtrip" | "oneway-domestic" ...

    def __post_init__(self):
        self.depart_date = to_iso(self.depart_date)
        if self.return_date:
            self.return_date = to_iso(self.return_date)
        if self.return_origin is None:
            self.return_origin = self.destination

    @property
    def key(self) -> str:
        base = "|".join([
            self.company, self.origin, self.destination,
            self.depart_date, self.return_date or "",
            self.return_origin or "", ",".join(self.carriers),
            str(self.max_stops), self.cabin, self.kind,
        ])
        return hashlib.sha1(base.encode()).hexdigest()[:12]

    @property
    def depart_dt(self) -> dt.date:
        return dt.date.fromisoformat(self.depart_date)

    def ticketing_deadline(self, lead_days: int) -> dt.date:
        """Datum, bis zu dem Tickets ausgestellt sein müssen."""
        return self.depart_dt - dt.timedelta(days=lead_days)

    def days_to_deadline(self, lead_days: int, today: dt.date | None = None) -> int:
        today = today or dt.date.today()
        return (self.ticketing_deadline(lead_days) - today).days

    def describe(self) -> str:
        legs = f"{self.origin}->{self.destination} {self.depart_date}"
        if self.return_date:
            legs += f" / {self.return_origin}->{self.origin} {self.return_date}"
        car = "/".join(self.carriers) or "any"
        stops = "nonstop" if self.max_stops == 0 else (
            "any" if self.max_stops is None else f"<={self.max_stops} stops")
        return f"{legs} [{car}, {stops}, {self.cabin}]"


@dataclass
class Offer:
    """Ein einzelnes Flugangebot, normalisiert über alle Provider hinweg."""
    price_total: float
    carrier: str = ""
    includes_checked_bag: bool = False
    stops: int | None = None
    currency: str = "EUR"
    booking_link: str | None = None
    raw: dict = field(default_factory=dict)
