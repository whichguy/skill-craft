import json, sys

REQ = json.load(open('/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/claude-csv-report.requirements.json'))['requirements']
rows = []

def C(cid, quote, observable, kind, cand=True, reason=""):
    req = cid.split('.')[0]
    row = {"id": cid, "requirement": req, "quote": quote, "observable": observable, "kind": kind, "candidate": cand}
    if not cand:
        row["exclude_reason"] = reason
    rows.append(row)

# ---------------- R-1
C("R-1.1", "runs on Python 3 using only the standard library",
  "No third-party import is needed to run report.py.", "structural", False,
  "An import restriction; no output, exit status or file effect of the program distinguishes it from outside.")
C("R-1.2", "one or more FILE args are all processed and aggregated into a single JSON object",
  "Running with two valid files prints one JSON object whose rows is the sum of both files' valid rows.", "behaviour")
C("R-1.3", "a repeated FILE is simply read twice",
  "Passing the same valid file twice doubles rows, revenue and by_product.", "boundary")
C("R-1.4", "stderr starts with `usage:`",
  "With no FILE args stderr starts with 'usage:'.", "error")
C("R-1.5", "no args -> stderr starts with `usage:`, stdout empty, exit 1",
  "With no FILE args stdout is empty.", "error")
C("R-1.6", "no args -> stderr starts with `usage:`, stdout empty, exit 1",
  "With no FILE args the exit status is 1.", "error")

# ---------------- R-2
C("R-2.1", "Header (line 1) is skipped",
  "A file whose first line is the header yields no row for line 1: a header-only file gives rows 0 and exit 0; the header is not counted.", "behaviour")
C("R-2.2", "Header (line 1) is skipped unvalidated.",
  "A malformed header (for example only two columns, or non-header text) produces no skip line and exit 0.", "behaviour")
C("R-2.3", "`2024-01-01,north,widget,3,2.50` is valid",
  "A file with that row counts rows 1, revenue 7.5, no stderr, exit 0.", "behaviour")
C("R-2.4", "`2024-01-01,north,widget,3` -> `expected 5 columns, got 4`",
  "A 4-column row gives stderr line ending 'expected 5 columns, got 4'.", "error")
C("R-2.5", "a 6-column row -> `expected 5 columns, got 6`",
  "A 6-column row gives stderr line ending 'expected 5 columns, got 6'.", "error")
C("R-2.6", "a blank line -> `expected 5 columns, got 0`",
  "A blank line in the data gives stderr line ending 'expected 5 columns, got 0'.", "error")
UN = "units `abc`, `1.5`, `1_0`, `1e3`, empty -> `non-numeric units 'X'`"
C("R-2.7", UN, "units 'abc' gives \"non-numeric units 'abc'\".", "error")
C("R-2.8", UN, "units '1.5' gives \"non-numeric units '1.5'\".", "error")
C("R-2.9", UN, "units '1_0' gives \"non-numeric units '1_0'\".", "error")
C("R-2.10", UN, "units '1e3' gives \"non-numeric units '1e3'\".", "error")
C("R-2.11", UN, "units '' (empty) gives \"non-numeric units ''\".", "error")
C("R-2.12", "units `-1` -> `negative units '-1'`",
  "units '-1' gives \"negative units '-1'\".", "error")
PR = "unit_price `abc`, `nan`, `inf`, `1e3`, empty -> `non-numeric unit_price 'X'`"
C("R-2.13", PR, "unit_price 'abc' gives \"non-numeric unit_price 'abc'\".", "error")
C("R-2.14", PR, "unit_price 'nan' gives \"non-numeric unit_price 'nan'\".", "error")
C("R-2.15", PR, "unit_price 'inf' gives \"non-numeric unit_price 'inf'\".", "error")
C("R-2.16", PR, "unit_price '1e3' gives \"non-numeric unit_price '1e3'\".", "error")
C("R-2.17", PR, "unit_price '' (empty) gives \"non-numeric unit_price ''\".", "error")
C("R-2.18", "unit_price `-0.5` -> `negative unit_price '-0.5'`",
  "unit_price '-0.5' gives \"negative unit_price '-0.5'\".", "error")
C("R-2.19", "units is checked before unit_price",
  "A row with units 'abc' and unit_price 'xyz' reports the units reason, not the unit_price reason.", "error")
C("R-2.20", "X = the stripped field",
  "A row with units ' abc ' (padded) reports \"non-numeric units 'abc'\" with the quote content stripped.", "format")
