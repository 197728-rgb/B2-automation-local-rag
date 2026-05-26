#!/usr/bin/env bash
# B2 SENTINEL - POSIX runner
set -euo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
python3 run.py "$@"
