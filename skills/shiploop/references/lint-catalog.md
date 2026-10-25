# Script-owned lint catalog

ShipLoop lints each work item itself on runs whose run option `lint` is `fix`
or `report` (new runs record `fix`; a saved run without the key is refused,
never migrated). The gate pass runs at `complete`: an `implement` step, `test`
or `verify` is not accepted as done while a new finding on a line the item
changed has no waiver. The pass on entry to `verify` is advisory, and ShipLoop never gates on the `shiploop lint` exit code.
The step still selects and runs its own checks. See
[the run option](run-options.md#script-owned-lint).

The fenced record at the end of this page is data that
`scripts/shiploop_lint.py` reads at runtime. The safety pins below are fixed in
code and are not catalog options.

## When it runs

- **Item base.** When a work item's inner loop starts, ShipLoop snapshots the
  working content (tracked and untracked, not ignored files) into a private
  Git index and records the tree under `<run>/lint/items/<W>.md`. This runs in
  every lint mode, as does the **change inventory**: each new `verify`
  action records the item's changed paths (base to current snapshot) under
  `<run>/lint/<action>-inventory.md` for verify's review. `off` stops only
  linters and auto-fix.
- **Scope.** Only files under the run's repository directory are in scope
  (a run whose `repo` is a subdirectory of a checkout never lints or fixes a
  sibling directory). ShipLoop runtime metadata (`.shiploop`,
  `.shiploop-improve`, `.until-loop`, `.shiploop-handoff` and the other
  workspace runtime directories) is never part of a work item's changes.
- **implement, test and verify (gate).** The `complete` that submits an
  `implement` step, `test` or `verify` with outcome `done` runs a pass before the result is accepted, stored as
  `<run>/lint/<action>.gate<N>.md`. With a per-item base it applies safe fixes
  on lines the item changed. It refuses the submission once after applying a
  fix, so the step reruns its checks. It also refuses while a new finding on a
  line the item changed is not listed in the result's `lint_waivers`
  (`[{"id": "L…", "reason": "…"}]`); the refusal prints each finding's ID. IDs
  hash the path, the message and the line's text, not its number, so they
  survive edits above the line. Findings present at the base or elsewhere in a
  file, uncovered files, missing tools, tool errors, timeouts and a pass that
  cannot run never refuse. `send-back` and `blocked` submissions are not linted.
  At `test` and `verify` the gate runs before ShipLoop's own test runs, so the
  tests cover any auto-fix. The implement and test packets print the
  report-only `lint` command to run after each edit, and the latest gate record.
- **verify (advisory).** The `complete` that enters `verify` runs a pass. Only
  the item's first entry may apply fixes, and only with a per-item base; later
  entries and any fallback base (workspace baseline, then `HEAD`) are
  report-only, and the block says so.
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
| 2 | discovered (below) | by file type | when the repository configures it; findings count on lines the item changed |
| 3 | `npm run lint`, `make lint` | changed files no other linter covers | only then; findings count only in changed files |

A Tier-0 syntax failure counts only as a regression: the base blob must have
passed the same check.

**Discovered linters.** For each catalog `discovered` row whose file types
include a changed file, ShipLoop looks for the row's configuration in the run's
repository directory, then the Git top level: a marker file, a
`pyproject.toml` table, or a `package.json` key. With a configuration (or, for
actionlint, none needed), it resolves the tool from `node_modules/.bin` for
node tools, then from `PATH`, and runs it in the run's repository directory on
the changed files of that type. A configured but missing tool produces a
recommendation. A row marked `fixable` in the catalog data (prettier, black,
gofmt, clang-format, terraform fmt today) applies its fix exactly like ruff —
journal-first, only on lines this work item changed, sha256-checked — before
any row's findings are reported; a row without that mark (eslint included,
pending its own fix path; tsc, mypy, markdownlint-cli2, yamllint, actionlint,
ktlint, phpcs, rubocop) only ever reports.

