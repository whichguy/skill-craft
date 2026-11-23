'use strict';
/** Clamped keyboard index movement for the choice widget (initial W1/S1 helper). */
function nextChoiceIndex(current, key, count) {
  if (!Number.isInteger(count) || count <= 0) return -1;
  if (!Number.isInteger(current)) return 0;
  if (key === 'ArrowRight') return Math.min(count - 1, current + 1);
  if (key === 'ArrowLeft') return Math.max(0, current - 1);
  return Math.max(0, Math.min(count - 1, current));
}
if (typeof module !== 'undefined') module.exports = { nextChoiceIndex };
