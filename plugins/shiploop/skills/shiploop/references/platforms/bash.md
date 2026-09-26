# Bash script development

Use the [guidance selector](../coding-guidance.md#select-guidance) when runtime
or boundary changes. Declare and verify shell/version and external-command
assumptions. Preserve argument boundaries with quoted
expansions and arrays where the dialect supports them; avoid string-built
commands, `eval`, and parsing human-formatted output. Test spaces, globs, empty
arguments, newlines, and leading-option values when relevant. Do not assume GNU
options or current Bash on every host.

Handle expected failure explicitly, including pipeline components and functions
called as conditions. `set -e` has contextual exceptions; `set -euo pipefail`
is useful but does not prove every error stops execution or every nonzero status
is an error. Consult the target [Bash manual](https://www.gnu.org/software/bash/manual/)
for the actual semantics. Preserve the meaningful status through cleanup, send
diagnostics to stderr, and keep machine-readable stdout usable.

Use isolated temporary directories and scoped traps for resources the script
owns. Verify cleanup after controlled failures and required signals; no trap
guarantees cleanup after every termination. Run the current static checker and
actual shell tests, including negative controls. Keep orchestration small;
consider an existing Python path when parsing, state, or recovery complexity
outgrows shell's simplicity.

A sourced file's functions and non-`local` variables join the caller's shell and
can replace its names or those of other sourced files. Give library functions a
shared prefix, declare function variables `local`, and export only the
environment variables a child process needs.
