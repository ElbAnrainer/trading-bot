# Paper Trading Simulator

Ein modular aufgebautes Analyse- und Simulationssystem für Backtesting, Screening und Strategie-Auswertung mit Fokus auf Transparenz, Erweiterbarkeit und Nachvollziehbarkeit.

## Wichtiger Hinweis

Dieses Projekt dient ausschließlich für:

- Simulation
- Backtesting
- persönliche Analyse
- Dokumentation von Beobachtungssignalen

Es werden **keine echten Orders ausgeführt**.  
Es besteht **keine Broker-Anbindung**.  
Die Ausgaben sind **keine Anlageberatung** und dürfen nicht als professionelle Finanzberatung für Dritte verstanden werden.

---

## Features

### Analyse & Strategie
- Backtesting auf historischen Daten
- Live-Screening mehrerer Aktien
- technische Signale wie Trend, Breakout und Momentum
- relative Stärke gegen den Markt
- einfaches Fundamentaldaten-Scoring
- selbstlernender Score auf Basis historischer Simulationsergebnisse
- Walk-Forward-Test über mehrere Zeitfenster

### Währungslogik
- automatische Umrechnung in EUR
- FX-Analyse für Fremdwährungen
- Darstellung in EUR und Handelswährung

### Output & Darstellung
- strukturierte Konsolen-Ausgabe
- Live-Terminal mit laufender Aktualisierung
- Ranking der besten Backtests
- Beobachtungssignale mit BUY, WATCH, SELL
- Diagnose pro Aktie
- Anzeige von Symbol und Firmenname

### CLI / Aufruf
- klassische Hilfe mit `python main.py --help`
- Kurzoptionen wie `-t` für `--top`
- Kurzoptionen wie `-mv` für `--min-volume`
- Zahlen-Suffixe wie `500k` oder `1m`
- klassische Manpage unter `docs/trading-bot.1`

### Simulationsjournal
Alle Entscheidungen werden im Journal gespeichert:

```text
reports/trading_journal.csv
