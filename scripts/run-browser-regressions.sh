#!/usr/bin/env bash
# The two suites use independent browser profiles and temporary directories.
set -euo pipefail

logs=$(mktemp -d)
trap 'rm -rf -- "$logs"' EXIT

node scripts/e2e-sgx-browser-v268.mjs >"$logs/dashboard.log" 2>&1 &
dashboard_pid=$!
node scripts/e2e-sgx-32-research-v296.mjs >"$logs/research.log" 2>&1 &
research_pid=$!

dashboard_status=0
research_status=0
wait "$dashboard_pid" || dashboard_status=$?
wait "$research_pid" || research_status=$?

printf '\nDashboard browser suite (exit %s)\n' "$dashboard_status"
cat "$logs/dashboard.log"
printf '\nResearch browser suite (exit %s)\n' "$research_status"
cat "$logs/research.log"

if (( dashboard_status != 0 || research_status != 0 )); then
  exit 1
fi
