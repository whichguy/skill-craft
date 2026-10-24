/**
 * Chess rules for one position. Inside this class a square is 0-63 with a1 = 0.
 * FEN and UCI exist only on the public methods. No queries and no DML.
 */
public class SLChessEngine {
    public class IllegalMoveException extends Exception {}

    private static final Integer EMPTY = 0;
    private static final Integer WP = 1;
    private static final Integer WN = 2;
    private static final Integer WB = 3;
    private static final Integer WR = 4;
    private static final Integer WQ = 5;
    private static final Integer WK = 6;
    private static final Integer BP = 9;
    private static final Integer BN = 10;
    private static final Integer BB = 11;
    private static final Integer BR = 12;
    private static final Integer BQ = 13;
    private static final Integer BK = 14;
    private static final Integer WHITE = 0;
    private static final Integer BLACK = 1;
    private static final String START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    private static final String PIECE_CHAR = '.PNBRQK..pnbrqk';
    private static final Integer[] KNIGHT_DF = new Integer[]{1, 1, -1, -1, 2, 2, -2, -2};
    private static final Integer[] KNIGHT_DR = new Integer[]{2, -2, 2, -2, 1, -1, 1, -1};
    private static final Integer[] KING_DF = new Integer[]{1, -1, 0, 0, 1, 1, -1, -1};
    private static final Integer[] KING_DR = new Integer[]{0, 0, 1, -1, 1, -1, 1, -1};

    private class Pos {
        Integer[] sq;
        Integer stm;
        Integer castle;
        Integer ep;
        Integer half;
        Integer full;
        Integer wk;
        Integer bk;
    }

    /**
     * @return The standard start position.
     */
    public static String startFen() {
        return START;
    }

    /**
     * @param fen Six-field FEN. The side to move is the side whose moves are returned.
     * @return Every legal UCI move, sorted A to Z. Promotion is e7e8q, never a bare e7e8.
     * @throws IllegalMoveException when fen is missing or not a position.
     */
    public static List<String> legalMoves(String fen) {
        Pos p = parse(fen);
        List<Integer> moves = legal(p);
        List<String> out = new List<String>();
        for (Integer move : moves) {
            out.add(toUci(move));
        }
        out.sort();
        return out;
    }

    /**
     * @param fen Six-field FEN.
     * @param move UCI move that must be legal in fen, such as e2e4 or e7e8q.
     * @return The FEN after the move, including rights, the en-passant square, and both clocks.
     * @throws IllegalMoveException when fen or move is unusable, or the move is illegal. No FEN is returned.
     */
    public static String applyMove(String fen, String move) {
        if (move == null) {
            throw new IllegalMoveException('move is required');
        }
        Pos p = parse(fen);
        Integer packed = parseMove(move);
        for (Integer item : legal(p)) {
            if (item == packed) {
                make(p, item, new Integer[9]);
                return emit(p);
            }
        }
        throw new IllegalMoveException('move is illegal, received ' + move);
    }

    /**
     * @param fen Six-field FEN.
     * @return ongoing, check, checkmate, or stalemate for the side to move.
     * @throws IllegalMoveException when fen is missing or not a position.
     */
    public static String status(String fen) {
        Pos p = parse(fen);
        Boolean hasMove = !legal(p).isEmpty();
        Integer kingSq = (p.stm == WHITE) ? p.wk : p.bk;
        Boolean opponentIsWhite = p.stm != WHITE;
        Boolean checked = attacked(p, kingSq, opponentIsWhite);
        if (!hasMove) {
            return checked ? 'checkmate' : 'stalemate';
        }
        return checked ? 'check' : 'ongoing';
    }

