# Practice board

The local 8×8 board remains the primary task. Its existing polite status now serves as the selected-square summary immediately below the board; it shows the selected coordinate, and Reset restores “Choose a square”. The existing square controls and state behavior remain in place, with no network calls or runtime package additions.

The post-implementation functional rerun recorded `node --test` as passing for the existing state tests. That result covers selection, coordinate validation, and Reset state; it does not establish rendered layout or visual quality.

To inspect the rendered layout and interaction, first probe the host-provided `PLAYWRIGHT_NODE_PATH` and `BROWSER_EXECUTABLE_PATH` route, then run:

```sh
node scripts/check-board-browser.cjs --light-page '#f4f1e9' --dark-page '#17201f' --square-a '#e7dcc5' --square-b '#34746b' --board-max 32rem --focus-color '#214c46' --dark-focus-color '#f3c15b' --dark-class theme-dark --summary-below --summary-max 32rem --summary-gap 1rem
```

The implementation-stage TC-LAYOUT observation remains pending because no product browser observations were captured during implementation. The test-spec stage planned this command but did not run it. A host capability probe alone is not a product visual result; do not report a rendered pass until the command output has been observed and recorded.
