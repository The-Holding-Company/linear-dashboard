#!/usr/bin/env bash
# Pull the Linear read-only key from OpenBao into .env (gitignored).
# Requires the vault to be unsealed; fails loudly otherwise.
set -euo pipefail
export VAULT_ADDR="${VAULT_ADDR:-https://bao-01.onprem.holdingco.com:8200}"
HERE="$(cd "$(dirname "$0")" && pwd)"

KEY=$(command bao kv get -field=read_only secret/holdingco/linear)
[ -n "$KEY" ] || { echo "ERROR: empty read_only key from bao" >&2; exit 1; }

umask 077
printf 'LINEAR_API_KEY=%s\n' "$KEY" > "$HERE/.env"
echo "wrote $HERE/.env"