    private static Pos parse(String fen) {
        if (String.isBlank(fen)) {
            throw new IllegalMoveException('fen is required');
        }
        List<String> parts = fen.split(' ');
        if (parts.size() != 6) {
            throw new IllegalMoveException('fen must have six fields, received ' + fen);
        }
        Pos p = new Pos();
        p.sq = new Integer[64];
        for (Integer i = 0; i < 64; i++) {
            p.sq[i] = EMPTY;
        }
        List<String> ranks = parts[0].split('/');
        if (ranks.size() != 8) {
            throw new IllegalMoveException('fen must have eight ranks, received ' + fen);
        }
        for (Integer r = 0; r < 8; r++) {
            Integer file = 0;
            String rank = ranks[r];
            for (Integer i = 0; i < rank.length(); i++) {
                String ch = rank.substring(i, i + 1);
                if (ch >= '1' && ch <= '8') {
                    file += ch.charAt(0) - 48;
                    continue;
                }
                Integer piece = pieceFromChar(ch);
                if (piece == null || file > 7) {
                    throw new IllegalMoveException('fen has a bad piece, received ' + fen);
                }
                Integer sq = (7 - r) * 8 + file;
                p.sq[sq] = piece;
                if (piece == WK) {
                    p.wk = sq;
                } else if (piece == BK) {
                    p.bk = sq;
                }
                file++;
            }
            if (file != 8) {
                throw new IllegalMoveException('fen rank is not eight squares, received ' + fen);
            }
        }
        if ((p.stm == WHITE && p.wk == null) || (p.stm == BLACK && p.bk == null)) {
            throw new IllegalMoveException('fen must contain the king of the side to move, received ' + fen);
        }
        if (parts[1] == 'w') {
            p.stm = WHITE;
        } else if (parts[1] == 'b') {
            p.stm = BLACK;
        } else {
            throw new IllegalMoveException('fen side to move must be w or b, received ' + fen);
        }
        p.castle = 0;
        if (parts[2] != '-') {
            for (Integer i = 0; i < parts[2].length(); i++) {
                Integer code = parts[2].charAt(i);
                // Apex string == is case-insensitive, so rights use character codes.
                if (code == 75) {
                    p.castle |= 1;
                } else if (code == 81) {
                    p.castle |= 2;
                } else if (code == 107) {
                    p.castle |= 4;
                } else if (code == 113) {
                    p.castle |= 8;
                } else {
                    throw new IllegalMoveException('fen castling rights must be KQkq, received ' + fen);
                }
            }
        }
        p.ep = -1;
        if (parts[3] != '-') {
            p.ep = parseSquare(parts[3], fen);
        }
        try {
            p.half = Integer.valueOf(parts[4]);
            p.full = Integer.valueOf(parts[5]);
        } catch (Exception ex) {
            throw new IllegalMoveException('fen clocks must be numbers, received ' + fen + ', cause ' + ex.getMessage());
        }
        return p;
    }

    private static Integer pieceFromChar(String ch) {
        Integer at = PIECE_CHAR.indexOf(ch);
        if (at == 1 || at == 2 || at == 3 || at == 4 || at == 5 || at == 6 || at >= 9) {
            return at;
        }
        return null;
    }

    private static String emit(Pos p) {
        List<String> ranks = new List<String>();
        for (Integer r = 7; r >= 0; r--) {
            Integer gap = 0;
            String out = '';
            for (Integer f = 0; f < 8; f++) {
                Integer piece = p.sq[r * 8 + f];
                if (piece == EMPTY) {
                    gap++;
                    continue;
                }
                if (gap > 0) {
                    out += String.valueOf(gap);
                    gap = 0;
                }
                out += PIECE_CHAR.substring(piece, piece + 1);
            }
            if (gap > 0) {
                out += String.valueOf(gap);
            }
            ranks.add(out);
        }
        String rights = '';
        if ((p.castle & 1) != 0) {
            rights += 'K';
        }
        if ((p.castle & 2) != 0) {
            rights += 'Q';
        }
        if ((p.castle & 4) != 0) {
            rights += 'k';
        }
        if ((p.castle & 8) != 0) {
            rights += 'q';
        }
        if (rights == '') {
            rights = '-';
        }
        String ep = p.ep < 0 ? '-' : squareName(p.ep);
        String side = p.stm == WHITE ? 'w' : 'b';
        return String.join(ranks, '/') + ' ' + side + ' ' + rights + ' ' + ep + ' ' + p.half + ' ' + p.full;
    }

