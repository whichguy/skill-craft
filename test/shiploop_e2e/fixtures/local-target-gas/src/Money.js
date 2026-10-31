/** Round a number of currency units to cents. Throws TypeError for a non-finite number. */
function cents(amount) {
  if (!Number.isFinite(amount)) throw new TypeError('cents: amount must be a finite number');
  return Math.round(amount * 100) / 100;
}
