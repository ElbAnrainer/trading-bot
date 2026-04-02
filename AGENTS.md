# AGENTS.md

## Purpose

This repository is a Python trading simulation and analysis project.

It is used for:
- backtesting
- simulation
- reporting
- dashboarding
- terminal-based monitoring

It is not used for:
- real broker connections
- real orders
- investment advice
- production live trading deployment

Any agent working in this repository should preserve that boundary.

## Repository Reality

This project is mostly organized as root-level Python modules instead of a package tree.

Important entry points and core modules:
- `main.py` -> main CLI entry point
- `run.sh` -> local launcher / interactive terminal flow
- `realistic_backtest.py` -> realistic portfolio backtest logic
- `mini_trading_system.py` -> persistent mini trading workflow
- `trading_engine.py` -> buy/sell decision planning
- `analysis_engine.py` -> analysis pipeline
- `dashboard.py` and `dashboard_live.py` -> dashboard output
- `report_pdf.py`, `daily_report.py`, `gmail_api_report.py` -> reporting
- `portfolio_state.py` and `state.py` -> persisted state
- `tests/` -> pytest suite
- `reports/` -> generated output and persisted runtime data

Do not assume directories like `/data`, `/strategy`, or `/execution` exist here. They do not reflect the current project layout.

## Environment

Local development currently uses:
- Python from `.venv`
- `pytest`
- `pandas`
- `yfinance`
- `matplotlib`
- `reportlab`
- optional Google mail dependencies for report delivery

Use the local environment first:

```bash
source .venv/bin/activate
```

Common validation commands:

```bash
.venv/bin/python -m pytest -p no:cacheprovider -q
env MPLCONFIGDIR=/tmp/mpl-trading-bot .venv/bin/python main.py --help
```

When running tests or CLI commands that import matplotlib, setting `MPLCONFIGDIR=/tmp/mpl-trading-bot` is preferred to avoid local cache permission noise.

## Development Rules

- Keep changes consistent with a simulation-only system.
- Prefer small, local changes over broad rewrites.
- Add or update tests when changing trading logic, state handling, reporting logic, or selection logic.
- Prefer deterministic unit tests with monkeypatching over network-dependent tests.
- Avoid introducing hidden behavior that depends on live network calls during tests.
- Preserve persisted state formats unless you intentionally migrate them.
- Use existing config values from `config.py` and trading profile helpers instead of scattering new constants.

## Trading and Modeling Constraints

Agents should explicitly guard against:
- lookahead bias
- future data leakage
- unrealistic fills
- missing fees or slippage assumptions
- breaking cooldown / holding-period logic
- mixing simulation behavior with implied real execution behavior

If a change touches:
- `realistic_backtest.py`
- `mini_trading_system.py`
- `trading_engine.py`
- `candle_backtest.py`
- `risk.py`
- `advanced_risk.py`

then review the effect on:
- fees
- slippage
- stop logic
- drawdown control
- cooldown behavior
- state persistence
- test determinism

## State and Output

This repository intentionally uses persistent files in `reports/`.

Important examples:
- learned scores
- portfolio state
- dashboard output
- latest report artifacts
- realistic backtest summaries

Agents must not assume the project is stateless.

When changing code that writes history or state, keep field names and time handling consistent across readers and writers.

## Testing Expectations

Before finishing meaningful code changes, prefer running:

```bash
.venv/bin/python -m pytest -p no:cacheprovider -q
```

For focused work, run the relevant test module first, then the full suite if the change is non-trivial.

Good tests in this repository are:
- fast
- local
- deterministic
- explicit about financial assumptions

## Review Guidance

When reviewing or proposing changes:
- call out unrealistic assumptions
- flag missing fees, slippage, cooldowns, or drawdown controls
- prefer simple explanations
- state assumptions clearly
- mention operational risk if state files, reports, or optional mail flows are affected

## Path Note

The active repository is the workspace copy under:

`/Users/thorsten/development/codex/Börse/trading-bot`

Do not treat the older copy under `/Users/thorsten/development/trading-bot` as the primary working tree.
