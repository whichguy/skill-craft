# Research: building and evaluating documentation prompts for a coding-agent "document" stage

Compiled 2026-10-30 (web research, read-only). Each finding gives: claim, source URL, evidence strength, and what it implies for the ShipLoop document-stage prompt.

Evidence labels:
- **measured** = peer-reviewed or preprint study with numbers
- **system source** = read from a project's published code or prompts
- **vendor doc** = a tool maker's own guidance (not independently tested)
- **standard** = a published convention or specification
- **opinion** = practitioner essay or book
- **snippet-level** = I saw only a search-result summary or abstract of the source, not its full text. Treat the numbers as unverified.

Numbers I could check in the primary text are marked "(checked)". Quotes are under 15 words.

---

## 0. Reading of the current ShipLoop text (context for the implications)

I read `skills/shiploop/scripts/shiploop_prompts.py` (the `"document"` entry) and `skills/shiploop/references/testing-and-documentation.md` (section "Documentation"). Three observations shape the implications:

1. The document duty already points to a reference ("Documentation guidance") instead of inlining it. The reference section is about 60 lines. It holds the in-code contract rules and the tombstone paragraph.
2. The duty text lists README/API/user/operator/error/design docs and the three knowledge files. It does not mention rereading the docstrings and comments that already sit at the changed code. That check lives in the implement-stage rubric ("Revalidate existing warnings when behavior changes").
3. Step 5 ("Reread every changed document and run its commands and examples") mixes two things. Running commands is external observation. Rereading is self-review.

---

## 1. How documentation-generation agents and prompts are built and evaluated

### F1.1 DocAgent: dependency-first processing was the measured driver of quality
- **Claim.** DocAgent (Meta, ACL 2025) uses Reader, Searcher, Writer, Verifier and Orchestrator agents. A "Navigator" topologically sorts code so each component is documented after its dependencies, and their finished docstrings become context. Removing that order (random order) lowered helpfulness from 3.88 to 3.44 (GPT-4o mini) and 2.35 to 2.18 (CodeLlama-34B). It lowered truthfulness (existence ratio) from 94.64% to 86.75% and from 87.76% to 83.06% (checked, paper Tables 4 and 5, 50 sampled components). The paper's body text quotes slightly different helpfulness figures (3.69 and 2.39) than Table 4. Use the tables.
- **Baselines.** A plain chat prompt with the code only scored 61.1% existence ratio (GPT-4o mini) against 95.74% for DocAgent. Completeness was 0.815 vs 0.934 (checked, Tables 1 and 3). Most of the gain is context supplied before writing, not prompt wording. DocAgent has no Verifier ablation.
- **Source.** https://arxiv.org/abs/2504.08725 (full text read via the PDF), repo https://github.com/facebookresearch/DocAgent
- **Strength.** measured, but Python only, small models, ablation on 50 components.
- **Implication.** Order the packet so the agent sees the dependencies' existing docs, and the spec/AD lines the step touches, before it writes anything. A script can do the "Searcher" job (list changed public symbols, their callers, and the doc files that mention them) so the prompt does not have to describe it.

### F1.2 DocAgent evaluation: two deterministic metrics plus one decomposed LLM judge
- **Claim.** Completeness is a deterministic AST/regex check of required sections. Truthfulness is the existence ratio: entities named in the docstring that really exist in the repository's dependency graph, divided by entities extracted. Helpfulness is an LLM judge on a 5-point scale, scored per docstring part (summary, description, parameters) with explicit rubrics, few-shot good/bad examples, and chain-of-thought (checked in the appendix). Parameter descriptions were the weakest part for every system (2.0 to 2.7 out of 5 for DocAgent).
- **Source.** https://arxiv.org/abs/2504.08725
- **Strength.** measured design.
- **Implication.** Two of three quality dimensions can be scripted: required sections present, and every named identifier, path or flag exists. Both can run outside the prompt. Use the judge only for the part that cannot be scripted, and split it per part.

### F1.3 DocAgent Verifier prompt: three short questions
- **Claim.** The Verifier reads the docstring as a first-time reader. It flags (a) content that repeats the code or states the obvious, (b) over-detailed implementation or exposed internals, and (c) missing required sections or missing critical usage information. It returns a boolean NEED_REVISION plus a suggestion, and requests more context only when "absolutely necessary" (paraphrased from the prompt source).
- **Source.** https://raw.githubusercontent.com/facebookresearch/DocAgent/main/src/agent/verifier.py
- **Strength.** system source. The paper reports no Verifier ablation, so its effect is unmeasured.
- **Implication.** This is a ready, compact "precise, not profuse" rubric: adds information? exposes implementation instead of contract? omits a critical usage fact?

### F1.4 DocAgent Writer prompt: Google format with constraints and triggers
- **Claim.** The Writer follows Google docstring format. Summary states the outcome without repeating the name. Description covers why, when, where and a high-level how. Args explain valid ranges, constraints and interdependencies. Returns explain the possible values and the conditions that change them. Raises lists the condition that triggers each exception. Examples appear only for public, non-abstract components. The prompt does not say "do not invent".
- **Source.** https://raw.githubusercontent.com/facebookresearch/DocAgent/main/src/agent/writer.py
- **Strength.** system source.
- **Implication.** The contract content the owner wants (argument constraints, return conditions, error triggers) matches what the best published docstring agent asks for. Cite "Google Python style, docstring sections" by name and add only the project-specific exceptions.

