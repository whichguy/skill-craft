import { LightningElement, track } from 'lwc';
// Whole game runs in the component: fleets, turns and the computer opponent.
export default class Battleship extends LightningElement {
    @track state = this.newGame();
    newGame() { return { player: this.place(), computer: this.place(), shots: { player: [], computer: [] }, turn: 'player' }; }
    place() { return []; /* random placement of 5,4,3,3,2 on a 10x10 grid */ }
    handleFire(event) { /* mark hit or miss on state.computer, then computerTurn() */ }
    computerTurn() { /* hunt/target AI */ }
}
