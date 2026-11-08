# Architecture and decisions

## Decisions

### AD-4 — Inherited chat interface

#### Existing chat identity and count marker
The current product styling is the established identity despite the absence of an earlier architecture decision. Preserve `--chat-paper: #f4f0e8`, `--chat-surface: #fffdfa`, `--chat-accent: #6750a4`, `--chat-accent-soft: #ece7f6`, and the existing `.conversation-item`, `.message-thread`, `.composer` components. The only authorized change is an unread-count marker on each current conversation row.

#### Marker spacing and contrast
Retain the existing `--chat-gap: 0.75rem` and `--chat-radius: 1.25rem`. Use the existing soft accent surface and accent text for a small readable marker; keep the name and message preview visible at narrow and wide sizes.
