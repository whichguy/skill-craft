# node-base

Tiny dependency-free Node service. `paginate(items, page, size)` uses `Math.ceil` so trailing partial pages return their remaining items cleanly, and rejects non-integer or non-positive page/size bounds.