| Linter | Files | Configured by | Output |
| --- | --- | --- | --- |
| eslint | JS/TS, Vue | `eslint.config.*`, `.eslintrc*`, `package.json` `eslintConfig` | JSON |
| prettier (fixable) | JS/TS, JSON, CSS, Markdown, YAML, HTML | `.prettierrc*`, `prettier.config.*`, `package.json` `prettier` | formatted stdin |
| tsc | TS | `tsconfig.json` (project run, findings kept for changed files) | `path(line,col)` |
| mypy | Python | `mypy.ini`, `.mypy.ini`, `[tool.mypy]` | lines |
| black (fixable) | Python | `[tool.black]` | formatted stdin |
| markdownlint-cli2 | Markdown | `.markdownlint-cli2.*`, `.markdownlint.*` | lines |
| yamllint | YAML | `.yamllint*` | parsable lines |
| actionlint | `.github/workflows/*.yml` | nothing; runs when on PATH | lines |
| gofmt (fixable) | Go | `go.mod` | formatted stdin |
| clang-format (fixable) | C/C++/Obj-C | `.clang-format`, `_clang-format` | formatted stdin |
| terraform fmt (fixable) | Terraform/HCL | nothing; runs when on PATH | formatted stdin |
| ktlint | Kotlin | nothing; runs when on PATH | lines |
| phpcs | PHP | `phpcs.xml*`, `.phpcs.xml*` | lines |
| rubocop | Ruby | `.rubocop.yml`, `.rubocop_todo.yml` | lines |

A discovered finding on a line the item changed counts as new. One elsewhere in
a changed file is reported as not compared with the base and never gates.