    private static List<Integer> legal(Pos p) {
        Integer[] pseudo = new Integer[256];
        Integer count = fillPseudo(p, pseudo);
        List<Integer> out = new List<Integer>();
        Integer[] undo = new Integer[9];
        Boolean moverWhite = p.stm == WHITE;
        for (Integer i = 0; i < count; i++) {
            make(p, pseudo[i], undo);
            Integer king = moverWhite ? p.wk : p.bk;
            if (!attacked(p, king, !moverWhite)) {
                out.add(pseudo[i]);
            }
            unmake(p, pseudo[i], undo);
        }
        return out;
    }

    private static Integer fillPseudo(Pos p, Integer[] buf) {
        Boolean moverWhite = p.stm == WHITE;
        Integer kingSq = moverWhite ? p.wk : p.bk;
        Boolean inCheck = attacked(p, kingSq, !moverWhite);
        Integer n = 0;
        for (Integer sq = 0; sq < 64; sq++) {
            Integer piece = p.sq[sq];
            if (moverWhite) {
                if (piece < WP || piece > WK) {
                    continue;
                }
            } else if (piece < BP || piece > BK) {
                continue;
            }
            Integer file = sq & 7;
            Integer rank = sq >> 3;
            if (piece == WP || piece == BP) {
                Integer dir = moverWhite ? 8 : -8;
                Integer one = sq + dir;
                if (one >= 0 && one < 64 && p.sq[one] == EMPTY) {
                    Integer destRank = rank + (moverWhite ? 1 : -1);
                    Boolean promote = destRank == (moverWhite ? 7 : 0);
                    n = addMove(buf, n, sq, one, promote);
                    if (rank == (moverWhite ? 1 : 6)) {
                        Integer two = sq + dir * 2;
                        if (p.sq[two] == EMPTY) {
                            n = addMove(buf, n, sq, two, false);
                        }
                    }
                }
                for (Integer df = -1; df <= 1; df += 2) {
                    Integer nf = file + df;
                    Integer nr = rank + (moverWhite ? 1 : -1);
                    if (!onBoard(nf, nr)) {
                        continue;
                    }
                    Integer to = nr * 8 + nf;
                    Integer target = p.sq[to];
                    Boolean enemy = moverWhite ? target >= BP : (target >= WP && target <= WK);
                    if (enemy || to == p.ep) {
                        Boolean promote = nr == (moverWhite ? 7 : 0);
                        n = addMove(buf, n, sq, to, promote);
                    }
                }
            } else if (piece == WN || piece == BN) {
                n = leap(p, buf, n, sq, moverWhite, true);
            } else if (piece == WK || piece == BK) {
                n = leap(p, buf, n, sq, moverWhite, false);
                if (!inCheck && piece == WK && kingSq == 4) {
                    if ((p.castle & 1) != 0 && p.sq[5] == EMPTY && p.sq[6] == EMPTY && p.sq[7] == WR
                        && !attacked(p, 5, false) && !attacked(p, 6, false)) {
                        n = addMove(buf, n, 4, 6, false);
                    }
                    // b1 must be empty, and it does not have to be safe.
                    if ((p.castle & 2) != 0 && p.sq[1] == EMPTY && p.sq[2] == EMPTY && p.sq[3] == EMPTY && p.sq[0] == WR
                        && !attacked(p, 2, false) && !attacked(p, 3, false)) {
                        n = addMove(buf, n, 4, 2, false);
                    }
                }
                if (!inCheck && piece == BK && kingSq == 60) {
                    if ((p.castle & 4) != 0 && p.sq[61] == EMPTY && p.sq[62] == EMPTY && p.sq[63] == BR
                        && !attacked(p, 61, true) && !attacked(p, 62, true)) {
                        n = addMove(buf, n, 60, 62, false);
                    }
                    if ((p.castle & 8) != 0 && p.sq[57] == EMPTY && p.sq[58] == EMPTY && p.sq[59] == EMPTY && p.sq[56] == BR
                        && !attacked(p, 58, true) && !attacked(p, 59, true)) {
                        n = addMove(buf, n, 60, 58, false);
                    }
                }
            } else {
                Boolean bishop = piece == WB || piece == BB || piece == WQ || piece == BQ;
                Boolean rook = piece == WR || piece == BR || piece == WQ || piece == BQ;
                if (bishop) {
                    n = slide(p, buf, n, sq, 1, 1, moverWhite);
                    n = slide(p, buf, n, sq, 1, -1, moverWhite);
                    n = slide(p, buf, n, sq, -1, 1, moverWhite);
                    n = slide(p, buf, n, sq, -1, -1, moverWhite);
                }
                if (rook) {
                    n = slide(p, buf, n, sq, 1, 0, moverWhite);
                    n = slide(p, buf, n, sq, -1, 0, moverWhite);
                    n = slide(p, buf, n, sq, 0, 1, moverWhite);
                    n = slide(p, buf, n, sq, 0, -1, moverWhite);
                }
            }
        }
        return n;
    }

