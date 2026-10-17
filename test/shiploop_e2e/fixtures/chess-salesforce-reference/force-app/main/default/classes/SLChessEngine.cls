/**
 * Chess rules engine. A position is a FEN string and every public method is a function of its arguments, so there is
 * no state to reset between calls.
 *
 * Inside, a position is a List<Integer> of CELLS cells. Cells 0..119 are a 10 x 12 mailbox board: square a1 is cell 21,
 * h1 is 28, a8 is 91 and h8 is 98, so one rank is 10 cells, a step in any direction is a constant offset, and every cell
 * outside the 64 squares holds OFFBOARD, which stops every ray and every step without a bounds test. A piece is its
 * type (PAWN..KING, 1..6) for White and the type plus 6 for Black; 0 is an empty square. Cells 120 and up hold the rest
 * of the FEN: the side to move, the four castling rights (0 or 1), the en passant target cell (0 for none), the two
 * clocks and the cell of each king.
 *
 * A move is three Integers (from cell, to cell, promotion type or 0) appended to a flat List<Integer>. Moves are
 * generated pseudo-legally, then kept only if the mover's king is not attacked after playing the move on a copy of the
 * position. UCI text is built only for the moves that are returned. No SOQL, no DML, no recursion.
 */
public class SLChessEngine {
    public class IllegalMoveException extends Exception {}

    private static final String START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    private static final String PIECE_CHARS = '.PNBRQKpnbrqk';
    private static final String FILES = 'abcdefgh';
    private static final String RANKS = '12345678';
    private static final String PROMOTION_IN = 'nbrq';
    private static final String PROMOTION_OUT = '..nbrq';

    private static final Integer PAWN = 1;
    private static final Integer KNIGHT = 2;
    private static final Integer BISHOP = 3;
    private static final Integer ROOK = 4;
    private static final Integer QUEEN = 5;
    private static final Integer KING = 6;
    private static final Integer OFFBOARD = 13;

    private static final Integer SIDE = 120;
    private static final Integer CASTLE_WK = 121;
    private static final Integer CASTLE_WQ = 122;
    private static final Integer CASTLE_BK = 123;
    private static final Integer CASTLE_BQ = 124;
    private static final Integer EP_SQUARE = 125;
    private static final Integer HALFMOVES = 126;
    private static final Integer FULLMOVES = 127;
    private static final Integer KING_WHITE = 128;
    private static final Integer KING_BLACK = 129;
    private static final Integer CELLS = 130;

    private static final List<Integer> KNIGHT_STEPS = new List<Integer>{ -21, -19, -12, -8, 8, 12, 19, 21 };
    private static final List<Integer> KING_STEPS = new List<Integer>{ -11, -10, -9, -1, 1, 9, 10, 11 };
    private static final List<Integer> DIAGONAL = new List<Integer>{ -11, -9, 9, 11 };
    private static final List<Integer> STRAIGHT = new List<Integer>{ -10, -1, 1, 10 };

    private static final List<String> SQ_NAMES = buildNames();
    private static final List<Integer> EMPTY_POSITION = buildEmpty();

    public static String startFen() {
        return START_FEN;
    }

    public static List<String> legalMoves(String fen) {
        List<Integer> pos = parse(fen);
        List<Integer> legal = legalTriples(pos, false);
        List<String> uci = new List<String>();
        for (Integer i = 0; i < legal.size(); i += 3) {
            uci.add(uciOf(legal.get(i), legal.get(i + 1), legal.get(i + 2)));
        }
        uci.sort();
        return uci;
    }

