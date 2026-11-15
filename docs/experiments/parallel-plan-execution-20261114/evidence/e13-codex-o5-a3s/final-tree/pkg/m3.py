"""Utilities for merging closed integer intervals."""


def merge_intervals(intervals):
    """Return sorted merged intervals without modifying the input."""
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
