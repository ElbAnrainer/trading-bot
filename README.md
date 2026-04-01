[200~# trading-bot

Regelbasiertes Trading- und Analyseprojekt für **Simulation**, **Backtesting**, **Dashboarding** und **Terminal-UI**.

## Wichtig

- **Keine Broker-Anbindung**
- **Keine echten Orders**
- **Keine Anlageberatung**
- Das Projekt dient ausschließlich **Backtesting, Simulation und Analyse**

## Hauptfunktionen

- realistischer Backtest mit Startkapital
- Anti-Overtrading-Regeln
- Risikomodul
- Terminal UI / Live-Ansicht
- Dashboard HTML/JSON
- PDF-Report mit Strategie-Erklärung
- Profilsystem (z. B. konservativ / mittel / offensiv)
- Test-Suite mit `pytest`

## Projektstruktur

- `main.py` – Einstiegspunkt
- `run.sh` – Startscript / Terminal-Launcher
- `terminal_ui.py` – Terminal Pro UI
- `realistic_backtest.py` – realistischer Backtest
- `dashboard.py` – Dashboard-Generierung
- `dashboard_live.py` – Live-Dashboard-Ausgabe
- `report_pdf.py` – PDF-Report
- `performance.py` – Performance-Auswertung
- `portfolio_state.py` – Persistenter Portfolio-Zustand
- `risk.py` / `advanced_risk.py` – Risiko- und Positionslogik
- `mini_trading_system.py` – Mini-Trading-System
- `tests/` – Test-Suite

## Setup

### Virtuelle Umgebung aktivieren

```bash
source .venv/bin/activate
