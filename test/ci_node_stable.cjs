'use strict';

function requireStable(version) {
  if (typeof version !== 'string' || !/^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version)) {
    throw new Error(`CI requires a stable Node runtime; got ${version}`);
  }
  return version;
}

module.exports = requireStable;
if (require.main === module) {
  console.log(`Stable Node runtime: ${requireStable(process.version)}`);
}
