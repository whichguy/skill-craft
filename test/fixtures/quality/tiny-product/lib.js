'use strict';
// A comment that names a === b && true and x > 99: operators in comments are not code.
const label = "x === y || false";
function isAdult(age) { return age >= 18; }
function bucket(n) {
  if (n > 0 && n < 10) { return 'small'; }
  return 'other';
}
const spin = false;
module.exports = { isAdult, bucket, spin, label };
