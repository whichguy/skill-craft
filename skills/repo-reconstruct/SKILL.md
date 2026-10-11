---
name: repo-reconstruct
description: >-
  Reverse-engineer an existing repository into evidence-backed spec.md,
  environment.md, and architecture.md files. Use to recover missing behavior
  specs, setup and verification instructions, or architecture choices from
  code, tests and documentation, including first-time ShipLoop initialization.
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
---

# repo-reconstruct

Recover what an existing repository does, how to build and verify it, and how it
is structured. This is retrospective documentation, not design from a prompt or
proof that existing behavior is desirable. Do not use for a new product's
requirements, a redesign, or an isolated code question without durable outputs.

## Inputs and destination

Accept a local repository path or repository URL, optional revision/scope, and
optional output directory. Resolve the exact target instead of assuming the
shell's working directory. A URL may be cloned into its own directory; record
the resolved commit and any shallow-history limit.

Use an explicitly requested output home. Otherwise discover existing maintained
homes first; link them and fill missing material instead of creating competing
specs. If none exists, use `docs/reconstruction/` under the target. Preserve
existing documents and IDs; update only the requested scope or write a clearly
named proposed addition. An external output directory is valid for evaluation
or read-only source access.

For explicit ShipLoop initialization, read
[references/shiploop.md](references/shiploop.md). Ordinary reconstruction does
not start ShipLoop, install tooling, or require it.

## Execute

Follow [prompts/main.prompt.md](prompts/main.prompt.md), using
[references/artifacts.md](references/artifacts.md) for the document roles.
Work in the current conversation with its available inspection tools; there is
no required model CLI, parser service, or agent runtime.

Finish with artifact links, inspected revision/scope, checks actually run, and
material unknowns. Say whether the result was self-checked or independently
reviewed. A partial reconstruction is useful when its gaps are explicit; do not
label it complete while a material surface is unaccounted for. Host evidence is
recorded in [references/host-matrix.md](references/host-matrix.md).
