# Retained remote fixture

These generated definitions and local regression checks were copied byte-for-byte
from the reviewed authoring trial. Run `node scripts/verify.cjs` here; it performs
local simulation only and never calls a remote service. The parent experiment's
normal hermetic checks also execute this command.

`TESTING.md`, `REMOTE.md` and `PLATFORM.md` are historical authoring/preflight
records, not current remote status. Copied operator documentation redacts host
paths and makes the private fallback configuration explicit; executable source
and local regression files remain byte-identical. Their initial revision, input GUIDANCE and
private evidence paths refer to the original authoring repository; private traces
are not bundled. See the parent experiment's campaign report for the later actual
remote execution and cleanup results. The authored test sources, selectors and
local runners remain reusable without those private files.

To use the remote route again, discover the current installed deployment server
and runtime contract, verify authentication, and provision another disposable
project. Historical server paths are redacted as `<deployment-server-checkout>`; resolve
that placeholder from current installation evidence before using the procedure. Explicitly constrain any fallback web app to
`executeAs: USER_ACCESSING`, `access: MYSELF`; never reuse the trashed pilot target.
No remote service, model or credential is needed for the bundled local checks.
