import os


ENV_FILE = ".env"


def load_env(path=ENV_FILE):
    """
    Lädt eine einfache .env-Datei mit KEY=VALUE Paaren in os.environ.
    Bereits gesetzte Umgebungsvariablen werden nicht überschrieben.
    Kommentare und leere Zeilen werden ignoriert.
    """

    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value
