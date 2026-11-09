# Hosts: what is needed, what is tested

Discovery is not execution: seeing this skill on a host does not mean the host can run its reads. Execution needs a browser
tool and nothing else; without one, the skill still gives the catalogue, the confirm text and the portal paths, and the agent
must say that execution is unavailable rather than guess.

## Prerequisites for running reads

1. Access to the owner's existing signed-in browser tab (or a tab the owner signs in), on the portal origin.
2. Evaluation of JavaScript in that tab's page context, with the result awaited (the snippets use `await`; where a tool needs
   a function declaration, pass `--wrap function`).
3. A result channel that returns the value as text, bounded in size, without the host editing or logging secrets.
4. Re-injection after navigation: a full page load clears `window.S80`, so load the runtime again.

For guided writes the host also needs safe navigation and form interaction in the same tab; the agent drives the portal's own
form and never posts directly.

Public reads need only a page on the portal origin (for `window.env`), not a login.

## Tested matrix

| Host and tool | Status |
|---------------|--------|
| Claude Code or desktop with Claude in Chrome (`javascript_tool`) | tested 2026-11-08: roles, club-scoped and public results, tab-resolved member tables, datatable counts, error mapping, discovery |
| Chrome DevTools MCP (`evaluate_script`) | not tested; expected to need `--wrap function` |
| Playwright or Puppeteer on a persisted profile (`page.evaluate`) | not tested |
| Codex, Grok, Cursor, OpenCode | not tested; they need one of the tools above |

## Recipe: Claude in Chrome

- Load the browser tools in one tool search, list tabs, and open a new tab rather than reusing the owner's. The tab group's
  tabs are signed in already when the owner is.
- If the portal sends the tab to the single sign-on page, use the approved password-manager fill on that page (the owner is
  prompted), submit the form, and for a code use the code-entry feature. Do not type credentials.
- The script tool returns about 1,000 characters and blocks output that looks like cookies or query strings. Keep results small
  (`--fields`, `--rows`, `--pick`), pass `--plain`, and for more write the result into a scratch tab on the same origin
  (open the portal's `robots.txt`) with `S80.show(result)`, then read that tab's page text. Never `show` in a tab you need.
- Top-level `await` works in the tool, so the default expression form runs as printed.
- Do not load the runtime from a local web server: the browser asks permission for local-network access and the call hangs.
  Paste the runtime text instead; it is under 20 KB.
- Close the tabs you opened and release the approved credentials when done.

## Recipe: any other tool

Run `"$S80" runtime` in the tab once, then `"$S80" js ID ... --wrap function` for each read and return the function's value. If
the tool cannot return values, it cannot run reads: say so.