    public static String applyMove(String fen, String move) {
        List<Integer> pos = parse(fen);
        if (move == null || (move.length() != 4 && move.length() != 5)) {
            throw illegal(move);
        }
        Integer fromSq = squareOf(move.substring(0, 2));
        Integer toSq = squareOf(move.substring(2, 4));
        Integer promo = 0;
        if (move.length() == 5) {
            Integer letter = PROMOTION_IN.indexOf(move.substring(4, 5));
            if (letter < 0) {
                throw illegal(move);
            }
            promo = letter + 2;
        }
        if (fromSq < 0 || toSq < 0) {
            throw illegal(move);
        }
        List<Integer> pseudo = new List<Integer>();
        pseudoMoves(pos, pseudo);
        Boolean found = false;
        for (Integer i = 0; i < pseudo.size(); i += 3) {
            if (pseudo.get(i) == fromSq && pseudo.get(i + 1) == toSq && pseudo.get(i + 2) == promo) {
                found = true;
                break;
            }
        }
        if (!found) {
            throw illegal(move);
        }
        Boolean white = pos.get(SIDE) == 0;
        Integer piece = pos.get(fromSq);
        Integer kind = white ? piece : piece - 6;
        List<Integer> moved = new List<Integer>(pos);
        Integer captured = play(moved, fromSq, toSq, promo);
        if (attacked(moved, moved.get(white ? KING_WHITE : KING_BLACK), white ? 6 : 0)) {
            throw illegal(move);
        }
        // A right is lost when its king or rook moves, and when anything lands on the rook's square (the rook was captured).
        if (fromSq == 25 || toSq == 25) {
            moved.set(CASTLE_WK, 0);
            moved.set(CASTLE_WQ, 0);
        }
        if (fromSq == 95 || toSq == 95) {
            moved.set(CASTLE_BK, 0);
            moved.set(CASTLE_BQ, 0);
        }
        if (fromSq == 28 || toSq == 28) {
            moved.set(CASTLE_WK, 0);
        }
        if (fromSq == 21 || toSq == 21) {
            moved.set(CASTLE_WQ, 0);
        }
        if (fromSq == 98 || toSq == 98) {
            moved.set(CASTLE_BK, 0);
        }
        if (fromSq == 91 || toSq == 91) {
            moved.set(CASTLE_BQ, 0);
        }
        // The en passant target is set after every two-square pawn push, whether or not an enemy pawn could capture.
        Boolean doublePush = kind == PAWN && (toSq - fromSq == 20 || toSq - fromSq == -20);
        moved.set(EP_SQUARE, doublePush ? (white ? fromSq + 10 : fromSq - 10) : 0);
        moved.set(HALFMOVES, (kind == PAWN || captured != 0) ? 0 : pos.get(HALFMOVES) + 1);
        moved.set(FULLMOVES, white ? pos.get(FULLMOVES) : pos.get(FULLMOVES) + 1);
        moved.set(SIDE, white ? 1 : 0);
        return format(moved);
    }

    public static String status(String fen) {
        List<Integer> pos = parse(fen);
        Boolean white = pos.get(SIDE) == 0;
        Boolean inCheck = attacked(pos, pos.get(white ? KING_WHITE : KING_BLACK), white ? 6 : 0);
        Boolean canMove = legalTriples(pos, true).size() > 0;
        if (canMove) {
            return inCheck ? 'check' : 'ongoing';
        }
        return inCheck ? 'checkmate' : 'stalemate';
    }

    // ---------------------------------------------------------------------------------------------- move generation

    // Appends every pseudo-legal move of the side to move to out: the moves legal except that they may leave the mover's king
    // attacked. Castling is the exception: it is checked completely here, because it depends on squares the king passes.
    private static void pseudoMoves(List<Integer> pos, List<Integer> out) {
        Boolean white = pos.get(SIDE) == 0;
        Integer shift = white ? 0 : 6;
        Integer foeLo = white ? 7 : 1;
        Integer foeHi = white ? 12 : 6;
        Integer forward = white ? 10 : -10;
        Integer epSq = pos.get(EP_SQUARE);
        for (Integer sq = 21; sq <= 98; sq++) {
            Integer piece = pos.get(sq);
            if (piece == 0 || piece > 12 || (white && piece > 6) || (!white && piece <= 6)) {
                continue;
            }
            Integer kind = piece - shift;
            if (kind == PAWN) {
                Integer one = sq + forward;
                if (pos.get(one) == 0) {
                    addPawnMove(out, sq, one, white);
                    Boolean onStart = white ? (sq >= 31 && sq <= 38) : (sq >= 81 && sq <= 88);
                    if (onStart && pos.get(one + forward) == 0) {
                        addMove(out, sq, one + forward, 0);
                    }
                }
                for (Integer dx = -1; dx <= 1; dx += 2) {
                    Integer target = one + dx;
                    Integer occupant = pos.get(target);
                    Boolean captures = occupant >= foeLo && occupant <= foeHi;
                    Boolean enPassant = target == epSq && occupant == 0 && pos.get(target - forward) == foeLo;
                    if (captures || enPassant) {
                        addPawnMove(out, sq, target, white);
                    }
                }
            } else if (kind == KNIGHT || kind == KING) {
                List<Integer> steps = kind == KNIGHT ? KNIGHT_STEPS : KING_STEPS;
                for (Integer i = 0; i < 8; i++) {
                    Integer target = sq + steps.get(i);
                    Integer occupant = pos.get(target);
                    if (occupant == 0 || (occupant >= foeLo && occupant <= foeHi)) {
                        addMove(out, sq, target, 0);
                    }
                }
            } else {
                if (kind == BISHOP || kind == QUEEN) {
                    slide(pos, out, sq, DIAGONAL, foeLo, foeHi);
                }
                if (kind == ROOK || kind == QUEEN) {
                    slide(pos, out, sq, STRAIGHT, foeLo, foeHi);
                }
            }
        }
        castlingMoves(pos, out, white);
    }

