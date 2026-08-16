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
from the plain text per that card's table, **print the interpolated argv**
and `mcp-considered`, then exec its shim with that argv. Fail-closed
(stop and ask) when there is no machine-checkable done — do not invent
`pytest`, a path, or a cwd.

Do not invent DEFINE/PROVE/BUILD or write product files — interpolating argv
is not BUILD. Do not add a fourth argv piece beyond `--repo`/`--lang`/
`verify_cmd`. Do not invoke Grok `/goal` or `/loop`. Do not use
`devloop-native` as DevLoop.
