# GitHub Actions + Gmail API Setup

Diese Anleitung zeigt dir, wie dein Bot automatisch in GitHub läuft,
Reports erzeugt und per Gmail API als HTML-Mail + PDF-Anhang verschickt.

---

## Ziel

GitHub Actions soll automatisch:

1. den Bot starten
2. Reports erzeugen
3. Premium-PDF erstellen
4. HTML-Mail über Gmail API verschicken

➡️ Dein Rechner muss dafür nicht laufen.

---

## 1. Voraussetzungen

Du brauchst lokal bereits:

- funktionierende Gmail API OAuth Einrichtung
- `credentials_google.json`
- `token_google.json`
- funktionierenden Mailversand mit:

```bash
python main.py --mail
