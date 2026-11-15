def merge_intervals(intervals):
    """Merge intervals sharing at least one integer point; input is not modified."""
    merged = []
    for start, end in sorted(([a, b] for a, b in intervals), key=lambda p: p[0]):
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged
