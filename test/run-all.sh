#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
status=0
for t in \
  test/skill-interop-frontmatter.test.js \
  test/skill-interop-hygiene.test.sh \
  test/scaffold-skill.test.sh \
  test/marketplace-run.test.sh \
  test/install-targets.test.sh
do
  if [[ ! -e "$root/$t" ]]; then
    echo "SKIP missing $t"
    continue
  fi
  if [[ "$t" == *.js ]]; then
    if node "$root/$t"; then echo "PASS $t"; else echo "FAIL $t"; status=1; fi
  else
    if bash "$root/$t"; then echo "PASS $t"; else echo "FAIL $t"; status=1; fi
  fi
done
exit "$status"
