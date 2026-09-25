# Changelog

Written by scripts/release.py.

## 2026-09-24

### review-coverage 0.3.1

- The host matrix installs from whichguy/skill-craft, explains moving an old Claude registration without uninstalling plugins, and replaces the plugin sync step with a change note.

### shiploop 0.24.2

- The README and navigator reference say a ShipLoop source edit adds a changes/shiploop note and checks a fresh package build; plugins/ and catalogs are release output that ordinary work items never regenerate or commit.

### shiploop-e2e-audit 0.4.2

- The freshness gate reads the released plugins/<leaf> and its entry in skill-craft's own marketplace catalog on the same main, instead of the retired skill-craft-market repository; a pending change note stops the gate until release.

### skill-interop 0.2.4

- Skill Interop now names skill-craft itself as the marketplace, with release-output catalogs and commit-pinned external plugins, and its checklist asks for a change note instead of a plugin view sync.
