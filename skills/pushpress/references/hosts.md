# Hosts: what is needed, what is tested

Discovery is not execution: seeing this skill on a host does not mean the host can drive PushPress. The UI half needs a
browser tool and the owner's sign-in; the API half needs the `pushpress` MCP server. Without a browser tool the skill still
gives the route map, the action classes and the API reference, and the agent must say that UI work is unavailable rather
than guess.

## Prerequisites for UI work

1. A browser the owner is signed in to (or signs in to), able to open **your own tab** on the tenant origin,
   `https://<tenant>.pushpress.com`.
2. Page content as text or an accessibility tree, and **real pointer clicks**: a synthetic script click does not switch the
   People tabs.
3. Evaluation of JavaScript in the page, with the result returned as text, for `scripts/pp-extract.js`. Without it the
   skill still works from page text and screenshots, more slowly, and the extractor's masks do not apply: take the same
   care by hand.
4. A credential path that never shows a password to the model: a password-manager fill the owner approves, or the owner
   typing it.
5. Re-injection after a full page load. A few routes (for example Reports ▸ Payroll) reload the page and clear page state;
   the extractor saves itself to session storage so one line re-installs it ([browser-technique.md](browser-technique.md#4-extraction-toolkit)).

## Prerequisites for API work (optional)

The `pushpress` MCP server from the official `@pushpress/pushpress` SDK, with an API key held in the environment or a secret
store, never in a committed file. Setup, the tools that message people and the confirmation rule are in
[api-and-mcp-tools.md](api-and-mcp-tools.md).

## Tested matrix

| Host and tools | Status |
|----------------|--------|
| Claude Code or desktop with Claude in Chrome (`mcp__claude-in-chrome__*`) | tested 2026-11-08, read-only, one tenant (*Core Pro Monthly*): every sidebar page, menus and drawers opened and closed, one member profile and the staff profile, sign-in observed once; three fresh-agent runs with the skill only |
| Claude's built-in browser | cannot sign in here: the password-manager grant works only in Claude in Chrome |
| Chrome DevTools MCP (`evaluate_script`), Playwright or Puppeteer on a persisted profile | not tested; the script text may need wrapping as a function, and the owner completes the sign-in |
| Codex, Grok, Cursor, OpenCode | not tested; they need one of the tools above |
| The `pushpress` MCP server (`mcp__pushpress__*` on Claude hosts) | read tools called live on the same tenant; no write tool was ever called |

## Recipe: Claude in Chrome

- Load every browser tool you will need in **one** tool search, and include the credential tools (`request_credentials`,
  `autofill_credential`, `list_granted_credentials`, `release_credentials`, `enter_verification_code`).
- Call `tabs_context_mcp` first, then work in **your own tab** (`tabs_create_mcp`). Never reuse tab IDs from an earlier
  session. Prefer `browser_batch` for sequences you can predict (navigate, wait, extract): it stops at the first error.
- Sign in: ask for the grant before navigating, with `request_credentials` and one `login` entry
  (`website: https://pushpress.com`, keywords `PushPress`, the company name, `gym` and any other word the owner uses for the
  item); the owner approves in 1Password. Then `autofill_credential` on the first login page fills the email and advances.
  At the password step it returned `autosubmit_failed` five times on 2026-11-08 while the session still authenticated (the
  card's step 5): try once, wait, re-check the URL, then ask the owner. `enter_verification_code` is the code-entry feature;
  none was seen.
- Clicks: `find` for the element, then `computer` `left_click` with its `ref`. Refs go stale after a re-render, and a `find`
  can return the neighbouring control, so confirm with a small screenshot when the target matters.
- Page script: `javascript_tool`. Top-level `await` works and an async IIFE returns `{}`; results are cut at about 2.5 K
  characters (write them into a page element and read it with `get_page_text`, as the extractor's `dump` does); output
  containing a URL query string is blocked; a `const` in one call is invisible to the next; a full page load wipes `window`.
- Page text: `get_page_text`. Never use it on a person page: its header carries the page title and URL, which hold a
  person's name and ID.
- Tidy up at the end: run `__pp.clear()`, call `release_credentials`, and close the tabs you opened.

## Recipe: any other tool

Install the extractor once per tab by passing the text of `scripts/pp-extract.js` to the tool's page-script call, then call
`__pp.*` per page as its header describes. If the tool cannot return values from the page, it cannot run the extractor: say
so, and read pages through page text and small screenshots instead. Keep every other rule in the card: your own tab, real
clicks, a yes before anything that saves, sends, charges, deletes or downloads, and no password through you.
