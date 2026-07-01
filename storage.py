"""SQLite-Speicher für Preishistorie + Statistik pro Watch."""

from __future__ import annotations
import os
import sqlite3
import datetime as dt
from statistics import mean

from models import Watch, Offer

DB_PATH = os.environ.get("MONITOR_DB", "flight_prices.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ts TEXT NOT NULL,
            watch_key TEXT NOT NULL,
            company TEXT, label TEXT,
            origin TEXT, destination TEXT,
            depart_date TEXT, return_date TEXT,
            carrier TEXT,
            price_total REAL, price_per_person REAL, currency TEXT,
            includes_checked_bag INTEGER,
            booking_link TEXT, source TEXT
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watch ON prices(watch_key, ts)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            watch_key TEXT NOT NULL,
            remind_date TEXT NOT NULL,
            PRIMARY KEY (watch_key, remind_date)
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watches (
            watch_key TEXT PRIMARY KEY,
            company TEXT, label TEXT, origin TEXT, destination TEXT,
            depart_date TEXT, return_date TEXT, return_origin TEXT,
            carriers TEXT, cabin TEXT, adults INTEGER,
            booked INTEGER, ticketed INTEGER, kind TEXT, calc_price REAL
        )""")
    # Migration: calc_price zu bestehender Tabelle ergänzen
    cols = [r[1] for r in conn.execute("PRAGMA table_info(watches)")]
    if "calc_price" not in cols:
        conn.execute("ALTER TABLE watches ADD COLUMN calc_price REAL")
    return conn


def _upsert_watch(conn, watch: Watch) -> None:
    conn.execute("""
        INSERT INTO watches (watch_key, company, label, origin, destination,
            depart_date, return_date, return_origin, carriers, cabin, adults,
            booked, ticketed, kind, calc_price)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(watch_key) DO UPDATE SET
            label=excluded.label, adults=excluded.adults,
            booked=excluded.booked, ticketed=excluded.ticketed,
            calc_price=excluded.calc_price
        """, (watch.key, watch.company, watch.label, watch.origin,
              watch.destination, watch.depart_date, watch.return_date,
              watch.return_origin, ",".join(watch.carriers), watch.cabin,
              watch.adults, int(watch.booked), int(watch.ticketed), watch.kind,
              watch.calc_price))


def record(watch: Watch, offer: Offer, per_person: float, source: str) -> None:
    with _conn() as conn:
        _upsert_watch(conn, watch)
        conn.execute(
            "INSERT INTO prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (dt.datetime.utcnow().isoformat(timespec="seconds"), watch.key,
             watch.company, watch.label, watch.origin, watch.destination,
             watch.depart_date, watch.return_date, offer.carrier,
             round(offer.price_total, 2), round(per_person, 2), offer.currency,
             int(offer.includes_checked_bag), offer.booking_link, source))


def last_price(watch_key: str) -> float | None:
    """Vorletzter -> aktueller Vergleich: gibt den zuletzt gespeicherten
    Preis PRO PERSON zurück (vor dem gerade neu eingefügten)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT price_per_person FROM prices WHERE watch_key=? "
            "ORDER BY ts DESC LIMIT 2", (watch_key,)).fetchall()
    return rows[1]["price_per_person"] if len(rows) >= 2 else None


def history(watch_key: str, days: int = 90) -> list[tuple[str, float]]:
    since = (dt.datetime.utcnow() - dt.timedelta(days=days)).isoformat()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT ts, price_per_person FROM prices WHERE watch_key=? AND ts>=? "
            "ORDER BY ts", (watch_key, since)).fetchall()
    return [(r["ts"], r["price_per_person"]) for r in rows]


def stats(watch_key: str, days: int = 90) -> dict | None:
    pts = [p for _, p in history(watch_key, days) if p is not None]
    if not pts:
        return None
    return {
        "count": len(pts),
        "current": pts[-1],
        "min": min(pts),
        "max": max(pts),
        "avg": round(mean(pts), 2),
        "all_time_low": pts[-1] <= min(pts),
        "vs_avg": round(pts[-1] - mean(pts), 2),
    }


def was_reminded_today(watch_key: str, today: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM reminders WHERE watch_key=? AND remind_date=?",
            (watch_key, today)).fetchone()
    return row is not None


def mark_reminded(watch_key: str, today: str) -> None:
    with _conn() as conn:
        conn.execute("INSERT OR IGNORE INTO reminders VALUES (?,?)",
                     (watch_key, today))


def all_watch_keys() -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            "SELECT DISTINCT watch_key, company, label, origin, destination, "
            "depart_date, return_date FROM prices").fetchall()


def list_watches() -> list[dict]:
    """Alle bekannten Watches mit Metadaten (für das Dashboard)."""
    with _conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM watches").fetchall()]
