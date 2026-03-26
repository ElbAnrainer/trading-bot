import base64
import os
from email.message import EmailMessage
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from report_pdf import build_report_context


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _split_recipients(value: str) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _load_config(mail_to_override: Optional[str] = None) -> dict:
    client_secret_file = _env("GOOGLE_CLIENT_SECRET_FILE", "credentials_google.json")
    token_file = _env("GOOGLE_TOKEN_FILE", "token_google.json")
    mail_from = _env("MAIL_FROM")
    mail_to = _split_recipients(mail_to_override or _env("MAIL_TO"))
    subject_prefix = _env("MAIL_SUBJECT_PREFIX", "[Trading Bot]")

    return {
        "client_secret_file": client_secret_file,
        "token_file": token_file,
        "mail_from": mail_from,
        "mail_to": mail_to,
        "subject_prefix": subject_prefix,
    }


def _validate_config(config: dict) -> None:
    missing = []

    if not config["mail_from"]:
        missing.append("MAIL_FROM")
    if not config["mail_to"]:
        missing.append("MAIL_TO oder --mail-to")
    if not os.path.exists(config["client_secret_file"]):
        missing.append(f"GOOGLE_CLIENT_SECRET_FILE ({config['client_secret_file']})")

    if missing:
        raise RuntimeError(
            "Gmail API Konfiguration unvollständig. Fehlend: " + ", ".join(missing)
        )


def _load_credentials(config: dict) -> Credentials:
    creds = None
    token_file = config["token_file"]

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            config["client_secret_file"],
            SCOPES,
        )
        creds = flow.run_local_server(port=0)

    with open(token_file, "w", encoding="utf-8") as token:
        token.write(creds.to_json())

    return creds


def _build_subject(config: dict) -> str:
    from datetime import datetime

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{config['subject_prefix']} Trading Report {ts}"


def _build_body_text() -> str:
    return (
        "Hallo,\n\n"
        "anbei der aktuelle Trading-Report aus dem Simulationssystem.\n\n"
        "Wichtig:\n"
        "- Nur Simulation\n"
        "- Keine echten Orders\n"
        "- Keine Anlageberatung\n\n"
        "Viele Grüße\n"
        "Trading Bot\n"
    )


def _fmt_money(value: float) -> str:
    return f"{value:.2f} EUR"


def _fmt_pct(value: float) -> str:
    return f"{value:.2f} %"


def _metric_card(title: str, value: str, subtitle: str = "") -> str:
    subtitle_html = f'<div style="font-size:12px;color:#9ca3af;margin-top:4px;">{subtitle}</div>' if subtitle else ""
    return f"""
    <td style="padding:8px;">
      <div style="background:#111827;border:1px solid #1f2937;border-radius:10px;padding:14px 16px;">
        <div style="font-size:12px;color:#9ca3af;text-transform:uppercase;letter-spacing:.06em;">{title}</div>
        <div style="font-size:24px;font-weight:700;color:#f9fafb;margin-top:6px;">{value}</div>
        {subtitle_html}
      </div>
    </td>
    """


