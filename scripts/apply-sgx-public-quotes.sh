#!/usr/bin/env bash
set -euo pipefail

feed=${1:?Provide the path to the candidate feed}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

today=$(TZ=Asia/Singapore date +%F)
session=${SGX_REQUESTED_SESSION:-$today}
if [[ ! "$session" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ || "$session" > "$today" ]]; then
  echo "::error::SGX session is in the future or is not a YYYY-MM-DD date."
  exit 1
fi
if [ "${SGX_PREFLIGHT:-}" = true ]; then
  node "$script_dir/check-sgx-close-readiness.js" "$feed" "$session" S63
  node "$script_dir/check-sgx-close-readiness.js" "$feed" "$session" G13
fi

if [ -z "${SGX_CLOSE_GRANT_JSON:-}" ]; then
  if [ "${SGX_PREFLIGHT:-}" = true ]; then
    echo "Evidence-only SGX preflight: share and financial checks ran; licensed close retrieval was skipped."
    echo "SGX preflight completed without fetching a close because no reviewed grant is configured." >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
    exit 0
  fi
  if [ -n "${SGX_REQUESTED_SESSION:-}" ]; then
    echo "::error::A reviewed SGX close grant must be configured for this run."
    exit 1
  fi
  echo "Licensed SGX close feed is not configured." >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
  exit 0
fi
work_dir=$(mktemp -d -- "$(dirname -- "$feed")/.sgx-close-XXXXXX")
trap 'rm -rf "$work_dir"' EXIT
printf '%s' "$SGX_CLOSE_GRANT_JSON" > "$work_dir/grant.json"
unset SGX_CLOSE_GRANT_JSON
node "$script_dir/fetch-sgx-public-quotes.js" "$feed" "$work_dir/grant.json" "$session" > "$work_dir/latest.json"
mv -- "$work_dir/latest.json" "$feed"
echo "Licensed SGX closes staged for $session." >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
