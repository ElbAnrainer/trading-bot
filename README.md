# trading-bot

Regelbasiertes Trading- und Analyseprojekt fuer **Simulation**,
**Backtesting**, **Dashboarding** und **Terminal-UI**.

## Wichtig

- **Keine Broker-Anbindung**
- **Keine echten Orders**
- **Keine Anlageberatung**
- Das Projekt dient ausschliesslich **Backtesting, Simulation und Analyse**

## Hauptfunktionen

- realistischer Backtest mit Startkapital
- Anti-Overtrading-Regeln
- Risikomodul
- Terminal UI / Live-Ansicht
- Dashboard HTML/JSON
- PDF-Report mit Strategie-Erklaerung
- Profilsystem (z. B. konservativ / mittel / offensiv)
- Test-Suite mit `pytest`

## Projektstruktur

- `main.py` - Einstiegspunkt
- `run.sh` - Startscript / Terminal-Launcher
- `terminal_ui.py` - Terminal Pro UI
- `realistic_backtest.py` - realistischer Backtest
- `dashboard.py` - Dashboard-Generierung
- `dashboard_live.py` - Live-Dashboard-Ausgabe
- `report_pdf.py` - PDF-Report
- `performance.py` - Performance-Auswertung
- `portfolio_state.py` - Persistenter Portfolio-Zustand
- `risk.py` / `advanced_risk.py` - Risiko- und Positionslogik
- `mini_trading_system.py` - Mini-Trading-System
- `tests/` - Test-Suite
- `docs/` - Dokumentation

## Setup

### Virtuelle Umgebung aktivieren

```bash
source .venv/bin/activate
```

### Abhaengigkeiten installieren

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

## Laufzeitdaten

Reports, Cache-Dateien und persistente Zustandsdaten liegen standardmaessig
ausserhalb des Repos:

- macOS: `~/Library/Application Support/trading-bot`
- Linux: `~/.local/share/trading-bot`

Der Speicherort kann ueber `TRADING_BOT_DATA_DIR` ueberschrieben werden:

```bash
export TRADING_BOT_DATA_DIR="$HOME/trading-bot-data"
```

Bestehende Laufzeitdaten aus alten Repo-Pfaden lassen sich einmalig migrieren:

```bash
python migrate_runtime_data.py
python migrate_runtime_data.py --apply
```

In CI wird der Datenordner bewusst auf den Workspace gesetzt, damit Artefakte
weiter unter `reports/` im Job veroeffentlicht werden koennen.

Mehr dazu steht in `docs/operations/runtime-data.md`.

## Nuetzliche Befehle

```bash
./.venv/bin/python -m pytest -p no:cacheprovider -q
env MPLCONFIGDIR=/tmp/mpl-trading-bot ./.venv/bin/python main.py --help
```
