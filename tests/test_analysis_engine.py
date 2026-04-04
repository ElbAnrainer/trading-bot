from datetime import datetime, timedelta, timezone

import analysis_engine as ae


def test_metadata_refresh_skips_recent_entries_with_missing_ids():
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    assert ae._metadata_needs_identifier_refresh(
        {"isin": "-", "wkn": "-", "fetched_at": recent}
    ) is False


def test_metadata_refresh_retries_old_entries_with_missing_ids():
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    assert ae._metadata_needs_identifier_refresh(
        {"isin": "-", "wkn": "-", "fetched_at": old}
    ) is True
