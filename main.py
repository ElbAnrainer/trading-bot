import argparse
import time

from env_loader import load_env
from dependency_check import check_dependencies

load_env()

from cli import choose_interval as _choose_interval
from analysis_engine import (
    run_analysis,
    get_signal_from_df as _get_signal_from_df,
    build_future_candidates as _build_future_candidates,
)
from output import (
    print_runtime,
    set_pro_mode,
    set_beginner_mode,
    print_explanations,
)
from decision_explanations import enrich_analysis_bundle
from report_pdf import run as run_pdf_report
from report_writer import update_latest_json_context
from gmail_api_report import send_report_email
from trading_engine import (
    build_trading_plan,
    print_trading_plan,
    simulate_trading_decisions,
    print_trading_decisions,
)
from walkforward import run_walk_forward
from performance import run_live, print_performance
from dashboard import build_dashboard
from dashboard_live import run_live_terminal
from mini_trading_system import run_mini_trading_system
from realistic_backtest import run_realistic_backtest, print_realistic_backtest_summary
from config import DAILY_REPORT_HTML, REPORTS_DIR, get_active_profile_name, get_trading_config, list_profile_names


def normalize_period_input(period):
    mapping = {
        "1t": "1d",
        "1d": "1d",
        "1w": "5d",
        "5d": "5d",
        "1m": "1mo",
        "1mo": "1mo",
        "3m": "3mo",
        "3mo": "3mo",
        "6m": "6mo",
        "6mo": "6mo",
        "1j": "1y",
        "1y": "1y",
        "2j": "2y",
        "2y": "2y",
        "3j": "3y",
        "3y": "3y",
    }
    if period is None:
        return None
    return mapping.get(str(period).lower(), period)


def choose_interval(period):
    period = normalize_period_input(period)
    return _choose_interval(period)


def get_signal_from_df(df, rate):
    return _get_signal_from_df(df, rate)


def build_future_candidates(analyzed, top_n):
    return _build_future_candidates(analyzed, top_n)


