# Flugpreis-Monitor

Self-hosted Preisüberwachung für feste Strecken, zwei Profile:

- **Samsara** — fest hinterlegte Strecken (deine Rajasthan/North India/Safari/South-India-Termine). Speichert die komplette Preishistorie, zeigt Statistik und schickt eine **Mail bei ≥ 50 EUR/Gast Preisrückgang**.
- **Taj Reisen** — Reiseverlauf als PDF hochladen; das Tool erkennt die Flüge automatisch, leitet die internationale Round-Trip ab und überwacht sie. **Inlandsflüge optional** (`--taj-domestic`).

Beide Profile bekommen zusätzlich eine **Ticketing-Erinnerung**: Tickets müssen ~3,5 Wochen vor Abflug ausgestellt werden — dafür gibt es eine automatische Mail an gebuchte, noch nicht ausgestellte Reisen.

Die Preis-**Beschaffung** ist bewusst deterministischer Code (kein LLM). Claude wird nur für zwei Dinge genutzt: robuste Flug-Erkennung aus PDFs und (optional) das Formulieren der Alert-Mail.

## Merkt es sich alles? / Durability

Ja. Jede Messung wird **angehängt und nie gelöscht** — die Historie ist vollständig. Die Statistik nutzt ein Zeitfenster (`HISTORY_DAYS_FOR_STATS`), die Rohdaten bleiben aber komplett erhalten.

Wo die Daten liegen, bestimmt die Robustheit:
- **GitHub Actions (Standard):** Der Runner ist zustandslos, deshalb wird `flight_prices.db` nach jedem Lauf zurück ins Repo committet (der Workflow macht vorher `git pull --rebase`, um Konflikte zu vermeiden). Für ein persönliches Tool ausreichend.
- **Wirklich dauerhaft:** VPS mit `crontab` (DB liegt einfach auf der Platte) oder eine gehostete SQLite/DB. Für gehostetes SQLite lässt sich z. B. **Turso/libSQL** einsetzen; dafür müsste nur `storage.py` auf den libSQL-Client umgestellt werden (die Tabellen bleiben gleich). Sag Bescheid, dann baue ich das um.

## Setup

```bash
pip install -r requirements.txt
```

Der einzige echte Baustein, den du selbst einsetzt, ist die Flug-API in `providers.py` (`fetch_offers`). Bis dahin läuft alles mit dem eingebauten **Mock**-Provider, sodass Historie, Statistik, Alerts, Erinnerungen und Dashboard sofort funktionieren. Empfohlene echte Quelle: **Duffel** (Suche = Offer Request, nie eine Order) — Skeleton inkl. Gepäck-/Carrier-/Stop-Filter liegt schon in `providers.py`.

## Ausführen

```bash
python monitor.py                                  # nur Samsara
python monitor.py --itinerary reise.pdf            # + Taj Reisen
python monitor.py --itinerary reise.pdf --taj-domestic   # + Inlandsflüge
python dashboard.py                                # dashboard.html (im Browser öffnen)
```

## Gäste pro Reise einstellen (wer hat schon gebucht)

In **`bookings.json`** — die zentrale Stelle, kein Code-Eingriff nötig:

```json
{
  "Rajasthan 16d · 29.10.2026": {"pax": 4, "ticketed": false},
  "South India 16d · 07.11.2026": {"pax": 2, "ticketed": true}
}
```

- Schlüssel = exaktes Watch-Label (Reise · Hinflugdatum).
- `pax` = Anzahl gebuchter/interessierter Gäste (steuert Preisrechnung + Ticketing).
- `ticketed` = `true`, sobald Tickets ausgestellt sind → stoppt die Erinnerung.

Reisen, die **nicht** in `bookings.json` stehen, werden nur beobachtet (mit `DEFAULT_PAX`) und lösen keine Ticketing-Erinnerung aus.

## Ticketing-Erinnerung

`config.py`: `TICKETING_LEAD_DAYS = 25` (≈ 3,5 Wochen) und `REMINDER_WINDOW_DAYS = 4`. Für jede gebuchte, nicht ausgestellte Reise wird die Deadline `Abflug − 25 Tage` berechnet; ab 4 Tagen davor (und bei Überfälligkeit) geht **einmal pro Tag** eine Mail raus, bis `ticketed: true` gesetzt ist.

## Umgebungsvariablen

| Variable | Zweck |
|---|---|
| `PROVIDER` | `mock` (Standard) oder `duffel` |
| `DUFFEL_TOKEN` | API-Token, wenn `PROVIDER=duffel` |
| `ANTHROPIC_API_KEY` | optional: PDF-Flugerkennung + Alert-Text via Claude |
| `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASS` | Mailversand |
| `ALERT_TO` / `ALERT_FROM` | Empfänger / Absender |
| `MONITOR_DB` | Pfad zur SQLite-Datei (Standard `flight_prices.db`) |
| `BOOKINGS_FILE` | Pfad zu bookings.json (Standard `bookings.json`) |

Ohne SMTP laufen Alerts **und** Erinnerungen als Dry-Run (Konsole).

## Zweimal täglich

`.github/workflows/monitor.yml` startet um 06:00 & 18:00 UTC, baut das Dashboard neu und persistiert DB + Dashboard. Secrets unter *Settings → Secrets and variables → Actions*.

VPS-Alternative:
```
0 6,18 * * *  cd /pfad && python3 monitor.py && python3 dashboard.py
```

## Vor dem Livegang

Die mitgelieferte `flight_prices.db` enthält **Demo-Daten** (Mock). Vor dem echten Betrieb löschen:
```bash
rm flight_prices.db
```

## Dateien

| Datei | Aufgabe |
|---|---|
| `config.py` | Samsara-Strecken + globale Einstellungen (Alert, Ticketing) |
| `bookings.json` / `bookings.py` | Gäste & Buchungsstatus pro Reise |
| `models.py` | Datenmodelle inkl. Ticketing-Deadline |
| `iata.py` | Stadt-/Airline-/Länder-Mapping |
| `providers.py` | **hier deine Flug-API einsetzen** (Mock + Duffel-Skeleton) |
| `extract_itinerary.py` | Taj Reisen: PDF → Flüge → Watch (+ Inland optional) |
| `storage.py` | SQLite: Historie, Statistik, Watch-Metadaten, Erinnerungs-Dedup |
| `alerts.py` | Mailversand + Preis-Alert |
| `reminders.py` | Ticketing-Erinnerungen |
| `monitor.py` | Hauptlauf |
| `dashboard.py` | HTML-Statistik-Report (hell, hochwertig) |
