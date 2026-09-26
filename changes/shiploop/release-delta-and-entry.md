---
bump: minor
---
A done `release-plan` now records `consumer_entry` (how a person reaches the result, and the repository files that create it), and ShipLoop refuses a release plan without one or whose files are missing. A Salesforce `lightning__Tab` target alone therefore no longer passes as a navigation entry. `release-check` runs the dry-run deploy and each post-release confirm command once, before the real deploy, so a confirm that cannot tell present from absent is fixed first. The Salesforce guide says to confirm tabs with `sf org list metadata --metadata-type CustomTab`. After a replan whose corrective items changed only non-code paths, each outer stage's packet names the delta and the result it accepted before the replan, so unchanged rows are cited rather than redone.
