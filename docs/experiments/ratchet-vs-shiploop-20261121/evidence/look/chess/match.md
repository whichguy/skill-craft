# Match one review's findings to another list

`/Users/dadleet/e2e-runs/d20261122-360a9f/look/chess/work/docs/shiploop/look.md` is a review of a delivered product: a list of shortfalls and a list of choices the customer was not told.
`/Users/dadleet/e2e-runs/d20261122-360a9f/look/chess/judged.json` is what other people found on the same product, working separately: `shortfalls` (conditions it handles
badly, ids U-n), `defects` (ids D-n) and `silent` (conditions it handles acceptably but its documents do not
mention, ids U-n). The request is `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/chess/request.md`.

For each shortfall in the review, list the ids in `shortfalls` or `defects` that describe the same behaviour of the
product (the same thing going wrong, whatever the wording), or none. For each choice in the review, list the ids
in `silent` (or `shortfalls`) about the same open point, or none. Match on substance; do not stretch.

Write `/Users/dadleet/e2e-runs/d20261122-360a9f/look/chess/matched.json` as one JSON object and nothing else:

```json
{"shortfalls": [{"n": 1, "title": "the review's own heading", "severity": "high|medium|low", "matches": ["D-2"]}],
 "choices": [{"n": 1, "text": "the first words of the review's line", "matches": ["U-7"]}]}
```

Number the review's items in its own order. Reply with the counts: shortfalls, of them matched; choices, of them
matched.