def parse_args():
    """
    Test-kompatible Funktion:
    gibt weiterhin ein Tuple zurück.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--period", default=None)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--min-volume", type=int, default=1000000)
    parser.add_argument("-l", "--pro", dest="pro_mode", action="store_true")

    args = parser.parse_args()

    return (
        bool(args.pro_mode),
        args.top,
        args.min_volume,
        normalize_period_input(args.period),
    )


def _build_cli_parser():
    active_profile = get_active_profile_name()

    parser = argparse.ArgumentParser(
        prog="python main.py",
        description=(
            "Trading-Bot für Analyse, Backtesting und Simulation.\n"
            "Es werden keine echten Orders ausgeführt und keine Broker angebunden.\n"
            f"Aktives Regel-/Trading-Profil: {active_profile}"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  python main.py\n"
            "  python main.py -p 6mo -t 10\n"
            "  python main.py --profile offensiv\n"
            "  python main.py --profile mittel --capital 5000\n"
            "  python main.py --compare-profiles\n"
            "  python main.py --pro\n"
            "  python main.py --pro --fast\n"
            "  python main.py --live\n"
            "  python main.py --dashboard\n"
            "  python main.py --mini-system\n"
            "  python main.py --no-pdf\n"
            "  python main.py --mail\n"
        ),
    )

    parser.add_argument(
        "-p",
        "--period",
        default=None,
        help="Analysezeitraum, z. B. 1mo, 3mo, 6mo oder 1y",
    )
    parser.add_argument(
        "-t",
        "--top",
        type=int,
        default=None,
        help="Anzahl der Top-Kandidaten für Auswahl und Auswertung",
    )
    parser.add_argument(
        "-mv",
        "--min-volume",
        type=int,
        default=1000000,
        help="Minimales durchschnittliches Handelsvolumen",
    )
    parser.add_argument(
        "--profile",
        choices=list_profile_names(),
        default=None,
        help="Profil nur fuer diesen Lauf ueberschreiben, ohne das gespeicherte aktive Profil zu aendern",
    )
    parser.add_argument(
        "--compare-profiles",
        action="store_true",
        help="Vergleicht alle Profile auf Basis des aktuellen Analyse-Snapshots",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=None,
        help="Kapital fuer diesen Lauf ueberschreiben; ohne Angabe wird das Profil-Startkapital verwendet",
    )

    parser.add_argument(
        "-l",
        "--pro",
        dest="pro_mode",
        action="store_true",
        help="Verbesserte Analyse-Ausgabe mit Fortschritt, Details, Farben und Warnhinweisen",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Separate Live-Tabelle mit laufend aktualisierten Score-Daten anzeigen",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Schnellmodus fuer Analyse/--pro: ueberspringt Walk-Forward und realistischen Backtest",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Echtes Live-Terminal mit Auto-Refresh starten",
    )
    parser.add_argument(
        "--long",
        action="store_true",
        help="Ausführlichere Detailausgabe aktivieren",
    )
    parser.add_argument(
        "--beginner",
        action="store_true",
        help="Zusätzliche Erklärungen für Einsteiger anzeigen",
    )
    parser.add_argument(
        "--mini-system",
        action="store_true",
        help="Mini-Trading-System mit gespeichertem Depotzustand starten",
    )

    parser.add_argument(
        "--mail",
        action="store_true",
        help="Erzeugte Reports zusätzlich per Mail versenden",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="PDF-Erzeugung deaktivieren",
    )
    parser.add_argument(
        "--skip-realistic-backtest",
        action="store_true",
        help="Realistische 10.000-EUR-Schätzung überspringen",
    )

    return parser


def _parse_cli():
    return _build_cli_parser().parse_args()


def _run_mail(send_mail, pdf_path):
    import os

    if not send_mail:
        return

    print("\n==============================")
    print("MAILVERSAND")
    print("------------------------------")

    try:
        if not pdf_path:
            raise RuntimeError("Kein PDF vorhanden")

        attachments = [pdf_path]

        if os.path.exists(DAILY_REPORT_HTML):
            attachments.append(DAILY_REPORT_HTML)

        send_report_email(attachment_paths=attachments)

    except Exception as exc:
        print("Mail-Fehler:", exc)

    print("==============================\n")


def _symbols_for_realistic_backtest(result, top_n: int) -> list[str]:
    symbols = []

    for item in result.get("future_candidates", []):
        sym = item.get("symbol")
        if sym:
            symbols.append(sym)

    if symbols:
        return symbols[:top_n]

    for item in result.get("results", []):
        sym = item.get("symbol")
        if sym:
            symbols.append(sym)

    return symbols[:top_n]


def _build_profile_comparison_rows(
    analysis_result: dict,
    total_capital: float | None = None,
    top_n: int | None = None,
    current_positions: dict | None = None,
    peak_equity: float | None = None,
    profile_names: list[str] | None = None,
) -> list[dict]:
    current_positions = current_positions or {}
    rows = []

    for profile_name in profile_names or list_profile_names():
        cfg = get_trading_config(profile_name)
        profile_capital = float(total_capital if total_capital is not None else cfg["initial_capital"])
        profile_top_n = int(top_n if top_n is not None else cfg["max_positions"])
        plan = build_trading_plan(
            total_capital=profile_capital,
            top_n=profile_top_n,
            profile_name=profile_name,
        )
        decisions = simulate_trading_decisions(
            analysis_result=analysis_result,
            total_capital=profile_capital,
            current_positions=current_positions,
            peak_equity=peak_equity,
            top_n=profile_top_n,
            profile_name=profile_name,
        )
        orders = decisions.get("orders", [])
        buy_orders = sum(1 for order in orders if order.get("action") == "BUY")
        sell_orders = sum(1 for order in orders if order.get("action") == "SELL")
        rows.append(
            {
                "profile_name": profile_name,
                "capital": profile_capital,
                "max_positions": int(cfg.get("max_positions", 0)),
                "max_position_pct": float(cfg.get("max_position_pct", 0.0)),
                "min_trade_eur": float(cfg.get("min_trade_eur", 0.0)),
                "stop_loss_pct": float(cfg.get("stop_loss_pct", 0.0)),
                "max_drawdown_pct": float(cfg.get("max_drawdown_pct", 0.0)),
                "plan_size": len(plan),
                "buy_orders": buy_orders,
                "sell_orders": sell_orders,
                "trading_blocked": bool(decisions.get("drawdown_state", {}).get("trading_blocked", False)),
                "top_symbols": [item.get("symbol", "-") for item in plan[:3]],
            }
        )

    return rows


def print_profile_comparison(rows: list[dict], selected_profile: str) -> None:
    print("\n========================================")
    print(" PROFILVERGLEICH")
    print("========================================")

    if not rows:
        print("Keine Vergleichsdaten verfuegbar.")
        print("========================================\n")
        return

    print(f"{'PROFIL':<14}{'KAPITAL':>12}{'TOP':>6}{'STOP':>8}{'DD':>8}{'BUY':>6}{'SELL':>6}{'BLOCK':>8}  TOP-SYMBOLE")
    print("-" * 100)

    for row in rows:
        label = row["profile_name"]
        if row["profile_name"] == selected_profile:
            label = f"{label}*"

        top_symbols = ", ".join(row.get("top_symbols", [])) or "-"
        print(
            f"{label:<14}"
            f"{float(row.get('capital', 0.0)):>12.0f}"
            f"{int(row.get('plan_size', 0)):>6}"
            f"{float(row.get('stop_loss_pct', 0.0)) * 100:>7.1f}%"
            f"{float(row.get('max_drawdown_pct', 0.0)) * 100:>7.1f}%"
            f"{int(row.get('buy_orders', 0)):>6}"
            f"{int(row.get('sell_orders', 0)):>6}"
            f"{('JA' if row.get('trading_blocked') else 'NEIN'):>8}  "
            f"{top_symbols}"
        )

    print("\n* markiert das fuer diesen Lauf ausgewaehlte Profil")
    print("========================================\n")


def run():
    args = _parse_cli()

    if not check_dependencies():
        print("Fehlende Abhängigkeiten. Der Start wurde abgebrochen.")
        return

    selected_profile = getattr(args, "profile", None) or get_active_profile_name()
    compare_profiles = bool(getattr(args, "compare_profiles", False))
    active_cfg = get_trading_config(selected_profile)
    run_capital = float(args.capital if args.capital is not None else active_cfg["initial_capital"])
    active_top_n = int(args.top if args.top is not None else active_cfg["max_positions"])

    if args.dashboard:
        run_live_terminal()
        return

    if args.mini_system:
        run_mini_trading_system(
            total_capital=run_capital,
            top_n=active_top_n,
            period=normalize_period_input(args.period) or "6mo",
            interval="1d",
            profile_name=selected_profile,
        )
        return

    if args.live:
        run_live()
        return

    set_pro_mode(args.pro_mode)
    set_beginner_mode(args.beginner)

    start = time.time()
    active_profile = selected_profile

    print("\n========================================")
    print(" AKTIVES PROFIL")
    print("========================================")
    print(active_profile)
    if getattr(args, "profile", None):
        print("(Override nur fuer diesen Lauf)")
    print(f"Kapital: {run_capital:.2f} EUR | Top-N: {active_top_n}")
    print("========================================\n")

    period = normalize_period_input(args.period) or "1mo"

    result = run_analysis(
        period=period,
        top_n=active_top_n,
        min_volume=args.min_volume,
        long_mode=args.long or args.pro_mode,
        show_progress=args.pro_mode,
        profile_name=active_profile,
    )

    plan = build_trading_plan(
        total_capital=run_capital,
        top_n=active_top_n,
        profile_name=active_profile,
    )
    result, plan, _ = enrich_analysis_bundle(
        result,
        trading_plan=plan,
        decisions=None,
        profile_name=active_profile,
    )
    print_trading_plan(plan)

    current_positions = {}

    decisions = simulate_trading_decisions(
        analysis_result=result,
        total_capital=run_capital,
        current_positions=current_positions,
        peak_equity=None,
        top_n=active_top_n,
        profile_name=active_profile,
    )
    result, plan, decisions = enrich_analysis_bundle(
        result,
        trading_plan=plan,
        decisions=decisions,
        profile_name=active_profile,
    )
    print_trading_decisions(decisions)

    if compare_profiles:
        comparison_rows = _build_profile_comparison_rows(
            analysis_result=result,
            total_capital=args.capital,
            top_n=args.top,
            current_positions=current_positions,
            peak_equity=None,
        )
        print_profile_comparison(comparison_rows, active_profile)
        result = dict(result)
        result["profile_comparison"] = comparison_rows

    update_latest_json_context(
        output_dir=REPORTS_DIR,
        profile_name=active_profile,
        results=result.get("results", []),
        portfolio=result.get("portfolio", {}),
        future_candidates=result.get("future_candidates", []),
        trading_plan=plan,
        decisions=decisions,
    )
    build_dashboard(
        analysis_result=result,
        trading_plan=plan,
        decisions=decisions,
        profile_name=active_profile,
    )

    if args.fast:
        print("\n[FAST MODE] Walk-Forward und realistischer Backtest werden uebersprungen.")
    else:
        run_walk_forward(
            top_n=active_top_n,
            min_volume=args.min_volume,
            profile_name=active_profile,
        )

    if not args.fast and not args.skip_realistic_backtest:
        symbols = _symbols_for_realistic_backtest(result, top_n=active_top_n)
        realistic = run_realistic_backtest(
            symbols=symbols,
            period=period,
            interval="1d",
            profile_name=active_profile,
        )
        print_realistic_backtest_summary(realistic)

    print_performance()

    pdf_path = None
    if not args.no_pdf:
        pdf_path = run_pdf_report()

    _run_mail(args.mail, pdf_path)

    runtime = time.time() - start
    print_runtime(runtime)
    print_explanations()

    return result


if __name__ == "__main__":
    run()