**Deliberately not catalogued yet**, each for a specific, checked reason
rather than an oversight: Rust (`rustfmt` has no confirmed way to combine
stdin input with a project's own `rustfmt.toml` — no `--assume-filename`-
equivalent flag — so a stdin fix could silently apply the wrong style);
Dockerfile (`hadolint`; `Dockerfile` has no file extension, and this
catalog's matching is suffix-based — needs a small follow-up to how a row
can match, not a catalog change); C#/.NET (`dotnet format` works at
project/solution scope, not a single file); Java (`checkstyle`'s exact
plain-format field layout isn't confirmed); SQL (`sqlfluff` supports stdin
but its parseable output format isn't confirmed). Report-only additions are
low-risk to get slightly wrong (a finding just doesn't parse); a `fixable`
one is not, so none of these is added on an unconfirmed guess.

**Safety pins (code, not catalog):**

- Tools, Git included, resolve from absolute `PATH` entries only, except a
  discovered node tool's `node_modules/.bin` entry, which runs by design
  (repository-configured linters execute repository code). A `PATH` match
  inside any work tree of the repository (a linked worktree's source checkout
  counts), or a version-manager shim (Volta, mise, asdf, nodenv, pyenv, rbenv;
  the realpath is checked), is refused and reported, never run.
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
- A fix — ruff's or any `fixable` discovered row's — is applied all or nothing
  per file, only when every changed hunk lies on a line this work item
  changed, to a regular single-link file inside the repository whose sha256
  is unchanged since it was read. Line endings and mode bits are preserved. A
  pending journal `<run>/lint/pending-<action>.patch` is written before any
  product file changes; it is one entry per path, not one per fixer, so a
  path two fixers both touch in the same pass (for example ruff then black on
  one `.py` file) still gets a single, correct diff from the pass's start to
  its end, never two sections for the same path. An unconsumed journal is
  shown on every packet until the next pass adopts it: that pass keeps it
  under `<run>/lint/logs/` and names it once in its block. A fix whose syntax
  guard does not complete is withheld (ruff only; the other fixable tools are
  pure reformatters and trusted once they exit cleanly). Identical blobs
  count as mirrors only under the same file name, and never when empty.
  `fixable` rows apply in the catalog's own listed order, one row fully
  applied before the next starts, so a file more than one fixable row
  matches (today, only eslint and prettier overlap, and eslint has no fix
  path yet) composes correctly instead of one tool's fix clobbering another's.
- The whole pass has a wall-clock budget of about 120 seconds (60 per tool
  call) that also bounds Git plumbing; files over 2 MB and changed-line diffs
  too large to attribute are not fixed, and skipped tools and files are
  reported.

## Not run by ShipLoop

Listed as not run (the run does not start them and the handoff lists them for the
user, since runs are unattended): `package.json` scripts other than
`lint` that look like lint or format scripts (a format script may rewrite
files), Makefile targets named `lint-*` or `format-check`, and pre-commit hooks
(pre-commit may download hook environments). Missing tools produce install
recommendations naming the searched `PATH`. ShipLoop never installs anything.

## Catalog data

```shiploop-state
{
  "schema": "shiploop-lint-catalog/v1",
  "classes": {
    "python": {
      "suffixes": [
        ".py",
        ".pyi"
      ],
      "shebang": [
        "python",
        "python3"
      ],
      "linter": "ruff"
    },
    "shell": {
      "suffixes": [
        ".sh",
        ".bash"
      ],
      "shebang": [
        "sh",
        "bash"
      ],
      "linter": "shellcheck"
    },
    "javascript": {
      "suffixes": [
        ".js",
        ".mjs",
        ".cjs"
      ],
      "shebang": [
        "node"
      ],
      "linter": ""
    },
    "json": {
      "suffixes": [
        ".json"
      ],
      "shebang": [],
      "linter": ""
    },
    "workflow": {
      "prefix": ".github/workflows/",
      "suffixes": [
        ".yml",
        ".yaml"
      ],
      "shebang": [],
      "linter": "actionlint"
    }
  },
  "jsonc_names": [
    "tsconfig*.json",
    "jsconfig*.json",
    ".vscode/*.json",
    "devcontainer.json",
    ".devcontainer/*.json",
    "*.jsonc"
  ],
  "run_in_phase_1": [
    "ruff",
    "shellcheck"
  ],
  "recommend": {
    "ruff": "ruff lints and safely fixes Python files",
    "shellcheck": "shellcheck lints shell scripts",
    "actionlint": "actionlint lints GitHub Actions workflow files",
    "eslint": "eslint lints JavaScript and TypeScript per the repository's config"
  },
  "declared_markers": {
    "ruff": [
      ".pre-commit-config.yaml",
      "requirements-dev.txt",
      "requirements.txt"
    ],
    "shellcheck": [
      ".pre-commit-config.yaml",
      ".shellcheckrc"
    ],
    "actionlint": [
      ".pre-commit-config.yaml"
    ]
  },
  "shim_dirs": [
    ".pyenv",
    ".nodenv",
    ".rbenv",
    ".asdf",
    "asdf",
    "mise",
    ".mise",
    "rtx"
  ],
  "caches": [
    ".ruff_cache"
  ],
  "discovered": [
    {
      "name": "eslint",
      "suffixes": [
        ".js",
        ".mjs",
        ".cjs",
        ".jsx",
        ".ts",
        ".tsx",
        ".mts",
        ".cts",
        ".vue"
      ],
      "markers": [
        "eslint.config.js",
        "eslint.config.mjs",
        "eslint.config.cjs",
        "eslint.config.ts",
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.cjs",
        ".eslintrc.json",
        ".eslintrc.yml",
        ".eslintrc.yaml"
      ],
      "package_key": "eslintConfig",
      "bin": "eslint",
      "node_bin": true,
      "argv": [
        "{bin}",
        "--format",
        "json",
        "--no-color",
        "{files}"
      ],
      "format": "eslint-json",
      "ok": [
        0,
        1
      ]
    },
    {
      "name": "prettier",
      "suffixes": [
        ".js",
        ".mjs",
        ".cjs",
        ".jsx",
        ".ts",
        ".tsx",
        ".mts",
        ".cts",
        ".vue",
        ".json",
        ".css",
        ".scss",
        ".less",
        ".md",
        ".yml",
        ".yaml",
        ".html",
        ".graphql"
      ],
      "markers": [
        ".prettierrc",
        ".prettierrc.js",
        ".prettierrc.cjs",
        ".prettierrc.mjs",
        ".prettierrc.json",
        ".prettierrc.yml",
        ".prettierrc.yaml",
        ".prettierrc.toml",
        "prettier.config.js",
        "prettier.config.cjs",
        "prettier.config.mjs"
      ],
      "package_key": "prettier",
      "bin": "prettier",
      "node_bin": true,
      "argv": [
        "{bin}",
        "--stdin-filepath",
        "{file}"
      ],
      "format": "stdin-diff",
      "ok": [
        0
      ],
      "fixable": true,
      "fix_hint": "prettier --write"
    },
    {
      "name": "tsc",
      "suffixes": [
        ".ts",
        ".tsx",
        ".mts",
        ".cts"
      ],
      "markers": [
        "tsconfig.json"
      ],
      "bin": "tsc",
      "node_bin": true,
      "argv": [
        "{bin}",
        "--noEmit",
        "--pretty",
        "false",
        "-p",
        "{marker}"
      ],
      "format": "lines",
      "ok": [
        0,
        1,
        2
      ],
      "scope": "project"
    },
    {
      "name": "mypy",
      "suffixes": [
        ".py",
        ".pyi"
      ],
      "markers": [
        "mypy.ini",
        ".mypy.ini"
      ],
      "pyproject_table": "tool.mypy",
      "bin": "mypy",
      "argv": [
        "{bin}",
        "--no-color-output",
        "--no-error-summary",
        "--show-column-numbers",
        "{files}"
      ],
      "format": "lines",
      "ok": [
        0,
        1
      ]
    },
    {
      "name": "black",
      "suffixes": [
        ".py",
        ".pyi"
      ],
      "markers": [],
      "pyproject_table": "tool.black",
      "bin": "black",
      "argv": [
        "{bin}",
        "--stdin-filename",
        "{file}",
        "-q",
        "-"
      ],
      "format": "stdin-diff",
      "ok": [
        0
      ],
      "fixable": true,
      "fix_hint": "black"
    },
    {
      "name": "markdownlint-cli2",
      "suffixes": [
        ".md"
      ],
      "markers": [
        ".markdownlint-cli2.jsonc",
        ".markdownlint-cli2.yaml",
        ".markdownlint-cli2.cjs",
        ".markdownlint-cli2.mjs",
        ".markdownlint.json",
        ".markdownlint.jsonc",
        ".markdownlint.yaml",
        ".markdownlint.yml"
      ],
      "bin": "markdownlint-cli2",
      "node_bin": true,
      "argv": [
        "{bin}",
        "{files}"
      ],
      "format": "lines",
      "ok": [
        0,
        1
      ]
    },
    {
      "name": "yamllint",
      "suffixes": [
        ".yml",
        ".yaml"
      ],
      "markers": [
        ".yamllint",
        ".yamllint.yml",
        ".yamllint.yaml"
      ],
      "bin": "yamllint",
      "argv": [
        "{bin}",
        "-f",
        "parsable",
        "{files}"
      ],
      "format": "lines",
      "ok": [
        0,
        1
      ]
    },
    {
      "name": "actionlint",
      "prefix": ".github/workflows/",
      "suffixes": [
        ".yml",
        ".yaml"
      ],
      "markers": [],
      "require_marker": false,
      "bin": "actionlint",
      "argv": [
        "{bin}",
        "-no-color",
        "{files}"
      ],
      "format": "lines",
      "ok": [
        0,
        1
      ]
    },
    {
      "name": "gofmt",
      "suffixes": [
        ".go"
      ],
      "markers": [
        "go.mod"
      ],
      "bin": "gofmt",
      "argv": [
        "{bin}"
      ],
      "format": "stdin-diff",
      "ok": [
        0
      ],
      "fixable": true,
      "fix_hint": "gofmt -w"
    },
    {
      "name": "clang-format",
      "suffixes": [
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".cxx",
        ".hpp",
        ".hh",
        ".hxx",
        ".m",
        ".mm"
      ],
      "markers": [
        ".clang-format",
        "_clang-format"
      ],
      "bin": "clang-format",
      "argv": [
        "{bin}",
        "--assume-filename={file}"
      ],
      "format": "stdin-diff",
      "ok": [
        0
      ],
      "fixable": true,
      "fix_hint": "clang-format -i"
    },
    {
      "name": "terraform fmt",
      "suffixes": [
        ".tf",
        ".tfvars"
      ],
      "markers": [],
      "require_marker": false,
      "bin": "terraform",
      "argv": [
        "{bin}",
        "fmt",
        "-"
      ],
      "format": "stdin-diff",
      "ok": [
        0
      ],
      "fixable": true,
      "fix_hint": "terraform fmt"
    },
    {
      "name": "ktlint",
      "suffixes": [
        ".kt",
        ".kts"
      ],
      "markers": [],
      "require_marker": false,
      "bin": "ktlint",
      "argv": [
        "{bin}",
        "{files}"
      ],
      "format": "lines",
      "ok": [
        0,
        1
      ]
    },
    {
      "name": "phpcs",
      "suffixes": [
        ".php"
      ],
      "markers": [
        "phpcs.xml",
        "phpcs.xml.dist",
        ".phpcs.xml",
        ".phpcs.xml.dist"
      ],
      "bin": "phpcs",
      "argv": [
        "{bin}",
        "--report=emacs",
        "--no-colors",
        "{files}"
      ],
      "format": "lines",
      "ok": [
        0,
        1,
        2,
        3
      ],
      "fix_hint": "phpcbf"
    },
    {
      "name": "rubocop",
      "suffixes": [
        ".rb"
      ],
      "markers": [
        ".rubocop.yml",
        ".rubocop_todo.yml"
      ],
      "bin": "rubocop",
      "argv": [
        "{bin}",
        "--format",
        "emacs",
        "--no-color",
        "{files}"
      ],
      "format": "lines",
      "ok": [
        0,
        1
      ],
      "fix_hint": "rubocop -a"
    }
  ],
  "project_scripts": [
    {
      "name": "npm run lint",
      "file": "package.json",
      "script": "lint",
      "bin": "npm",
      "argv": [
        "{bin}",
        "run",
        "--silent",
        "lint"
      ]
    },
    {
      "name": "make lint",
      "file": "Makefile",
      "target": "lint",
      "bin": "make",
      "argv": [
        "{bin}",
        "lint"
      ]
    }
  ]
}
```
