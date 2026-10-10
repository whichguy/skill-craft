Commit-message shapes for the lessons grammar (`skills/shiploop/scripts/shiploop_lessons.py`).

Each `*.md` file is one commit message, modelled on a shape found in the saved E2E runs (the Improve card's
`Key learnings:` line, release-verify's bare `Learned` section, a label on its own line with the text after a
blank line, a one-paragraph message) or on a shape the grammar must refuse (a heading that holds only the
`Co-Authored-By:` trailer). `expected.json` maps each file to the lessons text and the `Remote change` text the
parser must return (`""` when it must find none). `one-paragraph.md` expects no lessons on purpose: the
one-paragraph form is not read, and the refusal names the forms that are.
