#!/usr/bin/env python3
"""The question bank of QB1 (README.md): the clauses of intake item 9's K1-K11 catalog, one item each, in matched forms.

The catalog (``CATALOG`` in ../key-questions-intake-20261030/build.py, shipped as intake duty item 9) names eleven
categories, each a run of clauses ("who uses the result, through which entry point, and what observation shows it
works?").  ``BANK`` splits those clauses into 20 items and words each twice, as a question and as a statement, so a
difference between the two forms cannot come from content: no item asks for anything the catalog does not.
``K_LINES`` words the eleven catalog lines themselves in the same two forms, for arms Bq and Bs, which keep the shipped
mechanism (the model writes its own questions) and change only the grammar of the catalog.
"""
import textwrap

# (id, question form, statement form)
BANK = [
    ("K1.1", "Who uses the result, and through which entry point?",
     "Name who uses the result and the entry point it uses."),
    ("K1.2", "What observation shows it works?",
     "Name the observation that shows it works."),
    ("K2.1", "What is in scope, and what is out?",
     "State what is in scope and what is out."),
    ("K2.2", "What existing behaviour must not change?",
     "State the existing behaviour that must not change."),
    ("K3.1", "What are the exact inputs, outputs, commands, endpoints, files or messages, and their names and shapes?",
     "State the exact inputs, outputs, commands, endpoints, files or messages, and their names and shapes."),
    ("K3.2", "What status codes and errors does each give?",
     "State the status codes and errors each gives."),
    ("K4.1", "What are the domain rules, limits, boundaries and end conditions?",
     "State the domain rules, limits, boundaries and end conditions."),
    ("K4.2", "Which inputs are invalid?",
     "State which inputs are invalid."),
    ("K5.1", "What state exists, who owns it, and where does it live and for how long?",
     "State what state exists, who owns it, and where it lives and for how long."),
    ("K5.2", "Who may see it, and what happens on a concurrent change or a restart?",
     "State who may see it, and what happens on a concurrent change or a restart."),
    ("K6.1", "Which language and runtime versions apply?",
     "State the language and runtime versions."),
    ("K6.2", "Which dependencies are allowed or forbidden?",
     "State which dependencies are allowed or forbidden."),
    ("K6.3", "What configuration does it need (ports, environment variables, files)?",
     "State the configuration it needs (ports, environment variables, files)."),
    ("K7.1", "Which modules or seams does the behaviour need so it can be tested and changed in isolation?",
     "Name the modules or seams the behaviour needs so it can be tested and changed in isolation."),
    ("K8.1", "Which test framework and command run the tests?",
     "Name the test framework and its command."),
    ("K8.2", "What check observes each outcome at its real boundary?",
     "Name the check that observes each outcome at its real boundary."),
    ("K9.1", "Where must the result run or be delivered, and what access does that need?",
     "State where the result must run or be delivered, and the access that needs."),
    ("K10.1", "What performance, security, accessibility, interface polish or other bounds apply?",
     "State the performance, security, accessibility, interface polish or other bounds."),
    ("K11.1", "What would most likely make this work fail or be rejected?",
     "State what would most likely make this work fail or be rejected."),
    ("K11.2", "What would show that early?",
     "State what would show it early."),
]

# (id, title, question form, statement form): the catalog's own eleven lines
K_LINES = [
    ("K1", "Outcome and consumer",
     "who uses the result, through which entry point, and what observation shows it works?",
     "name who uses the result, through which entry point, and the observation that shows it works."),
    ("K2", "Scope and preserved behaviour",
     "what is in and out, and what existing behaviour must not change?",
     "state what is in and out, and the existing behaviour that must not change."),
    ("K3", "Interfaces and contracts",
     ("what are the exact inputs, outputs, commands, endpoints, files or messages, and their names, shapes, status codes "
      "and errors?"),
     ("state the exact inputs, outputs, commands, endpoints, files or messages, their names, shapes, status codes and "
      "errors.")),
    ("K4", "Rules and edge cases",
     "what are the domain rules, limits, invalid inputs, boundaries and end conditions?",
     "state the domain rules, limits, invalid inputs, boundaries and end conditions."),
    ("K5", "State and data",
     ("what state exists, who owns it, where does it live and for how long, who may see it, and what happens on a "
      "concurrent change or a restart?"),
     ("state what state exists, who owns it, where it lives and for how long, who may see it, and what happens on a "
      "concurrent change or a restart.")),
    ("K6", "Runtime and dependencies",
     ("which language and runtime versions apply, which dependencies are allowed or forbidden, and what configuration "
      "(ports, environment variables, files) does it need?"),
     ("state the language and runtime versions, the allowed or forbidden dependencies, and the configuration (ports, "
      "environment variables, files).")),
    ("K7", "Structure",
     "which modules or seams does the behaviour need so it can be tested and changed in isolation?",
     "name the modules or seams the behaviour needs so it can be tested and changed in isolation."),
    ("K8", "Verification",
     "which test framework and command run the tests, and what check observes each outcome at its real boundary?",
     "name the test framework, its command, and the check that observes each outcome at its real boundary."),
    ("K9", "Delivery",
     "where must the result run or be delivered, and what access does that need?",
     "state where the result must run or be delivered, and the access that needs."),
    ("K10", "Quality attributes",
     "what performance, security, accessibility, interface polish or other bounds apply?",
     "state the performance, security, accessibility, interface polish or other bounds."),
    ("K11", "Risks",
     "what would most likely make this work fail or be rejected, and what would show it early?",
     "state what would most likely make this work fail or be rejected, and what would show it early."),
]


def bank_item9(form: str) -> str:
    """Intake duty item 9 for arms Qb (``form`` "Q") and Sb ("S"): answer a fixed bank by id, write no questions."""
    noun, verb = ("question", "Answer") if form == "Q" else ("item", "Settle")
    head = (
        f"9. Key {noun}s. {verb} each key {noun} below for this request before anything is planned. In `answers`,\n"
        f"   write one row per {noun}: `id`, `basis` and `answer`. `basis` is the request sentence that settles the\n"
        f"   {noun} (S1, S2, ...) or one of: inspect (the repository or environment answers it), research (documentation\n"
        "   or other sources answer it), experiment (only running something answers it), default (no evidence can answer\n"
        "   it, so the run assumes `answer` and records it), person (only a person can decide it; `answer` is then the\n"
        "   default the run assumes), na (its answer would change nothing built, checked or delivered for this request;\n"
        "   `answer` is a few words of reason). Otherwise `answer` is what the request settles or the answer the run\n"
        "   assumes and records.\n"
    )
    index = 1 if form == "Q" else 2
    return head + "".join(f"   - {row[0]} {row[index]}\n" for row in BANK)


def catalog_block(form: str) -> str:
    """The K1-K11 lines of item 9 for arms Bq ("Q") and Bs ("S"), wrapped as the shipped catalog is."""
    index = 2 if form == "Q" else 3
    lines = []
    for row in K_LINES:
        text = f"{row[0]} {row[1]}: {row[index]}"
        lines.append(textwrap.fill(text, width=118, initial_indent="   - ", subsequent_indent="     ",
                                   break_long_words=False, break_on_hyphens=False))
    return "\n".join(lines) + "\n"
