import { LightningElement, api } from 'lwc';
import { callApex } from 'c/apex';
import save from '@salesforce/apex/ChessGameController.save';
export default class ChessBoard extends LightningElement {
    @api recordId;
    async persist(fen) { await callApex(this, save, { gameId: this.recordId, fen }); }
}
