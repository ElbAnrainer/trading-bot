import importlib
import subprocess
import sys


REQUIRED_PACKAGES = {
    "matplotlib": "matplotlib",
    "reportlab": "reportlab",
    "google.auth": "google-auth",
    "google_auth_oauthlib": "google-auth-oauthlib",
    "googleapiclient": "google-api-python-client",
}


def _print_header():
    print("\n========================================")
    print(" Dependency-Check")
    print("========================================\n")


def _install_packages(packages):
    if not packages:
        return True

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])
        return True
    except subprocess.CalledProcessError as exc:
        print(f"\nFehler bei der Installation: {exc}\n")
        return False


def check_dependencies(auto_install=False):
    _print_header()

    missing = []

    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
            print(f"OK    : {module_name}")
        except ImportError:
            print(f"FEHLT : {module_name}")
            missing.append(pip_name)

    if not missing:
        print("\nAlle Dependencies sind installiert.\n")
        return True

    print("\nFehlende Pakete:")
    for pkg in missing:
        print(f"  - {pkg}")

    if auto_install:
        print("\nAuto-Fix aktiv: installiere fehlende Pakete ...\n")
        success = _install_packages(missing)
        if not success:
            return False

        print("\nInstallationslauf abgeschlossen. Prüfe erneut ...\n")

        still_missing = []
        for module_name, pip_name in REQUIRED_PACKAGES.items():
            try:
                importlib.import_module(module_name)
                print(f"OK    : {module_name}")
            except ImportError:
                print(f"FEHLT : {module_name}")
                still_missing.append(pip_name)

        if still_missing:
            print("\nEinige Pakete fehlen weiterhin:")
            for pkg in still_missing:
                print(f"  - {pkg}")
            print()
            return False

        print("\nAlle fehlenden Dependencies wurden erfolgreich installiert.\n")
        return True

    print("\nBitte manuell installieren:")
    print(f"pip install {' '.join(missing)}\n")
    return False


if __name__ == "__main__":
    auto_fix = "--fix" in sys.argv
    ok = check_dependencies(auto_install=auto_fix)
    sys.exit(0 if ok else 1)
