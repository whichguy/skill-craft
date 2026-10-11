# ShipLoop navigator state

```shiploop-state
{
  "accepted": {
    "nav-5a33f68283194113a1d4315bdf6e6700": {
      "awaiting": {
        "kind": "present",
        "no_default": "Every Chrome launch in this host fails before the page request, so the recorded system command cannot pass here and a later stage cannot treat TC-BROWSER as done.",
        "report": "The exit code and the last lines of node browser.mjs. Exit 0 should print TC-BROWSER narrow and wide shots showed miss, hit, or sunk.",
        "steps": [
          "From the worktree, run node browser.mjs on a Mac where Google Chrome can open http://127.0.0.1 and show the Battleship page."
        ]
      },
      "blocked_by": "access",
      "headline": "Restart check passed; Chrome never loads the page here",
      "outcome": "blocked"
    }
  },
  "history": [
    {
      "action": "nav-774f810f16884215a05d6b8d887a894b",
      "outcome": "done",
      "stage": "system-test-author",
      "summary": "Two local system checks cover the criteria that node --test does not. node browser.mjs is TC-BROWSER (R-4, NFR-2): Chrom",
      "workitem": null
    },
    {
      "action": "nav-5a33f68283194113a1d4315bdf6e6700",
      "outcome": "blocked",
      "stage": "system-test",
      "summary": "node restart-check.mjs exited 0: an id from a stopped server.js is 404 after a new process starts. node browser.mjs exit",
      "workitem": null
    }
  ],
  "inner_loops": {},
  "stage": "system-test",
  "status": "blocked",
  "status_reason": "access: node restart-check.mjs exited 0: an id from a stopped server.js is 404 after a new process starts. node browser.mjs exited 1. Chrome lists the game URL but the document stays about:blank, and server.js never receives a request from Chrome. Stderr is CVDisplayLinkCreateWithCGDisplay failed, CVReturn -6670. Headless new, headless old, swiftshader, a woken display, and open -na all did the same. This host cannot produce the TC-BROWSER observation. SYS-RESTART is done. TC-BROWSER still needs a Chrome that can open http://127.0.0.1.",
  "work_index": 2,
  "work_items": [
    {
      "id": "W1"
    },
    {
      "id": "W2"
    }
  ]
}
```
