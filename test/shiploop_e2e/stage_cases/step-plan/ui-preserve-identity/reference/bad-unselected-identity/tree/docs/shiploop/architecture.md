# Architecture and decisions

## Decisions

### AD-1 — Existing local chat identity

#### Existing identity and unread-badge delta
The existing local chat identity is already visible in `styles.css`, even though no prior AD exists. Preserve `--chat-paper: #f4f0e8`, `--chat-accent: #6750a4`, `--chat-accent-soft: #ece7f6`, and `--chat-border: #ddd7cf`. Keep `.conversation-list`, `.conversation-item`, `.message-thread`, and `.composer`. The only authorized delta is unread-count badges on the current conversation items.

#### Badge placement and proportions
Use `--chat-accent-soft` for the badge surface and `--chat-accent` for its text. Retain the `--chat-radius: 1.25rem` shell and `--chat-gap: 0.75rem` spacing.
