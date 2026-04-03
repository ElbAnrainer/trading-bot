from pathlib import Path

import migrate_runtime_data as mrd


def test_build_migration_plan_prefers_reports_journal_and_includes_cache(tmp_path):
    source_reports = tmp_path / "reports"
    source_cache = tmp_path / ".cache"
    source_root_journal = tmp_path / "trading_journal.csv"
    destination_reports = tmp_path / "data" / "reports"
    destination_cache = tmp_path / "data" / "cache"

    (source_reports / "status").mkdir(parents=True)
    source_cache.mkdir()

    (source_reports / "trading_journal.csv").write_text("from_reports", encoding="utf-8")
    (source_reports / "status" / "check_status_latest.json").write_text("{}", encoding="utf-8")
    (source_cache / "ticker_metadata.json").write_text("{}", encoding="utf-8")
    source_root_journal.write_text("from_root", encoding="utf-8")

    plan = mrd.build_migration_plan(
        source_reports=source_reports,
        source_cache=source_cache,
        source_root_journal=source_root_journal,
        destination_reports=destination_reports,
        destination_cache=destination_cache,
    )

    pairs = {(op.source, op.destination) for op in plan}

    assert (
        source_reports / "trading_journal.csv",
        destination_reports / "trading_journal.csv",
    ) in pairs
    assert (
        source_root_journal,
        destination_reports / "trading_journal.csv",
    ) not in pairs
    assert (
        source_cache / "ticker_metadata.json",
        destination_cache / "ticker_metadata.json",
    ) in pairs


def test_apply_migration_plan_copies_files_and_skips_existing_by_default(tmp_path):
    source = tmp_path / "legacy.json"
    destination = tmp_path / "data" / "legacy.json"
    source.write_text('{"old": true}', encoding="utf-8")

    copied, skipped = mrd.apply_migration_plan(
        [mrd.MigrationOperation(source=source, destination=destination)]
    )

    assert copied == 1
    assert skipped == 0
    assert destination.read_text(encoding="utf-8") == '{"old": true}'

    source.write_text('{"old": false}', encoding="utf-8")

    copied, skipped = mrd.apply_migration_plan(
        [mrd.MigrationOperation(source=source, destination=destination)]
    )

    assert copied == 0
    assert skipped == 1
    assert destination.read_text(encoding="utf-8") == '{"old": true}'


def test_apply_migration_plan_overwrites_when_requested(tmp_path):
    source = tmp_path / "legacy.json"
    destination = tmp_path / "data" / "legacy.json"
    source.write_text('{"version": 2}', encoding="utf-8")
    destination.parent.mkdir(parents=True)
    destination.write_text('{"version": 1}', encoding="utf-8")

    copied, skipped = mrd.apply_migration_plan(
        [mrd.MigrationOperation(source=source, destination=destination)],
        overwrite=True,
    )

    assert copied == 1
    assert skipped == 0
    assert destination.read_text(encoding="utf-8") == '{"version": 2}'
