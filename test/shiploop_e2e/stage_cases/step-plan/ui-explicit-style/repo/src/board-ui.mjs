import { createBoardState, selectSquare, resetBoard } from "./board-state.mjs";

const board = document.querySelector("#board");
const status = document.querySelector("#selection-status");
const reset = document.querySelector("#reset");
let state = createBoardState();

function renderStatus() {
  status.textContent = state.status;
  for (const square of board.querySelectorAll("[data-square]")) {
    const selected = square.dataset.square === state.selected;
    square.dataset.selected = String(selected);
    square.setAttribute("aria-pressed", String(selected));
  }
}

for (let row = 8; row >= 1; row -= 1) {
  for (let column = 0; column < 8; column += 1) {
    const file = String.fromCharCode(97 + column);
    const coordinate = file + row;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "square " + ((row + column) % 2 === 0 ? "square--light" : "square--dark");
    button.dataset.square = coordinate;
    button.dataset.selected = "false";
    button.setAttribute("aria-label", "Square " + coordinate);
    button.setAttribute("aria-pressed", "false");
    button.setAttribute("role", "gridcell");
    button.addEventListener("click", () => {
      state = selectSquare(state, coordinate);
      renderStatus();
    });
    board.append(button);
  }
}

reset.addEventListener("click", () => {
  state = resetBoard();
  renderStatus();
});
