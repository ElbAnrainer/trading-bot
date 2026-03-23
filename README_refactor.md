# Trading-Bot Refactor und Beschleunigung

## Ziel
Die aktuelle `main.py` ist zu groß geworden und das Skript läuft unnötig lang. Die vorgeschlagene Struktur trennt deshalb:

- **CLI / Eingabe** in `cli.py`
- **Analyse- und Backtest-Logik** in `analysis_engine.py`
- **Startpunkt** in einer sehr kleinen `main.py`
- **Ausgabe** weiterhin in `output.py`

## Neue Struktur
- `main.py`: nur Startpunkt, Laufzeitmessung, Aufruf der Engine
- `cli.py`: Argumente, Zeitraumeingabe, Mapping von `1w` -> `5d`
- `analysis_engine.py`: Screening, Future-Kandidaten, Blocker-Analyse, Backtests

## Beschleunigungen
### 1. Metadaten später laden
Vorher wurden Metadaten für sehr viele Werte zu früh geladen. Jetzt erst für die ausgewählten Kandidaten.

### 2. Weniger Terminal-Ausgabe
`print_diagnostics()` nur noch im langen Modus `-l`.

### 3. Kürzere Batch-Pausen
`pause_seconds=0.2` statt längerer Pausen. Wenn Yahoo instabil wird, diesen Wert wieder erhöhen.

### 4. Laufzeit-Ausgabe
Am Ende wird die gesamte Laufzeit angezeigt.

## Geänderte Dateien
### main.py
Sehr klein, nur:
- CLI lesen
- Zeitraum bestimmen
- Engine starten
- Laufzeit ausgeben

### cli.py
Enthält:
- `parse_args()`
- `normalize_period_input()`
- `choose_interval()`
- `ask_period()`

### analysis_engine.py
Enthält:
- `get_signal_from_df()`
- `backtest_from_df()`
- `build_future_candidates()`
- `collect_buy_blockers()`
- `run_analysis()`

## Einbau im Projekt
Die drei Dateien aus dem Refactor-Ordner in dein Projekt kopieren:

- `main.py`
- `cli.py`
- `analysis_engine.py`

Danach testen:

```bash
PYTHONPATH=. pytest -q
python main.py
python main.py -l
```

## Hinweise
- Die Logik in `output.py`, `strategy.py`, `broker.py`, `data_loader.py` bleibt erhalten.
- Wenn du später noch mehr Geschwindigkeit willst, ist der nächste sinnvolle Schritt ein **Cache für Ticker-Metadaten** und ggf. ein **Zwischenspeicher für Benchmark-Daten**.

## Nächste sinnvolle Ausbaustufen
1. Metadaten-Cache als JSON-Datei
2. optionaler `--quiet` Modus
3. Watchlist-Historie über mehrere Tage
4. sauberer Architekturtest für Modul-Schnittstellen
