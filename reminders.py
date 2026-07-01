"""
Ticketing-Erinnerung: Tickets müssen ~3,5 Wochen vor Abflug ausgestellt werden.

Für jede GEBUCHTE, noch nicht ausgestellte Reise wird die Deadline berechnet
(Abflug − TICKETING_LEAD_DAYS). Nähert sich die Deadline (innerhalb von
REMINDER_WINDOW_DAYS) oder ist sie überschritten, geht eine Mail raus — höchstens
einmal pro Tag und Reise.
"""

from __future__ import annotations
import datetime as dt

import config
import storage
import alerts
from models import Watch


def _reminder_text(watch: Watch, deadline: dt.date, days_left: int) -> tuple[str, str]:
    when = deadline.strftime("%d.%m.%Y")
    if days_left < 0:
        head = f"ÜBERFÄLLIG: Ticketing-Deadline war am {when}"
    elif days_left == 0:
        head = f"HEUTE: Ticketing-Deadline ({when})"
    else:
        head = f"In {days_left} Tag(en): Ticketing-Deadline am {when}"

    subject = f"Ticketing {watch.company} · {watch.origin}->{watch.destination} " \
              f"{watch.depart_date} — {head}"
    body = "\n".join([
        head,
        "",
        f"Reise:   {watch.label}",
        f"Strecke: {watch.describe()}",
        f"Abflug:  {watch.depart_date}",
        f"Gäste:   {watch.adults}",
        "",
        f"Tickets bitte bis spätestens {when} ausstellen "
        f"(~3,5 Wochen vor Abflug).",
        "Danach in bookings.json \"ticketed\": true setzen, dann verstummt die Erinnerung.",
    ])
    return subject, body


def run(watches: list[Watch], today: dt.date | None = None) -> int:
    """Prüft alle Watches und verschickt fällige Erinnerungen. Gibt Anzahl zurück."""
    today = today or dt.date.today()
    today_iso = today.isoformat()
    sent = 0

    for w in watches:
        if not w.booked or w.ticketed:
            continue
        if w.depart_dt <= today:            # Abflug vorbei -> nichts mehr tun
            continue

        deadline = w.ticketing_deadline(config.TICKETING_LEAD_DAYS)
        days_left = (deadline - today).days

        in_window = days_left <= config.REMINDER_WINDOW_DAYS   # inkl. überfällig (<0)
        if not in_window:
            continue
        if storage.was_reminded_today(w.key, today_iso):
            continue

        subject, body = _reminder_text(w, deadline, days_left)
        alerts.deliver(subject, body)
        storage.mark_reminded(w.key, today_iso)
        sent += 1

    return sent
