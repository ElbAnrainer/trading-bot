import mimetypes
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

from config import TRADING_REPORT_PDF

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT_TLS = 587
GMAIL_SMTP_PORT_SSL = 465


def _env(name, default=""):
    return os.getenv(name, default).strip()


def _split_recipients(value):
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _load_mail_config(mail_to_override=None):
    to_value = mail_to_override or _env("MAIL_TO")
    config = {
        "smtp_host": _env("SMTP_HOST", GMAIL_SMTP_HOST),
        "smtp_port": int(_env("SMTP_PORT", str(GMAIL_SMTP_PORT_TLS))),
        "smtp_user": _env("SMTP_USER"),
        "smtp_password": _env("SMTP_PASSWORD"),
        "mail_from": _env("MAIL_FROM"),
        "mail_to": _split_recipients(to_value),
        "mail_subject_prefix": _env("MAIL_SUBJECT_PREFIX", "[Trading Bot]"),
        "use_ssl": _env("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes", "on"),
    }
    return config


def _validate_config(config):
    missing = []

    if not config["smtp_user"]:
        missing.append("SMTP_USER")
    if not config["smtp_password"]:
        missing.append("SMTP_PASSWORD")
    if not config["mail_from"]:
        missing.append("MAIL_FROM")
    if not config["mail_to"]:
        missing.append("MAIL_TO oder --mail-to")

    if missing:
        raise RuntimeError(
            "Mail-Konfiguration unvollständig. Fehlend: " + ", ".join(missing)
        )


def _build_subject(config):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{config['mail_subject_prefix']} Trading Report {now}"


def _build_body_text():
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


def _attach_file(message, file_path):
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


def _build_message(config, attachment_paths):
    message = EmailMessage()
    message["From"] = config["mail_from"]
    message["To"] = ", ".join(config["mail_to"])
    message["Subject"] = _build_subject(config)
    message.set_content(_build_body_text())

    for path in attachment_paths:
        _attach_file(message, path)

    return message


def _send_via_tls(config, message):
    with smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(config["smtp_user"], config["smtp_password"])
        server.send_message(message)


def _send_via_ssl(config, message):
    with smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"], timeout=30) as server:
        server.login(config["smtp_user"], config["smtp_password"])
        server.send_message(message)


def send_report_email(
    attachment_paths,
    mail_to_override=None,
):
    config = _load_mail_config(mail_to_override=mail_to_override)
    _validate_config(config)

    if isinstance(attachment_paths, str):
        attachment_paths = [attachment_paths]

    cleaned_paths = [p for p in attachment_paths if p]
    if not cleaned_paths:
        raise RuntimeError("Keine Anhänge für den Mailversand angegeben.")

    message = _build_message(config, cleaned_paths)

    if config["use_ssl"] or config["smtp_port"] == GMAIL_SMTP_PORT_SSL:
        _send_via_ssl(config, message)
    else:
        _send_via_tls(config, message)

    print("Mailversand erfolgreich.")
    print(f"Empfänger: {', '.join(config['mail_to'])}")
    for path in cleaned_paths:
        print(f"Anhang: {path}")


if __name__ == "__main__":
    send_report_email([TRADING_REPORT_PDF])