C("R-2.21", "fields are stripped of surrounding whitespace first",
  "units ' 7 ' (padded) is valid: counted, no stderr, by_product counts 7.", "boundary")
C("R-2.22", "fields are stripped of surrounding whitespace first",
  "unit_price ' 2.50 ' (padded) is valid: counted, revenue uses 2.50, no stderr.", "boundary")
C("R-2.23", "date, region, product are not validated",
  "A row with a garbage date (for example 'not-a-date') is valid and counted.", "behaviour")
C("R-2.24", "date, region, product are not validated",
  "A row with an empty region is valid and counted; by_region has the key ''.", "behaviour")
C("R-2.25", "date, region, product are not validated",
  "A row with an empty product is valid and counted; by_product has the key ''.", "behaviour")
VAL = "units `0`, price `0`, `.5`, `5.`, ` 7 ` (padded) are valid"
C("R-2.26", VAL, "units '0' is valid: counted, no stderr.", "boundary")
C("R-2.27", VAL, "unit_price '0' is valid: counted, no stderr.", "boundary")
C("R-2.28", VAL, "unit_price '.5' is valid: counted, revenue 0.5 for one unit.", "boundary")
C("R-2.29", VAL, "unit_price '5.' is valid: counted, revenue 5.0 for one unit.", "boundary")
C("R-2.30", "`-0` is rejected as negative",
  "units '-0' gives \"negative units '-0'\".", "boundary")
C("R-2.31", "`-0` is rejected as negative",
  "unit_price '-0' gives \"negative unit_price '-0'\".", "boundary")
C("R-2.32", "a leading `-` on an otherwise numeric field is \"negative\"",
  "unit_price '-.5' (leading minus on a dot-form number) gives \"negative unit_price '-.5'\", not non-numeric.", "boundary")
C("R-2.33", "a units field with more digits than Python's int conversion limit (5000 nines) is skipped with reason `units too large 'X'` instead of crashing",
  "A units field of 5000 nines gives a skip line with reason \"units too large '999...9'\", no traceback, and the other rows are still counted.", "boundary")
C("R-2.34", "a file with CRLF line endings",
  "A CRLF file with the header and '2024-01-01,north,widget,3,2.50' yields rows 1, revenue 7.5, empty stderr, exit 0.", "boundary")
C("R-2.35", "a file starting with a UTF-8 BOM",
  "A file starting with the UTF-8 BOM bytes and the header plus '2024-01-01,north,widget,3,2.50' yields rows 1, revenue 7.5, empty stderr, exit 0.", "boundary")

# ---------------- R-3
C("R-3.1", "Exactly one JSON object on a single stdout line",
  "Stdout holds exactly one line (no pretty-printing, one object even for several files).", "format")
C("R-3.2", "(plus trailing newline)",
  "Stdout ends with a newline character.", "format")
C("R-3.3", "top-level keys appear in the order `rows`, `revenue`, `by_region`, `by_product`",
  "The key order of the printed object is rows, revenue, by_region, by_product.", "format")
C("R-3.4", "rows = valid rows",
  "rows equals the number of valid rows (a skipped row is not counted).", "behaviour")
C("R-3.5", "revenue = sum of units*unit_price over valid rows",
  "Rows (2, 1.50) and (3, 0.25) give revenue 3.75 (units times price, summed over rows).", "behaviour")
C("R-3.6", "summed as Decimal",
  "Exact decimal sum: revenue is computed on exact decimals (a value like 1.005 rounds to 1.01, not 1.0).", "behaviour")
C("R-3.7", "rounded to 2 decimals half-up",
  "revenue is rounded to exactly 2 decimals (1.234 gives 1.23).", "behaviour")
C("R-3.8", "rounded to 2 decimals half-up",
  "revenue rounds half up (1.005 gives 1.01, 2.665 gives 2.67, not the banker's 1.0/2.66).", "boundary")
C("R-3.9", "give revenue 0.01 (rounded from the exact sum 0.008)",
  "Two regions with 0.004 each: revenue is 0.01 (rounded once from the exact sum), not the sum of rounded parts 0.0.", "boundary")
C("R-3.10", "by_region = per-region revenue rounded to 2 decimals",
  "by_region values are rounded to 2 decimals (0.004 per region gives 0.0).", "behaviour")
C("R-3.11", "by_region north 2.68 (half-up, not float 2.67)",
  "A single region value 2.675 gives by_region north 2.68.", "boundary")
