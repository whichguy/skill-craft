"""Interval merging."""


def merge_intervals(intervals):
    """Merge integer intervals sharing at least one point; input is not modified."""
    merged = []
    for start, end in sorted(intervals, key=lambda iv: (iv[0], iv[1])):
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged
