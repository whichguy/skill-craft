# Hello world specification

## Requirements

### R-1 Command output

Basis: November 22, 2026 request for hello.py to print exactly “Hello, world!” when run. This creates a new program on an empty baseline. The conventional single trailing newline is the November 22, 2026 default.

- From the repository root, run `python3 hello.py`. Expect stdout bytes `b'Hello, world!\n'`; missing or extra bytes fail the check. Observe the subprocess stdout and a successful exit. No arguments or persistent state are required.

### R-2 Output regression test

Basis: November 22, 2026 request for a unittest in test_hello.py. The empty baseline provides no test coverage.

- Run `python3 -B -m unittest -v` from the repository root. The suite discovers a test in test_hello.py that runs hello.py and compares its complete stdout against the R-1 value. A missing script or mismatched output fails the suite.

## Non-functional requirements

The program uses the installed Python standard library and emits one plain-text line. There is no graphical UI, storage, external service, or requested performance bound.

## Retired

None.