### F1.5 RepoAgent: bottom-up generation and diff-driven updates
- **Claim.** RepoAgent (EMNLP 2024 demo) parses ASTs, builds a reference graph, generates docs bottom-up so dependencies' docs are context, tracks git changes to update only affected objects, and can run as a pre-commit hook.
- **Source.** https://github.com/OpenBMB/RepoAgent (README); EMNLP 2024 System Demonstrations.
- **Strength.** snippet-level, system demo with small evaluation.
- **Implication.** Same shape as F1.1. Update objects in the diff and the objects that call them, not the whole tree.

### F1.6 LLM-written comments are often inaccurate, and consistency detectors did not catch it
- **Claim.** Manual labeling of 540 LLM-generated Java method comments found inaccurate statements in about one fifth of GPT-4's comments, about a third of GPT-3's, and at least half of StarCoder's. Error types, in rising severity: hallucinated intent, hallucinated references to nonexistent code, missing context, and mischaracterised visible code. None of nine existing code-comment consistency techniques had a statistically significant relationship with accuracy (p between 0.168 and 0.747). "Document testing" (generate tests from the comment, execute them) did. Rejecting comments scored below 0.8 removed 46% of inaccurate comments and kept 72% of accurate ones (checked).
- **Source.** https://arxiv.org/html/2406.14836v1
- **Strength.** measured, but older models and Java.
- **Implication.** "Document nothing you did not observe working" is the right stance. Observation by execution beats rereading. Claims about intent ("this exists because...") should come from the spec or an AD, not from the agent's inference.

### F1.7 Hallucination in change-to-text generation is hard to detect with metrics
- **Claim.** A 2025 study of code-change-to-natural-language generation names three hallucination types (input inconsistency, logic inconsistency, intention violation). Individual detection metrics were only marginally better than chance (56.6%).
- **Source.** https://preview.aclanthology.org/evt-to-venues/2025.ijcnlp-long.137.pdf
- **Strength.** snippet-level.
- **Implication.** Do not plan on a generic metric or judge to catch wrong claims. Use grounded checks (F4.6).

### F1.8 README generation: a developer-written plan beat autonomous planning
- **Claim.** Comparing single-agent, multi-agent and developer-guided README generation, the single agent matched the multi-agent system on lexical quality with 86% fewer tokens and about twice the speed. Multi-agent gave better structural consistency (98%). The developer-guided plan scored best, and the authors name autonomous planning as the bottleneck.
- **Source.** https://arxiv.org/abs/2606.30524 (ICSME 2026 NIER; abstract read)
- **Strength.** measured, but LLM-judge and manual inspection.
- **Implication.** A script-built worklist (changed behaviour -> doc home) is a "lightweight developer plan". It likely helps more than extra agent roles or longer prose.

### F1.9 A fixed few-shot prompt helped novices; experts needed less
- **Claim.** In a controlled experiment (20 professionals, 30 students, two Python functions), students using ad-hoc prompts got docs rated less readable, concise and helpful than a predefined few-shot prompt. Some professionals matched quality by adding the word "Docstring".
- **Source.** https://arxiv.org/abs/2408.00686
- **Strength.** measured, small, about humans prompting.
- **Implication.** Weak for an agent pipeline. It supports a fixed template/example over free-form instruction, and not much more.

### F1.10 Drift workflows scope by user-facing surface
- **Claim.** Mintlify's drift guidance triggers on merged PRs and watches API endpoints, request parameters, SDK methods, CLI flags, config options and response shapes. It maps each surface to its doc pages, skips internal refactors, validates that examples still match, and keeps human review. Swimm's CI "auto-sync" updates code elements in docs (snippets, tokens, paths) and flags docs that may be out of date.
- **Sources.** https://www.mintlify.com/library/how-to-stop-documentation-drift , https://docs.swimm.io/features/keep-docs-updated-with-auto-sync/
- **Strength.** vendor doc.
- **Implication.** The stage should key on public surfaces, treat "no doc change, with a reason" as a normal outcome, and let a script map a surface name to the docs that mention it.

### F1.11 Published rules for coding agents: short, non-derivable, referenced
- **Claude Code:** CLAUDE.md should hold only what Claude cannot work out from the code: commands to confirm work, places where the code misleads, decisions not in the repo, anything corrected twice. "Describe your architecture and file layout" is on the list of things to stop doing. A line that keeps being ignored means the file is too long, not that it needs emphasis. https://code.claude.com/docs/en/best-practices (vendor doc)
- **Cursor:** keep rules under 500 lines. "Reference files instead of copying their contents" keeps rules short and fresh. Referenced files are read on demand, so must-have context belongs in the rule body. Do not paste full style guides (use a linter). Add a rule when the agent repeats a mistake. https://cursor.com/docs/context/rules (vendor doc)
- **GitHub Copilot:** lists validated commands with preconditions and postconditions, errors with workarounds, and says to avoid task-specific content and conflicting instructions. File listings, README contents and snippets are lowest priority. https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions (vendor doc)
- **OpenHands:** "keep content concise" to save context. https://docs.all-hands.dev/modules/usage/prompting/microagents-syntax (vendor doc; snippet-level)
- **Aider:** a small read-only CONVENTIONS.md; no documentation guidance. https://aider.chat/docs/usage/conventions.html (vendor doc)
- **Implication.** Every vendor converges on "short, non-derivable, point to files." Only Cursor states the cost of pointing: the reference may not be read, so the must-do items stay in the body. In ShipLoop the script prints the packet, so it can print the exact section it wants read.