    private static Integer leap(Pos p, Integer[] buf, Integer n, Integer sq, Boolean moverWhite, Boolean knight) {
        Integer file = sq & 7;
        Integer rank = sq >> 3;
        Integer[] df = knight ? KNIGHT_DF : KING_DF;
        Integer[] dr = knight ? KNIGHT_DR : KING_DR;
        for (Integer i = 0; i < df.size(); i++) {
            Integer nf = file + df[i];
            Integer nr = rank + dr[i];
            if (!onBoard(nf, nr)) {
                continue;
            }
            Integer to = nr * 8 + nf;
            if (friendly(p, to, moverWhite)) {
                continue;
            }
            n = addMove(buf, n, sq, to, false);
        }
        return n;
    }

    private static Integer slide(Pos p, Integer[] buf, Integer n, Integer sq, Integer df, Integer dr, Boolean moverWhite) {
        Integer file = (sq & 7) + df;
        Integer rank = (sq >> 3) + dr;
        while (onBoard(file, rank)) {
            Integer to = rank * 8 + file;
            if (friendly(p, to, moverWhite)) {
                break;
            }
            n = addMove(buf, n, sq, to, false);
            if (p.sq[to] != EMPTY) {
                break;
            }
            file += df;
            rank += dr;
        }
        return n;
    }

    private static Integer addMove(Integer[] buf, Integer n, Integer frm, Integer to, Boolean promo) {
        if (promo) {
            buf[n] = pack(frm, to, 1);
            buf[n + 1] = pack(frm, to, 2);
            buf[n + 2] = pack(frm, to, 3);
            buf[n + 3] = pack(frm, to, 4);
            return n + 4;
        }
        buf[n] = pack(frm, to, 0);
        return n + 1;
    }

    private static Integer pack(Integer frm, Integer to, Integer promo) {
        return frm | (to << 6) | (promo << 12);
    }