def _build_html_dashboard_body() -> str:
    context = build_report_context()
    metrics = context["metrics"]
    top_symbols = context["top_symbols"]

    if not context["trades"]:
        return """
        <html>
          <body style="font-family:Arial,sans-serif;background:#0b1220;color:#f9fafb;padding:24px;">
            <h1 style="margin-top:0;">Trading Bot Report</h1>
            <p>Keine abgeschlossenen Simulations-Trades vorhanden.</p>
            <p>Nur Simulation. Keine echten Orders. Keine Anlageberatung.</p>
          </body>
        </html>
        """

    rows = []
    for item in top_symbols[:5]:
        rows.append(
            f"""
            <tr>
              <td style="padding:10px 12px;border-bottom:1px solid #1f2937;color:#f9fafb;">{item['symbol']}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #1f2937;color:#d1d5db;">{item['company']}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #1f2937;color:#d1d5db;text-align:right;">{item['trades']}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #1f2937;color:#d1d5db;text-align:right;">{item['pnl']:.2f} EUR</td>
              <td style="padding:10px 12px;border-bottom:1px solid #1f2937;color:#d1d5db;text-align:right;">{item['hit_rate']:.2f}%</td>
              <td style="padding:10px 12px;border-bottom:1px solid #1f2937;color:#d1d5db;text-align:right;">{item['avg_score']:.2f}</td>
            </tr>
            """
        )

    return f"""
    <html>
      <body style="margin:0;padding:0;background:#0b1220;font-family:Arial,sans-serif;">
        <div style="max-width:980px;margin:0 auto;padding:24px;">
          <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:24px;">
            <div style="font-size:12px;color:#9ca3af;text-transform:uppercase;letter-spacing:.08em;">Trading Bot</div>
            <h1 style="margin:8px 0 6px 0;color:#f9fafb;font-size:30px;">Daily Trading Report</h1>
            <div style="color:#9ca3af;font-size:14px;">Nur Simulation • Keine echten Orders • Keine Anlageberatung</div>
          </div>

          <div style="height:18px;"></div>

          <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            <tr>
              {_metric_card("Trades", str(metrics["trades"]), "abgeschlossen")}
              {_metric_card("Gesamt P/L", _fmt_money(metrics["total_pnl"]), "Gesamtergebnis")}
              {_metric_card("Trefferquote", _fmt_pct(metrics["win_rate"]), "Gewinntrades")}
            </tr>
            <tr>
              {_metric_card("Sharpe", f"{metrics['sharpe']:.2f}", "Risiko / Rendite")}
              {_metric_card("Drawdown", _fmt_pct(metrics["max_drawdown_pct"]), "Maximaler Rückgang")}
              {_metric_card("Expectancy", _fmt_money(metrics["expectancy"]), "pro Trade")}
            </tr>
          </table>

          <div style="height:18px;"></div>

          <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:20px;">
            <h2 style="margin:0 0 14px 0;color:#f9fafb;font-size:20px;">Top-Aktien nach Performance</h2>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
              <thead>
                <tr>
                  <th style="padding:10px 12px;text-align:left;color:#9ca3af;border-bottom:1px solid #1f2937;">Symbol</th>
                  <th style="padding:10px 12px;text-align:left;color:#9ca3af;border-bottom:1px solid #1f2937;">Firma</th>
                  <th style="padding:10px 12px;text-align:right;color:#9ca3af;border-bottom:1px solid #1f2937;">Trades</th>
                  <th style="padding:10px 12px;text-align:right;color:#9ca3af;border-bottom:1px solid #1f2937;">P/L</th>
                  <th style="padding:10px 12px;text-align:right;color:#9ca3af;border-bottom:1px solid #1f2937;">Treffer</th>
                  <th style="padding:10px 12px;text-align:right;color:#9ca3af;border-bottom:1px solid #1f2937;">Ø Score</th>
                </tr>
              </thead>
              <tbody>
                {''.join(rows)}
              </tbody>
            </table>
          </div>

          <div style="height:18px;"></div>

          <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:20px;">
            <h2 style="margin:0 0 10px 0;color:#f9fafb;font-size:20px;">Kurz-Einordnung</h2>
            <ul style="margin:0;padding-left:18px;color:#d1d5db;line-height:1.7;">
              <li>Endkapital: <strong>{_fmt_money(metrics["final_equity"])}</strong></li>
              <li>Bester Trade: <strong>{_fmt_money(metrics["best_trade"])}</strong></li>
              <li>Schwächster Trade: <strong>{_fmt_money(metrics["worst_trade"])}</strong></li>
            </ul>
          </div>

          <div style="height:18px;"></div>

          <div style="color:#9ca3af;font-size:12px;text-align:center;">
            Dieser Bericht basiert ausschließlich auf Simulationsdaten.
          </div>
        </div>
      </body>
    </html>
    """


def _attach_file(message: EmailMessage, file_path: str) -> None:
    import mimetypes

    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"Anhang nicht gefunden: {file_path}")

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        maintype, subtype = mime_type.split("/", 1)
    else:
        maintype, subtype = "application", "octet-stream"

    with open(file_path, "rb") as f:
        message.add_attachment(
            f.read(),
            maintype=maintype,
            subtype=subtype,
            filename=os.path.basename(file_path),
        )


def _create_message(config: dict, attachment_paths: List[str]) -> EmailMessage:
    message = EmailMessage()
    message["To"] = ", ".join(config["mail_to"])
    message["From"] = config["mail_from"]
    message["Subject"] = _build_subject(config)

    text_body = _build_body_text()
    message.set_content(text_body)

    html_body = _build_html_dashboard_body()
    message.add_alternative(html_body, subtype="html")

    for path in attachment_paths:
        _attach_file(message, path)

    return message


def _encode_message(message: EmailMessage) -> dict:
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_report_email(
    attachment_paths,
    mail_to_override: Optional[str] = None,
) -> None:
    config = _load_config(mail_to_override=mail_to_override)
    _validate_config(config)

    if isinstance(attachment_paths, str):
        attachment_paths = [attachment_paths]

    cleaned_paths = [p for p in attachment_paths if p]
    if not cleaned_paths:
        raise RuntimeError("Keine Anhänge für den Mailversand angegeben.")

    creds = _load_credentials(config)
    service = build("gmail", "v1", credentials=creds)

    message = _create_message(config, cleaned_paths)
    encoded = _encode_message(message)

    service.users().messages().send(userId="me", body=encoded).execute()

    print("Gmail API Versand erfolgreich.")
    print(f"Empfänger: {', '.join(config['mail_to'])}")
    for path in cleaned_paths:
        print(f"Anhang: {path}")


if __name__ == "__main__":
    latest_pdf = os.path.join("reports", "trading_report_latest.pdf")
    send_report_email([latest_pdf])
