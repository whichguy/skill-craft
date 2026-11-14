You are the parent agent of an orchestration probe. Nothing here is real work: each step is a small script that waits and writes a file. What is observed is how you carry out the plan. Use only the commands given here.

Plan: /private/tmp/claude-501/-Users-dadleet--claude-spares-spare-N8s753/664029b2-b8c1-4b45-89d1-8c7c3eff8a14/scratchpad/ppe-trials/e1-codex/work/plan.json (JSON; each step has an id and deps, the ids of the steps that must have finished before it starts). Kit: python3 /private/tmp/claude-501/-Users-dadleet--claude-spares-spare-N8s753/664029b2-b8c1-4b45-89d1-8c7c3eff8a14/scratchpad/ppe-trials/e1-codex/work/dagkit.py. Run directory: /private/tmp/claude-501/-Users-dadleet--claude-spares-spare-N8s753/664029b2-b8c1-4b45-89d1-8c7c3eff8a14/scratchpad/ppe-trials/e1-codex/work/run.

Hand each step to its own fresh sub-agent, one at a time:
1. Read the plan.
2. Choose a step whose deps have all finished. Start one fresh sub-agent for it, using your built-in facility for starting an agent with its own context. A sub-agent starts with no memory of this conversation, so give it the whole instruction. Its only job is to run exactly `python3 /private/tmp/claude-501/-Users-dadleet--claude-spares-spare-N8s753/664029b2-b8c1-4b45-89d1-8c7c3eff8a14/scratchpad/ppe-trials/e1-codex/work/dagkit.py run --run /private/tmp/claude-501/-Users-dadleet--claude-spares-spare-N8s753/664029b2-b8c1-4b45-89d1-8c7c3eff8a14/scratchpad/ppe-trials/e1-codex/work/run --step <ID>` and reply with the one line it prints.
3. Wait until that sub-agent has returned before you start the next one. Never have two sub-agents at the same time. Do not run steps yourself and do not use background jobs.
4. Repeat until every step that can run has finished.
5. Run: python3 /private/tmp/claude-501/-Users-dadleet--claude-spares-spare-N8s753/664029b2-b8c1-4b45-89d1-8c7c3eff8a14/scratchpad/ppe-trials/e1-codex/work/dagkit.py verify --run /private/tmp/claude-501/-Users-dadleet--claude-spares-spare-N8s753/664029b2-b8c1-4b45-89d1-8c7c3eff8a14/scratchpad/ppe-trials/e1-codex/work/run
6. End with one last line, exactly in this form: FINAL {"done":[step ids],"failed":[step ids],"not_run":[step ids]}
