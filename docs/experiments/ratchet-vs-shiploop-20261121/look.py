#!/usr/bin/env python3
"""One look at a delivered product: the instruction file and the command for each case (journal section 11).

    look.py prepare ROOT        writes ROOT/look/prompts/CASE.md and prints the one_session.py command for each case

The look is one session of the builder's model in a copy of ShipLoop's delivered product (the copy the deep judge
audited, ROOT/deep/CASE/products/<S>). It may write `docs/shiploop/look.md` and nothing else. This script calls no
model.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "ratchet-pilot-20261120"
sys.path.insert(0, str(HERE))
import deep_judge  # the cases, and this machine's Playwright paths

HOST, MODEL, EFFORT = "codex", "gpt-6.2-sol", "medium"
ALLOW = "docs/shiploop/look.md"
LOOK = """# One look at a delivered product

This folder ({{work}}) holds a product that was built and delivered for the request below. Every check passes. Its
builders' specification and working notes are in `docs/shiploop/`.

This look asks one question: now that the product runs, is there anything a user or an operator needs that it does
not do, or that it does without anyone having been told?

## The request
{request}

## What to weigh
- The product itself. Start it and use it as its users and operators would: the request's own examples, values at
  and just past each limit, wrong and odd input, the features next to what was asked, a restart, what its documents
  promise. Use it; do not only read it.{browser}
- The request, read once more for what it implies and the specification does not state.
- The specification and notes in `docs/shiploop/`, for a choice the builders made that the request did not settle.

## What to write
Write `docs/shiploop/look.md` and change nothing else: not the product, not a test, not another document.

**Shortfalls.** Each thing the product does not do that a user or an operator would care about and the request's
intent covers. For each: what is needed; the exact steps that show the product falling short (the commands or page
actions, what came back, what should have); and how much it matters: `high` (loses data, misleads a user or breaks
what worked), `medium` or `low`. A shortfall is not a new feature, a matter of taste or hardening nobody asked for.
If another correct product could behave differently and nobody would miss it, leave it out. Try what you suspect
before you write it: a shortfall you did not see happen does not belong here.

**Choices the customer was not told.** Each place where the request left something open, the product does
something reasonable there, and neither the request nor the documents delivered with the product (not counting
`docs/shiploop/`) say what it does. One line each: the open point, and what the product does.

Write the single line "Nothing found." under a heading whose list is empty.

## Conduct
Work only inside {{work}}; temporary files go in {{tmp}}. Use a free port you pick yourself and data files under
{{tmp}}. Stop every process you start, by its process id, before you finish; never stop processes by name.
"""
BROWSER = """
  Where it has a page, drive the page for real with Playwright from a Node script:
  `const {{{{ chromium }}}} = require('{playwright}')` and
  `chromium.launch({{{{ executablePath: '{browser}' }}}})` (headless). Close every browser you open."""


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] != "prepare":
        raise SystemExit(__doc__)
    root = Path(argv[1]).expanduser().resolve()
    prompts = root / "look" / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    cases = json.loads((PILOT / "cases.json").read_text())
    for case, full_name in deep_judge.CASES.items():
        key = json.loads((root / "deep" / case / "key.json").read_text())
        code = next(code for code, entry in key.items() if entry["point"] == "S")
        browser = BROWSER.format(playwright=deep_judge.PLAYWRIGHT, browser=deep_judge.BROWSER) if case == "grokbot" else ""
        text = LOOK.format(request=cases[full_name]["request"].strip().replace("{", "{{").replace("}", "}}"), browser=browser)
        (prompts / f"{case}.md").write_text(text.replace("{{", "{").replace("}}", "}"))
        print(f"python3 {PILOT / 'one_session.py'} --folder {root / 'deep' / case / 'products' / code} "
              f"--prompt {prompts / f'{case}.md'} --allow {ALLOW} --output {root / 'look' / case} "
              f"--host {HOST} --model {MODEL} --effort {EFFORT} --role look")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
