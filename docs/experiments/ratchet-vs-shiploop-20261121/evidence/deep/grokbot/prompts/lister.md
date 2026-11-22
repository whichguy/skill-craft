# What a request asks for, and what it leaves unsaid

Read `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/request.md`: a request a customer gave a software builder. The files the builder started from are in `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/base/` (read them as far as the request touches them). 
You will not see anything that was built. Do not build anything.

Write two lists.

**stated**: every requirement the request states, as separate items that can each be checked on a running product
on its own. One behaviour an item. Keep the request's own words for values, names and limits. Leave nothing out and
add nothing the request does not say.

**unstated**: the conditions the request leaves unsaid that the customer, someone operating the product or the next
person to maintain it would plausibly care about once the product is in use. For each one: what the request does
not settle, why someone would care, and a `probe`: exact steps on a running product that show what it does there.
Leave out anything a reasonable builder could ignore: taste, speculative scale, hardening no one asked for. Do not
decide the answer; where several answers would be fine, say so in `fine_answers`.

Answer with one JSON object and nothing else:

```json
{"stated": [{"text": "..."}],
 "unstated": [{"text": "what is left unsaid", "why": "who cares and why", "probe": "exact steps", "fine_answers": "..."}]}
```
