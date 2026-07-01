"""
Mailversand für Preis-Alerts UND Ticketing-Erinnerungen.

SMTP über Umgebungsvariablen; ohne Konfiguration läuft alles als Dry-Run
(Ausgabe auf der Konsole), praktisch zum Testen.
"""

from __future__ import annotations
import os
import smtplib
from email.message import EmailMessage

import requests

from models import Watch

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT") or "587")
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
ALERT_TO = os.environ.get("ALERT_TO")
ALERT_FROM = os.environ.get("ALERT_FROM", SMTP_USER or "monitor@localhost")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def deliver(subject: str, text: str) -> None:
    """Verschickt eine Mail — oder gibt sie aus, wenn SMTP nicht gesetzt ist."""
    if not (SMTP_HOST and ALERT_TO):
        print(f"\n[DRY-RUN — SMTP nicht konfiguriert]\n{subject}\n{text}\n")
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = ALERT_FROM
    msg["To"] = ALERT_TO
    msg.set_content(text)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    print(f"[gesendet] {subject}")


# ----------------------------------------------------------------------------
# Preis-Alert
# ----------------------------------------------------------------------------

def should_alert(current_pp: float, previous_pp: float | None, threshold: float) -> bool:
    return previous_pp is not None and (previous_pp - current_pp) >= threshold


def _claude_summary(watch: Watch, current_pp: float, previous_pp: float,
                    stats: dict | None) -> str | None:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        prompt = (
            f"Strecke {watch.company}: {watch.describe()}. "
            f"Preis pro Person jetzt {current_pp} EUR (vorher {previous_pp}). "
            f"Statistik: {stats}. Schreibe eine knappe deutsche Alert-Nachricht "
            "(max 2 Sätze): Ersparnis nennen und einordnen, ob günstig ggü. Schnitt. "
            "Keine Anrede, kein Fließtext.")
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 200,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30)
        r.raise_for_status()
        blocks = r.json().get("content", [])
        txt = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return txt.strip() or None
    except Exception:
        return None


def send_alert(watch: Watch, current_pp: float, previous_pp: float,
               stats: dict | None, booking_link: str | None) -> None:
    drop = round(previous_pp - current_pp, 2)
    subject = (f"-{drop:.0f} EUR/Person · {watch.company} · "
               f"{watch.origin}->{watch.destination} {watch.depart_date}")
    body = _claude_summary(watch, current_pp, previous_pp, stats) or (
        f"Preis pro Person: {current_pp} EUR (vorher {previous_pp} EUR, -{drop} EUR).")
    lines = [body, "", watch.describe(),
             f"Gesamtpreis ({watch.adults} Gaeste): {round(current_pp * watch.adults, 2)} EUR"]
    if stats:
        lines.append(f"Schnitt {stats['avg']} · Min {stats['min']} · "
                     f"Max {stats['max']} EUR (pro Person)")
        if stats.get("all_time_low"):
            lines.append("-> Neuer Tiefstwert im Beobachtungszeitraum.")
    if booking_link:
        lines.append(f"\n{booking_link}")
    deliver(subject, "\n".join(lines))
