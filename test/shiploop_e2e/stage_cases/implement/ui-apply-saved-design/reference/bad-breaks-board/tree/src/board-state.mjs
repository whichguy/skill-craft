export function createBoardState() {
  return { selected: "a1", status: "Selected: a1" };
}

export function selectSquare(state, square) {
  if (!/^[a-h][1-8]$/.test(square)) throw new RangeError("square must be a1 through h8");
  return { ...state, selected: square, status: "Selected: " + square };
}

export function resetBoard() {
  return { selected: "a1", status: "Selected: a1" };
}
