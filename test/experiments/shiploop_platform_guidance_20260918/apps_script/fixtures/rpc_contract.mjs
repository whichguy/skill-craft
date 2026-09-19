/**
 * A deliberately incomplete local model of the public google.script.run
 * contract. It is a test seam, not an Apps Script emulator.
 */

export class RpcContractError extends Error {
  constructor(message) {
    super(message);
    this.name = "RpcContractError";
  }
}

function copyWireValue(value, seen = new Set(), arrayMember = false) {
  if (value === undefined) {
    return arrayMember ? null : undefined;
  }

  if (value === null || ["string", "number", "boolean"].includes(typeof value)) {
    return value;
  }

  if (value instanceof Date) {
    throw new RpcContractError("Date is not a legal RPC value");
  }

  if (typeof value === "function") {
    throw new RpcContractError("Function is not a legal RPC value");
  }

  if (typeof value !== "object") {
    throw new RpcContractError(`Unsupported RPC value: ${typeof value}`);
  }

  if (seen.has(value)) {
    throw new RpcContractError("Circular RPC value");
  }

  seen.add(value);
  try {
    if (Array.isArray(value)) {
      return value.map(item => copyWireValue(item, seen, true));
    }

    const copy = {};
    for (const [key, item] of Object.entries(value)) {
      const copied = copyWireValue(item, seen, false);
      if (copied !== undefined) {
        copy[key] = copied;
      }
    }
    return copy;
  } finally {
    seen.delete(value);
  }
}

export function createReferenceRpcCall(serverFunction) {
  return async (...clientArgs) => {
    const copiedArgs = clientArgs.map(value => copyWireValue(value));
    await Promise.resolve();
    const serverResult = await serverFunction(...copiedArgs);
    return copyWireValue(serverResult);
  };
}

function makeRunner(serverFunctions, handlers) {
  return new Proxy(
    {
      withFailureHandler(handler) {
        return makeRunner(serverFunctions, {...handlers, failure: handler});
      },
      withSuccessHandler(handler) {
        return makeRunner(serverFunctions, {...handlers, success: handler});
      },
    },
    {
      get(target, property) {
        if (property in target) {
          return target[property];
        }
        if (typeof property !== "string") {
          return undefined;
        }
        return (...args) => {
          const serverFunction = serverFunctions[property];
          void Promise.resolve()
            .then(async () => {
              if (typeof serverFunction !== "function") {
                throw new Error(`No exposed server function named ${property}`);
              }
              const copiedArgs = args.map(value => copyWireValue(value));
              const result = await serverFunction(...copiedArgs);
              return copyWireValue(result);
            })
            .then(result => handlers.success?.(result))
            .catch(error => handlers.failure?.(error));
          return undefined;
        };
      },
    },
  );
}

export function createReferenceRunner(serverFunctions) {
  return makeRunner(serverFunctions, {});
}

// Plausible starting implementation: a direct local function call. It is useful
// for a unit test but does not preserve the RPC boundary or asynchronous return.
export function createDirectCallSeed(serverFunction) {
  return (...args) => serverFunction(...args);
}

// Plausible but unsafe mutant: it passes host-only values through unchanged.
export function createUnsafeWireMutant(serverFunction) {
  return async (...args) => serverFunction(...args);
}
