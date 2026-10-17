# Sol review of the compact implement guidance and Code craft (2026-10-17)

persona codex-sol, model_used gpt-6.1-sol, effort medium, fallback False. Question: sol-compaction-question-2026-10-17.md. Every fix it named was applied before adoption.

**Verdict: adopt CONCISE with fixes. Keep prose for Considerations.** Most compression preserves the contract; several edits change it. Rankings below reflect likely implementation impact, not character count.

### 1. Implement guidance: changed obligations

1. **Checklist recovery loses its source and iteration cadence.**  
   CURRENT: “Reuse it **each iteration** … rebuild it **from this packet** after context loss.”  
   CONCISE: “reuse it … rebuild it after context loss.”  
   Restore both phrases. Otherwise a model can reuse the checklist sporadically or reconstruct it from incomplete memory.

2. **Proof suitability loses validity as a condition.**  
   CURRENT: “If it cannot **validly assess** this step now, report revise.”  
   CONCISE: “If it cannot assess this step now, report revise.”  
   A Proof can run and assess something while being invalid for the assigned criterion. Restore “validly.”

3. **The initial reading obligation becomes less precise.**  
   CURRENT: “Read **the assignment and its anchors** … their **quoted R-n** … the **HOME sections under Anchored in**, and the **listed cards**.”  
   CONCISE: “Read the criteria, their R-n … the Anchored-in sections and the cards.”  
   This drops explicit reading of the assignment beyond those components and obscures the exact quoted requirements and HOME anchors. Preserve those references, especially if they match packet labels.

4. **Parallel work loses the independence condition.**  
   CURRENT: “**independent** work run in parallel where the platform supports it and the gain is real.”  
   CONCISE: “parallel work where the platform allows it and it pays.”  
   Platform support and benefit do not establish independence. Restore “independent.”

5. **“Wiring” potentially narrows required connections.**  
   CURRENT: “the change and its **connections** (entry points, registration, **wiring**, configuration …).”  
   CONCISE: “the change and its **wiring** (entry points, registration, configuration …).”  
   CURRENT treats wiring as one connection category; CONCISE makes it the umbrella. Keep “connections,” particularly because permissions, content and documentation are not naturally wiring.

6. **Unchanged reuse is less explicit.**  
   CURRENT: “Before creating anything, **reuse it unchanged**, combine existing pieces, or extend one.”  
   CONCISE: “reuse, combine or extend before creating.”  
   Reuse remains required, but the explicit option of using an existing capability without alteration disappears. Restore “unchanged.”

7. **Authority loses its run-specific qualifier.**  
   CURRENT: “Perform only the effects **the run’s recorded authority** covers.”  
   CONCISE: “Only effects **the recorded authority** covers.”  
   Likely equivalent in context, but weaker against importing permission from another run. Retain “run’s.”

8. **Several scope qualifiers disappear, creating small broadenings.**

   - CURRENT: “R-n requirements and AD-n decisions **that constrain it**.” CONCISE: “**The R-n and AD-n bind it**.” This can imply every referenced requirement or decision applies wholesale.
   - CURRENT: “Any transition **it needs**.” CONCISE: “**Any transition**.” The step-specific restriction becomes implicit.
   - CURRENT: “A new **implementation** decision.” CONCISE: “A new decision.” This broadens what must become an AD.
   - CURRENT: “A command **that now works**.” CONCISE: “A working command.” This can require recording already-working commands.
   - CURRENT repeatedly says “**assigned criterion**”; CONCISE says “criterion.” The opening supplies context, but the evidence and completion rules become less locally explicit.

   These are lower risk than items 1–7, but retain the qualifiers if the requirement is *no obligation changed*.

**CONCISE says more clearly:**

- “Changing or departing from an R-n or AD-n is a revise” makes the trigger direct.
- “No permanent tests or suites here” makes the prohibition immediately visible.
- The shorter Building, State and Proof entries are easier to scan without materially changing their remaining requirements.

### 2. Code craft: changed obligations

1. **The success-default prohibition narrows.**  
   CURRENT: “Never swallow an error or **substitute a success default**.”  
   CONCISE: “Never swallow an error or **return a success default**.”  
   Substitution can happen through assignment, callbacks or continued execution without returning a default. Restore “substitute.”

