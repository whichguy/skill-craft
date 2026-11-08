# Architecture and decisions

## Decisions

### AD-1 — Existing local chat identity

#### Existing identity and unread-badge delta
The existing local chat identity is already visible in `styles.css`, even though the product had no earlier AD or design document. Preserve the current tokens `--chat-paper: #f4f0e8`, `--chat-ink: #292631`, `--chat-surface: #fffdfa`, `--chat-accent: #6750a4`, `--chat-accent-soft: #ece7f6`, and `--chat-border: #ddd7cf`. Keep the existing `.conversation-list`, `.conversation-item`, `.message-thread`, and `.composer` components. The only authorized delta is unread-count badges on the existing conversation items; a missing AD does not turn this product into a new interface.

#### Badge placement and current proportions
Use the existing `--chat-accent-soft` surface and `--chat-accent` text for the count marker. Keep the `--chat-radius: 1.25rem` shell shape and `--chat-gap: 0.75rem` spacing. Align each count within its existing conversation row without hiding the name or preview. On narrow layouts keep the selected conversation and message composer reachable.
