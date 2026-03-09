#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Local default: tolerate repeated native policy blocks on Windows hosts.
export ALLOW_NATIVE_POLICY_BLOCK="${ALLOW_NATIVE_POLICY_BLOCK:-1}"

# If gcc is missing in bash, try the common WinGet MinGW location.
if ! command -v gcc >/dev/null 2>&1; then
  for candidate in /mnt/c/Users/*/AppData/Local/Microsoft/WinGet/Packages/BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe/mingw64/bin; do
    if [[ -d "$candidate" ]]; then
      export PATH="$candidate:$PATH"
      break
    fi
  done
fi

if [[ -f "$SCRIPT_DIR/check_native_toolchain.sh" ]]; then
  "$SCRIPT_DIR/check_native_toolchain.sh" || \
    echo "[WARN] Native preflight reported missing prerequisites; continuing with tolerant local checks." >&2
fi

exec "$SCRIPT_DIR/check_all.sh" "$@"
