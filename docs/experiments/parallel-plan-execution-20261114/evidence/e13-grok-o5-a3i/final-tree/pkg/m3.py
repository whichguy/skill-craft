"""Merge overlapping closed integer intervals."""


def merge_intervals(intervals):
    """Return a new sorted list of merged [start, end] intervals.

    Intervals that share at least one integer point are combined.
    The input list and its inner pairs are left unchanged.
    """
    if not intervals:
        return []
    ordered = sorted(([start, end] for start, end in intervals), key=lambda pair: pair[0])
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last = merged[-1]
        if start <= last[1]:
            if end > last[1]:
                last[1] = end
        else:
            merged.append([start, end])
    return merged
