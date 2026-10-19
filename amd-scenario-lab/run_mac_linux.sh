#!/usr/bin/env bash
set -euo pipefail
exec bash "$(dirname "$0")/../scenario-lab/run_mac_linux.sh" "$@"
