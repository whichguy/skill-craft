'use strict';

// A missing or ambiguous host match never authorizes a new launch.
module.exports = function resolveLookup(expectedTaskName, inventory) {
  const matches = inventory.filter((item) => item.agent_name === expectedTaskName);
  if (matches.length !== 1) {
    return {
      action: 'reconcile',
      reason: matches.length === 0 ? 'missing native task' : 'ambiguous native task',
      matches: matches.length,
    };
  }
  return { action: 'record-handle', handle: matches[0].agent_name, matches: 1 };
};
