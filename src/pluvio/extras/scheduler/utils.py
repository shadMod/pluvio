from __future__ import annotations

from datetime import date, timedelta


def group_consecutive_dates(dates: list[date]) -> list[tuple[date, date]]:
    """
    Collapse a sorted list of dates into contiguous (start, end) ranges.

    Example:
        [2024-01-01, 2024-01-02, 2024-01-03, 2024-01-07]
        → [(2024-01-01, 2024-01-03), (2024-01-07, 2024-01-07)]

    This minimises CDS API requests by batching consecutive missing days.
    """
    if not dates:
        return []

    ranges: list[tuple[date, date]] = []
    start = prev = dates[0]

    for d in dates[1:]:
        if d - prev > timedelta(days=1):
            ranges.append((start, prev))
            start = d
        prev = d

    ranges.append((start, prev))
    return ranges
