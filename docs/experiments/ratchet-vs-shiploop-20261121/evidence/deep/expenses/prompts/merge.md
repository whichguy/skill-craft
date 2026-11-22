# Merge the lists into one inventory

In `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/expenses/` are two lists written from the same request by two readers who saw no product: `lister-a.json` and
`lister-b.json` (the request is `request.md`). `arm-points.md` is a third list: points raised by people who built
the product.

Work in this order and write `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/expenses/merged.json`:

```json
{"stated": [{"id": "S-1", "text": "..."}],
 "unstated": [{"id": "U-1", "text": "...", "why": "who cares and what a failure costs", "probe": "exact steps on a running product",
               "fine_answers": "the outcomes that would be acceptable", "sources": ["a", "b", "arm"]}]}
```

1. `stated`: the union of the two readers' stated items, duplicates merged, one checkable behaviour an item, in the
   request's order. Check each against `request.md`: drop an item the request does not state, and add one it states
   that both readers missed.
2. `unstated`, first from the two readers only: the union of their unstated points. Merge duplicates and merge
   variants of one obligation into one item (one obligation, one item, however many ways it can be worded), with
   the sources that raised it (`a`, `b`). Finish this list before you open `arm-points.md`.
3. Then read `arm-points.md`. Where a point there is already an item, add `arm` to that item's sources and change
   nothing else in it. Where it is new, add an item with sources `["arm"]`, as a condition a product can be
   probed for. Leave out lines that are not about the product's behaviour (benchmark hardware, visual taste).
4. Do not judge whether a point matters: that is another step. Every item needs a probe a person could follow on
   any build of this request, written against the product's interface and not one build's internals, and the
   outcomes that would be acceptable. Write them where the source gave none.
5. Number the items S-1.. and U-1.. Write nothing else in the file. Reply with the two counts and the number of
   unstated items by source combination.
