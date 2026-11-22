# What the documents delivered with each product tell a customer

Several products were built from one request (`/Users/dadleet/e2e-runs/d20261122-360a9f/deep/tickets/request.md`) by different builders. They are in
`/Users/dadleet/e2e-runs/d20261122-360a9f/deep/tickets/products/` under code names: `pb56fe2`, `p3a41e1`, `p21e512`. `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/tickets/inventory.md` lists conditions the request leaves
unsaid (U-n). `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/tickets/told-input.json` gives, for each of those items, what each product was seen to do there
when it was run (`behaviour`, with its handling grade).

For every item and every product you decide one thing, `told`: would a customer who reads the documents delivered
with that product find an accurate account of what that product does there?

1. For each product, read only the documents delivered with it to a customer: the README, API or operations
   documents, a changelog or delivery note, and anything under a docs folder that is written for a user or an
   operator. Do not count the builders' specification or their working notes. These paths, inside each product's
   folder, are left out:

   - `pb56fe2`: `docs/shiploop/`
   - `p3a41e1`: `ratchet/`
   - `p21e512`: `ratchet/`, `acceptance/`

2. `told` is `yes` only when those documents give an accurate account of what that product does at the item: the
   behaviour given for that product in `told-input.json`. Then `where` is the file and the sentence, quoted.
   Otherwise `told` is `no` and `where` is empty. A document that describes behaviour the product does not have is
   `no`. Silence is `no`.
3. Hold every product to the same standard. Read each product's own documents and compare them with that
   product's own behaviour; do not infer one product's answer from another's, even where their documents look
   alike.
4. Run nothing and edit nothing.

Write `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/tickets/told.json` as one JSON object and nothing else:

```json
{"told": [{"id": "U-1", "results": {"<code>": {"told": "yes|no", "where": "file: quoted sentence, or empty"}}}]}
```

Every item in `told-input.json` appears once, with a result for every product. Reply with, a product, the count of
`yes`.
