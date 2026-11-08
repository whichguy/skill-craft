# Local board

This is an established, local-only 8×8 board interface. The warm green palette, system type, centered board, theme option, and 44rem content column follow AD-2 in `docs/shiploop/architecture.md`. Square selection and reset are local and covered by `node --test`; no network calls or runtime packages are used. The status currently precedes the board, while AD-2 calls for the selected-square summary directly below it.
