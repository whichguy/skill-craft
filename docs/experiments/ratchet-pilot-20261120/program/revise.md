# The specification after the requester's answer

You are one step of a loop that a script runs. Another session wrote the specification in `ratchet/spec.md` for the
change request below; the requester was then asked one question about it and has answered. Bring the specification
up to date with the answer. The next session plans the build from it and knows only what the files say. Write no
product code, no tests and no plan.

## The request
[[REQUEST]]

## The question that was put
[[QUESTION]]

## The requester's answer
[[ANSWER]]

## Your work
The answer is a requirement now, as binding as a sentence of the request. Change `ratchet/spec.md` so that it says
so:

- State what the answer requires as a clause of its own, or in the clause it settles, with an Observable line that
  shows it and `Source: answer`.
- Remove the `Open:` line, or the part of one, that the answer settles. Every other open point stays as it is.
- Where a clause or a use case now contradicts the answer, correct it. Change nothing else. Keep the form and the
  numbering without gaps: a new clause takes the next number.

If the requester had no preference, the answer settles nothing: change nothing.

## Done when
- `ratchet/spec.md` agrees with the answer, keeps its form, and is the only file you changed.

[[CONDUCT]]
