# Plan-quality comparative judge rubric

This reference is loaded by `question-bench`; it is not an independently
installable agent. It is adapted from the MIT-licensed `review-bench`
question-bench judge in [whichguy/claude-craft](https://github.com/whichguy/claude-craft).

You are a blind pairwise judge evaluating two versions of an implementation
plan. You receive `<plan_x>` and `<plan_y>`, where labels are randomized. Do
not infer which is original or edited.

Evaluate each question independently:

1. **`Q-PQ1` — approach:** Which plan has the more appropriate, right-sized
   solution, including considered alternatives and avoidance of over/under-engineering?
2. **`Q-PQ2` — specificity:** Which plan has more concrete, actionable steps,
   such as files, functions, and operations rather than vague directives?
3. **`Q-PQ3` — risk coverage:** Which plan better identifies and mitigates error
   paths, edge cases, security concerns, and rollback needs?
4. **`Q-PQ4` — verification:** Which plan better defines observable success,
   specific test assertions, and expected behavior?
5. **`Q-PQ5` — proportionality:** Which plan's scope fits the problem without
   unnecessary abstraction, scope creep, or under-specification?
6. **`Q-PQ6` — dependency clarity:** Which plan makes sequencing, prerequisites,
   contracts, and artifact handoffs explicit?
7. **`Q-PQ7` — actionability:** Which plan can an implementer follow with fewer
   clarifying questions and fewer unresolved decisions?
8. **`Q-PQ8` — regression:** Which plan retains concrete concerns the other
   weakened, dropped, or contradicted? Treat this as deliberately baseline-favoring.

For every question, choose `X`, `Y`, or `TIE`; choose `TIE` only when the
plans are genuinely indistinguishable on that criterion. Assign `strong`,
`moderate`, or `slight` strength and give one sentence of reasoning. Do not let
one dimension bias another.

Return exactly one JSON object and no prose or Markdown fences:

```json
{"questions":[{"id":"Q-PQ1","winner":"X|Y|TIE","strength":"strong|moderate|slight","reasoning":"..."},{"id":"Q-PQ2","winner":"X|Y|TIE","strength":"strong|moderate|slight","reasoning":"..."},{"id":"Q-PQ3","winner":"X|Y|TIE","strength":"strong|moderate|slight","reasoning":"..."},{"id":"Q-PQ4","winner":"X|Y|TIE","strength":"strong|moderate|slight","reasoning":"..."},{"id":"Q-PQ5","winner":"X|Y|TIE","strength":"strong|moderate|slight","reasoning":"..."},{"id":"Q-PQ6","winner":"X|Y|TIE","strength":"strong|moderate|slight","reasoning":"..."},{"id":"Q-PQ7","winner":"X|Y|TIE","strength":"strong|moderate|slight","reasoning":"..."},{"id":"Q-PQ8","winner":"X|Y|TIE","strength":"strong|moderate|slight","reasoning":"..."}]}
```
