# Product specification

## Existing behavior
The page opens to a seeded local conversation list. Selecting a conversation updates the active heading and its local message thread. Submitting text adds a message to that active thread. The composer is local; it does not call a messaging service. The built-in Node test suite covers seeded state, selection and local message addition.

## Appearance record
No UI architecture or design decision has been written yet. The current product interface is defined by its existing `index.html` and `styles.css`.

## User request (verbatim)
> Add unread-count badges to each conversation in the seeded local chat list. Selecting a conversation clears its unread count; retain the existing local conversation/message behavior. No network or package dependencies.

## Requirements
- **R-1 — new feature:** Show an unread-count badge for each seeded conversation and clear that conversation's unread count when it is selected.
- **R-2 — existing behavior:** Preserve the current local conversation selection, active message thread, and compose-and-append behavior. Keep the existing interface identity; the request adds unread counts without a broader redesign.
