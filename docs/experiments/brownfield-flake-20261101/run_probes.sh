#!/bin/bash
# The first set of probes (2026-11-01): the calibration suite's own graded(), alternating pool sizes 16 and 6, at low priority.
#   bash run_probes.sh CHECKOUT      (CHECKOUT holds the suite exactly as on main)
S=$(cd "$(dirname "$0")" && pwd); X=${1:?a checkout}
for spec in "16 d1" "6 s1" "16 d2" "6 s2"; do
  set -- $spec; pool=$1; tag=$2
  PROBE_POOL=$pool nice -n 10 python3 -B $S/flake_probe.py $X $tag > $S/probe-$tag.json 2> $S/probe-$tag.err
done
