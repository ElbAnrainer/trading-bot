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
from config import DAILY_REPORT_HTML, REPORTS_DIR, get_active_profile_name


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
        default=5,
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


def run():
    args = _parse_cli()

    if not check_dependencies():
        print("Fehlende Abhängigkeiten. Der Start wurde abgebrochen.")
        return

    if args.dashboard:
        run_live_terminal()
        return

    if args.mini_system:
        run_mini_trading_system(
            total_capital=10_000.0,
            top_n=args.top,
            period=normalize_period_input(args.period) or "6mo",
            interval="1d",
        )
        return

    if args.live:
        run_live()
        return

    set_pro_mode(args.pro_mode)
    set_beginner_mode(args.beginner)

    start = time.time()
    active_profile = get_active_profile_name()

    print("\n========================================")
    print(" AKTIVES PROFIL")
    print("========================================")
    print(active_profile)
    print("========================================\n")

    period = normalize_period_input(args.period) or "1mo"

    result = run_analysis(
        period=period,
        top_n=args.top,
        min_volume=args.min_volume,
        long_mode=args.long or args.pro_mode,
        show_progress=args.pro_mode,
    )

    plan = build_trading_plan(
        total_capital=1000,
        top_n=args.top,
        profile_name=active_profile,
    )
    print_trading_plan(plan)

    current_positions = {}

    decisions = simulate_trading_decisions(
        analysis_result=result,
        total_capital=1000.0,
        current_positions=current_positions,
        peak_equity=None,
        top_n=args.top,
        profile_name=active_profile,
    )
    print_trading_decisions(decisions)

    update_latest_json_context(
        output_dir=REPORTS_DIR,
        future_candidates=result.get("future_candidates", []),
        trading_plan=plan,
        decisions=decisions,
    )
    build_dashboard(
        analysis_result=result,
        trading_plan=plan,
        decisions=decisions,
    )

    if args.fast:
        print("\n[FAST MODE] Walk-Forward und realistischer Backtest werden uebersprungen.")
    else:
        run_walk_forward(
            top_n=args.top,
            min_volume=args.min_volume,
            profile_name=active_profile,
        )

    if not args.fast and not args.skip_realistic_backtest:
        symbols = _symbols_for_realistic_backtest(result, top_n=args.top)
        realistic = run_realistic_backtest(
            symbols=symbols,
            period=period,
            interval="1d",
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
