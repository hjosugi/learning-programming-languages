#!/usr/bin/env bash
# Test suite for the payroll report processor.
#
# Two modes, auto-selected:
#   * cobc INSTALLED  -> the REAL test: compile, run, and golden-diff actual
#                        output against expected_output.txt, plus targeted
#                        assertions on individual computed/edited values.
#   * cobc MISSING    -> a STRUCTURAL test: verify the COBOL source contains
#                        every required language feature and that the golden
#                        file is internally consistent. (GnuCOBOL could not be
#                        installed on the authoring machine; see README.)
#
# Exits NON-ZERO on any failure in either mode.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

SRC="$HERE/src/payroll.cob"
EXPECTED="$HERE/expected_output.txt"
PASS=0
FAIL=0

ok()   { printf '  ok   - %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  FAIL - %s\n' "$1"; FAIL=$((FAIL+1)); }

# assert_in PATTERN FILE MSG   (pattern is a fixed string)
assert_in() {
  if grep -qF -- "$1" "$2"; then ok "$3"; else bad "$3 (missing: $1)"; fi
}
# assert_re PATTERN FILE MSG   (pattern is an ERE)
assert_re() {
  if grep -qE -- "$1" "$2"; then ok "$3"; else bad "$3 (no match: $1)"; fi
}

echo "=== learning-cobol :: payroll test suite ==="

# --------------------------------------------------------------------------
# Structural checks (always run; cheap and catch source regressions).
# --------------------------------------------------------------------------
echo "[structure] required COBOL features present in source"
assert_in "IDENTIFICATION DIVISION." "$SRC" "IDENTIFICATION DIVISION present"
assert_in "ENVIRONMENT DIVISION."    "$SRC" "ENVIRONMENT DIVISION present"
assert_in "DATA DIVISION."           "$SRC" "DATA DIVISION present"
assert_in "PROCEDURE DIVISION."      "$SRC" "PROCEDURE DIVISION present"
assert_in "WORKING-STORAGE SECTION." "$SRC" "WORKING-STORAGE SECTION present"
assert_in "OCCURS 6 TIMES"           "$SRC" "OCCURS table declared"
assert_in "PERFORM VARYING"          "$SRC" "PERFORM VARYING loop present"
assert_in "EVALUATE TRUE"            "$SRC" "EVALUATE (switch) present"
assert_re "PIC +S9\(7\)V99 +COMP-3"  "$SRC" "packed-decimal (COMP-3) numeric PIC"
assert_re "PIC +X\("                  "$SRC" "alphanumeric PIC (X) present"
assert_in '$$$,$$9.99'               "$SRC" "floating-currency edited PIC"
assert_in "ZZ9.99"                   "$SRC" "zero-suppressed edited PIC"
assert_in '$*,***,**9.99'            "$SRC" "check-protection (*) edited PIC"
assert_in 'CR'                       "$SRC" "credit-symbol (CR) edited PIC"
assert_in "88  EMP-WORKED"           "$SRC" "88-level condition name"
assert_in "COMPUTE WS-OT-PAY ROUNDED" "$SRC" "ROUNDED money arithmetic"

echo "[structure] golden file is present and well-formed"
if [[ -f "$EXPECTED" ]]; then ok "expected_output.txt exists"; else bad "expected_output.txt missing"; fi
assert_in "ACME CORP - WEEKLY PAYROLL REPORT" "$EXPECTED" "report banner in golden file"
assert_in "GRAND TOTALS"                       "$EXPECTED" "grand totals line in golden file"
# Spot-check a few hand-verified computed values in the golden file.
assert_in '$1,955.00' "$EXPECTED" "emp 1001 gross = \$1,955.00 (40*42.50 + 4*42.50*1.5)"
assert_in '$835.20'   "$EXPECTED" "emp 1003 tax   = \$835.20 (2784.00 * 30%)"
assert_in '$8,244.67' "$EXPECTED" "grand total net = \$8,244.67"
assert_in '$****1,648.93' "$EXPECTED" "average net check-protected = \$****1,648.93"

# --------------------------------------------------------------------------
# Behavioural checks: only meaningful when cobc is available.
# --------------------------------------------------------------------------
if command -v cobc >/dev/null 2>&1; then
  echo "[compile/run] cobc found -> golden-diff test"
  mkdir -p bin
  if cobc -x -free -Wall -o bin/payroll "$SRC" 2> "$HERE/.cobc-warnings.txt"; then
    ok "cobc compiled cleanly"
  else
    bad "cobc failed to compile"
    cat "$HERE/.cobc-warnings.txt" >&2
  fi
  if [[ -x "$HERE/bin/payroll" ]]; then
    "$HERE/bin/payroll" > "$HERE/.actual_output.txt" 2>&1 || bad "program exited non-zero"
    if diff -u "$EXPECTED" "$HERE/.actual_output.txt"; then
      ok "actual output matches expected_output.txt (byte-for-byte)"
    else
      bad "actual output differs from expected_output.txt (see diff above)"
    fi
    # Targeted value assertions against real output.
    assert_in '  GRAND TOTALS' "$HERE/.actual_output.txt" "totals line emitted by program"
    assert_in '$8,244.67'      "$HERE/.actual_output.txt" "program computed grand total net"
  fi
else
  echo "[compile/run] cobc NOT found -> structural mode only"
  echo "             install with: sudo pacman -S gnucobol   (Arch/CachyOS)"
  echo "             then re-run this script for the full golden-diff test."
fi

echo "-------------------------------------------------------------------"
echo "passed: $PASS   failed: $FAIL"
[[ $FAIL -eq 0 ]] || exit 1
echo "ALL TESTS PASSED"
