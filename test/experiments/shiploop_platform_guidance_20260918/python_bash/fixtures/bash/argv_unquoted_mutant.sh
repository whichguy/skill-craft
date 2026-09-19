#!/usr/bin/env bash
# Mutant: unquoted $@ applies splitting and pathname expansion.
set -u

output=$1
shift
printf '%s\0' $@ >"$output"