2. **The tombstone rule permits the wrong subject.**  
   CURRENT: “an approach **tried or considered and rejected**, and why.”  
   CONCISE: “an approach **tried or rejected**, and why.”  
   CONCISE permits documenting a tried approach that was retained. Use “an approach considered or tried, then rejected, and why.”

3. **The anti-conflation rule becomes broader.**  
   CURRENT: “a parameter that fuses **two different rules**.”  
   CONCISE: “a parameter fusing **two rules**.”  
   This can prohibit legitimate parameterization within one meaning, despite the preceding sentence. Restore “different.”

4. **Diagnostic summaries lose their required content.**  
   CURRENT: “short, redacted **state summaries**.”  
   CONCISE: “short redacted **summaries**.”  
   A model could satisfy the latter with generic action summaries. Restore “state.”

5. **Three smaller scope or precision changes remain.**

   - CURRENT: docstring gives “**errors raised**”; CONCISE: “**errors**.” Raised exceptions become less explicit.
   - CURRENT: “**A new name** must not collide”; CONCISE: “**No name** that collides.” This can extend the obligation to pre-existing names.
   - CURRENT: “No hard-coded … **in code**”; CONCISE omits “in code.” Read literally, it can prohibit the configuration values the next clause requires.

   Restore these short qualifiers.

**CONCISE says more clearly:**

- “shared mutable state guarded” expresses the required concurrency invariant directly.
- “every list paged or limited” is compact and preserves the remote-list obligation.
- The numbered rules retain recognizable names and actionable verbs despite substantial compression.

### 3. SYMBOLIC: interpretation risks

No supplied evidence establishes how often Sonnet, Grok or GPT would misread it. The following are concrete ambiguities available to any implementing model.

1. **Undefined and newly introduced notation.** `C` is never defined. `AD` loses the “interaction” qualifier in item 2. ``considerations.<key>`` introduces an output shape absent from CURRENT. These are contract changes, not cosmetic notation.

2. **`reuse > combine > extend > create` invents a ranking.** CURRENT requires considering existing options before creating; it does not rank reuse, composition and extension against one another. `>` can also mean a pipeline rather than preference.

3. **`→` has incompatible meanings despite its legend.** The legend says “then,” but it also means destination, obligation, implication and transformation:
   - “Each → `considerations.<key>`”
   - “untrusted input → validate”
   - “usage/ops change → note”
   - “shape before→after”

   A defined symbol should retain one meaning.

4. **Material prose conditions disappear.**
   - Whole step loses “everything the assigned criteria need at this step’s boundary.”
   - Interactions loses the affected-or-required scope condition.
   - Operations again loses “independent.”
   - “staged/reversible if risky” can require either measure whenever any risk exists; CURRENT makes the measure conditional on what the risk calls for.
   - “prepared ≠ authorized” omits the explicit treatment of **recording a release action**.

5. **The file-qualified anchors assert additional facts.** `[A§Stack]`, `[A§Real-boundary checks]` and `[E§Skills]` assign headings to particular files. CURRENT’s supplied text does not establish those locations. Verify them before encoding them.

6. **Symbol safety, ranked:**

   | Symbol | Assessment |
   |---|---|
   | `=` in a legend; `·` as a separator | Low risk |
   | `≠` | Familiar, but “does not imply authorization” is more exact than inequality |
   | `§`, `@` | Understandable with a legend; unnecessary decoding for anchors |
   | `+`, `/` | Ambiguous between conjunction, alternatives and shorthand |
   | `→`, `>`, `\|` | Risky here: overloaded sequencing, ranking or alternatives |
   | `⊆` | Mathematically clear, but less direct than “perform only authorized effects” |
   | `✗` | Understandable prohibition, but visually noisy and dependent on interpretation |

**Not worth adopting as supplied.** A roughly 16% token saving is modest compensation for undefined notation, invented ordering and lost conditions. Character savings matter less than token savings for model context cost.

### 4. Recommended disposition

1. **Adopt CONCISE after restoring the obligations above**, especially checklist recovery, valid Proof assessment, independent work, connection scope, success-default substitution and rejected-approach tombstones.
2. **Retain prose Considerations.** Shorten wording rather than introducing a notation system.
3. Treat these as **semantic review findings**, not measured model-performance claims. Packet snapshot tests can confirm insertion text; they cannot establish equivalent instruction-following behavior.