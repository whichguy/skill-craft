# Help desk ticket service specification

## Requirements

### R-1. Assign permanent due dates

Basis: November 2026 help-desk request for configurable response times set once per ticket. Each new ticket gets a UTC ISO 8601 `due` equal to its creation time plus its priority's whole hours, including internal writes before API activation. Defaults are urgent 4, high 24, normal 72, and low 168. A new process can apply environment overrides to future assignments. Existing values survive priority updates, transitions, restarts and changes in hours. The HTTP and disk tests compare due values against fixed clocks and check changed configuration against historical and new tickets. Creation and patch bodies retain existing field validation, so callers cannot set due.

### R-2. Display and filter when activated

Basis: November 2026 requirement for `due`, `GET /tickets?overdue=true`, and baseline responses before activation. Only exact `DUE_TIMES=on` enables the API field and filter. All routes that return a ticket, including write responses and list items, show due. The exact `overdue=true` filter selects only `open` and `in_progress` tickets with due strictly before the request's clock time, using existing filters and pagination. Other values do not select overdue tickets specially. HTTP assertions check past, exact, future, resolved and closed cases, cursor paging and flag-off equality of ticket shapes and ignored query behavior.

### R-3. Prepare production data before activation

Basis: November 2026 requirement for stored creation-based deadlines on existing tickets before feature activation. An operator prepares the existing file with its writer stopped. Missing values are assigned from each record's creation time and stored priority. All existing due values, ticket fields, audit records, sequence numbers and outbox records survive. Repeating the command with changed hours leaves assigned dates unchanged. A populated file with missing values blocks enabled startup until preparation succeeds. An in-memory or empty store is ready immediately. Tests observe the file before the enabled service opens it and verify the unchanged file on retry or invalid input.

### R-4. Preserve 1.4.0 rollback

Basis: November 2026 fallback request and decision 8. Exact 1.4.0 must start on the candidate's file and list every ticket, including tickets created after rollout. The current service still owns the live file during normal startup. During a downgrade operators capture a consistent copy after stopping the new version, then run 1.4.0 against the live file. The copy supplies original dates by id and creation time on re-upgrade after legacy writes. Recovery keeps ticket changes and new records written by the legacy release. Candidate integration tests exercise restore and a local rehearsal runs the actual 1.4.0 startup against a candidate-written file.

### R-5. Keep other service behavior

Basis: November 2026 requirement to preserve the existing service and suite, README, API, operations and decisions 5, 7 and 8. Preserve dependency-free Node 22+, PORT, standard API envelopes, audit and notifications, raw CLI columns, reporting and cursor behavior. Tests under test/ use node:test and run in the unchanged npm test command. The source checkout is the delivery target. The operator performs production preparation and activation using the documented commands.

## Non-functional requirements

Compatibility is verified at the actual HTTP, CLI and legacy file boundaries. Durability uses the existing single-writer rule and same-directory atomic replacement. Verify unaffected state and repeatable preparation against real temporary files. Capture only synthetic data in tests. Existing data visibility, log sinks and worker ownership are unchanged. This change adds no graphical surface or external service, so there is no new UI or network dependency. No new throughput target is specified.

## Retired

None.