    private static void make(Pos p, Integer move, Integer[] undo) {
        Integer frm = move & 63;
        Integer to = (move >> 6) & 63;
        Integer promo = (move >> 12) & 7;
        Integer piece = p.sq[frm];
        Integer captured = p.sq[to];
        Integer victim = -1;
        if (p.ep == to && (piece == WP || piece == BP)) {
            victim = piece == WP ? to - 8 : to + 8;
            captured = p.sq[victim];
        }
        undo[0] = captured;
        undo[1] = victim;
        undo[2] = p.castle;
        undo[3] = p.ep;
        undo[4] = p.half;
        undo[5] = p.full;
        undo[6] = p.wk;
        undo[7] = p.bk;
        undo[8] = p.stm;
        p.sq[frm] = EMPTY;
        if (victim >= 0) {
            p.sq[victim] = EMPTY;
        }
        Integer placed = piece;
        if (promo != 0) {
            Integer kind = promo == 1 ? WQ : promo == 2 ? WR : promo == 3 ? WB : WN;
            placed = piece == WP ? kind : kind + 8;
        }
        p.sq[to] = placed;
        if (piece == WK && to - frm == 2) {
            p.sq[5] = p.sq[7];
            p.sq[7] = EMPTY;
        } else if (piece == WK && frm - to == 2) {
            p.sq[3] = p.sq[0];
            p.sq[0] = EMPTY;
        } else if (piece == BK && to - frm == 2) {
            p.sq[61] = p.sq[63];
            p.sq[63] = EMPTY;
        } else if (piece == BK && frm - to == 2) {
            p.sq[59] = p.sq[56];
            p.sq[56] = EMPTY;
        }
        if (piece == WK) {
            p.wk = to;
            p.castle = drop(drop(p.castle, 1), 2);
        } else if (piece == BK) {
            p.bk = to;
            p.castle = drop(drop(p.castle, 4), 8);
        } else if (piece == WR && frm == 7) {
            p.castle = drop(p.castle, 1);
        } else if (piece == WR && frm == 0) {
            p.castle = drop(p.castle, 2);
        } else if (piece == BR && frm == 63) {
            p.castle = drop(p.castle, 4);
        } else if (piece == BR && frm == 56) {
            p.castle = drop(p.castle, 8);
        }
        if (captured == WR && to == 7) {
            p.castle = drop(p.castle, 1);
        } else if (captured == WR && to == 0) {
            p.castle = drop(p.castle, 2);
        } else if (captured == BR && to == 63) {
            p.castle = drop(p.castle, 4);
        } else if (captured == BR && to == 56) {
            p.castle = drop(p.castle, 8);
        }
        p.ep = -1;
        if ((piece == WP || piece == BP) && Math.abs(to - frm) == 16) {
            p.ep = (frm + to) / 2;
        }
        if (piece == WP || piece == BP || captured != EMPTY) {
            p.half = 0;
        } else {
            p.half = p.half + 1;
        }
        if (p.stm == BLACK) {
            p.full = p.full + 1;
        }
        p.stm = p.stm == WHITE ? BLACK : WHITE;
    }

    private static void unmake(Pos p, Integer move, Integer[] undo) {
        Integer frm = move & 63;
        Integer to = (move >> 6) & 63;
        Integer promo = (move >> 12) & 7;
        Integer captured = undo[0];
        Integer victim = undo[1];
        Integer mover = p.sq[to];
        if (promo != 0) {
            mover = undo[8] == WHITE ? WP : BP;
        }
        if (promo == 0 && (mover == WK || mover == BK) && Math.abs(to - frm) == 2) {
            if (to > frm) {
                p.sq[to + 1] = p.sq[to - 1];
                p.sq[to - 1] = EMPTY;
            } else {
                p.sq[to - 2] = p.sq[to + 1];
                p.sq[to + 1] = EMPTY;
            }
        }
        p.sq[to] = victim >= 0 ? EMPTY : captured;
        if (victim >= 0) {
            p.sq[victim] = captured;
        }
        p.sq[frm] = mover;
        p.castle = undo[2];
        p.ep = undo[3];
        p.half = undo[4];
        p.full = undo[5];
        p.wk = undo[6];
        p.bk = undo[7];
        p.stm = undo[8];
    }

    private static Integer drop(Integer castle, Integer bit) {
        if ((castle & bit) != 0) {
            return castle - bit;
        }
        return castle;
    }