    // The king's two-square move, when the right is kept, king and rook stand at home, the squares between them are empty and
    // the king neither starts on, crosses nor lands on an attacked square. The rook may cross an attacked square (b1 or b8).
    private static void castlingMoves(List<Integer> pos, List<Integer> out, Boolean white) {
        Integer shift = white ? 0 : 6;
        Integer foeShift = white ? 6 : 0;
        Integer home = white ? 25 : 95;
        if (pos.get(home) != KING + shift || attacked(pos, home, foeShift)) {
            return;
        }
        Integer rookCode = ROOK + shift;
        Boolean shortRight = pos.get(white ? CASTLE_WK : CASTLE_BK) == 1;
        Boolean longRight = pos.get(white ? CASTLE_WQ : CASTLE_BQ) == 1;
        if (shortRight && pos.get(home + 3) == rookCode && pos.get(home + 1) == 0 && pos.get(home + 2) == 0
                && !attacked(pos, home + 1, foeShift) && !attacked(pos, home + 2, foeShift)) {
            addMove(out, home, home + 2, 0);
        }
        if (longRight && pos.get(home - 4) == rookCode && pos.get(home - 1) == 0 && pos.get(home - 2) == 0
                && pos.get(home - 3) == 0 && !attacked(pos, home - 1, foeShift) && !attacked(pos, home - 2, foeShift)) {
            addMove(out, home, home - 2, 0);
        }
    }

    private static void slide(List<Integer> pos, List<Integer> out, Integer sq, List<Integer> steps, Integer foeLo, Integer foeHi) {
        for (Integer i = 0; i < 4; i++) {
            Integer step = steps.get(i);
            Integer target = sq + step;
            while (pos.get(target) == 0) {
                addMove(out, sq, target, 0);
                target += step;
            }
            Integer occupant = pos.get(target);
            if (occupant >= foeLo && occupant <= foeHi) {
                addMove(out, sq, target, 0);
            }
        }
    }

    private static void addMove(List<Integer> out, Integer fromSq, Integer toSq, Integer promo) {
        out.add(fromSq);
        out.add(toSq);
        out.add(promo);
    }

    // A pawn reaching the last rank yields one move per promotion piece (knight, bishop, rook, queen).
    private static void addPawnMove(List<Integer> out, Integer fromSq, Integer toSq, Boolean white) {
        Boolean lastRank = white ? (toSq >= 91) : (toSq <= 28);
        if (lastRank) {
            for (Integer promo = KNIGHT; promo <= QUEEN; promo++) {
                addMove(out, fromSq, toSq, promo);
            }
        } else {
            addMove(out, fromSq, toSq, 0);
        }
    }

    // The legal moves of pos as (from, to, promotion) triples; with firstOnly it stops at the first, which is all a status needs.
    private static List<Integer> legalTriples(List<Integer> pos, Boolean firstOnly) {
        List<Integer> pseudo = new List<Integer>();
        pseudoMoves(pos, pseudo);
        Boolean white = pos.get(SIDE) == 0;
        Integer kingCell = white ? KING_WHITE : KING_BLACK;
        Integer foeShift = white ? 6 : 0;
        List<Integer> legal = new List<Integer>();
        for (Integer i = 0; i < pseudo.size(); i += 3) {
            List<Integer> moved = new List<Integer>(pos);
            play(moved, pseudo.get(i), pseudo.get(i + 1), pseudo.get(i + 2));
            if (!attacked(moved, moved.get(kingCell), foeShift)) {
                addMove(legal, pseudo.get(i), pseudo.get(i + 1), pseudo.get(i + 2));
                if (firstOnly) {
                    break;
                }
            }
        }
        return legal;
    }