### F1.12 Agent-authored context files did not help, human-written minimal ones did
- **Claim.** Across coding agents on SWE-bench Lite and a new AGENTbench built from issues in repositories whose developers committed their own context files, LLM-generated context files changed resolution by about -0.5% and -2% and raised cost about 20% to 23%. Developer-written files improved resolution by about 4% with up to 19% more cost. Agents followed the instructions (more testing and traversal), so unneeded requirements made tasks harder. Repository overviews did not help find files faster. When all .md docs were removed, generated files helped (+2.7%), which suggests they duplicate existing docs. The authors advise that human-written files "should describe only minimal requirements" (checked, HTML v1).
- **Source.** https://arxiv.org/abs/2602.11988 , https://arxiv.org/html/2602.11988v1
- **Strength.** measured preprint (ICLR 2026 listing). Wording in the abstract changed between versions, so check the final text before quoting.
- **Implication.** This is the strongest direct evidence for the owner's suspicion. Text that restates what the repo already says costs steps and money, and every added duty gets followed. Added documentation duties should each trace to an observed miss.

### F1.13 Long-prompt guidance from the model vendor
- **Anthropic context engineering:** aim for the smallest set of high-signal tokens. "Minimal" does not mean short. Prefer a few diverse canonical examples to long rule lists. Keep lightweight references (paths, links) and load on demand. Use notes outside the context for durable state. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents (vendor doc)
- **Anthropic prompting guide:** give the reason behind an instruction; use 3 to 5 examples in tags; put long data first and the instructions last (up to 30% better in their tests); say what to do instead of what not to do; softer wording for newer models because emphasis now over-applies rules. https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices (vendor doc)
- **Anthropic skill guide:** challenge every paragraph for its token cost; keep SKILL.md under 500 lines; keep references one level deep, because nested references led the model to preview files with `head -100` and miss content; add a table of contents to references over 100 lines; use "run validator, fix, repeat" loops; build evaluations first and write the minimum that closes observed gaps. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices (vendor doc)
- **Implication.** Reference, one level deep, with a contents list; examples over rule lists; reasons attached to the few rules that matter; instruction last.

---

## 2. Frameworks a prompt can cite instead of restating

The three most useful rules per framework for an agent updating docs after a small code change.

