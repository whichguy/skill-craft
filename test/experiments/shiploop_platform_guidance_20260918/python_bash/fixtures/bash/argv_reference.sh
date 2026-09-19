#!/usr/bin/env bash
# Reference: preserve every argument boundary, including empty arguments.
set -u

output=$1
shift
printf '%s\0' "$@" >"$output"
