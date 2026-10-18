import { LightningElement } from 'lwc';
import newGame from '@salesforce/apex/SLBattleController.newGame';
import fire from '@salesforce/apex/SLBattleController.fire';

const GRID = 10;
const SEED_RANGE = 2147483646;

function errorText(error) {
    return (error && error.body && error.body.message) || (error && error.message) || 'Something went wrong.';
}

export default class SlBattleBoard extends LightningElement {
    game = null;
    state = null;
    message = '';
    busy = false;

    connectedCallback() {
        this.startGame();
    }

    async startGame() {
        this.busy = true;
        this.message = '';
        try {
            this.game = await newGame({ seed: Math.floor(Math.random() * SEED_RANGE) + 1 });
            this.state = JSON.parse(this.game);
        } catch (error) {
            this.message = errorText(error);
        } finally {
            this.busy = false;
        }
    }

    handleNewGame() {
        this.startGame();
    }

    async handleCellClick(event) {
        const row = Number(event.currentTarget.dataset.row);
        const col = Number(event.currentTarget.dataset.col);
        if (this.busy || !this.state || this.state.gameOver || this.fired.has(row * GRID + col)) {
            return;
        }
        this.busy = true;
        try {
            this.game = await fire({ game: this.game, row, col });
            this.state = JSON.parse(this.game);
            this.message = '';
        } catch (error) {
            this.message = errorText(error);
        } finally {
            this.busy = false;
        }
    }

    get ships() {
        return this.state ? this.state.ships : [];
    }

    get fired() {
        return new Set(this.state ? this.state.fired : []);
    }

    // The grid, row by row: a cell shows open water, a miss, a hit or a sunk ship; an unhit ship cell looks like open water.
    get rows() {
        const fired = this.fired;
        const hit = new Set();
        const sunk = new Set();
        for (const ship of this.ships) {
            const down = ship.hits === ship.cells.length;
            for (const cell of ship.cells) {
                if (fired.has(cell)) {
                    (down ? sunk : hit).add(cell);
                }
            }
        }
        const over = this.gameOver;
        const rows = [];
        for (let row = 0; row < GRID; row++) {
            const cells = [];
            for (let col = 0; col < GRID; col++) {
                const cell = row * GRID + col;
                let status = 'open';
                if (sunk.has(cell)) {
                    status = 'sunk';
                } else if (hit.has(cell)) {
                    status = 'hit';
                } else if (fired.has(cell)) {
                    status = 'miss';
                }
                cells.push({
                    id: 'cell-' + cell,
                    row,
                    col,
                    className: 'cell ' + status,
                    label: 'Row ' + (row + 1) + ', column ' + (col + 1) + ': ' + (status === 'open' ? 'not fired at' : status),
                    glyph: status === 'open' ? '' : status === 'miss' ? '·' : '✕',
                    disabled: over || status !== 'open'
                });
            }
            rows.push({ id: 'row-' + row, cells });
        }
        return rows;
    }

    get shots() {
        return this.state ? this.state.shots : 0;
    }

    get shipsLeft() {
        return this.state ? this.state.shipsLeft : 0;
    }

    get gameOver() {
        return Boolean(this.state && this.state.gameOver);
    }

    get sunkText() {
        const names = this.ships.filter((ship) => ship.hits === ship.cells.length).map((ship) => ship.name);
        return names.length ? 'Sunk: ' + names.join(', ') + '.' : 'No ship sunk yet.';
    }

    get statusText() {
        if (!this.state) {
            return 'Placing the fleet...';
        }
        if (this.state.gameOver) {
            return 'Game over: every ship is sunk, in ' + this.state.shots + ' shots.';
        }
        const last = this.state.lastShot;
        if (!last) {
            return 'Fire at a cell.';
        }
        if (last.result === 'sunk') {
            return 'You sank the ' + last.ship + '.';
        }
        return last.result === 'hit' ? 'Hit.' : 'Miss.';
    }
}