| Framework | Rules most useful to the stage | Source (strength) |
|---|---|---|
| **Diataxis** | (1) Reference "describes and only describes": neutral, austere, no instruction or explanation; it links to how-to and explanation. (2) Mirror the product's structure so docs and code are navigated together. (3) Short usage examples are fine in reference. Put a fact in one type only. | https://diataxis.fr/reference/ (standard; the "do not mix" rule is on other pages I did not fetch) |
| **Google developer documentation style guide** | Active voice; address the reader as "you"; sentence-case headings; descriptive link text; code font for code; conditions before instructions; numbered lists for sequences. | https://developers.google.com/style/highlights (standard). Enforce with Vale, not prose. |
| **Write the Docs, docs as code** | Same tools, review and tests as code; writers and developers share ownership; teams can gate merges on docs. | https://www.writethedocs.org/guide/docs-as-code/ (opinion/community). The page does not mention link checking or linting; those extend the "automated tests" principle. |
| **PEP 257** | One-line imperative summary; do not restate the signature; functions document behaviour, arguments, return values, side effects, exceptions, and restrictions on when to call; scripts' docstrings double as usage messages. | https://peps.python.org/pep-0257/ (standard) |
| **Google Python style 3.8** | Docstring required for public API, non-trivial or non-obvious functions. Give enough to call it without reading the code, no implementation detail. Args, Returns (omit for None), Raises only for exceptions relevant to the interface, not ones caused by API misuse. Comments: "Never describe the code." | https://google.github.io/styleguide/pyguide.html (standard) |
| **NumPy docstring** | Short summary must not use the function or variable names; Raises "sparingly" for non-obvious errors; implementation and theory go in Notes; Examples are doctests that illustrate usage, not a test framework. | https://numpydoc.readthedocs.io/en/latest/format.html (standard) |
| **TSDoc / JSDoc** | `@param name - description` with a hyphen; do not repeat types in TypeScript. `eslint-plugin-jsdoc` rules `check-param-names`, `require-param`, `require-returns`, `no-types` check doc against code. | https://tsdoc.org/ , https://github.com/gajus/eslint-plugin-jsdoc (standard / tool doc) |
| **Javadoc** | Doc comments are the API specification: first sentence is the summary; do not describe bugs or how an out-of-spec implementation behaves; no built-in pre/postcondition tags, so write them as text or a custom tag. | https://www.oracle.com/technical-resources/articles/java/javadoc-tool.html (vendor doc, **not fetched** (403); snippet-level, with course notes for tags) |
| **Design by Contract** | Precondition = what the caller must ensure; postcondition = what the implementer guarantees; class invariant = what always holds. The "contract view" (signature, header comment, assertions) is the spec without the implementation. Because it lives in code it is checkable and cannot drift as a separate document. | https://www.eiffel.org/doc/solutions/Design_by_Contract_and_Assertions (vendor doc) |
| **ADRs (Nygard)** | One decision per record, 1 to 2 pages, five parts: title, status, context, decision in "We will..." form, consequences (good, bad and neutral). Number never reused; a reversed decision stays, marked superseded. | https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions (opinion, original) |
| **MADR** | Mandatory: title, context and problem, considered options, decision outcome. Optional: drivers, consequences, confirmation, pros and cons. Rejected options belong in the record. | https://adr.github.io/madr/ (standard/template) |
| **arc42 / C4** | arc42 section 9 holds important, expensive, large-scale or risky decisions with rationale. Decisions local to one building block go in that block's description. Do not repeat what the solution strategy already says. Not every section is required: document what is relevant. C4: four levels (context, containers, components, code); I could not confirm from the page that the code level is optional. | https://docs.arc42.org/section-9/ , https://c4model.com/ |
| **Keep a Changelog** | Changelogs are for humans. Group by Added, Changed, Deprecated, Removed, Fixed, Security. Keep an Unreleased section at the top. | https://keepachangelog.com/en/1.1.0/ (standard). In skill-craft the changelog is release-tool output; for other products it is a normal duty. |
| **Living documentation (Martraire)** | Reliable, low effort, collaborative, insightful. Most knowledge already exists in code, tests and behaviour; find and exploit it. The book has a "reconciliation/verification mechanism" section (not read). | https://www.infoq.com/articles/book-review-living-documentation/ , https://hilton.org.uk/blog/martraire-documentation-principles (opinion) |
| **Standard Readme** | Required: title, short description (under 120 characters), contributing, license; install and usage unless a docs-only repo. No broken links; code examples linted like project code. | https://github.com/RichardLitt/standard-readme/blob/main/spec.md (standard) |
| **Software Engineering at Google, ch. 10** | Docs in source control with owners; update with the code in the same change; one canonical document per topic, merge or retire duplicates; rationale in design docs, not API reference; landing pages link rather than hold content; three review types (technical, audience, writing). | https://abseil.io/resources/swe-book/html/ch10.html (opinion/vendor) |
| **Google eng-practices (reviewer)** | Comments mainly explain why; if code needs a comment for what, simplify it (regex and complex algorithms excepted). If a change alters how users build, test, interact with or release, check the README and reference docs. If code is deleted or deprecated, consider removing its docs. A pre-existing comment may warn against the change being made. | https://google.github.io/eng-practices/review/reviewer/looking-for.html (vendor doc) |

**Implication.** A prompt can name "Google Python docstrings (Args, Returns, Raises for interface-relevant errors)", "TSDoc", "Diataxis reference" and "Nygard ADR" in a line each. The model has seen all of them, and the rules above are the ones that matter after a small change. One tension to resolve in the prompt: Google Python says do not list exceptions that arise only from API misuse, while Design by Contract treats a violated precondition as the caller's fault. State preconditions in Args as constraints, and reserve Raises for errors a correct caller can still meet.

---

## 3. Prompt length and style for agents (measured results first)

### F3.1 Position matters, and long inputs cost accuracy
- **Claim.** Performance is highest when the relevant information is at the start or end of a long input and drops when it is in the middle; accuracy falls as the input grows, even for long-context models (Liu et al., TACL 2024).
- **Source.** https://arxiv.org/abs/2307.03172
- **Strength.** measured (2023 models).
- **Implication.** Put the duty and the deliverable fields at the end of the packet, after the evidence it works from. Do not bury the one rule that must hold in the middle of a long block.

### F3.2 Context rot
- **Claim.** Across 18 models, performance becomes less reliable as input grows, even on trivial tasks. Distractors that are semantically close hurt more. On a conversational-memory benchmark, a focused prompt of about 300 tokens beat the full 113k-token prompt. Whether information is present matters less than how it is presented.
- **Source.** https://trychroma.com/research/context-rot
- **Strength.** measured, vendor technical report (not peer reviewed).
- **Implication.** Do not pad the packet with neighbouring rules. Print only the sections the stage needs.

### F3.3 Reasoning degrades with padding at around 3,000 tokens
- **Claim.** Holding the task fixed and adding irrelevant text made reasoning accuracy fall at 3,000 tokens, far below the models' limits.
- **Source.** https://arxiv.org/abs/2402.14848 (ACL 2024; snippet-level)
- **Strength.** measured.
- **Implication.** A document packet with 8k tokens of rubric plus a diff is in the range where this was observed. It supports trimming, but it does not size the effect for a documentation task.

### F3.4 More simultaneous instructions lowers the chance of meeting all of them
- **Claim.** On ManyIFEval (up to 10 instructions) and StyleMBPP (up to 6 coding-style instructions) across 10 LLMs, performance consistently declined as the instruction count rose. A logistic regression on instruction count predicted performance within about 10% (checked, abstract). IFScale (20 models, 500 keyword instructions) found the best models reached 68% at the highest density, and a primacy bias toward earlier instructions.
- **Sources.** https://arxiv.org/abs/2509.21051 , https://arxiv.org/abs/2507.11538
- **Strength.** measured, but synthetic, checkable instructions. IFScale's densities are far above a documentation duty list.
- **Implication.** Each instruction that a script can check should move to the script. That leaves fewer for the model to hold at once. Put the most important ones first.

