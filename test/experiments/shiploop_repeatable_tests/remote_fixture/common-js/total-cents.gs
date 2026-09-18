function _main(module = globalThis.__getCurrentModule(), exports = module.exports) {
  function totalCents(quantity, unitCents) {
    [quantity, unitCents].forEach(function (value) {
      if (typeof value !== 'number') {
        throw new TypeError('quantity and unitCents must be numbers');
      }
      if (!Number.isInteger(value) || value < 0) {
        throw new RangeError('quantity and unitCents must be nonnegative integers');
      }
    });
    return quantity * unitCents;
  }

  module.exports = { totalCents };
}
__defineModule__(_main);
