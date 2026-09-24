# Change notes

Every change to a skill adds one note here instead of editing its version:

```text
changes/<leaf>/<short-slug>.md
```

```markdown
---
bump: patch
---
One or more lines telling people who install the skill what changed.
```

`bump` is `patch`, `minor` or `major`. To set an exact version instead, write
`version: 1.2.3`. A prerelease such as `0.3.0-rc.1` stays on its line for a
patch bump (`0.3.0-rc.2`).

Two branches never edit the same note, so notes do not conflict.
`scripts/release.py` turns pending notes into one release commit: it bumps
versions, writes `CHANGELOG.md`, deletes the notes, and regenerates
`plugins/`, the host catalogs and the README inventory. CI
(`scripts/check-release-boundary.py`) rejects ordinary commits that edit
versions or release output, and skill changes without a note. A change nobody
needs to receive as an update (for example a typo fix) can instead carry a
`No-Change-Note: <reason>` commit trailer. Git reads trailers only from the
last paragraph of a message, so keep it in the same final block as any
`Co-Authored-By:` line, with no blank line between them.
