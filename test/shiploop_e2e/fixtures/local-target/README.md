# local-target-shop

Code runs from a deployed target, a folder that keeps state between commands (`LOCAL_TARGET`). `node scripts/deploy.js` copies src/ over it and removes nothing; `--clean` empties it first. Tests load modules from the target (test/deployed.js). `npm test` deploys and then runs node:test.
