import os
W = '/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/v2170-ds-battleship/witnesses'
HEAD = "'use strict';\nconst L = require('./_lib.js');\nconst C = require('./_cdp.js');\nconst { check } = L;\n"
def write(wid, body):
    open(os.path.join(W, wid + '.js'), 'w').write(HEAD + body.strip('\n') + '\n')
