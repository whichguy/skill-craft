'use strict';
const meter = require('./meter');

const STATUSES = ['open', 'shipped'];
const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** One order per non-blank line: `id=<n>;qty=<n>;price=<cents>;status=<open|shipped>;shipped_at=<YYYY-MM-DD or empty>`. */
function parseOrders(text) {
  if (typeof text !== 'string') throw new TypeError('parseOrders: text must be a string');
  const orders = [];
  text.split('\n').forEach((raw, index) => {
    const line = index + 1;
    if (!raw.trim()) return;
    const fields = {};
    for (const part of raw.split(';')) {
      const at = part.indexOf('=');
      if (at < 0) throw new SyntaxError(`line ${line}: field without =`);
      fields[part.slice(0, at).trim()] = part.slice(at + 1).trim();
    }
    const qty = Number(fields.qty);
    if (!Number.isInteger(qty) || qty <= 0) throw new RangeError(`line ${line}: qty must be a positive integer`);
    const price = Number(fields.price);
    if (!Number.isInteger(price) || price < 0) throw new RangeError(`line ${line}: price must be whole cents`);
    const status = (fields.status || '').toLowerCase();
    if (!STATUSES.includes(status)) throw new SyntaxError(`line ${line}: unknown status`);
    const shippedAt = fields.shipped_at || '';
    if (shippedAt && !DATE.test(shippedAt)) throw new SyntaxError(`line ${line}: shipped_at is not YYYY-MM-DD`);
    if ((status === 'shipped') !== Boolean(shippedAt)) {
      throw new SyntaxError(`line ${line}: shipped needs shipped_at and open must not have one`);
    }
    orders.push({ id: Number(fields.id), qty, price, status, shippedAt });
  });
  return orders;
}

/** Sum of qty * price in cents; one meter tick per order. */
function total(orders) {
  let sum = 0;
  for (const order of orders) {
    meter.tick();
    sum += order.qty * order.price;
  }
  return sum;
}

module.exports = { parseOrders, total };
