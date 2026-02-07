#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${RENDER_API_KEY:-}" ]]; then
  echo "RENDER_API_KEY is not set. Aborting."
  exit 1
fi

if ! command -v render >/dev/null 2>&1; then
  curl -fsSL https://raw.githubusercontent.com/render-oss/cli/refs/heads/main/bin/install.sh | sh
  export PATH="$HOME/bin:$PATH"
fi

if [[ -z "${RENDER_SERVICE_ID:-}" ]]; then
  echo "RENDER_SERVICE_ID is not set. Aborting."
  exit 1
fi

cmd=(render deploys create "$RENDER_SERVICE_ID" --confirm --output json --wait)

if [[ -n "${RENDER_COMMIT:-}" ]]; then
  cmd+=(--commit "$RENDER_COMMIT")
fi

if [[ -n "${RENDER_IMAGE_URL:-}" ]]; then
  cmd+=(--image "$RENDER_IMAGE_URL")
fi

echo "Triggering Render deploy for service: $RENDER_SERVICE_ID"
"${cmd[@]}"
