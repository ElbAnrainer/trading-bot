import argparse
import os
import time

from dependency_check import check_dependencies


def _early_fix_requested():
    import sys
    return "--fix" in sys.argv


if not check_dependencies(auto_install=_early_fix_requested()):
    print("Abbruch: Fehlende Dependencies.")
    raise SystemExit(1)

from analysis_engine import (
    build_future_candidates as _build_future_candidates,
    get_signal_from_df as _get_signal_from_df,
    run_analysis,
)
from cli import choose_interval as _choose_interval
from env_loader import load_env
from gmail_api_report import send_report_email
from output import (
    print_runtime,
    set_pro_mode,
    set_beginner_mode,
    print_explanations,
)
from report_pdf import run as run_pdf_report


load_env()


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
    return mapping.get(str(period).strip().lower(), period)


def choose_interval(period):
    normalized = normalize_period_input(period)
    return _choose_interval(normalized)


def get_signal_from_df(df, rate_to_eur_latest):
    return _get_signal_from_df(df, rate_to_eur_latest)


def build_future_candidates(analyzed, top_n):
    return _build_future_candidates(analyzed, top_n)


def _parse_human_number(value):
    text = str(value).strip().lower().replace("_", "")

    if not text:
        raise argparse.ArgumentTypeError("Leerer Zahlenwert ist nicht erlaubt.")

    multipliers = {
        "k": 1_000,
        "m": 1_000_000,
    }

    suffix = text[-1]
    if suffix in multipliers:
        try:
            return int(float(text[:-1]) * multipliers[suffix])
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Ungültiger Zahlenwert: {value}") from exc

    try:
        return int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Ungültiger Zahlenwert: {value}") from exc


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description=(
            "Paper-Trading Simulator\n"
            "========================================\n"
            "Analyse- und Backtesting-System für Aktien.\n\n"
            "Hinweis:\n"
            "  - Nur Simulation\n"
            "  - Keine echten Orders\n"
            "  - Keine Broker-Anbindung\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--period",
        dest="period",
        default=None,
        help=(
            "Analysezeitraum\n"
            "----------------------------------------\n"
            "Kurzformen:\n"
            "  1t, 1w, 1m, 3m, 6m, 1j, 2j, 3j\n\n"
            "Langformen:\n"
            "  1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 3y\n\n"
            "Default: interaktive Auswahl"
        ),
    )

    parser.add_argument(
        "-t",
        "--top",
        dest="top",
        type=_parse_human_number,
        default=5,
        metavar="N",
        help=(
            "Anzahl der Top-Aktien für Backtest (Default: 5)\n"
            "Erlaubt auch Suffixe wie: 10, 25, 1k"
        ),
    )

    parser.add_argument(
        "-mv",
        "--min-volume",
        dest="min_volume",
        type=_parse_human_number,
        default=1_000_000,
        metavar="VOLUME",
        help=(
            "Minimales durchschnittliches Handelsvolumen (Default: 1000000)\n"
            "Erlaubt auch Suffixe wie: 500k, 1m"
        ),
    )

    parser.add_argument(
        "-l",
        action="store_true",
        help="Pro-Modus: Detailausgabe + Live-Fortschritt + Farben/Highlights/Warnungen",
    )

    parser.add_argument(
        "--long",
        action="store_true",
        help="Nur Detailmodus (ohne Pro-Modus)",
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Nur Live-Fortschritt",
    )

    parser.add_argument(
        "--beginner",
        action="store_true",
        help="Einsteiger-Modus: zusätzliche Erklärungen am Ende der Ausgabe",
    )

    parser.add_argument(
        "--mail",
        action="store_true",
        help="Verschickt den Report per Gmail API als E-Mail",
    )

    parser.add_argument(
        "--mail-to",
        dest="mail_to",
        default=None,
        help="Empfängeradresse für den Mailversand (überschreibt MAIL_TO)",
    )

    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Automatischen PDF-Report nach dem Lauf deaktivieren",
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Installiert fehlende Python-Abhängigkeiten automatisch vor dem Start",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="trading-bot v3.0",
    )

    parser.epilog = (
        "\nBeispiele:\n"
        "----------------------------------------\n"
        "  python main.py\n"
        "  python main.py -t 10 -p 3y\n"
        "  python main.py -mv 500k\n"
        "  python main.py --live\n"
        "  python main.py --long\n"
        "  python main.py -l\n"
        "  python main.py --beginner\n"
        "  python main.py --mail\n"
        "  python main.py --mail --mail-to thorsten@example.com\n"
        "  python main.py --fix\n"
        "  python main.py --no-pdf\n\n"
        "Weitere Tools:\n"
        "----------------------------------------\n"
        "  python walk_forward.py        Langfrist-Test\n"
        "  python daily_report.py        Tagesreport\n"
        "  python report_pdf.py          Premium-PDF erzeugen\n"
        "  man ./docs/trading-bot.1      Manpage anzeigen\n"
    )

    return parser


