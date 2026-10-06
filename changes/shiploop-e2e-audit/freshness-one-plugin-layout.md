---
bump: patch
---
The publication/freshness preflight now reads skill-craft's one-plugin layout: the released ShipLoop and Improve are the copies under `plugins/skill-craft/skills/<leaf>`, the catalog has one `skill-craft` entry whose version is the bundle's, and each skill keeps its own version. Before this, every live case was refused at the preflight with `required-package-tree-is-missing`, because the gate looked for a `plugins/<leaf>` per skill that the repository no longer publishes. A repository or catalog in the old per-skill layout is refused, not read.
