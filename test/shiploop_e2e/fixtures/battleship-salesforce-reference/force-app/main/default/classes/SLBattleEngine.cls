/**
 * The rules of single-player Battleship: a 10 x 10 grid, the standard fleet placed from a seed, one shot at a time.
 *
 * A game is a JSON string:
 *   {"ships": [{"name": "carrier", "size": 5, "cells": [12, 13, 14, 15, 16], "hits": 0}, ...],
 *    "fired": [cells fired at], "shots": 0, "shipsLeft": 5, "gameOver": false, "lastShot": null}
 * A cell is row * 10 + col. After a shot, lastShot is {"row", "col", "result": "miss" | "hit" | "sunk", "ship", "size"}, with ship
 * and size set only when the shot sank that ship. Every method parses the game it is given and returns a new string, so nothing
 * is kept between calls.
 */
public with sharing class SLBattleEngine {
    public class InvalidShotException extends Exception {}

    public static final Integer GRID = 10;
    private static final List<String> SHIP_NAMES = new List<String>{'carrier', 'battleship', 'cruiser', 'submarine', 'destroyer'};
    private static final List<Integer> SHIP_SIZES = new List<Integer>{5, 4, 3, 3, 2};
    private static final Long MODULUS = 2147483647L;
    private static final Long MULTIPLIER = 48271L;

    // A Park-Miller generator: the same seed always gives the same numbers, and every product stays far inside a Long.
    private class Generator {
        private Long seedState;

        public Generator(Integer seed) {
            Long start = 0L;
            if (seed != null) {
                start = seed;
            }
            seedState = Math.mod(Math.abs(start), MODULUS - 1) + 1;
        }

        // A number from 0 to bound - 1.
        public Integer below(Integer bound) {
            seedState = Math.mod(seedState * MULTIPLIER, MODULUS);
            Long span = bound;
            return Math.mod(seedState, span).intValue();
        }
    }

    public static String newGame(Integer seed) {
        Generator random = new Generator(seed);
        Set<Integer> taken = new Set<Integer>();
        List<Object> ships = new List<Object>();
        for (Integer s = 0; s < SHIP_NAMES.size(); s++) {
            Integer shipSize = SHIP_SIZES[s];
            List<Integer> cells;
            do {
                Boolean across = random.below(2) == 0;
                Integer startRow = random.below(across ? GRID : GRID - shipSize + 1);
                Integer startCol = random.below(across ? GRID - shipSize + 1 : GRID);
                cells = new List<Integer>();
                for (Integer k = 0; k < shipSize; k++) {
                    cells.add(across ? startRow * GRID + startCol + k : (startRow + k) * GRID + startCol);
                }
            } while (overlaps(cells, taken));
            taken.addAll(cells);
            ships.add(new Map<String, Object>{'name' => SHIP_NAMES[s], 'size' => shipSize, 'cells' => cells, 'hits' => 0});
        }
        return JSON.serialize(new Map<String, Object>{
            'ships' => ships, 'fired' => new List<Integer>(), 'shots' => 0, 'shipsLeft' => ships.size(),
            'gameOver' => false, 'lastShot' => null
        });
    }

    public static String fire(String game, Integer row, Integer col) {
        if (row == null || col == null || row < 0 || row >= GRID || col < 0 || col >= GRID) {
            throw new InvalidShotException('A shot needs a row and a column from 0 to 9, not (' + row + ', ' + col + ').');
        }
        Map<String, Object> state = (Map<String, Object>) JSON.deserializeUntyped(game);
        Integer cell = row * GRID + col;
        List<Object> fired = (List<Object>) state.get('fired');
        for (Object done : fired) {
            if ((Integer) done == cell) {
                throw new InvalidShotException('The cell (' + row + ', ' + col + ') was already fired at.');
            }
        }
        fired.add(cell);
        String outcome = 'miss';
        String sunkName = null;
        Integer sunkSize = null;
        Integer afloat = 0;
        for (Object item : (List<Object>) state.get('ships')) {
            Map<String, Object> ship = (Map<String, Object>) item;
            List<Object> cells = (List<Object>) ship.get('cells');
            Integer hits = (Integer) ship.get('hits');
            if (cells.contains(cell)) {
                hits++;
                ship.put('hits', hits);
                if (hits == cells.size()) {
                    outcome = 'sunk';
                    sunkName = (String) ship.get('name');
                    sunkSize = cells.size();
                } else {
                    outcome = 'hit';
                }
            }
            if (hits < cells.size()) {
                afloat++;
            }
        }
        state.put('shots', (Integer) state.get('shots') + 1);
        state.put('shipsLeft', afloat);
        state.put('gameOver', afloat == 0);
        state.put('lastShot', new Map<String, Object>{
            'row' => row, 'col' => col, 'result' => outcome, 'ship' => sunkName, 'size' => sunkSize
        });
        return JSON.serialize(state);
    }

    private static Boolean overlaps(List<Integer> cells, Set<Integer> taken) {
        for (Integer cell : cells) {
            if (taken.contains(cell)) {
                return true;
            }
        }
        return false;
    }
}
