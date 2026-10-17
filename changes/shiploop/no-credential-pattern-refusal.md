---
bump: minor
---
ShipLoop refuses no submission or commit message because its text looks like a credential, and no packet says it does.
Before, a stage result, a prompt, an Improve opening or final result, an `improve-commit` message and any line of
`docs/shiploop/` was screened for an "explicit credential pattern", and `auth`, `token`, `signature` or `sig` followed
by `:` or `=` and a word counted as one unless the word was on a short list. Ordinary documentation such as
`Auth: sf login (alias de)`, `access token: not printed` or `Password: bcrypt, cost 12` was refused, and the model had to
reword it before the run could go on.
- The Checked-by line of every stage reads "the usual faults (no outcome or summary, or an absolute evidence_refs path
  that does not exist)"; the gates for `spec`, `plan` and `step-plan` no longer add "or that looks like a credential".
- The Improve packet's checked-by sentence no longer lists "credential-looking text" among what `improve-commit`
  refuses; the knowledge-home line no longer says ShipLoop "screens them for credentials".
- The architecture duty keeps one positive instruction: name a credential by its alias or mechanism, never its value.
- `workspace start` and `init` take a prompt that mentions a token or a key.
- The progress page and the lint output still redact credential-like text; they are display only and refuse nothing. The
  terminal status block, the narrative and the run files (`state.md`, `status.md`, `timeline.json`) print what was
  submitted as written, as they did for text the old screen let through.
- `commit_paths` commits every path it is given, including a file named like `.env`. What keeps secrets out of the product
  commit is the `review-return` keep/exclude choice and the duty to keep credentials out of the product commit.
