'use strict';
/** <counter-badge>: a button that counts its clicks and shows the count. */
class CounterBadge extends HTMLElement {
  connectedCallback() {
    this.count = 0;
    this.button = document.createElement('button');
    this.button.textContent = '0';
    this.button.addEventListener('click', () => { this.count += 1; this.button.textContent = String(this.count); });
    this.appendChild(this.button);
  }
}
customElements.define('counter-badge', CounterBadge);
