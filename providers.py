"""
Preis-Beschaffung. Hier steckst du deine echte Flug-API ein.

PROVIDER (Env-Var) wählt die Quelle:
  - "mock"   : deterministische Fake-Preise, damit die ganze Pipeline sofort läuft
  - "duffel" : Skeleton für die Duffel-API (Suche = Offer Request, KEINE Order)

fetch_offers(watch) gibt immer eine Liste normalisierter Offer-Objekte zurück.
"""

from __future__ import annotations
import os
import hashlib

import requests

from models import Watch, Offer

PROVIDER = os.environ.get("PROVIDER", "mock").lower()


# ----------------------------------------------------------------------------
# MOCK — sofort lauffähig, deterministisch pro Strecke/Datum
# ----------------------------------------------------------------------------

def _mock_offers(watch: Watch) -> list[Offer]:
    seed = int(hashlib.sha1((watch.key + os.environ.get("MOCK_ROUND", "")).encode())
               .hexdigest(), 16)
    base = {"DEL": 620, "MAA": 690}.get(watch.destination, 650)
    jitter = (seed % 140) - 40                      # -40 .. +99
    drop = int(os.environ.get("MOCK_DROP", "0"))    # zum Testen von Alerts
    total = (base + jitter - drop) * watch.adults
    carrier = (watch.carriers or ["LH"])[0]
    return [Offer(price_total=float(total), carrier=carrier,
                  includes_checked_bag=True, stops=watch.max_stops or 0,
                  currency=watch.__dict__.get("currency", "EUR"),
                  booking_link="https://example.com/mock")]


# ----------------------------------------------------------------------------
# DUFFEL — Skeleton (Suche only). Docs: https://duffel.com/docs
# ----------------------------------------------------------------------------

def _duffel_offers(watch: Watch) -> list[Offer]:
    token = os.environ["DUFFEL_TOKEN"]
    slices = [{"origin": watch.origin, "destination": watch.destination,
               "departure_date": watch.depart_date}]
    if watch.return_date:
        slices.append({"origin": watch.return_origin, "destination": watch.origin,
                       "departure_date": watch.return_date})

    r = requests.post(
        "https://api.duffel.com/air/offer_requests?return_offers=true",
        headers={"Authorization": f"Bearer {token}",
                 "Duffel-Version": "v2", "Content-Type": "application/json"},
        json={"data": {"slices": slices,
                       "passengers": [{"type": "adult"}] * watch.adults,
                       "cabin_class": watch.cabin}},
        timeout=60,
    )
    r.raise_for_status()
    offers = []
    for o in r.json()["data"].get("offers", []):
        # Carrier-Filter
        carrier = o.get("owner", {}).get("iata_code", "")
        if watch.carriers and carrier not in watch.carriers:
            continue
        # Stops-Filter
        stops = max((len(s.get("segments", [])) - 1) for s in o.get("slices", [])) \
            if o.get("slices") else 0
        if watch.max_stops is not None and stops > watch.max_stops:
            continue
        # Gepäck: enthält irgendein Passagier ein Aufgabegepäck?
        has_bag = False
        for s in o.get("slices", []):
            for seg in s.get("segments", []):
                for p in seg.get("passengers", []):
                    for b in p.get("baggages", []):
                        if b.get("type") == "checked" and b.get("quantity", 0) > 0:
                            has_bag = True
        offers.append(Offer(
            price_total=float(o["total_amount"]), carrier=carrier,
            includes_checked_bag=has_bag, stops=stops,
            currency=o.get("total_currency", "EUR"),
            booking_link=None, raw={"offer_id": o.get("id")},
        ))
    return offers


def fetch_offers(watch: Watch) -> list[Offer]:
    if PROVIDER == "duffel":
        return _duffel_offers(watch)
    return _mock_offers(watch)
