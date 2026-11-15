# Plan format

Write the plan as one JSON object in this shape.

## Top-level keys

Required: `goal`, `initial_state`, `steps`, `parallel_groups`, `unresolved`. Optional: `goal_needs`.

- **`goal`**: one sentence describing the **end state** the plan achieves, not a task title or a verb-first to-do
  ("User authentication works end-to-end", not "Add auth").
- **`initial_state`**: concrete facts already true **and evidenced** before any step runs (supplied by the request or
  found by inspection while planning). Implementers may rely on them; they are not guesses.
- **`steps`**: at least one step; every step's `produces` has at least one non-empty string.
- **`parallel_groups`**: the steps of each dependency depth, derived from the inputs. You may leave it `[]`.
- **`unresolved`**: the open needs the plan cannot close (shape below); `[]` when none remain.
- **`goal_needs`** (optional): the request's terminal needs. Each must appear in some step's `produces` or in
  `initial_state` for the plan to be complete. Never invent an entry to fill the field; `[]` means no terminal
  constraint. An inherited plan's `goal_needs` stay exactly as supplied.

## Steps

Every step has **five required fields**, `id`, `statement`, `produces`, `inputs` and `origin`, plus one optional
field, `confirm`. `origin` is `seed` or `discovered`. Do not invent other step or plan fields (`dependents`, `flags`,
`rationale`, `preconditions` and so on).

**`statement` and every entry in `produces` are postconditions (state or conclusion), never actions, commands or tool
calls.** Write what becomes true when the step is done: "the database migration has been applied", not "run the
migration"; "the User model exposes a fullName getter", not "add a fullName getter".

**IDs and origins.** A new plan's steps use IDs `S1`, `S2`, … with `origin: "seed"`. When you work on an inherited
plan, its steps keep their IDs and origins (never rename or renumber them), and the steps you add use `D1`, `D2`, … in
creation order with `origin: "discovered"`. Never remove an inherited step's input edge; you may add edges and widen a
step's `statement` or `produces` in place, unless the request's edit bounds say otherwise. Inherited content (a step,
edge or confirmation in the supplied plan) stays unless the request's edit bounds make it changeable.

**`confirm`** (optional array) records how each produce is confirmed. Each entry is
`{"produces": "<exact text of one of this step's produces>", "by": "<command, observation or inspection>; pass when
<expected result>", "level": "execute" | "inspect" | "unconfirmable"}` and names a produce at most once. Write one for
every produce, work steps included. A confirmation must pass the two-people test: two people running it separately
would be forced to agree. `execute` means the condition must be exercised; `inspect` means inspection is enough. Give
content criteria (docs, changelogs, test coverage) a command-checkable confirmation, such as a search for required
terms. A produce no available check can confirm keeps its entry with `level: "unconfirmable"` and `by` naming what
would confirm it. When a check relies on an external oracle (a golden file, fixture or snapshot), the confirmation also
confirms that the oracle agrees with the task. An inherited confirmation stays exactly as supplied unless the edit
bounds allow changing it.

## Inputs

Each input is an object with required keys `need` (string) and `from`:

- `from: null`: the need is already true. It must also be listed, word for word, in `initial_state`.
- `from: "<step id>"`: the need is supplied by that step's `produces`.
- Never write `"initial"` or any other placeholder in `from`; only `null` or a real step id.

Optional fields: `artifact` (the concrete carrier) and `match` (only when the need's wording and the supplier's differ
in a way that is not obvious). Do not invent other input keys.

## Unresolved

Each entry has required keys `step`, `need` and `reason`:

- `reason: "residual-risk"`: the gap cannot be closed; no `cycle` field.
- `reason: "circular"`: committing the edge would create a cycle; a required `cycle` array of at least two step ids
  names the refused loop. Do not also put that edge in `inputs`.

Never drop a genuine need silently: close it with an input edge, widen a step, add a supplier step, or record it in
`unresolved`.

## Structural invariants

A valid plan satisfies all seven:

1. **Schema shape**: only the fields above; each `confirm` entry names the exact text of one of its step's `produces`,
   at most once, with a non-blank `by` and a `level` of `execute`, `inspect` or `unconfirmable`.
2. **Acyclic committed edges**: no dependency cycles; a circular risk goes in `unresolved`, not in `from` edges.
3. **Suppliers exist**: every non-null `inputs[].from` names an existing step id.
4. **Discovered steps consumed**: every `discovered` step supplies another step's input or a `goal_needs` entry.
5. **No double-track**: a need is not both an input and an unresolved entry of the same step.
6. **Bookkeeping consistency**: every step id in `unresolved` and `cycle` exists, and a non-empty `parallel_groups`
   matches the dependency depths.
7. **Null origins declared**: every `from: null` need also appears in `initial_state` (exact match after trimming and
   collapsing whitespace).

A structurally valid plan with entries in `unresolved` is valid but incomplete, which is normal for honest gaps. With
`goal_needs`, every entry must also be covered for the plan to be complete.
