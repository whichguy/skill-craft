#!/bin/sh
# Create a toy repo and a sibling .shiploop-runs parent outside every temp
# directory (sandboxes allow temp writes, which would hide the result).
set -eu
base="${1:-$HOME/shiploop-grant-exp-$(openssl rand -hex 3)}"
mkdir -p "$base/src/toy" "$base/src/.shiploop-runs"
git -C "$base/src/toy" init -q
git -C "$base/src/toy" -c user.name=t -c user.email=t@t commit -q --allow-empty -m init
echo "$base"
