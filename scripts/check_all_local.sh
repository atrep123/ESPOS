#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DESIGN="main_scene.json"
DESIGN_ARG_SET=0
STRICT_ARTIFACTS=0
STRICT_TRIAGE_CSV=0
STRICT_TRIAGE_DELTA_CSV=0
POLICY_PROBE_JSON="reports/native_policy_probe_auto.json"
POLICY_HISTORY_JSONL="reports/native_policy_probe_history.jsonl"
POLICY_SUMMARY_MD="reports/native_policy_summary.md"
POLICY_HISTORY_CSV="reports/native_policy_history.csv"
POLICY_TRIAGE_CSV=""
POLICY_TRIAGE_DELTA_CSV=""
TRIAGE_CSV_ARG_SET=0
TRIAGE_DELTA_CSV_ARG_SET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict-artifacts)
      STRICT_ARTIFACTS=1
      shift
      ;;
    --strict-triage-csv)
      STRICT_TRIAGE_CSV=1
      shift
      ;;
    --strict-triage-delta-csv)
      STRICT_TRIAGE_DELTA_CSV=1
      shift
      ;;
    --native-policy-probe-json)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "[FAIL] Missing value for --native-policy-probe-json" >&2
        exit 2
      fi
      POLICY_PROBE_JSON="$2"
      shift 2
      ;;
    --native-policy-history-jsonl)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "[FAIL] Missing value for --native-policy-history-jsonl" >&2
        exit 2
      fi
      POLICY_HISTORY_JSONL="$2"
      shift 2
      ;;
    --native-policy-summary-markdown)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "[FAIL] Missing value for --native-policy-summary-markdown" >&2
        exit 2
      fi
      POLICY_SUMMARY_MD="$2"
      shift 2
      ;;
    --native-policy-history-csv)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "[FAIL] Missing value for --native-policy-history-csv" >&2
        exit 2
      fi
      POLICY_HISTORY_CSV="$2"
      shift 2
      ;;
    --native-policy-triage-csv)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "[FAIL] Missing value for --native-policy-triage-csv" >&2
        exit 2
      fi
      POLICY_TRIAGE_CSV="$2"
      TRIAGE_CSV_ARG_SET=1
      shift 2
      ;;
    --native-policy-triage-delta-csv)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "[FAIL] Missing value for --native-policy-triage-delta-csv" >&2
        exit 2
      fi
      POLICY_TRIAGE_DELTA_CSV="$2"
      TRIAGE_DELTA_CSV_ARG_SET=1
      shift 2
      ;;
    --help|-h)
      cat <<'EOF'
Usage: ./scripts/check_all_local.sh [design.json] [options]

Options:
  --strict-artifacts                    Run strict artifact checker after tolerant run
  --strict-triage-csv                   Require triage combined CSV in strict checker
  --strict-triage-delta-csv             Require triage delta CSV in strict checker
  --native-policy-probe-json PATH       Probe JSON path (default reports/native_policy_probe_auto.json)
  --native-policy-history-jsonl PATH    History JSONL path (default reports/native_policy_probe_history.jsonl)
  --native-policy-summary-markdown PATH Summary markdown path (default reports/native_policy_summary.md)
  --native-policy-history-csv PATH      History CSV path (default reports/native_policy_history.csv)
  --native-policy-triage-csv PATH       Triage combined CSV path (requires --strict-triage-csv; default reports/native_policy_triage.csv)
  --native-policy-triage-delta-csv PATH Triage delta CSV path (requires --strict-triage-delta-csv; default reports/native_policy_triage_delta.only.csv)
EOF
      exit 0
      ;;
    --*)
      echo "[FAIL] Unknown option: $1" >&2
      exit 2
      ;;
    *)
      if [[ "$DESIGN_ARG_SET" -eq 1 ]]; then
        echo "[FAIL] Multiple design paths provided: '$DESIGN' and '$1'" >&2
        exit 2
      fi
      DESIGN="$1"
      DESIGN_ARG_SET=1
      shift
      ;;
  esac
done

if [[ "$STRICT_ARTIFACTS" -eq 0 && ( "$STRICT_TRIAGE_CSV" -eq 1 || "$STRICT_TRIAGE_DELTA_CSV" -eq 1 ) ]]; then
  echo "[FAIL] --strict-triage-csv/--strict-triage-delta-csv require --strict-artifacts" >&2
  exit 2
fi

if [[ "$TRIAGE_CSV_ARG_SET" -eq 1 && -z "$POLICY_TRIAGE_CSV" ]]; then
  echo "[FAIL] --native-policy-triage-csv was provided but is empty" >&2
  exit 2
