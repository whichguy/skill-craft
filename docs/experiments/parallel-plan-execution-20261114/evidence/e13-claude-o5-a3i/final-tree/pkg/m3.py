"""Interval merging."""


def merge_intervals(intervals):
    """Merge integer intervals sharing at least one point; return new sorted list."""
    result = []
    for start, end in sorted(([s, e] for s, e in intervals), key=lambda p: p[0]):
        if result and start <= result[-1][1]:
            if end > result[-1][1]:
                result[-1][1] = end
        else:
            result.append([start, end])
    return result
