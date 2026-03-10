#!/usr/bin/env bash
set -euo pipefail

print_usage() {
  cat <<'EOF'
Usage: ./scripts/check_native_toolchain.sh

Checks whether `pio` and `gcc` are available in PATH and prints platform-specific
guidance when prerequisites are missing.
EOF
}

if [[ "$#" -eq 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
  print_usage
  exit 0
fi

if [[ "$#" -gt 0 ]]; then
  echo "Unexpected argument(s): $*" >&2
  exit 2
fi

echo "== Native Toolchain Check =="

HAS_PIO=0
HAS_GCC=0

if command -v pio >/dev/null 2>&1; then
  echo "[OK] pio found: $(command -v pio)"
  HAS_PIO=1
else
  echo "[FAIL] pio not found in PATH"
fi

if command -v gcc >/dev/null 2>&1; then
  echo "[OK] gcc found: $(command -v gcc)"
  HAS_GCC=1
else
  echo "[FAIL] gcc not found in PATH"
fi

if [[ "$HAS_GCC" -eq 0 ]]; then
  echo
  echo "Suggested fix:"
  case "$(uname -s)" in
    Linux*)
      if command -v apt >/dev/null 2>&1; then
        echo "- sudo apt update; sudo apt install -y build-essential"
      elif command -v dnf >/dev/null 2>&1; then
        echo "- sudo dnf groupinstall -y \"Development Tools\""
      elif command -v pacman >/dev/null 2>&1; then
        echo "- sudo pacman -S --needed base-devel gcc"
      else
        echo "- Install gcc using your distro package manager"
      fi
      ;;
    Darwin*)
      if command -v brew >/dev/null 2>&1; then
        echo "- brew install gcc"
      else
        echo "- Install Xcode Command Line Tools: xcode-select --install"
      fi
      ;;
    *)
      echo "- Install MSYS2 or MinGW-w64"
      echo "- Add the gcc bin folder to PATH"
      ;;
  esac
  echo "- Verify with: gcc --version"
fi

if [[ "$HAS_PIO" -eq 1 && "$HAS_GCC" -eq 1 ]]; then
  echo
  echo "[OK] Native prerequisites look good."
  exit 0
fi

echo
echo "[WARN] Native prerequisites are incomplete."
exit 1
