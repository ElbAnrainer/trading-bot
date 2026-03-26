import os


ENV_FILE = ".env"


def load_env(path=ENV_FILE):
    """
    Lädt einfache .env-Datei (KEY=VALUE) in os.environ
    Überschreibt KEINE bereits gesetzten Systemvariablen
    """

    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Leer / Kommentar
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Nur setzen, wenn noch nicht vorhanden
            if key not in os.environ:
                os.environ[key] = value
