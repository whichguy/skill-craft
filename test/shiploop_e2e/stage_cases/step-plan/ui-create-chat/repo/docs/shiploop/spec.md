# Product specification

## Existing behavior
The local chat shows two seeded conversations. Selecting a conversation displays its messages. Sending non-empty text appends a message to the active conversation. These local interactions are covered by `node --test`.

## Appearance
No appearance requirement or accepted visual identity has been recorded. The current page is a plain starter.

## Requirements
- R-1: Give the local chat its first clear, responsive visual direction, with readable conversation choices, active conversation and message composer. Record a rendered browser check at narrow and wide widths in light and dark themes.
- R-2: Preserve local conversation selection and message display and sending; retain the existing node:test suite. Do not add a dependency or external service.

## Request (verbatim)

> This repository contains a local chat demo with a plain starter screen, two seeded conversations, conversation switching, message display, and a local send action. R-1: Give it its first designed interface so the conversation list, active thread, and composer are clear, responsive, keyboard-usable, and easy to read. Choose a visual direction from product context; no brand or palette is prescribed. Plan a rendered browser check at narrow and wide widths in light and dark themes. R-2: Preserve local conversation selection and message behavior, including appending non-empty messages and ignoring empty text, and retain the existing node:test suite. Stay local, with no dependency or external service.
