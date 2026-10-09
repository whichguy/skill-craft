# state

```shiploop-state
{
 "status": "active",
 "stage": "inner-loop",
 "revision": 15,
 "planning_review": "none",
 "history": [
  {
   "stage": "intake",
   "outcome": "done",
   "workitem": null,
   "action": "nav-5195c9a34320448ca9037824af1e7c38"
  },
  {
   "stage": "discovery",
   "outcome": "done",
   "workitem": null,
   "action": "nav-bdf2efb2038b434c85f324f1d1a1cd05"
  },
  {
   "stage": "research",
   "outcome": "done",
   "workitem": null,
   "action": "nav-8bd7834ee0234c4190d39b736ca7ddf8"
  },
  {
   "stage": "spec",
   "outcome": "done",
   "workitem": null,
   "action": "nav-980f32cf2ff74c4abfa56f5da3936fd2"
  },
  {
   "stage": "test-strategy",
   "outcome": "done",
   "workitem": null,
   "action": "nav-3630bbd5cee4429d97bd5a1936fe032f"
  },
  {
   "stage": "plan",
   "outcome": "done",
   "workitem": null,
   "action": "nav-191c9362817849c98fdcb30388585e58"
  },
  {
   "stage": "prepare",
   "outcome": "done",
   "workitem": null,
   "action": "nav-08d3cdbd6d144eabac0e9544a3af35db"
  },
  {
   "stage": "get-next-work-item",
   "outcome": "done",
   "workitem": "W1",
   "action": "nav-31a4031afe4047c587b2e12e7e9bd303"
  },
  {
   "stage": "step-plan",
   "outcome": "done",
   "workitem": "W1",
   "action": "nav-5a6f372b323747ee86e3feb6a9d64f1d"
  },
  {
   "stage": "test-spec",
   "outcome": "done",
   "workitem": "W1",
   "action": "nav-7a4aadc020a045219b15f7a108194355"
  },
  {
   "stage": "baseline",
   "outcome": "done",
   "workitem": "W1",
   "action": "nav-a0ffe375927546578950c6f116106b22"
  },
  {
   "stage": "test-author",
   "outcome": "done",
   "workitem": "W1",
   "action": "nav-6d27b38fd69a48d094421df530fc3828"
  },
  {
   "stage": "test-red",
   "outcome": "done",
   "workitem": "W1",
   "action": "nav-270c3de7b85e4f11b3194871ea62995e"
  },
  {
   "stage": "implement",
   "outcome": "done",
   "workitem": "W1",
   "action": "nav-45a075801937477a821befeb9b9d3c03"
  },
  {
   "stage": "implement",
   "outcome": "done",
   "workitem": "W1",
   "action": "nav-503e9bc05ab449f690cff4fd6e585dea"
  }
 ],
 "inner_loops": {
  "W1": {
   "action": {
    "id": "nav-fc245996d1d54460b11982becb5e9db1",
    "stage": "implement"
   },
   "stage": "implement"
  }
 },
 "work_items": [
  {
   "context": "Owns R-1..R-7, D-1..D-6, F-1..F-3, T-1..T-6. Spec: docs/shiploop/spec.md. Commands live only in docs/shiploop/test-strategy.md (full and focused: node --test; smoke: node --test test/rules.test.js; opt-in TC-13: node check/browser-fire.mjs, not under test/). Execution and target are the local worktree. Fixtures: each test builds its own game; HTTP tests use 127.0.0.1 port 0 except the R-2 child that binds 3000; teardown closes the server. Re-check if node or Chrome changes. Module format: CommonJS rules.js and server.js with no package.json. Load seam: require(../rules.js) and a listen export. Steps: S1 rules (deps none) before S2 server (deps S1) before S3 page and S4 HTTP tests (deps S2); S5 browser check deps S3; S6 README deps S2. Injected layouts for deterministic shots; one TC-3 test uses Math.random and counts 17 ship cells. Baseline: discovery node --test was tests 0, missing coverage, not a pass. Expected RED is an assertion failure after a loadable placeholder. No repo skill; re-read SHIPLOOP.md at step plan. UI: spec UI premises, host skill frontend-design by name, cell click plus status text, reduced motion. State: server Map of games, HTTP request/response, gone on process exit. Delivery: no remote; workspace return to local main. Plan note: docs/shiploop/features/build-a-small-single-player-battleship-b142ec/plan.md.",
   "id": "W1",
   "title": "Build the Battleship rules module, Node server, page, and node:test suite"
  }
 ],
 "work_index": 0
}
```
