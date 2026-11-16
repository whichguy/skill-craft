---
bump: patch
---
In a run with no Backchain child (the default `--backchain-passes none`), the spec, plan and delegated step-plan and carry-forward packets now say what the printed `backchain-check` reads: only a candidate graph in Backchain's plan schema, a JSON file, never a spec, a Markdown note or a prose plan. They tell the host to run it after each revision of a graph it wrote, and not to write a graph only to run it. In the 2026-11-15 default run the host had run the check on the spec Markdown, was refused as not JSON, then wrote one graph and re-ran it at four stages to have a receipt at each. The `one` and `converge` packets are unchanged.