def _parse_cli_namespace():
    parser = _build_parser()
    args = parser.parse_args()

    if args.period:
        args.period = normalize_period_input(args.period)

    args.long_mode = bool(args.long or args.l)
    args.live_mode = bool(args.live or args.l)
    args.pro_mode = bool(args.l)
    args.beginner_mode = bool(args.beginner)

    return args


def parse_args():
    args = _parse_cli_namespace()
    return args.long_mode, args.top, args.min_volume, args.period


def _choose_period_interactively():
    print("\nZeitraum wählen:")
    print("  1t  = 1 Tag")
    print("  1w  = 1 Woche")
    print("  1m  = 1 Monat")
    print("  3m  = 3 Monate")
    print("  6m  = 6 Monate")
    print("  1j  = 1 Jahr")
    print("  2j  = 2 Jahre")
    print("  3j  = 3 Jahre\n")

    selected = input("-> ").strip().lower()
    return normalize_period_input(selected or "1m")


def _resolve_existing_pdf():
    latest_path = os.path.join("reports", "trading_report_latest.pdf")
    if os.path.exists(latest_path):
        return latest_path
    return None


def _run_auto_pdf_report(skip_pdf):
    if skip_pdf:
        return _resolve_existing_pdf()

    print("\n==============================")
    print("AUTO-PDF-REPORT")
    print("------------------------------")
    try:
        pdf_path = run_pdf_report()
        print("Premium-PDF erfolgreich erzeugt.")
        print("==============================\n")
        return pdf_path
    except Exception as exc:
        print(f"PDF-Report konnte nicht erzeugt werden: {exc}")
        print("==============================\n")
        return None


def _run_mail_report(send_mail, mail_to, attachment_path):
    if not send_mail:
        return

    print("\n==============================")
    print("MAILVERSAND")
    print("------------------------------")

    try:
        if not attachment_path:
            raise RuntimeError(
                "Kein PDF-Report vorhanden. Erzeuge zuerst einen Report oder nutze main.py ohne --no-pdf."
            )

        attachments = [attachment_path]

        daily_html = os.path.join("reports", "daily_report_latest.html")
        daily_txt = os.path.join("reports", "daily_report_latest.txt")

        if os.path.exists(daily_html):
            attachments.append(daily_html)
        if os.path.exists(daily_txt):
            attachments.append(daily_txt)

        send_report_email(
            attachment_paths=attachments,
            mail_to_override=mail_to,
        )
    except Exception as exc:
        print(f"Mailversand fehlgeschlagen: {exc}")

    print("==============================\n")


def run():
    args = _parse_cli_namespace()

    period = args.period or _choose_period_interactively()

    set_pro_mode(args.pro_mode)
    set_beginner_mode(args.beginner_mode)

    start_time = time.time()

    result = run_analysis(
        period=period,
        top_n=args.top,
        min_volume=args.min_volume,
        long_mode=args.long_mode,
        show_progress=args.live_mode,
    )

    pdf_path = _run_auto_pdf_report(skip_pdf=args.no_pdf)
    _run_mail_report(
        send_mail=args.mail,
        mail_to=args.mail_to,
        attachment_path=pdf_path,
    )

    runtime_seconds = time.time() - start_time
    print_runtime(runtime_seconds)
    print_explanations()

    return result


if __name__ == "__main__":
    run()
