# 1. Record decisions

Date: 2025-01-13
Status: Accepted

## Context

The service is small, but its team changes: two of the people who wrote the first version have moved to other teams, and
questions like "why do ids look like this?" were answered from memory, or not at all.

## Decision

We will record each decision that shapes the code in `docs/decisions/`, one numbered Markdown file per decision, in the
shape of [template.md](template.md): context, decision, consequences, with a date and a status.

A record is not edited once accepted, apart from its status. When a decision no longer holds, a new record supersedes it,
and the old one's status says which record replaced it.

## Consequences

- A pull request that changes a recorded decision adds a record that supersedes it.
- Reviewers can ask "which record covers this?" and expect an answer.
- The index in `docs/decisions/README.md` lists every record and its status.