    // Plays a pseudo-legal move on the board cells of pos (not on the rights, clocks or side to move) and returns the code of the
    // piece it captured, 0 for none. Handles en passant (a pawn moving diagonally onto an empty square), castling (the king moving
    // two squares also moves the rook) and promotion, and keeps the king's cell current.
    private static Integer play(List<Integer> pos, Integer fromSq, Integer toSq, Integer promo) {
        Integer piece = pos.get(fromSq);
        Boolean white = piece <= 6;
        Integer kind = white ? piece : piece - 6;
        Integer captured = pos.get(toSq);
        Integer delta = toSq - fromSq;
        if (kind == PAWN && captured == 0 && (delta == 9 || delta == 11 || delta == -9 || delta == -11)) {
            Integer victim = white ? toSq - 10 : toSq + 10;
            captured = pos.get(victim);
            pos.set(victim, 0);
        }
        pos.set(toSq, promo == 0 ? piece : promo + (white ? 0 : 6));
        pos.set(fromSq, 0);
        if (kind == KING) {
            pos.set(white ? KING_WHITE : KING_BLACK, toSq);
            if (delta == 2) {
                pos.set(fromSq + 1, pos.get(fromSq + 3));
                pos.set(fromSq + 3, 0);
            } else if (delta == -2) {
                pos.set(fromSq - 1, pos.get(fromSq - 4));
                pos.set(fromSq - 4, 0);
            }
        }
        return captured;
    }

    // True when square sq is attacked by a piece of the colour whose codes are type + shift (shift 0: White, 6: Black).
    private static Boolean attacked(List<Integer> pos, Integer sq, Integer shift) {
        if (shift == 0) {
            if (pos.get(sq - 9) == PAWN || pos.get(sq - 11) == PAWN) {
                return true;
            }
        } else {
            if (pos.get(sq + 9) == PAWN + 6 || pos.get(sq + 11) == PAWN + 6) {
                return true;
            }
        }
        Integer knightCode = KNIGHT + shift;
        for (Integer i = 0; i < 8; i++) {
            if (pos.get(sq + KNIGHT_STEPS.get(i)) == knightCode) {
                return true;
            }
        }
        Integer kingCode = KING + shift;
        for (Integer i = 0; i < 8; i++) {
            if (pos.get(sq + KING_STEPS.get(i)) == kingCode) {
                return true;
            }
        }
        Integer queenCode = QUEEN + shift;
        Integer bishopCode = BISHOP + shift;
        for (Integer i = 0; i < 4; i++) {
            Integer step = DIAGONAL.get(i);
            Integer target = sq + step;
            while (pos.get(target) == 0) {
                target += step;
            }
            Integer found = pos.get(target);
            if (found == bishopCode || found == queenCode) {
                return true;
            }
        }
        Integer rookCode = ROOK + shift;
        for (Integer i = 0; i < 4; i++) {
            Integer step = STRAIGHT.get(i);
            Integer target = sq + step;
            while (pos.get(target) == 0) {
                target += step;
            }
            Integer found = pos.get(target);
            if (found == rookCode || found == queenCode) {
                return true;
            }
        }
        return false;
    }

    // ------------------------------------------------------------------------------------------- FEN and UCI text

    private static List<Integer> parse(String fen) {
        if (fen == null) {
            throw new IllegalMoveException('Invalid FEN: null');
        }
        List<String> parts = fen.trim().split(' ');
        if (parts.size() < 4) {
            throw badFen(fen);
        }
        List<String> rows = parts.get(0).split('/');
        if (rows.size() != 8) {
            throw badFen(fen);
        }
        List<Integer> pos = new List<Integer>(EMPTY_POSITION);
        Integer whiteKings = 0;
        Integer blackKings = 0;
        for (Integer i = 0; i < 8; i++) {
            String row = rows.get(i);
            Integer rankBase = 21 + (7 - i) * 10;
            Integer file = 0;
            for (Integer k = 0; k < row.length(); k++) {
                Integer code = row.codePointAt(k);
                if (code >= 49 && code <= 56) {
                    file += code - 48;
                } else {
                    Integer piece = PIECE_CHARS.indexOf(row.substring(k, k + 1));
                    if (piece < 1 || file > 7) {
                        throw badFen(fen);
                    }
                    pos.set(rankBase + file, piece);
                    if (piece == KING) {
                        pos.set(KING_WHITE, rankBase + file);
                        whiteKings++;
                    } else if (piece == KING + 6) {
                        pos.set(KING_BLACK, rankBase + file);
                        blackKings++;
                    }
                    file++;
                }
            }
            if (file != 8) {
                throw badFen(fen);
            }
        }
        if (whiteKings != 1 || blackKings != 1) {
            throw badFen(fen);
        }
        String mover = parts.get(1);
        if (mover.equals('w')) {
            pos.set(SIDE, 0);
        } else if (mover.equals('b')) {
            pos.set(SIDE, 1);
        } else {
            throw badFen(fen);
        }
        String rights = parts.get(2);
        pos.set(CASTLE_WK, rights.indexOf('K') >= 0 ? 1 : 0);
        pos.set(CASTLE_WQ, rights.indexOf('Q') >= 0 ? 1 : 0);
        pos.set(CASTLE_BK, rights.indexOf('k') >= 0 ? 1 : 0);
        pos.set(CASTLE_BQ, rights.indexOf('q') >= 0 ? 1 : 0);
        String ep = parts.get(3);
        if (!ep.equals('-')) {
            Integer epSq = ep.length() == 2 ? squareOf(ep) : -1;
            if (epSq < 0) {
                throw badFen(fen);
            }
            pos.set(EP_SQUARE, epSq);
        }
        pos.set(HALFMOVES, 0);
        pos.set(FULLMOVES, 1);
        if (parts.size() >= 6) {
            if (!parts.get(4).isNumeric() || !parts.get(5).isNumeric()) {
                throw badFen(fen);
            }
            pos.set(HALFMOVES, Integer.valueOf(parts.get(4)));
            pos.set(FULLMOVES, Integer.valueOf(parts.get(5)));
        }
        return pos;
    }

