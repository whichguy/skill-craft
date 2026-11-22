R-3 as the newest commit of the spec at or before N1 (2026-11-22T21:56:24Z) holds it, unverified (a plain note stores no digest):

### R-3 File staging and rollback
Basis: help-desk response-time request and [data-file decision](../decisions/0008-json-data-file.md). Backfill stored tickets before activating; use their stored creation and priority and keep existing deadlines. The operation is repeatable, preserves other records and uses atomic replacement. Activation on an incomplete persisted file fails before listening. Verify the original 1.4.0 reader can start on the migrated file and list every ticket, and that a saved pre-rollback file can restore established deadlines when returning from 1.4.0.
