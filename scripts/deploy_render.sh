#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${RENDER_API_KEY:-}" ]]; then
  echo "RENDER_API_KEY is not set. Aborting."
  exit 1
fi

echo "Render deploy script."
echo "Expected: create a Render service tied to this repo, then trigger deploy."
echo "Replace this script with `render deploy` or API calls when ready."