fi

if [[ "$TRIAGE_DELTA_CSV_ARG_SET" -eq 1 && -z "$POLICY_TRIAGE_DELTA_CSV" ]]; then
  echo "[FAIL] --native-policy-triage-delta-csv was provided but is empty" >&2
  exit 2
fi

if [[ "$STRICT_TRIAGE_CSV" -eq 0 && "$TRIAGE_CSV_ARG_SET" -eq 1 ]]; then
  echo "[FAIL] --native-policy-triage-csv requires --strict-triage-csv" >&2
  exit 2
fi

if [[ "$STRICT_TRIAGE_DELTA_CSV" -eq 0 && "$TRIAGE_DELTA_CSV_ARG_SET" -eq 1 ]]; then
  echo "[FAIL] --native-policy-triage-delta-csv requires --strict-triage-delta-csv" >&2
  exit 2
fi

if [[ "$STRICT_TRIAGE_DELTA_CSV" -eq 1 && -z "$POLICY_TRIAGE_DELTA_CSV" ]]; then
  POLICY_TRIAGE_DELTA_CSV="reports/native_policy_triage_delta.only.csv"
  echo "[INFO] Using default delta triage CSV path: $POLICY_TRIAGE_DELTA_CSV"
fi

if [[ "$STRICT_TRIAGE_CSV" -eq 1 && -z "$POLICY_TRIAGE_CSV" ]]; then
  POLICY_TRIAGE_CSV="reports/native_policy_triage.csv"
  echo "[INFO] Using default triage CSV path: $POLICY_TRIAGE_CSV"
fi

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

"$SCRIPT_DIR/check_all.sh" "$DESIGN"

if [[ "$STRICT_ARTIFACTS" -eq 1 ]]; then
  PS_CMD=""
  if command -v powershell >/dev/null 2>&1; then
    PS_CMD="powershell"
  elif command -v powershell.exe >/dev/null 2>&1; then
    PS_CMD="powershell.exe"
  elif command -v pwsh >/dev/null 2>&1; then
    PS_CMD="pwsh"
  elif command -v pwsh.exe >/dev/null 2>&1; then
    PS_CMD="pwsh.exe"
  fi

  if [[ -z "$PS_CMD" ]]; then
    echo "[FAIL] Strict artifacts require PowerShell (powershell/pwsh) in PATH." >&2
    exit 127
  fi

  checker="$SCRIPT_DIR/check_native_policy_artifacts.ps1"
  if [[ ! -f "$checker" ]]; then
    echo "[FAIL] Missing script: $checker" >&2
    exit 1
  fi

  checker_arg="$checker"
  if command -v wslpath >/dev/null 2>&1; then
    checker_arg="$(wslpath -w "$checker")"
  elif command -v cygpath >/dev/null 2>&1 && [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* || "${MSYSTEM:-}" != "" ]]; then
    checker_arg="$(cygpath -w "$checker")"
  fi

  args=(
    -NoProfile
    -NonInteractive
    -ExecutionPolicy Bypass
    -File "$checker_arg"
    -ProbeJson "$POLICY_PROBE_JSON"
    -HistoryJsonl "$POLICY_HISTORY_JSONL"
    -SummaryMarkdown "$POLICY_SUMMARY_MD"
    -HistoryCsv "$POLICY_HISTORY_CSV"
    -RequireMarkdown
    -RequireCsv
  )

  if [[ "$STRICT_TRIAGE_CSV" -eq 1 ]]; then
    args+=( -RequireTriageCsv )
  fi
  if [[ "$STRICT_TRIAGE_DELTA_CSV" -eq 1 ]]; then
    args+=( -RequireTriageDeltaCsv )
  fi
  if [[ "$STRICT_TRIAGE_CSV" -eq 1 && -n "$POLICY_TRIAGE_CSV" ]]; then
    args+=( -TriageCsv "$POLICY_TRIAGE_CSV" )
  fi
  if [[ "$STRICT_TRIAGE_DELTA_CSV" -eq 1 && -n "$POLICY_TRIAGE_DELTA_CSV" ]]; then
    args+=( -TriageDeltaCsv "$POLICY_TRIAGE_DELTA_CSV" )
  fi

  echo "[INFO] Running strict native policy artifact check..."
  "$PS_CMD" "${args[@]}"
  ps_exit=$?
  if [[ "$ps_exit" -ne 0 ]]; then
    echo "[FAIL] Strict native policy artifact check failed with exit code $ps_exit" >&2
    exit "$ps_exit"
  fi
fi

echo "[OK] All requested checks completed."
