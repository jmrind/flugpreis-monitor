# Einrichtung & Bedienung

Die Automatik (zweimal täglich Preise holen) läuft über GitHub Actions; das
**Bedienpanel** (die Webseite) zeigt die Übersicht UND lässt dich Flüge und Werte
direkt bearbeiten. Alles im Browser.

## Erststart (falls noch nicht geschehen)
1. Repo auf github.com anlegen, Dateien hochladen (inkl. Ordner `.github`).
2. **Settings → Actions → General → Workflow permissions → Read and write** → Save.
3. **Settings → Secrets → Actions:** `PROVIDER=duffel`, `DUFFEL_TOKEN=…`
   (optional SMTP für Mail-Alerts).
4. **Settings → Pages:** Branch `main`, Ordner `/(root)` → Save. Das ist die Adresse
   deines Bedienpanels (z. B. `https://DEINNAME.github.io/flugpreis-monitor/`).
5. **Actions → Run workflow** für den ersten Lauf.

## Bedienpanel scharf schalten (Zugangs-Token)

Die Übersicht funktioniert sofort. Zum **Bearbeiten/Speichern** braucht das Panel
einmalig einen Token (eine statische Webseite kann sonst nichts zurückschreiben):

1. GitHub → **Settings (dein Profil, oben rechts) → Developer settings →
   Personal access tokens → Fine-grained tokens → Generate new token.**
2. **Resource owner:** dein Konto. **Repository access:** nur `flugpreis-monitor`.
3. **Permissions → Repository permissions:**
   - **Contents: Read and write**
   - **Actions: Read and write** (damit „Speichern & jetzt aktualisieren" geht)
4. Token erzeugen und **kopieren**.
5. Im Bedienpanel oben **„Verbindung & Zugang"** aufklappen → Konto/Repo/Branch prüfen,
   Token einfügen → **Speichern**. Der Token bleibt nur in deinem Browser.

## Flüge & Werte bearbeiten (im Tool)

Reiter **Verwalten**:
- **+ Reise hinzufügen** / **Reise löschen** — neue Verbindung oder raus.
- Pro Reise: Ab/Nach, Rück-ab (Open-Jaw), Airlines, Stops, Klasse, **kalkulierter Preis €/Gast**.
- Pro Termin (Tabelle): Hin-/Rückflug (TT.MM.JJJJ), **Gäste**, **gebucht**, **Tickets ausgestellt** — Zeilen per **+ Termin** / **✕**.
- **Speichern** übernimmt es beim nächsten Lauf. **Speichern & jetzt aktualisieren**
  stößt sofort einen Lauf an (Übersicht ist in ein paar Minuten aktuell).

Reiter **Übersicht**: Filter nach Firma und **nach Reise**, Sortierung (u. a.
„größte Veränderung" und „Marge – Verlust zuerst"), pro Karte die **Marge**
(kalkuliert − aktuell), Verlauf und Ticketing-Status.

## Kosten
Duffel berechnet reine Suchen mit ~0,004 €. 2×/Tag × 33 Strecken ≈ **~8 €/Monat**.
Weniger Läufe oder weniger Strecken senken das entsprechend.
