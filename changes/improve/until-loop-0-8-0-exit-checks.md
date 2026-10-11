---
bump: minor
---
The bundled Until Loop runtime is now upstream 0.8.1 (whichguy/until-loop v0.8.1, 529a42d); its state has no size limit and exit checks have no count cap. Contracts may carry
frozen `exit_checks` written from the request before any work; each active packet prints a `verify_script` that the
executor runs as its shell command's own text (so permission prompts and hooks see every check) and that pipes the
real results into the runtime's `record` step; a satisfied report needs a fresh recorded run and every check
passing. Failed checks can be repaired (never their clauses). The runtime's state limit is 64 KiB. Contracts without
exit checks behave as before. Evidence: until-loop-lab, 374+ graded runs on Sonnet 5.5, Grok 4.7 and GPT-6.1 Sol.
