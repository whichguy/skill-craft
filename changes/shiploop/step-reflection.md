---
bump: minor
---
Each step's document stage reflects on what the step showed (design T section 9.1, 2b-3, option C). There is no
separate knowledge stage.
- Document records in the knowledge home what the step showed:
  - a clarified requirement, or the files that now meet it, as a marked line in spec.md;
  - a decision implement did not record, as an `AD-<n>`;
  - a command, harness or platform fact, in environment.md.
- Its result gains a required `knowledge` record: `spec`, `architecture` and `environment`, each with what the step
  changed in that living file or why nothing did. The step commit prints it as a Knowledge home section. Document's
  packet now names the step and its spec mark (`<item>/<step>`), and lists all three living files.
- Document is an open-item stage. It records work found outside the item as an open item due at the item's
  carry-forward, and every step's open items stay listed until then.
- The spec write-back gate runs at document's complete and again when the step's review is imported, so the step
  commit holds a tree a gate ran on. The step review's focus covers the knowledge edits.
- The skill decision stays once per item, at carry-forward.