C("R-3.12", "by_region = per-region revenue rounded to 2 decimals",
  "Rows are grouped by the region column: revenue of rows in the same region is summed under that region's key.", "behaviour")
C("R-3.13", "by_product = per-product total units (integers)",
  "Rows are grouped by the product column and units are summed per product.", "behaviour")
C("R-3.14", "by_product = per-product total units (integers)",
  "by_product values print as JSON integers (4 not 4.0).", "format")
C("R-3.15", "the keys inside by_region and by_product are sorted",
  "by_region keys appear in sorted order whatever order the rows come in.", "format")
C("R-3.16", "the keys inside by_region and by_product are sorted",
  "by_product keys appear in sorted order whatever order the rows come in.", "format")
EX = 'prints exactly `{"rows": 2, "revenue": 7.6, "by_region": {"north": 7.5, "south": 0.1}, "by_product": {"widget": 4}}`'
C("R-3.17", EX, "The stdout text uses ', ' between items and ': ' between key and value (default JSON separators).", "format")
C("R-3.18", EX, "Numbers print without trailing zeros: 7.6 and 7.5, not 7.60 or 7.50.", "format")

# ---------------- R-4
C("R-4.1", "Each skipped row writes one stderr line `FILE:LINE: <reason>`",
  "The stderr line has the form PATH:LINE: REASON (colon, no space before the line number, one space before the reason).", "format")
C("R-4.2", "Each skipped row writes one stderr line",
  "Two bad rows give two stderr lines, one for each.", "behaviour")
C("R-4.3", "FILE as given on the command line",
  "The path in the stderr line is exactly the argument as typed (for example a relative path stays relative).", "format")
C("R-4.4", "header is line 1",
  "The first data row is line 2, so a bad first data row is reported as ':2:'.", "boundary")
C("R-4.5", "a quoted field containing a newline on line 2 followed by a bad record starting on line 4 reports `:4:`",
  "A multi-line quoted field on line 2 followed by a bad record starting on line 4 reports ':4:'.", "boundary")
C("R-4.6", "valid rows are still counted",
  "With one bad row among valid ones, rows counts the valid ones.", "behaviour")
C("R-4.7", "the JSON is still printed",
  "With a bad row, stdout still holds the JSON summary.", "behaviour")
C("R-4.8", "exit 2 if any row was skipped in any file",
  "A bad row in a single file gives exit 2.", "error")
C("R-4.9", "exit 2 if any row was skipped in any file",
  "A bad row in the first of two files (second file all valid) gives exit 2.", "error")
C("R-4.10", "all-valid input -> exit 0",
  "All-valid input gives exit 0.", "behaviour")
C("R-4.11", "all-valid input -> exit 0, empty stderr",
  "All-valid input gives empty stderr.", "behaviour")
C("R-4.12", "second file's lines are numbered independently of the first",
  "A bad row on line 3 of the second file is reported as ':3:' whatever the first file's length.", "boundary")
C("R-4.13", "bad row on the last line without a trailing newline is reported with its line number",
  "A bad final line with no trailing newline is still reported with its line number.", "boundary")
C("R-4.14", "stderr exactly `path:3: expected 5 columns, got 4`",
  "Stderr holds exactly the skip lines and nothing else.", "format")

# ---------------- R-5
MSG = "prints `report.py: error: cannot read FILE: <reason>` on stderr"
C("R-5.1", "A FILE that is missing, a directory, unreadable, or not decodable as UTF-8 " + MSG,
  "A missing path gives stderr starting 'report.py: error: cannot read <path>:'.", "error")
C("R-5.2", "A FILE that is missing, a directory, unreadable, or not decodable as UTF-8 " + MSG,
  "A directory path gives stderr starting 'report.py: error: cannot read <path>:'.", "error")
C("R-5.3", "A FILE that is missing, a directory, unreadable, or not decodable as UTF-8 " + MSG,
  "A file without read permission gives stderr starting 'report.py: error: cannot read <path>:'.", "error")
C("R-5.4", "A FILE that is missing, a directory, unreadable, or not decodable as UTF-8 " + MSG,
  "A file with invalid UTF-8 bytes gives stderr starting 'report.py: error: cannot read <path>:'.", "error")
C("R-5.5", "invalid UTF-8 after a valid row: still no stdout",
  "A file with a valid row followed by invalid UTF-8 prints nothing on stdout.", "error")
C("R-5.6", "(no traceback)",
  "A missing file gives no 'Traceback' on stderr.", "error")
