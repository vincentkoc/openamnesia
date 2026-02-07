#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${AKASH_WALLET:-}" ]]; then
  echo "AKASH_WALLET is not set. Aborting."
  exit 1
fi

export PATH="$HOME/bin:$PATH"

if ! command -v provider-services >/dev/null 2>&1; then
  curl -fsSL https://raw.githubusercontent.com/akash-network/provider/main/install.sh | sh
  export PATH="$HOME/bin:$PATH"
fi

if [[ -z "${AKASH_KEY_NAME:-}" ]]; then
  echo "AKASH_KEY_NAME is not set. Aborting."
  exit 1
fi

export AKASH_KEYRING_BACKEND="${AKASH_KEYRING_BACKEND:-os}"
export AKASH_NET="${AKASH_NET:-https://raw.githubusercontent.com/akash-network/net/main/mainnet}"

SDL_PATH="deploy/akash/deploy.yml"
if [[ ! -f "$SDL_PATH" ]]; then
  echo "Missing $SDL_PATH. Aborting."
  exit 1
fi

IMAGE="${AKASH_IMAGE:-ghcr.io/${GITHUB_REPOSITORY:-openamnesia}/openamnesia:latest}"
TMP_SDL="$(mktemp)"
sed "s|__AKASH_IMAGE__|$IMAGE|g" "$SDL_PATH" > "$TMP_SDL"

echo "Creating deployment on Akash..."
provider-services tx deployment create "$TMP_SDL" \
  --from "$AKASH_KEY_NAME" \
  --keyring-backend "$AKASH_KEYRING_BACKEND" \
  --yes

echo "Deployment submitted. Use provider-services to view bids and create lease."
echo "Example:"
echo "  provider-services query market bid list --owner $(provider-services keys show -a "$AKASH_KEY_NAME")"
echo "  provider-services tx market lease create --bid <bid_id> --from $AKASH_KEY_NAME --yes"
echo "  provider-services tx deployment upload-manifest $TMP_SDL --from $AKASH_KEY_NAME --yes"
