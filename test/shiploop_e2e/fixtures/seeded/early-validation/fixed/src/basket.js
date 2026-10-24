'use strict';
/** A basket holding at most `limit` items. TypeError for a bad limit; RangeError when adding to a full basket. */
class Basket {
  constructor({ limit } = {}) {
    this.limit = limit;
    this.check();
    this.items = [];
  }
  check() {
    if (!(Number.isInteger(this.limit) && this.limit > 0)) {
      throw new TypeError('Basket: limit must be a positive integer');
    }
  }
  add(item) {
    if (this.items.length >= this.limit) throw new RangeError('Basket: full');
    this.items.push(item);
    return this.items.length;
  }
}
module.exports = { Basket };
