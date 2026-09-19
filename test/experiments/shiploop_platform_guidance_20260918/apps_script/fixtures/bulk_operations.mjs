/**
 * A local call-count model for a spreadsheet-shaped service and a notification
 * transport. It demonstrates semantic preconditions for batching; it does not
 * measure Apps Script quota consumption or SpreadsheetApp performance.
 */

export class SyntheticQuotaError extends Error {
  constructor(limit) {
    super(`synthetic service-call budget ${limit} exceeded`);
    this.name = "SyntheticQuotaError";
  }
}

export class SyntheticQuota {
  constructor(limit) {
    this.limit = limit;
    this.calls = 0;
  }

  consume() {
    this.calls += 1;
    if (this.calls > this.limit) {
      throw new SyntheticQuotaError(this.limit);
    }
  }
}

export class GridPort {
  constructor({quota, rows, columns}) {
    this.quota = quota;
    this.grid = Array.from({length: rows}, () => Array(columns).fill(null));
  }

  setBackground(row, column, color) {
    this.quota.consume();
    this.grid[row][column] = color;
  }

  setBackgrounds(startRow, startColumn, colors) {
    this.quota.consume();
    for (let row = 0; row < colors.length; row += 1) {
      for (let column = 0; column < colors[row].length; column += 1) {
        this.grid[startRow + row][startColumn + column] = colors[row][column];
      }
    }
  }

  snapshot() {
    return this.grid.map(row => [...row]);
  }
}

// Seed: a correct result for small inputs, but one service operation per cell.
export function renderCellByCellSeed(port, colors) {
  for (let row = 0; row < colors.length; row += 1) {
    for (let column = 0; column < colors[row].length; column += 1) {
      port.setBackground(row, column, colors[row][column]);
    }
  }
}

// Reference: one contiguous write after CPU-only color calculation.
export function renderGridBatchReference(port, colors) {
  port.setBackgrounds(0, 0, colors);
}

export class NotificationPort {
  constructor() {
    this.deliveries = [];
  }

  send(recipient, message) {
    this.deliveries.push({message, recipient});
  }

  sendMany(recipients, message) {
    for (const recipient of recipients) {
      this.deliveries.push({message, recipient});
    }
  }
}

export function sendDistinctNotificationsReference(port, events) {
  for (const event of events) {
    port.send(event.recipient, event.message);
  }
}

// Mutant: assumes messages can be collapsed merely because there is more than
// one destination, destroying event-specific payloads.
export function blindNotificationBatchMutant(port, events) {
  port.sendMany(
    events.map(event => event.recipient),
    events[0].message,
  );
}
