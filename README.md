# Flugpreis-Monitor

Self-hosted Preisüberwachung mit Bedienpanel. Zwei Profile (Samsara, Taj Reisen),
zweimal täglich echte Preise (Duffel), vollständige Historie, Kalkulations-Marge,
−50-€-Alerts und Ticketing-Erinnerungen (~3,5 Wochen vor Abflug).

**Bedienung komplett im Browser** über das Panel (`index.html`): Übersicht mit
Filtern/Sortierung/Marge, und ein Verwalten-Tab zum Anlegen/Löschen/Ändern von
Flügen und Werten, der direkt ins Repo speichert. Einrichtung: siehe SETUP.md.

## Wie es zusammenhängt
- `flights.json` — die überwachten Reisen/Termine + kalkulierter Preis + Buchungen.
  Wird im Bedienpanel bearbeitet (oder direkt als Datei).
- `monitor.py` (per GitHub Actions, 2×/Tag) liest `flights.json`, holt Preise,
  speichert Historie in `flight_prices.db`, verschickt Alerts/Erinnerungen.
- `dashboard.py` schreibt `data.json` (Preise/Statistik/Marge) für das Panel.
- `index.html` — das Bedienpanel (Übersicht + Editor).

## Dateien
| Datei | Aufgabe |
|---|---|
| `flights.json` | überwachte Flüge + Kalkulation + Buchungen (im Panel bearbeitbar) |
| `index.html` | Bedienpanel (Übersicht + Verwalten) |
| `config.py` | globale Einstellungen, liest flights.json |
| `models.py` | Datenmodelle |
| `iata.py` | Stadt-/Airline-/Länder-Mapping |
| `providers.py` | Flug-API (Duffel + Mock), Rate-Limit-Handling |
| `extract_itinerary.py` | Taj Reisen: PDF → Flüge |
| `storage.py` | SQLite-Historie + Statistik |
| `alerts.py` | Mailversand + Preis-Alert |
| `reminders.py` | Ticketing-Erinnerungen |
| `monitor.py` | Hauptlauf |
| `dashboard.py` | schreibt data.json fürs Panel |
| `data.json` | vom Lauf erzeugte Preisdaten (nicht selbst bearbeiten) |
