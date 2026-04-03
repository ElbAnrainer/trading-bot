# Laufzeitdaten

Diese Anwendung trennt Quellcode, Dokumentation und Laufzeitdaten bewusst.

## Standardpfade

- macOS: `~/Library/Application Support/trading-bot`
- Linux: `~/.local/share/trading-bot`

Der Pfad kann ueber `TRADING_BOT_DATA_DIR` ueberschrieben werden.

## Inhalt

- `reports/` -> Reports, Dashboard-Ausgaben, Statusdateien, Journal, State
- `cache/` -> Metadaten- und Marktdaten-Cache sowie Lernmodell

## Einmalige Migration

Wenn noch alte Daten im Repository unter `reports/`, `.cache/` oder als
`trading_journal.csv` im Repo-Root liegen, fuehre zuerst einen Dry-Run aus:

```bash
python migrate_runtime_data.py
```

Danach die eigentliche Migration:

```bash
python migrate_runtime_data.py --apply
```

Optional koennen vorhandene Zieldateien bewusst ersetzt werden:

```bash
python migrate_runtime_data.py --apply --overwrite
```

Die Migration kopiert Daten nur in den neuen Datenordner. Sie loescht keine
Quelldateien im Repository.

## Betrieb

- Die Anwendung liest Laufzeitdaten nur noch aus dem konfigurierten Datenordner.
- GitHub Actions setzen `TRADING_BOT_DATA_DIR` bewusst auf den Workspace, damit
  CI-Artefakte weiter unter `reports/` veroeffentlicht werden koennen.
- Der Auto-Run-Workflow laedt Reports als Artefakte hoch, statt sie nach
  `main` zurueck zu committen.
