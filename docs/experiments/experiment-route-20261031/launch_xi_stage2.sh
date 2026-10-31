#!/bin/bash
# XI Stage 2 (README.md, "XI"): 3 more arm-A runs and 6 arm-B runs, interleaved B B A three times, on the one lane;
# launch_xi.sh waits for port 4180's lease before each. XI_CANDIDATE names the candidate checkout (arm B).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
: "${XI_CANDIDATE:?the candidate checkout}"
for pair in "B 1" "B 2" "A 4" "B 3" "B 4" "A 5" "B 5" "B 6" "A 6"; do
  set -- $pair
  bash "$HERE/launch_xi.sh" "$1" "$2"
done
