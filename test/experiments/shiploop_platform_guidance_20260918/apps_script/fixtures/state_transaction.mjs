/**
 * Local model of a state-changing operation with durable receipts, an advisory
 * cache, and a scoped mutex. It exercises the guidance shape only; it is not a
 * substitute for LockService, PropertiesService, or CacheService.
 */

export class DurableStore {
  constructor() {
    this.value = 0;
    this.receipts = new Map();
    this.commits = [];
  }

  async getReceipt(id) {
    const receipt = this.receipts.get(id);
    return receipt ? {...receipt} : undefined;
  }

  async readValue() {
    return this.value;
  }

  async commit(id, nextValue, receipt) {
    this.value = nextValue;
    this.receipts.set(id, {...receipt});
    this.commits.push({id, nextValue});
  }

  snapshot() {
    return {
      commitCount: this.commits.length,
      receiptIds: [...this.receipts.keys()].sort(),
      value: this.value,
    };
  }
}

export class VolatileCache {
  constructor() {
    this.values = new Map();
  }

  clear() {
    this.values.clear();
  }

  get(key) {
    return this.values.get(key);
  }

  put(key, value) {
    this.values.set(key, value);
  }
}

export class AsyncMutex {
  #tail = Promise.resolve();

  async run(work) {
    let release;
    const previous = this.#tail;
    this.#tail = new Promise(resolve => {
      release = resolve;
    });
    await previous;
    try {
      return await work();
    } finally {
      release();
    }
  }
}

export class StateReference {
  constructor({cache, lock, store}) {
    this.cache = cache;
    this.lock = lock;
    this.store = store;
  }

  async apply({delta, id}) {
    return this.lock.run(async () => {
      const oldReceipt = await this.store.getReceipt(id);
      if (oldReceipt) {
        return {...oldReceipt, replayed: true};
      }

      const before = await this.store.readValue();
      await Promise.resolve();
      const receipt = {id, value: before + delta};
      await this.store.commit(id, receipt.value, receipt);
      this.cache.put("latest-value", receipt.value);
      return {...receipt, replayed: false};
    });
  }

  async readAuthoritativeValue() {
    const value = await this.store.readValue();
    this.cache.put("latest-value", value);
    return value;
  }
}

// Plausible seed: shared state with no serialization of read-modify-write.
export class NoLockSeed {
  constructor({cache, store}) {
    this.cache = cache;
    this.store = store;
  }

  async apply({delta, id}) {
    const oldReceipt = await this.store.getReceipt(id);
    if (oldReceipt) {
      return {...oldReceipt, replayed: true};
    }
    const before = await this.store.readValue();
    await Promise.resolve();
    const receipt = {id, value: before + delta};
    await this.store.commit(id, receipt.value, receipt);
    this.cache.put("latest-value", receipt.value);
    return {...receipt, replayed: false};
  }
}

// Mutant: treats cache entries as durable state and idempotency evidence.
export class CacheAuthorityMutant {
  constructor({cache, store}) {
    this.cache = cache;
    this.store = store;
  }

  async apply({delta, id}) {
    const cacheKey = `receipt:${id}`;
    const oldReceipt = this.cache.get(cacheKey);
    if (oldReceipt) {
      return {...oldReceipt, replayed: true};
    }
    const before = this.cache.get("latest-value") ?? 0;
    const receipt = {id, value: before + delta};
    this.cache.put("latest-value", receipt.value);
    this.cache.put(cacheKey, receipt);
    return {...receipt, replayed: false};
  }
}

export class AlwaysBusyLock {
  async run() {
    throw new Error("lock unavailable");
  }
}

export function formatReadReference(input) {
  return String(input).trim().toUpperCase();
}

// Mutant: puts a pure transformation behind a lock even though it owns no
// shared state, changing a valid request into an avoidable operational failure.
export class BlanketLockMutant {
  constructor(lock) {
    this.lock = lock;
  }

  async format(input) {
    return this.lock.run(() => formatReadReference(input));
  }
}
