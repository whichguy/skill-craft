'use strict';
// Preload for witnesses only: crypto.randomUUID returns g-1, g-2, ... so a witness can guess game ids.
const crypto = require('node:crypto');
let n = 0;
crypto.randomUUID = () => 'g-' + (++n);
