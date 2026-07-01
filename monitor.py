"""
Hauptlauf. Zweimal täglich per Scheduler ausführen.

  python monitor.py                              # nur Samsara
  python monitor.py --itinerary reise.pdf        # + Taj-Reisen aus PDF
  python monitor.py --itinerary reise.pdf --taj-domestic   # + Inlandsflüge

Ablauf: Preise holen -> Gepäckregel -> Historie speichern -> Preis-Alert;
danach Ticketing-Erinnerungen (~3,5 Wochen vor Abflug) für gebuchte Reisen.
"""

from __future__ import annotations
import argparse

import config
from models import Watch, Offer
import providers
from providers import fetch_offers
import storage
import alerts
import reminders


def total_with_bag(offer: Offer, watch: Watch) -> float:
    price = offer.price_total
    if watch.checked_bag and not offer.includes_checked_bag:
        fee = config.BAG_FEES.get(offer.carrier, config.BAG_FEES["_default"])
        legs = 2 if watch.return_date else 1
        price += fee * legs * watch.adults
    return round(price, 2)


def cheapest_offer(watch: Watch) -> tuple[Offer, float] | None:
    offers = fetch_offers(watch)
    if not offers:
        return None
    scored = [(o, total_with_bag(o, watch)) for o in offers]
    return min(scored, key=lambda x: x[1])


def process(watch: Watch) -> None:
    try:
        result = cheapest_offer(watch)
    except Exception as e:
        print(f"[!!] {watch.company:11} {watch.label}: Fehler ({e})")
        return
    if not result:
        print(f"[--] {watch.company:11} {watch.label}: keine Angebote")
        return

    offer, total = result
    per_person = round(total / max(watch.adults, 1), 2)
    previous_pp = storage.last_price(watch.key)
    storage.record(watch, offer, per_person, source=providers.PROVIDER)

    if alerts.should_alert(per_person, previous_pp, config.ALERT_DROP_PER_PERSON):
        st = storage.stats(watch.key, config.HISTORY_DAYS_FOR_STATS)
        alerts.send_alert(watch, per_person, previous_pp, st, offer.booking_link)
    else:
        delta = f"({per_person - previous_pp:+.0f})" if previous_pp else "(neu)"
        flag = " ●booked" if watch.booked else ""
        print(f"[ok] {watch.company:11} {watch.label:28} "
              f"{per_person:>7.0f} EUR/Gast {delta}{flag}")


def collect_watches(itinerary: str | None, taj_domestic: bool) -> list[Watch]:
    watches = config.samsara_watches()
    if itinerary:
        from extract_itinerary import extract_flights, build_watches
        flights = extract_flights(itinerary)
        taj = build_watches(flights, adults=config.DEFAULT_PAX,
                            include_domestic=taj_domestic)
        print(f"[Taj] {len(flights)} Flüge erkannt -> {len(taj)} Watch(es)"
              f"{' (inkl. Inland)' if taj_domestic else ''}")
        watches += taj
    return watches


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--itinerary", help="Pfad zu einem Reiseverlauf-PDF (Taj Reisen)")
    ap.add_argument("--taj-domestic", action="store_true",
                    help="auch Inlandsflüge aus dem Reiseverlauf überwachen")
    ap.add_argument("--no-reminders", action="store_true",
                    help="Ticketing-Erinnerungen in diesem Lauf überspringen")
    args = ap.parse_args()

    watches = collect_watches(args.itinerary, args.taj_domestic)
    booked = sum(1 for w in watches if w.booked)
    print(f"Überwache {len(watches)} Verbindungen ({booked} gebucht) · "
          f"Alert ab -{config.ALERT_DROP_PER_PERSON:.0f} EUR/Gast\n")

    for w in watches:
        process(w)

    if not args.no_reminders:
        n = reminders.run(watches)
        print(f"\nTicketing-Erinnerungen verschickt: {n}")


if __name__ == "__main__":
    main()