### F3.5 Staged, self-contained packets beat long multi-turn context
- **Claim.** Models averaged a 39% relative drop on multi-turn, underspecified conversations compared with single-turn, fully specified prompts, mostly from unreliability. Models made early assumptions and over-relied on them.
- **Source.** https://arxiv.org/abs/2505.06120 (ICLR 2026; figure from search summary)
- **Strength.** measured.
- **Implication.** Supports the harness design of one stage per packet with context cleared. Make the document packet self-contained (changed paths, step plan, spec lines) and do not assume the agent remembers implement-stage decisions.

### F3.6 Self-critique alone does not fix errors; external signals and structured checklists do
- **Claim (a).** LLMs cannot reliably self-correct reasoning without external feedback, and performance sometimes degrades after self-correction (Huang et al., ICLR 2024). https://arxiv.org/abs/2310.01798 (measured; abstract-level)
- **Claim (b).** Chain-of-Verification has the model draft, plan verification questions, answer them in separate prompts so the draft cannot bias them, then revise. It reduced hallucination in list, closed-book QA and long-form generation (ACL Findings 2024). https://arxiv.org/abs/2309.11495 (measured; numbers not checked)
- **Claim (c).** Checklist-based self-refinement (STICK) improved LiveBench reasoning by 7.8 points absolute and best-of-N on WildBench by 6.3, and beat unstructured self-critique. On verifiable tasks (math, code) results improved after one iteration and then degraded. https://arxiv.org/abs/2410.03608 (measured; snippet-level numbers)
- **Claim (d).** Anthropic: asking the model to verify against test criteria "catches errors reliably" for coding, but on Claude Opus 5 such instructions can cause over-verification, so remove them there. https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices (vendor doc)
- **Implication.** Make the verification step name concrete external checks (run the command, grep that the identifier exists, run the link and doc-example tools) and give specific checklist items. A bare "reread" is the weakest form. Owner note: TICK's one-iteration result bears on loop limits, but adding any limit is the owner's decision (recorded rule: ask before adding or changing a limit).

### F3.7 Examples steer style and detail better than description
- **Claim.** Anthropic recommends 3 to 5 relevant, varied examples in tags, and says examples convey desired style and detail more clearly than descriptions. DocAgent's own judge uses good/bad few-shot examples to anchor its rubric.
- **Sources.** https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices , https://arxiv.org/abs/2504.08725
- **Strength.** vendor doc plus system design. No measured study isolates examples for docstring prompts.
- **Implication.** One before/after pair (a docstring that narrates the code vs one that states the contract) would carry "precise, not profuse" in fewer tokens than three paragraphs of rule.

### F3.8 LLM judges have a length bias whose direction differs by model
- **Claim.** Recent judge-bias evaluations report verbosity bias for some judges (prefer longer) and the opposite for others (a Claude judge preferred shorter), so test your own judge with length-matched pairs.
- **Source.** https://arxiv.org/pdf/2604.23178 , https://arxiv.org/html/2601.00624v1
- **Strength.** snippet-level.
- **Implication.** If prompt variants are compared with a judge, report word counts and use the deterministic metrics of F1.2 alongside the judge.

---

## 4. Code comments: what pays off, what drifts, how to detect it

### F4.1 Comments should carry the why; contract docs carry the interface
- **Claim.** Google's reviewer guide: comments mainly explain why code exists, information the code cannot contain; class, module and function docs are a separate thing describing purpose, use and behaviour. Google Python style: never describe the code. Ousterhout (via book notes): interface comments should add precision such as units, bounds, ownership and invariants, and if an interface comment must describe the implementation, the method is shallow.
- **Sources.** https://google.github.io/eng-practices/review/reviewer/looking-for.html , https://google.github.io/styleguide/pyguide.html , https://theleo.zone/books/a-philosophy-of-software-design/ (secondary)
- **Strength.** vendor doc / standard / opinion.
- **Implication.** Rubric in one line: "docstring = contract the caller needs; comment = why, or a warning; neither narrates the code."

### F4.2 Trivial comments exist but are a minority of the problem
- **Claim.** A comment-quality model on five Java systems flagged "trivial" member comments (high word overlap with the method name) at 1% to 9% of member comments and "unrelated" ones at 9% to 39%. 18% to 49% of all comments were copyright boilerplate and up to 11% were commented-out code (checked, Table V).
- **Source.** https://teamscale.com/hubfs/26978363/Publications/2013-quality-analysis-of-source-code-comments.pdf (Steidl, Hummel, Juergens, ICPC 2013)
- **Strength.** measured, old, Java.
- **Implication.** Modest. The dangerous comments are stale or wrong ones, not the redundant ones. Weight the prompt toward reconciliation (F4.3) over anti-redundancy rules.

