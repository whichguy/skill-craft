# Current check evidence

All product checks below were read-only and ran in
`<study>/candidate-dependent/product`.
They establish only the controlled archive/source boundary. They do not prove a
browser reload journey, target identity behavior, service behavior, deployment,
or draft persistence.

## First Improve review

1. History attempt required for this review:

   ```sh
   git -C <study>/candidate-dependent/product log -7 --format=fuller
   ```

   Result: exit 128, `fatal: not a git repository (or any of the parent directories): .git`.
   This is expected for the fixture archive. No Git repository was initialized;
   commit history therefore cannot inform this review.

2. Controlled environment probe:

   ```sh
   python3 scripts/probe_environment.py
   ```

   Result: exit 0.

   ```json
   {"client_persistent_storage":"unavailable","draft_api":false,"observation_scope":"controlled fixture target facts; not a live deployment","observation_sha256":"40a3900ae08cf109734f411f62c8a89dbd5fae84c5f04d127ff000ea3038c878","script_src":["self"],"server_runtime":false,"style_src":["self"],"target":"fieldnotes-embedded-v2","websocket":false}
   ```

   The required durable draft carrier and target-browser verification route stay
   unavailable.

3. Existing smoke syntax check:

   ```sh
   node --check app.js
   ```

   Result: exit 0; stdout empty.

4. Source/contract boundary assertion:

   ```sh
   node - <<'NODE'
   const fs = require('fs');
   const app = fs.readFileSync('app.js', 'utf8');
   const api = fs.readFileSync('docs/api.md', 'utf8');
   const plan = fs.readFileSync('../evidence/step-plan-W1.md', 'utf8');
   if (!app.includes('function noteUrl(account, id)') || !app.includes('baseRevision: recordAtSave.revision')) throw new Error('Observed note-save source behavior is incomplete.');
   if (!api.includes('No subscription or draft-storage endpoint is available.') || api.includes('/api/accounts/')) throw new Error('API-document boundary differs from the reviewed plan premise.');
   if (!plan.includes('product/docs/api.md has note-save and export contracts')) throw new Error('The original plan premise under review is absent.');
   console.log('PASS: app.js observes an account-note request and revision-bearing save, while docs/api.md documents exports and explicitly denies a draft-storage endpoint; it does not document the account-note endpoint.');
   NODE
   ```

   Result: exit 0; printed the stated PASS line.

5. Harness inventory:

   ```sh
   rg --files -g package.json -g package-lock.json -g npm-shrinkwrap.json -g yarn.lock -g pnpm-lock.yaml -g '*test*' -g '*spec*' .
   ```

   Result: no matching paths (the raw `rg` exit is 1 for no matches). The
   product has no package manifest, lockfile, test/spec file, or registered
   executable test runner. No dependency or test framework was installed.

6. Ownership/content recheck:

   ```sh
   find product -type f -not -path 'product/.shiploop-improve/*' -exec shasum -a 256 {} \; | LC_ALL=C sort | shasum -a 256
   ```

   Result: `4a7deedd123a8c64ca649ab7e4f747809cfdd597d94b53895cee1df1c23ac898`,
   matching the frozen pre-child product identity. Only this child evidence tree
   was added.

### Preliminary non-counting command correction

Before the child started, a first ad hoc assertion mistakenly treated the
documented phrase `draft-storage endpoint` as evidence that the API document
had changed. That assertion exited nonzero and was not used as evidence. The
corrected boundary assertion above explicitly requires that documented negative
phrase and passed. No product defect, source edit, or review count was inferred
from the malformed preliminary command.

## Second Improve review

1. History attempt:

   ```sh
   git -C <study>/candidate-dependent/product log -7 --format=fuller
   ```

   Result: exit 128, `fatal: not a git repository (or any of the parent directories): .git`.
   The archive still has no reachable history and was not initialized.

2. Final current-check sequence:

   ```sh
   python3 scripts/probe_environment.py
   node --check app.js
   node - <<'NODE'
   // Checks original plan hash, observed app note behavior, docs/api.md's
   // export-only/no-draft boundary, and the first review's correction text.
   NODE
   ```

   Result: all commands exit 0. The probe remains
   `fieldnotes-embedded-v2` with `client_persistent_storage: unavailable`,
   `draft_api: false`, and `server_runtime: false`. The assertion printed:

   ```text
   PASS: original plan is preserved; current source still exposes only observed note behavior; API documentation remains export-only/no-draft-storage; material correction preserves the primary blocked carrier prerequisite.
   ```

3. Harness and archive checks:

   ```sh
   rg --files -g package.json -g package-lock.json -g npm-shrinkwrap.json -g yarn.lock -g pnpm-lock.yaml -g '*test*' -g '*spec*' .
   find .. -maxdepth 1 -name '.git' -print
   ```

   Result: no matching harness paths (the raw `rg` exit is 1 for no matches),
   and no Git metadata was introduced. No dependency or test framework was
   installed.

4. Content identity:

   ```sh
   find product -type f -not -path 'product/.shiploop-improve/*' -exec shasum -a 256 {} \; | LC_ALL=C sort | shasum -a 256
   ```

   Result: `4a7deedd123a8c64ca649ab7e4f747809cfdd597d94b53895cee1df1c23ac898`,
   still the frozen product identity outside this child evidence tree.

### Second-review assertion correction

The first version of the second-review assertion looked for the exact contiguous
phrase `source code is not an accepted target API contract`. The review record
wraps that sentence across Markdown lines, so the assertion exited nonzero even
though the review record contained the intended statement. The corrected
read-only assertion checks the stable phrase `accepted target API contract` and
passed. This was an ad hoc diagnostic-script defect, not a product, plan, or
test-suite failure; no candidate change or review count was inferred from its
failed preliminary run.

## Third Improve review

1. History attempt:

   ```sh
   git -C <study>/candidate-dependent/product log -7 --format=fuller
   ```

   Result: exit 128, `fatal: not a git repository (or any of the parent directories): .git`.
   The fixture remains a Git archive; no history was invented and Git was not
   initialized.

2. Current candidate and correction checks:

   ```sh
   python3 scripts/probe_environment.py
   node --check app.js
   node - <<'NODE'
   // Checks original plan hash; observed note route/revision/payload shape;
   // docs/api.md's export-only/no-draft boundary; and review-one/review-two.
   NODE
   ```

   Result: all commands exit 0. The assertion printed:

   ```text
   PASS: frozen source and primary blocker are unchanged; the material plan correction remains accurate; the first qualifying review has no unresolved evidence gap.
   ```

   The probe again reports `fieldnotes-embedded-v2`,
   `client_persistent_storage: unavailable`, `draft_api: false`, and
   `server_runtime: false`.

3. Boundary/receipt checks:

   ```sh
   rg --files -g package.json -g package-lock.json -g npm-shrinkwrap.json -g yarn.lock -g pnpm-lock.yaml -g '*test*' -g '*spec*' .
   test ! -e .git
   python3 - <<'PY'
   # Parses packet.json and checks active status plus trivial_streak == 1.
   PY
   ```

   Result: no harness paths (raw `rg` exit 1 for no matches); no Git metadata;
   and the saved latest packet parsed as active JSON with one qualifying review.
   No dependency/test framework was installed.

4. Content identity:

   ```sh
   find product -type f -not -path 'product/.shiploop-improve/*' -exec shasum -a 256 {} \; | LC_ALL=C sort | shasum -a 256
   ```

   Result: `4a7deedd123a8c64ca649ab7e4f747809cfdd597d94b53895cee1df1c23ac898`,
   matching the frozen product identity. Only child review/receipt artifacts
   exist under `.shiploop-improve`.
