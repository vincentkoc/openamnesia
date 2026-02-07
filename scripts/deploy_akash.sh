#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${AKASH_WALLET:-}" ]]; then
  echo "AKASH_WALLET is not set. Aborting."
  exit 1
fi

echo "Akash deploy script."
echo "Expected: use akash CLI to submit SDL and deploy."
echo "Replace this script with your SDL + akash tx flow when ready."
