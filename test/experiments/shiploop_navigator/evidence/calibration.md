# Oracle calibration reference

Prepared before execution workers received their tasks. This candidate matched all
210 checks but did not settle the original specification ambiguity.

```python
def normalize_ranges(ranges):
    values = []
    for pair in ranges:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError('pair shape')
        start, end = pair
        if type(start) is not int or type(end) is not int or start > end:
            raise ValueError('endpoints')
        values.append([start, end])
    answer = []
    for start, end in sorted(values):
        if answer and start <= answer[-1][1]:
            answer[-1][1] = max(answer[-1][1], end)
        else:
            answer.append([start, end])
    return answer
```
