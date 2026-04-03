# AGENTS.md

## Zweck

Dieses Repository ist ein Python-Projekt fuer Trading-Simulation, Analyse,
Backtesting, Reporting, Dashboarding und Terminal-Monitoring.

Es dient nicht fuer:

- echte Broker-Anbindungen
- echte Orders
- Anlageberatung
- produktiven Live-Handel

Jede Aenderung soll diese Grenze klar erhalten.

## Repo-Realitaet

Das Projekt besteht ueberwiegend aus Python-Modulen im Repo-Root und nicht aus
einem klassischen Paketbaum.

Wichtige Einstiegspunkte und Kernmodule:

- `main.py` -> Haupt-CLI
- `run.sh` -> lokaler Launcher / interaktiver Terminal-Flow
- `run_walk_forward.sh` -> kanonischer Walk-Forward-Skriptstart
- `realistic_backtest.py` -> realistischer Portfolio-Backtest
- `mini_trading_system.py` -> persistenter Mini-Trading-Workflow
- `trading_engine.py` -> Buy-/Sell-Planung
- `analysis_engine.py` -> Analysepipeline
- `dashboard.py` und `dashboard_live.py` -> Dashboard-Ausgabe
- `report_pdf.py`, `daily_report.py`, `gmail_api_report.py` -> Reporting
- `portfolio_state.py` und `state.py` -> persistenter Zustand
- `tests/` -> `pytest`-Suite
- `reports/` -> CI-/Override-Ziel fuer generierte Ausgaben
- `docs/` -> Dokumentation, getrennt nach `manual/` und `refactor/`

Nicht von Verzeichnissen wie `/data`, `/strategy` oder `/execution`
ausgehen. Diese Struktur existiert hier nicht.

## Umgebung

Lokale Entwicklung verwendet aktuell:

- Python aus `.venv`
- `pytest`
- `pandas`
- `yfinance`
- `matplotlib`
- `reportlab`
- optionale Google-Mail-Abhaengigkeiten fuer den Report-Versand

Bevorzugte Basisbefehle:

```bash
source .venv/bin/activate
```

Haeufige Validierungen:

```bash
./.venv/bin/python -m pytest -p no:cacheprovider -q
env MPLCONFIGDIR=/tmp/mpl-trading-bot ./.venv/bin/python main.py --help
```

Wenn Tests oder CLI-Kommandos `matplotlib` importieren, ist
`MPLCONFIGDIR=/tmp/mpl-trading-bot` bevorzugt, um lokale Cache- und
Berechtigungsprobleme zu vermeiden.

## Arbeitsregeln fuer Agenten

- Immer vom Repo-Root arbeiten. Die Tests verlassen sich auf `pythonpath = .`.
- Wenn vorhanden, `.venv/bin/python` und `.venv/bin/pytest` verwenden.
- Benutzernahe Texte, CLI-Hilfe und Reports sind ueberwiegend auf Deutsch.
  Diesen Stil bei neuen Ausgaben beibehalten.
- `.env` wird ueber `env_loader.py` geladen. Keine Secrets, OAuth-Dateien oder
  Tokens committen.
- Laufzeitpfade immer ueber `config.py` und `TRADING_BOT_DATA_DIR` behandeln,
  nicht ueber hart verdrahtete Repo-Root-Pfade.
- Mailversand existiert (`gmail_api_report.py`, `--mail`, `.env`-Werte), soll
  aber nicht in Tests oder Smoke-Checks ausgeloest werden.
- Generierte Dateien im konfigurierten `REPORTS_DIR` nicht manuell pflegen,
  wenn stattdessen die erzeugende Python-Quelle angepasst werden kann.
- Persistente Formate fuer Zustandsdateien moeglichst stabil halten, es sei
  denn, eine bewusste Migration ist Teil der Aenderung.
- Bestehende Werte aus `config.py` und den Trading-Profilen nutzen, statt neue
  verteilte Konstanten einzufuehren.

## Trading- und Modellierungsgrenzen

Bei fachlichen Aenderungen immer explizit auf folgende Risiken achten:

- Lookahead Bias
- Future Data Leakage
- unrealistische Fills
- fehlende Gebuehren oder Slippage-Annahmen
- kaputte Cooldown- oder Holding-Period-Regeln
- Vermischung von Simulation mit impliziter Real-Ausfuehrung

Wenn eine Aenderung eines dieser Module betrifft:

- `realistic_backtest.py`
- `mini_trading_system.py`
- `trading_engine.py`
- `candle_backtest.py`
- `risk.py`
- `advanced_risk.py`

dann die Auswirkungen auf Folgendes mitpruefen:

- Gebuehren
- Slippage
- Stop-Logik
- Drawdown-Kontrolle
- Cooldown-Verhalten
- State-Persistenz
- Test-Determinismus

## Zustand und Ausgaben

Dieses Repository ist nicht zustandslos. Es nutzt persistente Dateien im
konfigurierten Datenordner aus `config.py`. Standardmaessig liegt dieser
ausserhalb des Repos; in CI kann er bewusst auf das Repo zeigen.

Wichtige Beispiele:

- gelernte Scores
- Portfolio-State
- Dashboard-Ausgaben
- aktuelle Report-Artefakte
- Zusammenfassungen realistischer Backtests

Wenn Code Historie oder Zustand schreibt, Feldnamen und Zeitbehandlung ueber
Leser und Schreiber hinweg konsistent halten.

## Bekannte Stolperstellen

- `walk_forward.py` ist das kanonische Walk-Forward-Modul.
- `walkforward.py` ist ein Kompatibilitaets-Shim fuer alte Importe.
- `run_walk_forward.sh` ist der kanonische Skriptname fuer den Walk-Forward-Lauf.
- `run_walk_forwad.sh` ist ein Legacy-/Typo-Wrapper.
- `performance.py` verwendet `portfolio.py`.
- `porfolio.py` ist ein Legacy-/Typo-Shim auf `portfolio.py`.
- `dependency_check.py` kann fehlende Pakete installieren, sollte aber nicht
  nebenbei in Tests oder Reviews ausgefuehrt werden.

## Test-Erwartungen

Vor dem Abschluss relevanter Codeaenderungen bevorzugt ausfuehren:

```bash
./.venv/bin/python -m pytest -p no:cacheprovider -q
```

Bei fokussierter Arbeit zuerst den betroffenen Test, danach bei nicht-trivialen
Aenderungen die gesamte Suite laufen lassen.

Gute Tests in diesem Repository sind:

- schnell
- lokal
- deterministisch
- explizit in ihren finanziellen Annahmen

## Review-Hinweise

Bei Reviews oder Aenderungsvorschlaegen:

- unrealistische Annahmen benennen
- fehlende Fees, Slippage, Cooldowns oder Drawdown-Grenzen markieren
- einfache und direkte Erklaerungen bevorzugen
- Annahmen klar aussprechen
- auf operative Risiken hinweisen, wenn Zustandsdateien, Reports oder optionale
  Mail-Flows betroffen sind

## Abschlusskriterien

- Fuer Codeaenderungen mindestens die betroffenen Tests ausfuehren, idealerweise
  die komplette Suite.
- Bei Aenderungen an Reports oder CLIs einen kurzen Smoke-Test ausfuehren.
- Keine unbeabsichtigten Artefakte oder Geheimnisse im Datenordner oder im Repo
  hinterlassen.