    private static Boolean attacked(Pos p, Integer sq, Boolean byWhite) {
        Integer file = sq & 7;
        Integer rank = sq >> 3;
        Integer knight = byWhite ? WN : BN;
        for (Integer i = 0; i < 8; i++) {
            Integer nf = file + KNIGHT_DF[i];
            Integer nr = rank + KNIGHT_DR[i];
            if (onBoard(nf, nr) && p.sq[nr * 8 + nf] == knight) {
                return true;
            }
        }
        Integer pawnDir = byWhite ? -1 : 1;
        Integer pawn = byWhite ? WP : BP;
        for (Integer df = -1; df <= 1; df += 2) {
            Integer nf = file + df;
            Integer nr = rank + pawnDir;
            if (onBoard(nf, nr) && p.sq[nr * 8 + nf] == pawn) {
                return true;
            }
        }
        Integer king = byWhite ? WK : BK;
        for (Integer df = -1; df <= 1; df++) {
            for (Integer dr = -1; dr <= 1; dr++) {
                if (df == 0 && dr == 0) {
                    continue;
                }
                Integer nf = file + df;
                Integer nr = rank + dr;
                if (onBoard(nf, nr) && p.sq[nr * 8 + nf] == king) {
                    return true;
                }
            }
        }
        Integer bishop = byWhite ? WB : BB;
        Integer queen = byWhite ? WQ : BQ;
        if (ray(p, file, rank, 1, 1, bishop, queen) || ray(p, file, rank, 1, -1, bishop, queen)
            || ray(p, file, rank, -1, 1, bishop, queen) || ray(p, file, rank, -1, -1, bishop, queen)) {
            return true;
        }
        Integer rook = byWhite ? WR : BR;
        return ray(p, file, rank, 1, 0, rook, queen) || ray(p, file, rank, -1, 0, rook, queen)
            || ray(p, file, rank, 0, 1, rook, queen) || ray(p, file, rank, 0, -1, rook, queen);
    }

    private static Boolean ray(Pos p, Integer file, Integer rank, Integer df, Integer dr, Integer slider, Integer queen) {
        Integer f = file + df;
        Integer r = rank + dr;
        while (onBoard(f, r)) {
            Integer piece = p.sq[r * 8 + f];
            if (piece != EMPTY) {
                return piece == slider || piece == queen;
            }
            f += df;
            r += dr;
        }
        return false;
    }

    private static Boolean friendly(Pos p, Integer to, Boolean moverWhite) {
        Integer piece = p.sq[to];
        if (piece == EMPTY) {
            return false;
        }
        return moverWhite ? piece <= WK : piece >= BP;
    }

    private static Boolean onBoard(Integer file, Integer rank) {
        return file >= 0 && file < 8 && rank >= 0 && rank < 8;
    }

    private static String toUci(Integer move) {
        String text = squareName(move & 63) + squareName((move >> 6) & 63);
        Integer promo = (move >> 12) & 7;
        if (promo == 1) {
            return text + 'q';
        }
        if (promo == 2) {
            return text + 'r';
        }
        if (promo == 3) {
            return text + 'b';
        }
        if (promo == 4) {
            return text + 'n';
        }
        return text;
    }

    private static String squareName(Integer sq) {
        String files = 'abcdefgh';
        Integer file = sq & 7;
        return files.substring(file, file + 1) + String.valueOf((sq >> 3) + 1);
    }

    private static Integer parseMove(String move) {
        if (move.length() != 4 && move.length() != 5) {
            throw new IllegalMoveException('move must be four or five characters, received ' + move);
        }
        Integer frm = parseSquare(move.substring(0, 2), move);
        Integer to = parseSquare(move.substring(2, 4), move);
        Integer promo = 0;
        if (move.length() == 5) {
            String ch = move.substring(4, 5);
            if (ch == 'q') {
                promo = 1;
            } else if (ch == 'r') {
                promo = 2;
            } else if (ch == 'b') {
                promo = 3;
            } else if (ch == 'n') {
                promo = 4;
            } else {
                throw new IllegalMoveException('move promotion must be q, r, b, or n, received ' + move);
            }
        }
        return pack(frm, to, promo);
    }

    private static Integer parseSquare(String sq, String source) {
        if (sq == null || sq.length() != 2) {
            throw new IllegalMoveException('square must be a file and a rank, received ' + source);
        }
        Integer file = sq.substring(0, 1).charAt(0) - 97;
        Integer rank = sq.substring(1, 2).charAt(0) - 49;
        if (file < 0 || file > 7 || rank < 0 || rank > 7) {
            throw new IllegalMoveException('square is off the board, received ' + source);
        }
        return rank * 8 + file;
    }
}
