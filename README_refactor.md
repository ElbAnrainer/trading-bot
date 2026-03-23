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
- Score-System zur Bewertung von Aktien

### Währungslogik
- automatische Umrechnung in EUR
- FX-Analyse für Fremdwährungen
- Darstellung in EUR und Handelswährung

### Output & Darstellung
- strukturierte Konsolen-Ausgabe
- Fortschrittsbalken mit ETA
- Ranking der besten Backtests
- Beobachtungssignale mit BUY, WATCH, SELL
- Diagnose pro Aktie
- Anzeige von Symbol und Firmenname

### Simulationsjournal
Alle Entscheidungen werden im Journal gespeichert:

```text
reports/trading_journal.csv