### F4.3 Comment-code inconsistency is linked to bugs, but unevenly
- **Claim (a).** In FreeBSD, PostgreSQL and Eclipse, comment-update practices predicted future bugs better than prior bugs or change counts. Inconsistent updates were not necessarily correlated with more bugs. The risky change is one that departs from the function's usual practice (code changed without its comment where comments are usually updated, or the reverse) (checked, abstract). The paper cites a manual analysis finding 60 FreeBSD bugs caused by out-of-date comments, and developers who lose confidence in all comments after meeting one wrong comment. https://sail.cs.queensu.ca/data/pdfs/JSS_OnTheRelationshipBetweenCommentUpdatePracticesAndSoftwareBugs.pdf
- **Claim (b).** A 2024 LLM-assisted study found inconsistent code-comment changes about 1.5 times more likely to lead to a bug-introducing commit, with the effect strongest right after the inconsistency appears. https://arxiv.org/abs/2409.10781
- **Claim (c).** iComment found 60 comment-code inconsistencies in Linux, Mozilla, Wine and Apache: 33 new bugs and 27 bad comments. https://www.cs.purdue.edu/homes/lintan/publications/icomment_sosp07.pdf (snippet-level)
- **Claim (d).** Wen et al. mined 1,500 Java projects and 500 fix commits to build a taxonomy of comment changes. https://www.inf.usi.ch/faculty/lanza/PUBS/P/Wen2019a.pdf (snippet-level)
- **Strength.** measured.
- **Implication.** When behaviour changes, update or delete the comments and docstrings adjacent to the changed lines. The document stage currently lists README/API/user docs only, and not the existing in-code comments at the changed code (see section 0, point 2).

### F4.4 Wrong comments mislead the next agent, not only the next human
- **Claim.** In code generation on LiveCodeBench, comments taken from solutions that pass raised recipient pass@1 by 17.2% on average. Comments from failing solutions gave no reliable gain. Comments written for a different problem lowered pass@1 by 20.8%. The authors conclude comments help because they carry correct solution content.
- **Source.** https://arxiv.org/abs/2609.09242 (EMNLP Findings 2026)
- **Strength.** measured.
- **Implication.** In an agent-driven repo the next step's implement agent reads these comments as ground truth. A stale one is an active hazard.

### F4.5 Warnings about removed approaches ("tombstones") have no standard form
- **Claim.** I found no established convention named "tombstone comment". The nearest practices are: comments at the decision point that name the risk, say how it was verified, explain the current choice, and are written for a reader who cannot ask the author (Atomic Object, paraphrased); recording considered-and-rejected alternatives with reasons so people stop re-proposing them (a reader comment on John D. Cook's post; MADR's "Considered Options"); and commit messages that say a removal was deliberate (an LLVM commit). In Bugsnag's usage, "tombstone" means a runtime call that reports when supposedly dead code runs, a different meaning. Claude Code's own guidance lists "places where the code is misleading: an old pattern... new code must not copy" as core content for agent instructions.
- **Sources.** https://spin.atomicobject.com/chestertons-fence-code-comments/ (opinion) , https://www.johndcook.com/blog/2019/09/17/why-would-anyone-do-that/ (opinion) , https://adr.github.io/madr/ , https://bugsnag.com/blog/javascript-refactoring-with-bugsnag-and-tombstones (opinion) , https://code.claude.com/docs/en/best-practices
- **Strength.** opinion plus vendor doc. No measured study.
- **Implication.** Keep the idea. The comment holds the one-line warning at the decision point plus the AD id. The AD holds the rejected option and the failure it caused. Define "tombstone" once in the prompt, since the word is not standard.

### F4.6 Detecting drift: what exists, and what each tool can and cannot see

| Tool | What it checks | Cannot see | Source |
|---|---|---|---|
| doctest (Python), rustdoc doctests | Docstring examples still run and give the output shown | Prose claims | https://docs.python.org/3/library/doctest.html , https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html |
| pytest-examples, markdown-pytest | Run and lint code blocks in README/markdown | Prose claims | https://github.com/dmontagu/pytest-examples (snippet-level) |
| pydoclint | Docstring Args, Returns, Raises, Yields match the signature and code (numpy, Google, Sphinx styles) | Whether the descriptions are true | https://github.com/jsh9/pydoclint |
| eslint-plugin-jsdoc | `@param` names match, params and returns documented, no types in TS | Meaning | https://github.com/gajus/eslint-plugin-jsdoc |
| interrogate | Docstring presence/coverage with a fail-under threshold | Accuracy or usefulness (it only counts) | https://interrogate.readthedocs.io/en/latest/ |
| Vale | Prose style rules; `error` severity fails CI | Facts | https://docs.vale.sh/ |
| markdownlint (53 rules), lychee | Markdown structure; broken links | Facts | https://github.com/DavidAnson/markdownlint , https://github.com/lycheeverse/lychee |
| Swimm auto-sync, markdown-code | Code snippets, tokens and paths in docs follow the code; check mode | Prose | https://docs.swimm.io/features/keep-docs-updated-with-auto-sync/ |
| Existence-ratio check (DocAgent) | Every named entity exists in the repo | Wrong behaviour of an existing entity | https://arxiv.org/abs/2504.08725 |
| Document testing (Kang et al.) | Tests generated from a comment, then executed | Cost; Java prototype | https://arxiv.org/html/2406.14836v1 |

