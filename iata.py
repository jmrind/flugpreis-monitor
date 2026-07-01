"""Namens-Mappings für den Reiseverlauf-Parser (Stadt/Airline -> IATA)."""

import unicodedata

# Stadt-/Flughafennamen -> IATA. Ergänze bei Bedarf.
CITY_TO_IATA = {
    # Deutschland / Europa
    "berlin": "BER", "muenchen": "MUC", "munchen": "MUC", "munich": "MUC",
    "frankfurt": "FRA", "hamburg": "HAM", "duesseldorf": "DUS", "dusseldorf": "DUS",
    "koeln": "CGN", "koln": "CGN", "cologne": "CGN", "stuttgart": "STR",
    "wien": "VIE", "vienna": "VIE", "zuerich": "ZRH", "zurich": "ZRH",
    # Drehkreuze
    "dubai": "DXB", "doha": "DOH", "istanbul": "IST", "abu dhabi": "AUH",
    # Indien
    "delhi": "DEL", "neu-delhi": "DEL", "new delhi": "DEL",
    "mumbai": "BOM", "bombay": "BOM", "bengaluru": "BLR", "bangalore": "BLR",
    "chennai": "MAA", "madras": "MAA", "kolkata": "CCU", "hyderabad": "HYD",
    "kochi": "COK", "cochin": "COK", "goa": "GOI", "jaipur": "JAI",
    "udaipur": "UDR", "jodhpur": "JDH", "varanasi": "VNS", "amritsar": "ATQ",
    "trivandrum": "TRV", "thiruvananthapuram": "TRV", "ahmedabad": "AMD",
    "agra": "AGR", "leh": "IXL", "srinagar": "SXR",
}

# Airline-Namen -> IATA.
AIRLINE_TO_IATA = {
    "lufthansa": "LH", "air india": "AI", "emirates": "EK",
    "qatar": "QR", "qatar airways": "QR", "etihad": "EY",
    "turkish": "TK", "turkish airlines": "TK", "vistara": "UK",
    "indigo": "6E", "swiss": "LX", "austrian": "OS", "klm": "KL",
    "air france": "AF", "british airways": "BA", "finnair": "AY",
}


# IATA -> Land (für die Inlandsflug-Erkennung im Reiseverlauf-Parser).
COUNTRY_OF = {
    "BER": "DE", "MUC": "DE", "FRA": "DE", "HAM": "DE", "DUS": "DE",
    "CGN": "DE", "STR": "DE", "VIE": "AT", "ZRH": "CH",
    "DXB": "AE", "AUH": "AE", "DOH": "QA", "IST": "TR",
    "DEL": "IN", "BOM": "IN", "BLR": "IN", "MAA": "IN", "CCU": "IN",
    "HYD": "IN", "COK": "IN", "GOI": "IN", "JAI": "IN", "UDR": "IN",
    "JDH": "IN", "VNS": "IN", "ATQ": "IN", "TRV": "IN", "AMD": "IN",
    "AGR": "IN", "IXL": "IN", "SXR": "IN",
}


def country_of(iata: str) -> str | None:
    return COUNTRY_OF.get(iata.upper())


def is_domestic(origin: str, destination: str) -> bool:
    """True, wenn beide Flughäfen im selben Land liegen (z.B. Indien-Inland)."""
    a, b = country_of(origin), country_of(destination)
    return a is not None and a == b


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.strip().lower()


def city_iata(name: str) -> str | None:
    return CITY_TO_IATA.get(_norm(name))


def airline_iata(name: str) -> str | None:
    key = _norm(name)
    if key in AIRLINE_TO_IATA:
        return AIRLINE_TO_IATA[key]
    for k, v in AIRLINE_TO_IATA.items():   # Teilstring-Treffer ("mit Lufthansa ...")
        if k in key:
            return v
    return None
