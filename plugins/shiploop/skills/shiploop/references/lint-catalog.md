# Script-owned lint catalog

ShipLoop runs a small advisory lint pass itself on runs whose run option `lint`
is `fix` or `report` (new runs record `fix`; a saved run without
the key behaves as `off` and is never migrated). The pass is supporting output,
not exit-criteria evidence: the step still selects and runs its own static
checks, and ShipLoop never gates a transition on a lint result or on the
`shiploop lint` exit code. See [the run option](../SKILL.md#script-owned-lint).

The fenced record at the end of this page is data that
`scripts/shiploop_lint.py` reads at runtime. The safety pins below are fixed in
code and are not catalog options.

## When it runs

- **Item base.** When a work item's inner loop starts, ShipLoop snapshots the
  working content (tracked and untracked, not ignored files) into a private
  Git index and records the tree under `<run>/lint/items/<W>.md`.
- **Scope.** Only files under the run's repository directory are in scope
  (a run whose `repo` is a subdirectory of a checkout never lints or fixes a
  sibling directory). ShipLoop runtime metadata (`.shiploop`,
  `.shiploop-improve`, `.until-loop`, `.shiploop-handoff` and the other
  workspace runtime directories) is never part of a work item's changes.
- **static-checks.** The `complete` that enters `static-checks` runs a pass.
  Only the item's first entry may apply fixes, and only with a per-item base;
  later entries and any fallback base (workspace baseline, then `HEAD`) are
  report-only, and the block says so.
- **verify.** Entry to `verify` runs a report-only pass, or repeats the stored
  static-checks result word for word when the tree is unchanged.
- `next` and `context` only re-render the stored record and mark it stale when a
  scoped file changed afterwards. They never lint.

Records live under `<run>/lint/` with schema `shiploop-lint/v1`. They never enter
checks, manifests, documentation receipts or chain evidence.

## Tools

| Tier | Tool | Files | Runs |
| --- | --- | --- | --- |
| 0 | `git diff --check` | every changed file | always; conflict-marker findings are dropped for `*.md` |
| 0 | `bash -n` | shell | only when ShellCheck is absent |
| 0 | `node --check` | JavaScript | only when `node` resolves to a real binary, not a shim |
| 0 | JSON parse (in process) | `*.json` | skips JSONC names such as `tsconfig*.json` |
| 1 | `ruff` | Python | check (`--no-fix`) plus a stdin fixer |
| 1 | `shellcheck` | shell | check only (`-f gcc`) |
| rec. | `actionlint` | `.github/workflows/*.yml` | never run in phase 1; recommended or listed |

A Tier-0 syntax failure counts only as a regression: the base blob must have
passed the same check.

**Safety pins (code, not catalog):**

- Tools, Git included, resolve from absolute `PATH` entries only. A resolved
  path inside any work tree of the repository (a linked worktree's source
  checkout counts), or a version-manager shim (Volta, mise, asdf, nodenv,
  pyenv, rbenv; the realpath is checked), is refused and reported, never run.
  Tool children get a `PATH` without relative or repository entries. Changed
  paths are passed as `./<path>` or after `--`, never as a bare argument.
- The ruff fixer always carries `--no-unsafe-fixes`,
  `--config 'lint.extend-safe-fixes=[]'` and
  `--config 'lint.extend-unfixable=["F401","F811","F841"]'`; deletion-type
  findings are reported as fixable, not applied. Check runs carry `--no-fix`.
  Ruff merges `extend-safe-fixes` across layers, so the empty pin cannot clear a
  repository's own list: before applying a fix under a project config, ShipLoop
  reads `ruff check --show-settings` and withholds the file's fixes unless
  `linter.safety_table.forced_safe` is empty.
  A file with no project ruff configuration (walking up for `ruff.toml`,
  `.ruff.toml`, or a `pyproject.toml` with a `[tool.ruff` table) is linted with
  `--isolated --select F,E9`; a file only ruff's built-in excludes skip there
  counts as uncovered, not as excluded by the repository.
- ShellCheck without a `.shellcheckrc` runs with `-S warning --norc`.
- A fix is applied all or nothing per file, only when every changed hunk lies on
  a line this work item changed, to a regular single-link file inside the
  repository whose sha256 is unchanged since it was read. Line endings and mode
  bits are preserved. A pending journal `<run>/lint/pending-<action>.patch` is
  written before any product file changes. An unconsumed journal is shown on
  every packet until the next pass adopts it: that pass keeps it under
  `<run>/lint/logs/` and names it once in its block. A fix whose syntax guard
  does not complete is withheld. Identical blobs count as mirrors only under
  the same file name, and never when empty.
- The whole pass has a wall-clock budget of about 20 seconds that also bounds
  Git plumbing; files over 2 MB and changed-line diffs too large to attribute
  are not fixed, and skipped tools and files are reported.

## Not run by ShipLoop

Linters that execute repository code are listed with a risk tag and "ask the
user before running": `package.json` lint scripts, Makefile targets named
`lint`, `lint-*` or `format-check`, pre-commit hooks, and eslint, prettier or
markdownlint-cli2 configurations. Missing tools produce install
recommendations naming the searched `PATH`. ShipLoop never installs anything.

## Catalog data

```shiploop-state
{
  "schema": "shiploop-lint-catalog/v1",
  "classes": {
    "python": {"suffixes": [".py", ".pyi"], "shebang": ["python", "python3"], "linter": "ruff"},
    "shell": {"suffixes": [".sh", ".bash"], "shebang": ["sh", "bash"], "linter": "shellcheck"},
    "javascript": {"suffixes": [".js", ".mjs", ".cjs"], "shebang": ["node"], "linter": ""},
    "json": {"suffixes": [".json"], "shebang": [], "linter": ""},
    "workflow": {"prefix": ".github/workflows/", "suffixes": [".yml", ".yaml"], "shebang": [], "linter": "actionlint"}
  },
  "jsonc_names": ["tsconfig*.json", "jsconfig*.json", ".vscode/*.json", "devcontainer.json", ".devcontainer/*.json", "*.jsonc"],
  "run_in_phase_1": ["ruff", "shellcheck"],
  "recommend": {
    "ruff": "ruff lints and safely fixes Python files",
    "shellcheck": "shellcheck lints shell scripts",
    "actionlint": "actionlint lints GitHub Actions workflow files"
  },
  "declared_markers": {
    "ruff": [".pre-commit-config.yaml", "requirements-dev.txt", "requirements.txt"],
    "shellcheck": [".pre-commit-config.yaml", ".shellcheckrc"],
    "actionlint": [".pre-commit-config.yaml"]
  },
  "shim_dirs": [".pyenv", ".nodenv", ".rbenv", ".asdf", "asdf", "mise", ".mise", "rtx"],
  "caches": [".ruff_cache"],
  "repo_code_configs": {
    "eslint": ["eslint.config.js", "eslint.config.mjs", "eslint.config.cjs", "eslint.config.ts", ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", ".eslintrc.yml", ".eslintrc.yaml"],
    "prettier": [".prettierrc", ".prettierrc.js", ".prettierrc.cjs", ".prettierrc.json", ".prettierrc.yml", ".prettierrc.yaml", "prettier.config.js", "prettier.config.cjs", "prettier.config.mjs"],
    "markdownlint-cli2": [".markdownlint-cli2.jsonc", ".markdownlint-cli2.yaml", ".markdownlint-cli2.cjs", ".markdownlint-cli2.mjs"]
  }
}
```
