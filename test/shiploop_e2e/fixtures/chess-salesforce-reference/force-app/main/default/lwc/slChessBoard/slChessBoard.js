import { LightningElement } from 'lwc';
import legalMoves from '@salesforce/apex/SLChessController.legalMoves';
import applyMove from '@salesforce/apex/SLChessController.applyMove';
import status from '@salesforce/apex/SLChessController.status';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const FILES = 'abcdefgh';
// The solid glyphs for both colours; the colour comes from the CSS class. U+FE0E asks for text, not emoji, presentation.
const GLYPHS = { k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟︎' };
const NAMES = { k: 'king', q: 'queen', r: 'rook', b: 'bishop', n: 'knight', p: 'pawn' };

// The 8 ranks of a FEN placement field, rank 8 first, as arrays of 8 piece letters ('' for an empty square).
function parseBoard(fen) {
    return fen.split(' ')[0].split('/').map((row) => {
        const cells = [];
        for (const ch of row) {
            if (ch >= '1' && ch <= '8') {
                for (let i = 0; i < Number(ch); i++) {
                    cells.push('');
                }
            } else {
                cells.push(ch);
            }
        }
        return cells;
    });
}

function errorText(error) {
    return (error && error.body && error.body.message) || (error && error.message) || 'Something went wrong.';
}

export default class SlChessBoard extends LightningElement {
    fen = START_FEN;
    moves = [];
    gameStatus = 'ongoing';
    selected = null;
    targets = [];
    message = '';
    busy = false;

    connectedCallback() {
        this.startGame();
    }

    get turn() {
        return this.fen.split(' ')[1] === 'w' ? 'White' : 'Black';
    }

    get isOver() {
        return this.gameStatus === 'checkmate' || this.gameStatus === 'stalemate';
    }

    get statusText() {
        if (this.gameStatus === 'checkmate') {
            return 'Checkmate. ' + (this.turn === 'White' ? 'Black' : 'White') + ' wins.';
        }
        if (this.gameStatus === 'stalemate') {
            return 'Stalemate. The game is a draw.';
        }
        return this.turn + ' to move' + (this.gameStatus === 'check' ? ' and in check.' : '.');
    }

    get squares() {
        const board = parseBoard(this.fen);
        const squares = [];
        for (let r = 0; r < 8; r++) {
            for (let f = 0; f < 8; f++) {
                const id = FILES[f] + (8 - r);
                const piece = board[r][f];
                const classes = ['square', (r + f) % 2 === 0 ? 'light' : 'dark'];
                if (piece) {
                    classes.push(piece === piece.toUpperCase() ? 'white-piece' : 'black-piece');
                }
                if (id === this.selected) {
                    classes.push('selected');
                }
                if (this.targets.includes(id)) {
                    classes.push(piece ? 'capture' : 'target');
                }
                const lower = piece.toLowerCase();
                squares.push({
                    id,
                    glyph: piece ? GLYPHS[lower] : '',
                    className: classes.join(' '),
                    label: id + (piece ? ' ' + (piece === piece.toUpperCase() ? 'white ' : 'black ') + NAMES[lower] : ' empty')
                });
            }
        }
        return squares;
    }

    pieceAt(square) {
        return parseBoard(this.fen)[8 - Number(square[1])][FILES.indexOf(square[0])];
    }

    isOwn(piece) {
        return piece !== '' && (piece === piece.toUpperCase()) === (this.turn === 'White');
    }

    async startGame() {
        this.fen = START_FEN;
        this.message = '';
        await this.refresh();
    }

    // Asks the server for the legal moves and the status of the current position and clears the selection.
    async refresh() {
        try {
            const [moves, state] = await Promise.all([legalMoves({ fen: this.fen }), status({ fen: this.fen })]);
            this.moves = moves;
            this.gameStatus = state;
        } catch (error) {
            this.moves = [];
            this.message = errorText(error);
        }
        this.selected = null;
        this.targets = [];
    }

    handleNewGame() {
        this.startGame();
    }

    handleSquareClick(event) {
        if (this.busy) {
            return;
        }
        const square = event.currentTarget.dataset.square;
        if (this.isOver) {
            this.message = 'The game is over. Start a new game.';
            return;
        }
        if (this.selected === null) {
            this.selectSquare(square);
        } else if (square === this.selected) {
            this.selected = null;
            this.targets = [];
            this.message = '';
        } else if (this.targets.includes(square)) {
            this.play(this.selected, square);
        } else if (this.isOwn(this.pieceAt(square))) {
            this.selectSquare(square);
        } else {
            this.message = 'Illegal move: ' + this.selected + ' to ' + square + '.';
            this.selected = null;
            this.targets = [];
        }
    }

    selectSquare(square) {
        if (!this.isOwn(this.pieceAt(square))) {
            this.message = 'Pick one of ' + this.turn + "'s pieces.";
            return;
        }
        const targets = this.moves.filter((move) => move.startsWith(square)).map((move) => move.substring(2, 4));
        if (targets.length === 0) {
            this.message = 'That piece has no legal move.';
            return;
        }
        this.selected = square;
        this.targets = [...new Set(targets)];
        this.message = '';
    }

    // A pawn reaching the last rank promotes to a queen.
    async play(from, to) {
        const promotion = this.moves.includes(from + to + 'q') ? 'q' : '';
        this.busy = true;
        try {
            this.fen = await applyMove({ fen: this.fen, move: from + to + promotion });
            this.message = '';
            await this.refresh();
        } catch (error) {
            this.message = errorText(error);
            this.selected = null;
            this.targets = [];
        } finally {
            this.busy = false;
        }
    }
}
