# How the independent review was run

- Reviewer: gpt-6.2-sol (the newest Sol in ~/.codex/models_cache.json, fetched 2026-11-19), effort max, ask-sol runner, --profile consult (read-only sandbox).
- Working directory: a neutral mktemp export of origin/main d1bc14e4ba94edcab016917c452b53dd60b73634 (git archive), plus REVIEW-CONTEXT/ with the last 40 E2E commit messages, older one-line subjects, and the 2026-11-18 campaign's E2E-FINDINGS.md; account name, host name, emails and the owner's name masked in the added files.
- Brief: sol-review-brief.md (verbatim). Answer: sol-review.md (verbatim text of the runner's JSON 'text').
