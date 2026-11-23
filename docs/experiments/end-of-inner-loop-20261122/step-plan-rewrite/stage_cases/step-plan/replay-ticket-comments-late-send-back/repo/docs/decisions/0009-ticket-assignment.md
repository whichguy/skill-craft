# 9. Ticket assignment

Date: 2026-10-29
Status: Accepted

## Context

Agents need ownership of active tickets and notification when assigned. Existing version 1 data files and the raw CLI
consumer must remain usable.

## Decision

We store a nullable assignee with each ticket, treating the missing field in older files as null. Active tickets may
change assignment through the store, which records audit and enqueues a notification for every actual assignment.
The event key includes the audit sequence so pending notifications do not suppress later assignments. List filters
intersect and the raw CLI appends the assignee after the existing columns.

## Consequences

The existing outbox worker delivers and retries agent notifications. Old files remain readable and acquire the field
when saved. Consumers of raw CLI output must tolerate the fifth column; the existing first four positions stay fixed.
