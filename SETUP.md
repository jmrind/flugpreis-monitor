# Einrichtung: automatisch in der Cloud (GitHub Actions + Pages)

Danach läuft alles von selbst — zweimal täglich, ohne dass dein Rechner an sein
muss — und das Dashboard ist unter einer festen Web-Adresse erreichbar.
Alle Schritte passieren im Browser. Kein Terminal nötig.

---

## 0. Vorab: öffentlich oder privat?

GitHub Pages ist für **öffentliche** Repos kostenlos. Öffentlich heißt: der Code,
das Dashboard **und die Preis-Datenbank** sind für jeden mit dem Link sichtbar.
Deine Passwörter/Keys bleiben trotzdem geheim (die liegen in „Secrets", nicht im Code).

- Nur die Preise/Strecken sichtbar zu haben, ist meist ok → **öffentliches Repo**.
- Willst du das nicht: **privates Repo** nehmen. Dann läuft die Automatik genauso,
  aber Pages (die Web-Adresse) braucht einen bezahlten GitHub-Plan. Ohne den siehst
  du das Dashboard, indem du `dashboard.html` im Repo öffnest/herunterlädst.

---

## 1. Konto & Repo anlegen

1. Auf **github.com** ein kostenloses Konto erstellen (falls noch keins da ist).
2. Oben rechts **+ → New repository**.
3. Name z. B. `flugpreis-monitor`, Sichtbarkeit wählen (siehe Schritt 0),
   **Create repository**.

## 2. Dateien hochladen

1. Im leeren Repo: **Add file → Upload files**.
2. Entpacke `flightmonitor.zip` auf deinem Rechner und ziehe den **Inhalt** des
   Ordners (nicht den Ordner selbst) ins Browser-Fenster — inklusive des Ordners
   `.github`. Falls der `.github`-Ordner beim Drag-and-drop verschwindet: einzeln
   nachladen (er enthält `workflows/monitor.yml`).
3. Unten **Commit changes**.

> Die mitgelieferte `flight_prices.db` enthält Demo-Preise, damit sofort etwas im
> Dashboard steht. Sobald der echte Provider läuft, kannst du sie im Repo löschen
> (**Datei öffnen → Papierkorb-Symbol → Commit**), dann startet die Historie frisch.

## 3. Secrets eintragen (Keys & Mail)

**Settings → Secrets and variables → Actions → New repository secret.**
Lege je Zeile ein Secret an:

| Name | Wert | Pflicht? |
|---|---|---|
| `PROVIDER` | `duffel` | für Echtpreise |
| `DUFFEL_TOKEN` | dein Duffel-API-Token | für Echtpreise |
| `SMTP_HOST` | z. B. `smtp.gmail.com` | für Mail-Alerts |
| `SMTP_PORT` | z. B. `587` | für Mail-Alerts |
| `SMTP_USER` | deine Absender-Adresse | für Mail-Alerts |
| `SMTP_PASS` | App-Passwort (nicht dein normales!) | für Mail-Alerts |
| `ALERT_TO` | wohin die Alerts gehen | für Mail-Alerts |
| `ANTHROPIC_API_KEY` | optional (PDF-Erkennung, Alert-Texte) | optional |

Nichts eingetragen? Dann läuft es mit **Mock-Preisen** und Alerts als „Dry-Run"
(nur im Log). Zum Ausprobieren völlig ok.

> Gmail & Co. brauchen ein **App-Passwort** (normale Passwörter werden abgelehnt).
> Das erstellst du in deinen Google-Kontoeinstellungen unter „App-Passwörter".

## 4. Automatik aktivieren & ersten Lauf starten

1. Reiter **Actions** öffnen → falls gefragt: **I understand my workflows, enable them**.
2. Links **flight-price-monitor** wählen → **Run workflow → Run workflow**
   (das ist der manuelle Teststart; danach läuft er automatisch um 06:00 & 18:00 UTC
   = 08:00 & 20:00 MESZ).
3. Der Lauf sollte grün durchlaufen. Im Log siehst du die Preiszeilen und ggf. Alerts.

## 5. Dashboard als Webseite (Pages)

1. **Settings → Pages.**
2. Unter **Build and deployment → Source:** „Deploy from a branch".
3. **Branch:** `main`, Ordner **/(root)** → **Save**.
4. Nach ein, zwei Minuten erscheint oben die Adresse, etwa
   `https://DEINNAME.github.io/flugpreis-monitor/`.
   Das ist dein Dashboard — als Lesezeichen speichern. Es aktualisiert sich bei jedem
   Lauf von selbst.

---

## Gäste & Ticketing pflegen (im Browser)

- **Wer hat gebucht / wie viele Gäste:** `bookings.json` im Repo öffnen →
  Stift-Symbol → Zahlen anpassen → **Commit**. Wirkt beim nächsten Lauf.
- **Tickets ausgestellt:** in `bookings.json` bei der Reise `"ticketed": true`
  setzen → die Erinnerung verstummt.
- **Strecken/Termine ändern:** `config.py` bearbeiten (gleiches Prinzip).

## Taj Reisen (Reiseverlauf-PDF)

Der PDF-Upload ist ein separater, manueller Schritt (eine hochgeladene Datei kann der
Cron-Lauf nicht „sehen"). Zwei einfache Wege:
- PDF ins Repo legen und den Aufruf im Workflow um
  `--itinerary DEINE_DATEI.pdf --taj-domestic` ergänzen, oder
- lokal einmalig `python monitor.py --itinerary reise.pdf` laufen lassen.
Sag Bescheid, dann baue ich dir den Taj-Upload als eigenen „per Klick auslösbaren"
Workflow-Schritt mit Datei-Eingabe.

## Wenn etwas klemmt

- **Actions-Lauf rot:** ins Log klicken; meist ein falsch benanntes Secret oder eine
  vergessene Datei aus `.github/`.
- **Seite 404:** Pages braucht nach dem Aktivieren ein paar Minuten und mindestens
  eine `index.html` im Root (die legt der Workflow automatisch an — einmal laufen lassen).