Automated comment updating is itself unreliable: a fine-tuned model's just-in-time comment updates were 65% correct in manual evaluation (ICSE 2025, C4RLLaMA, snippet-level, https://conf.researchr.org/details/icse-2025/icse-2025-research-track/10/Code-Comment-Inconsistency-Detection-and-Rectification-Using-a-Large-Language-Model), and a December 2025 detector reports gains over fine-tuned LLMs on JITDATA/CCIBENCH (https://arxiv.org/abs/2512.19883, snippet-level).

- **Implication.** Presence checks and style checks are cheap and belong in scripts. The claims most likely to be wrong (behaviour, intent) are the ones only execution or an existence grep can catch. The prompt should say which command is run for which claim, and the scripts should print the tool findings into the packet's result.

### F4.7 Good commit messages carry what and why
- **Claim.** A study of about 1,600 messages from five OSS projects defines a good commit message as one that says what changed and why, and built a classifier (81.6% precision).
- **Source.** https://arxiv.org/abs/2202.02974
- **Strength.** measured (snippet-level).
- **Implication.** The commit is the third home for rationale. A removal rationale in a commit message is cheap and findable, but it is not read by the next agent unless something points to it.

---

## 5. Persistent versus transient: what belongs in a durable design document

### F5.1 ADR triggers cluster around five categories
- **Claim.** Record "architecturally significant" decisions: those affecting structure, non-functional characteristics, dependencies, interfaces or construction techniques (Nygard). AWS's ADR process lists the same five (structure, non-functional requirements, dependencies, interfaces, construction techniques) citing Richards and Ford. arc42 adds "important, expensive, large-scale or risky". MADR is looser: any important decision, as long as writing it is easy.
- **Sources.** https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions , https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html , https://docs.arc42.org/section-9/ , https://adr.github.io/madr/
- **Strength.** opinion/standard, widely used.
- **Implication.** Give the stage a short trigger: an AD is warranted when the step changed or departed from structure, an NFR, a dependency, an interface or a construction technique.

### F5.2 What to leave out
- **Claim.** Skip decisions that are not architectural, are tiny or self-contained, are already covered by standards or docs, or are temporary (workarounds, proofs of concept, experiments). arc42: decisions local to one building block go in that block's description; do not repeat the solution strategy; rationale matters more than the bare fact. Martraire: document long-lived, widely useful, valuable or critical knowledge; do not document what is cheaper to recreate; "the default is don't".
- **Sources.** https://github.com/joelparkerhenderson/architecture-decision-record , https://docs.arc42.org/section-9/ , https://hilton.org.uk/blog/martraire-documentation-principles
- **Strength.** opinion.
- **Implication.** Same test works for R-n lines and environment commands: add an entry only if it is not derivable from the code, would change a later step's behaviour, is costly to rediscover, and will outlive the next refactor. Otherwise it stays in RUN notes.

### F5.3 Supersede, do not rewrite
- **Claim.** Accepted ADRs are immutable; a changed decision gets a new ADR and the old one is marked superseded (Nygard, AWS). A common practitioner variant keeps a dated "living document". Numbers are never reused.
- **Sources.** as F5.1 and https://github.com/joelparkerhenderson/architecture-decision-record
- **Strength.** opinion.
- **Implication.** Matches the existing rule (a superseded AD-n moves to "## Superseded"; spec lines are added, not edited). Keep it.

### F5.4 Agent instruction and memory files follow a "cannot derive it" test
- **Claim.** Claude Code: include only what cannot be worked out from the code, and anything corrected twice. Cursor: add a rule when the agent repeats a mistake. Copilot: validated commands with errors and workarounds, no task-specific content. Anthropic: structured notes outside the context window (a NOTES.md) preserve progress across resets.
- **Sources.** https://code.claude.com/docs/en/best-practices , https://cursor.com/docs/context/rules , https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions , https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- **Strength.** vendor docs. The only measured comparison (F1.12) says agent-written files that restate docs do not help.
- **Implication.** Entries in spec/architecture/environment should be what a fresh packet cannot get from the code or README, and should link to the authoritative home.

---

## 6. Evidence gaps and cautions

- **No study tests documentation-stage prompt length directly.** I found no A/B of a "document after change" prompt at 300 vs 1,500 words. The nearest measured evidence is F1.12 (context files), F3.2 to F3.4 (length and instruction count) and DocAgent's context-order ablation. Expect the effect of trimming to be real but unsized; the owner's own harness is the only place to size it.
- **The strongest measured effect is context order and grounding, not prompt wording** (F1.1, F1.6).
- **Short does not mean sparse.** Anthropic says minimal is not short, and the repo's own rule is precision over word limits. The evidence supports removing restatement, not removing obligations.
- **Several sources are snippet-level** (marked above): RepoAgent, Liu et al. IJCNLP 2025, C4RLLaMA, iComment, Wen et al., judge-bias papers, the Javadoc article (403 on fetch), "Same Task, More Tokens".
- **Possible prompt-injection text seen.** The docs.vale.sh page contained text addressed to AI agents (asking for GET requests to an external endpoint), and one search result for README generation had garbled unrelated instructions. I did not act on either.

---

## 7. Ranked implications for the document-stage prompt

Ranked by (evidence strength) x (how directly it changes the prompt) x (cost to adopt).

