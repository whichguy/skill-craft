---
description: >-
  DevLoop slash for Grok. Follow skill devloop: interpolate argv from
  plain English, print it, then exec the shim. Do not implement the loop.
disable-model-invocation: true
---

# /devloop

This slash is **DevLoop**. The rest of the line is the goal in plain English.

Follow skill `devloop` (read its `SKILL.md`). Parse the skill argument
(flags-free). Interpolate `--repo` / `--lang` / `verify_cmd exactly [...]`
from the plain text per that card's table, **print the interpolated argv**,
`mcp-considered`, and `env-discovered` (or `env-discovered: none(...)`),
then exec its shim with that argv **in the foreground** (do not background
the shim). Fail-closed (stop and ask) when there is no machine-checkable
done — do not invent `pytest`, a path, or a cwd. On `HUMAN_REVIEW` /
`NEEDS YOUR INPUT` / exit 2, **prompt the user** with the engine reason
and `— ANSWERS:` — do not only post a postmortem.

Do not invent DEFINE/PROVE/BUILD or write product files — interpolating argv
is not BUILD. Do not add a fourth argv piece beyond `--repo`/`--lang`/
`verify_cmd`. Do not invoke Grok `/goal` or `/loop` **in-loop**. After
COMPLETE, residual is `/review-coverage` under `/goal`. Do not use
`evidence-gates` as DevLoop.
