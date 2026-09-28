---
name: repo-distill
description: >
  Distill a specification from an existing repository: what it does, its pinned
  public interface, numbered behaviour claims each citing evidence in the repo,
  its relationships and its unknowns. Use to understand a repository you
  reference, or to build a clean-room case: optionally port the repository's
  tests into an admitted black-box oracle, and pick candidate repositories by
  star rank through material-value gates. Invoke as /repo-distill <repo path>,
  "distill a spec from this repo", "what does this repo do and how does it
  relate", "initialize ShipLoop's spec for this repo", or "port these
  tests into a black-box oracle".
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
---

# /repo-distill

Turn a repository into a specification a person or a builder can use without
reading the source. The repository's **observed behaviour is the truth**; its
tests and docs are evidence, not authority.

## Invocation

```
/repo-distill <repo>                    # spec only (default)
/repo-distill <repo> --init             # initialize ShipLoop's knowledge home for an existing repo
/repo-distill <repo> --oracle           # also port its tests into a black-box oracle
/repo-distill --select                  # pick a candidate repository by stars and gates
```

`<repo>` is a local checkout (clone a GitHub repository first, pinned to a
commit). Scripts live in `scripts/` next to this file; run them with
`python3` (and `node` for the oracle).

## 1. Distill (always)

1. Choose the product name the spec will use. For plain understanding keep the
   real name; for a clean-room case pick a neutral name and never use the
   original name, owner or URL.
2. Run `prompts/distill.md` against the repository, substituting
   `{SPEC_PATH}` (where to write the spec, inside the repository, e.g.
   `.distill/spec.md`) and `{PRODUCT_NAME}`. The prompt states the intent, the
   required sections (purpose; runtime and launch contract; pinned public
   interface; claims `D-n` with `Evidence: path:line`; relationships;
   unknowns with default readings; left free) and a self-grade.
3. Check it: `python3 scripts/spec_check.py <spec> <repo> [--forbid <name>...]`.
   It passes only when every claim cites evidence, every citation resolves (to
   the repository or its dependencies), and no forbidden string appears in the
   **builder view**. Fix the spec, not the checker, unless the checker
   misreads a valid citation.
4. Hand a builder only the builder view (`spec_check.builder_view`): the same
   spec with every `Evidence:`/`Test:` citation removed. Citations are for
   verifying the distill; their file paths often carry the original name.

Report: claim count, unknowns, citation result, and anything the original
does that its tests or docs contradict.

## 1b. Initialize (with `--init`)

For a repository that has never run ShipLoop: run `prompts/initialize.md` in
the repository. It writes ShipLoop's **long-lived** baseline, which every later
run reads and merges its delivered changes into (a run's own changes live in
its `features/<slug>/spec.md` change spec). It writes only `docs/shiploop/` (index, `spec.md` with
requirements `R-n` marked `Status: observed` and anchored to `path:line`,
`architecture.md` with structure and decisions, `environment.md` with the
commands it actually ran, `test-strategy.md`). The README is a primary
source: its purposes, features, options and promises become requirements.
Grade the result with `/spec-judge <repo> docs/shiploop/spec.md --architecture docs/shiploop/architecture.md`
before relying on it.

## 2. Oracle (with `--oracle`)

1. Run `prompts/oracle-port.md` in the repository, substituting
   `{ORACLE_DIR}`, `{APP_CMD_ORIGINAL}` (the shell command that runs the
   original's command line or server) and `{APP_MODULE_ORIGINAL}` (the file a
   consumer gets when importing it, for a library). The oracle uses only the
   platform's built-in test runner and reaches the program only through
   `$APP_CMD` and `$APP_MODULE`.
2. Admit it:
   `python3 scripts/oracle_run.py <oracle> --admit --original "<cmd>" --original-module <file> --stub "node scripts/stub_server.mjs"`.
   Admitted means: every check passes on the original twice (no flakes), and
   fewer than half pass against the do-nothing stubs (`stub_server.mjs` for a
   command line or server, `stub_module.mjs` for a library). Checks that never
   report against the stub count as not passing.
3. Report the admission JSON and the oracle's `MAPPING.md` totals (mapped,
   not observable, excluded).

## 3. Select (with `--select`)

`python3 scripts/select_repos.py --out <dir>` walks the most-starred
JavaScript/TypeScript repositories in descending order and reports the first
that pass, cheapest gate first: maintained; a rebuildable interface (`bin`);
not a monorepo; no git submodules and no runtime dependency published from the
same owner's other repositories (an aggregation of repositories); has tests;
material own code (`scripts/repo_value.py`: 1,000 to 10,000 own lines). After
distilling, `repo_value.py <repo> --spec <spec>` also reports the share of the
spec's evidence citing dependency code (a high share means a thin layer over
other packages). The bars are starting proposals; state them when you report.

## Honesty

A spec claim without evidence is an unknown, not a claim. A check that passes
against the stub tests nothing. Say which gate a repository failed and why;
never widen a gate to admit a favourite.
