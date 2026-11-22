You are writing a checklist. You change nothing but the one file named at the end.

In your working directory: `request.txt`, one sentence asking for a change to an existing program; `base/`, that program
as it is before the change (read its README.md, everything under docs/ and src/, and bin/; skim test/); and
`examples.json`, two checklists written earlier for other requests on other programs. They show the form and the grain
of an item. They are not a list of what to write.

Write the checklist for this request on this program: the specific things a well-elaborated specification of the
request ought to state, each as one sentence naming something to be settled, not how to settle it. It is written before
any specification exists and will be used to read specifications that other people write from the same sentence.

- Between 18 and 22 items.
- Each item is about the requested change in this program: its behaviour, its boundaries and errors, who may use it,
  what it does to what the program already has, what must stay as it is, and the rigour a correct and safe change needs.
  Do not add items for product capabilities the sentence does not ask for and the program does not have.
- Give each item one of these categories: interaction, permission, unhappy, edge, async, data, operator, nonfunctional,
  preserve.
- One sentence an item, specific enough that two readers would agree whether a specification states it.

Write `checklist.json` in your working directory, and nothing else:
{"nuances": [{"id": "N-1", "category": "<category>", "nuance": "<one sentence>"}, ...]}
