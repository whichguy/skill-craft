# Ticket due-time specification

## Scope

The existing help-desk service and its local Node entry points. Deployment and activation remain operator actions.

## Requirements

### R-1 Assign the due time at creation

The service records the creation instant plus 4, 24, 72 or 168 hours for urgent, high, normal and low. Operators may override each window with the corresponding positive whole-hour DUE_HOURS_<PRIORITY> environment setting. API tests compare against a manual clock and restart with a changed setting. Priority edits and transitions leave existing due values fixed.

### R-2 Show and filter due times

With DUE_TIMES=on, all HTTP ticket representations include the due timestamp in UTC. GET /tickets?overdue=true restricts listings to open and in-progress tickets strictly past due and applies before pagination, alongside existing filters. CLI show and the human table may display due when enabled through the same flag. Raw CLI columns remain fixed. Tests cover the boundary, transitions, filters, pages and CLI.

### R-3 Backfill before serving and preserve disabled behavior

Before listening, fill missing due values using each record’s own creation time and persisted priority, then atomically save them when DATA_FILE is set. Preserve all present due values and the audit, outbox and ticket IDs. With DUE_TIMES unset or any value other than on, HTTP and CLI output keep their 1.4.0 shapes and overdue is ignored. Verify file contents and HTTP after restarts, including startup failure if the application cannot save the migration.

### R-4 Read the new file with release 1.4.0

The exact baseline service must start and list every ticket from version-1 candidate output. Verify with an isolated rollback drill. If 1.4.0 rewrites the file, operators can recover formerly assigned due values from the pre-rollback snapshot for matched ticket IDs.

### R-5 Keep existing entry points and regressions covered

Node standard library only. npm start honors PORT, existing node:test files are untouched, and npm test runs both old and new cases. Existing ticket operations, audit and outbox behavior continue.

## Retired

None.
