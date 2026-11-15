def merge_intervals(intervals):
    """Merge intervals that share at least one integer point.

    Returns a new list of [start, end] lists, sorted by start. Does not
    modify the input list or its inner interval lists.
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