    private static String format(List<Integer> pos) {
        List<String> rows = new List<String>();
        for (Integer rank = 7; rank >= 0; rank--) {
            String row = '';
            Integer gap = 0;
            for (Integer file = 0; file < 8; file++) {
                Integer piece = pos.get(21 + rank * 10 + file);
                if (piece == 0) {
                    gap++;
                } else {
                    if (gap > 0) {
                        row += String.valueOf(gap);
                        gap = 0;
                    }
                    row += PIECE_CHARS.substring(piece, piece + 1);
                }
            }
            if (gap > 0) {
                row += String.valueOf(gap);
            }
            rows.add(row);
        }
        String rights = '';
        if (pos.get(CASTLE_WK) == 1) {
            rights += 'K';
        }
        if (pos.get(CASTLE_WQ) == 1) {
            rights += 'Q';
        }
        if (pos.get(CASTLE_BK) == 1) {
            rights += 'k';
        }
        if (pos.get(CASTLE_BQ) == 1) {
            rights += 'q';
        }
        String ep = pos.get(EP_SQUARE) == 0 ? '-' : SQ_NAMES.get(pos.get(EP_SQUARE));
        return String.join(rows, '/') + ' ' + (pos.get(SIDE) == 0 ? 'w' : 'b') + ' ' + (rights.length() == 0 ? '-' : rights)
            + ' ' + ep + ' ' + String.valueOf(pos.get(HALFMOVES)) + ' ' + String.valueOf(pos.get(FULLMOVES));
    }

    private static String uciOf(Integer fromSq, Integer toSq, Integer promo) {
        return SQ_NAMES.get(fromSq) + SQ_NAMES.get(toSq) + (promo == 0 ? '' : PROMOTION_OUT.substring(promo, promo + 1));
    }

    // The cell of a square name such as e4, or -1 when the text is not a square.
    private static Integer squareOf(String name) {
        Integer file = FILES.indexOf(name.substring(0, 1));
        Integer rank = RANKS.indexOf(name.substring(1, 2));
        if (file < 0 || rank < 0) {
            return -1;
        }
        return 21 + rank * 10 + file;
    }

    private static IllegalMoveException illegal(String move) {
        return new IllegalMoveException('Illegal move: ' + move);
    }

    private static IllegalMoveException badFen(String fen) {
        return new IllegalMoveException('Invalid FEN: ' + fen);
    }

    // ------------------------------------------------------------------------------------------------ static tables

    private static List<String> buildNames() {
        List<String> names = new List<String>();
        for (Integer i = 0; i < 120; i++) {
            names.add('');
        }
        for (Integer rank = 0; rank < 8; rank++) {
            for (Integer file = 0; file < 8; file++) {
                names.set(21 + rank * 10 + file, FILES.substring(file, file + 1) + RANKS.substring(rank, rank + 1));
            }
        }
        return names;
    }

    private static List<Integer> buildEmpty() {
        List<Integer> blank = new List<Integer>();
        for (Integer i = 0; i < CELLS; i++) {
            blank.add(i < 120 ? OFFBOARD : 0);
        }
        for (Integer rank = 0; rank < 8; rank++) {
            for (Integer file = 0; file < 8; file++) {
                blank.set(21 + rank * 10 + file, 0);
            }
        }
        return blank;
    }
}
