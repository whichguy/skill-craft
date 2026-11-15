"""Interval merge utilities."""


def merge_intervals(intervals):
    """Merge integer intervals that share at least one point.

    intervals is a list of [start, end] pairs with start <= end, in any
    order. Returns a new list of [start, end] lists sorted by start.
    The input list (and its inner lists) are not modified.
    """
    if not intervals:
        return []

    ordered = sorted(([start, end] for start, end in intervals), key=lambda iv: iv[0])
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last = merged[-1]
        if start <= last[1]:
            if end > last[1]:
                last[1] = end
        else:
            merged.append([start, end])
    return merged
