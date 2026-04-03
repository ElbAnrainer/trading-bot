from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from config import (
    CACHE_DIR,
    DATA_DIR,
    DATA_DIR_ENV_VAR,
    PROJECT_CACHE_DIR,
    PROJECT_REPORTS_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
)

IGNORED_FILENAMES = {
    ".DS_Store",
}


@dataclass(frozen=True)
class MigrationOperation:
    source: Path
    destination: Path


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in IGNORED_FILENAMES
    )


def build_migration_plan(
    source_reports: Path | None = None,
    source_cache: Path | None = None,
    source_root_journal: Path | None = None,
    destination_reports: Path | None = None,
    destination_cache: Path | None = None,
) -> list[MigrationOperation]:
    source_reports = source_reports or Path(PROJECT_REPORTS_DIR)
    source_cache = source_cache or Path(PROJECT_CACHE_DIR)
    source_root_journal = source_root_journal or (Path(PROJECT_ROOT) / "trading_journal.csv")
    destination_reports = destination_reports or Path(REPORTS_DIR)
    destination_cache = destination_cache or Path(CACHE_DIR)

    operations_by_destination: dict[Path, Path] = {}

    for source in _iter_files(source_reports):
        destination = destination_reports / source.relative_to(source_reports)
        operations_by_destination.setdefault(destination, source)

    if source_root_journal.exists():
        destination = destination_reports / "trading_journal.csv"
        operations_by_destination.setdefault(destination, source_root_journal)

    for source in _iter_files(source_cache):
        destination = destination_cache / source.relative_to(source_cache)
        operations_by_destination.setdefault(destination, source)

    plan: list[MigrationOperation] = []
    for destination, source in sorted(operations_by_destination.items(), key=lambda item: str(item[0])):
        if source.resolve() == destination.resolve():
            continue
        plan.append(MigrationOperation(source=source, destination=destination))
    return plan


def apply_migration_plan(
    plan: list[MigrationOperation],
    *,
    overwrite: bool = False,
) -> tuple[int, int]:
    copied = 0
    skipped = 0

    for operation in plan:
        operation.destination.parent.mkdir(parents=True, exist_ok=True)
        if operation.destination.exists() and not overwrite:
            skipped += 1
            print(f"[SKIP] {operation.destination}")
            continue

        shutil.copy2(operation.source, operation.destination)
        copied += 1
        print(f"[COPY] {operation.source} -> {operation.destination}")

    return copied, skipped


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Migriert alte Laufzeitdaten aus dem Repo in den konfigurierten "
            "Datenordner."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Migration wirklich ausfuehren. Ohne diesen Schalter erfolgt nur ein Dry-Run.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Vorhandene Zieldateien ueberschreiben.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    plan = build_migration_plan()

    print(f"Repo-Quelle reports/: {PROJECT_REPORTS_DIR}")
    print(f"Repo-Quelle .cache/:  {PROJECT_CACHE_DIR}")
    print(f"Ziel-Datenordner:     {DATA_DIR}")
    print(f"Ziel-Reports:         {REPORTS_DIR}")
    print(f"Ziel-Cache:           {CACHE_DIR}")
    print(f"Env-Override:         {DATA_DIR_ENV_VAR}")
    print()

    if not plan:
        print("Keine alten Laufzeitdaten im Repo gefunden.")
        return 0

    print("Geplante Migration:")
    for operation in plan:
        action = "ueberschreiben" if args.overwrite and operation.destination.exists() else "kopieren"
        if operation.destination.exists() and not args.overwrite:
            action = "ueberspringen"
        print(f"- {action}: {operation.source} -> {operation.destination}")

    print()

    if not args.apply:
        print("Dry-Run abgeschlossen.")
        print("Zum Ausfuehren: python migrate_runtime_data.py --apply")
        print("Optional mit Ueberschreiben: python migrate_runtime_data.py --apply --overwrite")
        return 0

    copied, skipped = apply_migration_plan(plan, overwrite=args.overwrite)
    print()
    print(f"Migration abgeschlossen: {copied} kopiert, {skipped} uebersprungen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