1. **Add a duty line only for an observed miss; delete restated rubric.** Agent-authored and over-specified context cut resolution rates and added 20% cost, while minimal human-written requirements helped (F1.12), and vendors say the same (F1.11, F1.13). Cut text that repeats what the repo, linters or the standards already say. Keep obligations that a failure has shown are missed. *Sources: https://arxiv.org/abs/2602.11988 , https://code.claude.com/docs/en/best-practices*

2. **Replace "reread" with named external checks; use scripts for everything mechanical.** Self-critique without external signal is unreliable (F3.6). Execution-based document testing tracked accuracy while consistency detectors did not (F1.6). A script can print: example/doctest results, link check, docstring-vs-signature lint (pydoclint or eslint-plugin-jsdoc), and an existence check that every backticked identifier, path and flag resolves (F1.2: 95.7% vs 61.1% for context-free chat). The prompt then only says "fix what the checks print and run each documented command". *Sources: https://arxiv.org/html/2406.14836v1 , https://arxiv.org/abs/2504.08725 , https://arxiv.org/abs/2310.01798*

3. **Order the packet: evidence first, duty last.** Print the changed public symbols, their existing docs, and the spec/AD lines the step touches, then the instructions and result fields at the end. Dependency-first context was the measured driver in DocAgent (F1.1), and position effects favour the end (F3.1, Anthropic's up-to-30% for queries last). *Sources: https://arxiv.org/abs/2504.08725 , https://arxiv.org/abs/2307.03172 , https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices*

4. **Reference by file, but have the script print the exact section; keep references one level deep with a contents list.** Models partly read nested references (Anthropic), and Cursor warns that referenced files are read on demand. This keeps the owner's "reference project files" instinct and avoids the risk that the reference is never opened. This is a design inference from vendor guidance, not a tested result. *Sources: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices , https://cursor.com/docs/context/rules*

5. **Add one line: reconcile the existing docstrings and comments at the changed code.** Update or delete them, and keep a warning only if its reason still holds. Comment-code inconsistency predicts bugs where practice deviates (F4.3), and wrong comments cut a model's pass rate by 20.8% (F4.4). Google reviewers are told to check pre-existing comments, including ones that warn against the change. *Sources: https://sail.cs.queensu.ca/data/pdfs/JSS_OnTheRelationshipBetweenCommentUpdatePracticesAndSoftwareBugs.pdf , https://arxiv.org/abs/2609.09242 , https://google.github.io/eng-practices/review/reviewer/looking-for.html*

6. **Cite standards by name in one line each instead of restating them.** "Docstrings: Google Python style 3.8 / TSDoc / Javadoc; reference docs: Diataxis reference (describe only, link out)." State the one project-specific resolution: preconditions go in Args; Raises is for errors a correct caller can meet (F2). Cursor's guidance is to use a linter, not pasted style guides. *Sources: https://google.github.io/styleguide/pyguide.html , https://diataxis.fr/reference/ , https://cursor.com/docs/context/rules*

7. **Encode "precise, not profuse" as three questions plus one example.** Questions from DocAgent's Verifier: does each sentence add information the code lacks; does it expose implementation instead of the contract; is a critical usage fact (constraint, error trigger, side effect) missing? Add one before/after docstring pair. Examples carry style in fewer tokens than rules (F3.7). *Sources: https://raw.githubusercontent.com/facebookresearch/DocAgent/main/src/agent/verifier.py , https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices*

8. **Give the knowledge files a four-part admission test.** Not derivable from code or tests; changes how a later step or reviewer acts; costly to rediscover; likely to outlive the next refactor. Otherwise it stays in RUN notes. ADR triggers: structure, non-functional requirements, dependencies, interfaces, construction techniques; skip tiny, self-contained or temporary choices. Supersede, never rewrite. *Sources: https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions , https://docs.arc42.org/section-9/ , https://hilton.org.uk/blog/martraire-documentation-principles*

9. **Tombstone: one-line comment at the decision point plus the AD id; the AD holds the rejected option and failure.** Define the word once (it is not standard, and Bugsnag uses it for a runtime probe). Write it for a reader who cannot ask. *Sources: https://spin.atomicobject.com/chestertons-fence-code-comments/ , https://adr.github.io/madr/ , https://code.claude.com/docs/en/best-practices*

10. **Trigger and scope by user-facing surface, with a script mapping surface to doc home.** Public behaviours, CLI flags, config, errors, response shapes. Internal refactors with unchanged public behaviour get "no documentation change, reason" and no docs edit. Keep one canonical doc per topic. *Sources: https://www.mintlify.com/library/how-to-stop-documentation-drift , https://abseil.io/resources/swe-book/html/ch10.html*

11. **Evaluate prompt variants with deterministic metrics first.** Use DocAgent's split: scripted completeness and existence ratio, plus a judge decomposed per part with rubric examples. Report word counts and test the judge for length bias. Because no study sizes the effect of trimming a documentation prompt (section 6), run the A/B on the owner's harness before claiming a gain. *Sources: https://arxiv.org/abs/2504.08725 , https://arxiv.org/pdf/2604.23178*

12. **Keep verification instructions specific, because newer models over-verify.** Anthropic reports that generic "verify your work" lines can add cost on Opus 5. Observation steps ("run this command, record the output") are different and should stay. Any iteration limit on a verification loop is the owner's decision. *Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices*
