'use strict';

/**
 * Return page `page` (1-based) of `items`, `size` items per page, with the page count.
 */
function paginate(items, page, size) {
  if (!Array.isArray(items)) throw new TypeError('items must be an array');
  if (!Number.isInteger(size) || size < 1) throw new RangeError('size must be a positive integer');
  if (!Number.isInteger(page) || page < 1) throw new RangeError('page must be a positive integer');
  const pages = Math.ceil(items.length / size);
  const start = (page - 1) * size;
  return { page, pages, items: page <= pages ? items.slice(start, start + size) : [] };
}

module.exports = { paginate };
