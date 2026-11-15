"""Merge overlapping closed integer intervals."""


def merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted(([start, end] for start, end in intervals), key=lambda pair: pair[0])
    merged = [ordered[0][:]]
    for start, end in ordered[1:]:
        last = merged[-1]
        if start <= last[1]:
            if end > last[1]:
                last[1] = end
        else:
            merged.append([start, end])
    return merged
