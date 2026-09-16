# Local browser-consumer fixture

This fixture separates a local candidate from the independently served artifact
and from the consumer's interactive result. It has no cloud target, account,
credential, or external resource.

Run one served state on a loopback-only HTTP server:

```sh
python3 test/experiments/shiploop_delivery/browser_consumer/serve_fixture.py --case working
```

The command prints an `http://127.0.0.1:PORT/` URL and runs until interrupted.
Open that URL in a browser and perform these checks:

| Case | Expected browser observation |
| --- | --- |
| `working` | `Candidate: candidate-2`; clicking **Move piece** changes the live result to `Movement cue visible for the selected piece.` and `data-result` to `passed`. |
| `broken` | `Candidate: candidate-2`; clicking **Move piece** reports `Movement cue did not become visible.` and `data-result` to `failed`. |
| `stale` | The served page says `Candidate: candidate-1`, even though `local-candidate/index.html` says `candidate-2`; do not call it current behavior. |
| `login` | The page reports that login is required; no interactive behavior observation exists. |

For a quick loopback-serving check without a browser:

```sh
python3 test/experiments/shiploop_delivery/browser_consumer/serve_fixture.test.py
```

That check only verifies static served content. The click behavior remains a
manual browser observation, intentionally distinct from source or HTTP status.