C("R-5.7", "(no traceback), nothing on stdout, exit 1",
  "A missing file gives empty stdout.", "error")
C("R-5.8", "(no traceback), nothing on stdout, exit 1",
  "A missing file gives exit status 1.", "error")
C("R-5.9", "this wins over exit 2",
  "A bad row in file A plus a missing file B gives exit 1, not 2.", "error")
C("R-5.10", "applies even when other files were fine",
  "A good file first and a missing file second gives empty stdout and exit 1.", "error")
C("R-5.11", "a field longer than the csv field limit (csv.Error) is also an unreadable file, same output rules",
  "A 200000-character field gives 'report.py: error: cannot read <path>:', no Traceback, empty stdout, exit 1.", "error")
C("R-5.12", "a revenue total beyond about 1e197 prints `report.py: error: totals too large to summarise (beyond about 1e197)` on stderr",
  "A revenue beyond 1e197 gives the stderr line 'report.py: error: totals too large to summarise (beyond about 1e197)'.", "boundary")
C("R-5.13", "a revenue total beyond about 1e197 prints `report.py: error: totals too large to summarise (beyond about 1e197)` on stderr, nothing on stdout, exit 1",
  "A revenue beyond 1e197 gives empty stdout and exit status 1 (no traceback).", "boundary")

# ---------------- R-6
C("R-6.1", "header-only file alone -> `{\"rows\": 0, \"revenue\": 0.0, \"by_region\": {}, \"by_product\": {}}`",
  "A header-only file prints exactly {\"rows\": 0, \"revenue\": 0.0, \"by_region\": {}, \"by_product\": {}}.", "behaviour")
C("R-6.2", "header-only file alone -> `{\"rows\": 0, \"revenue\": 0.0, \"by_region\": {}, \"by_product\": {}}`, exit 0",
  "A header-only file gives exit 0.", "behaviour")
C("R-6.3", "A file with only the header (or zero bytes) contributes no rows, no stderr and no revenue",
  "A header-only file gives empty stderr.", "behaviour")
C("R-6.4", "A file with only the header (or zero bytes) contributes no rows, no stderr and no revenue",
  "A zero-byte file alone prints the same zero summary, empty stderr, exit 0.", "boundary")
C("R-6.5", "header-only file combined with a normal file leaves the normal file's totals unchanged",
  "A header-only file plus a normal file gives the normal file's totals and exit 0.", "boundary")
C("R-6.6", "zero-byte file behaves the same",
  "A zero-byte file plus a normal file gives the normal file's totals, empty stderr and exit 0.", "boundary")

# ---------------- R-7
C("R-7.1", "Tests live in `tests/` (package, `test_*.py`) and run from the repo root with `python3 -m unittest`",
  "A tests/ package with test_*.py files that unittest discovers from the repo root.", "tests-themselves", False,
  "Concerns the test suite itself, not product behaviour; there is no product code to mutate.")
C("R-7.2", "exit 0, standard library only, covering R-1..R-6",
  "The suite exits 0 and uses only stdlib.", "tests-themselves", False,
  "Concerns the test suite itself.")
C("R-7.3", "runs >= 1 test per requirement",
  "The suite runs at least one test per requirement.", "tests-themselves", False,
  "Concerns the test suite itself.")
C("R-7.4", "a deliberately broken revenue rounding makes a test fail",
  "A recorded mutation run.", "tests-themselves", False,
  "A test-stage activity; this experiment's kill measure covers it for revenue rounding (R-3.7, R-3.8).")
C("R-7.5", "tests use tempfile directories and leave nothing behind",
  "No leftover files after the suite.", "tests-themselves", False,
  "Concerns the test suite itself.")
C("R-7.6", "a `.gitignore` containing `__pycache__/` is committed so `git status --porcelain` is empty after the run",
  ".gitignore holds __pycache__/.", "structural", False,
  "A repository file, not product behaviour; no product code to mutate.")

# verify quotes verbatim
bad = 0
for r in rows:
    if r["quote"] not in REQ[r["requirement"]]:
        print("QUOTE NOT VERBATIM:", r["id"], repr(r["quote"]))
        bad += 1
ids = [r["id"] for r in rows]
assert len(ids) == len(set(ids))
print(len(rows), "rows;", sum(r["candidate"] for r in rows), "candidates; bad quotes:", bad)
if bad:
    sys.exit(1)
json.dump(rows, open('/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/claude-csv-report/conditions.json', 'w'), indent=1)
