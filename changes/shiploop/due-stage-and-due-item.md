---
bump: patch
---
- **Due stage and due item:** an open item's `consumer` is now `due_stage` (the later stage it is due at), matching
  `unverified[].due_stage`. On the plan's open assumptions, which name a work item, it is `due_item`. The duties,
  templates, refusals ("Fix the due stages", "names due_item"), renderers ("due:"), the report's Due column and
  planning-experiments.md say so. "Consumer" now means only the person or system that uses what the run delivers
  (`consumer_checks`, `consumer_entry`, a delivery contract), as the glossary records; the old open-item wording is
  retired.
