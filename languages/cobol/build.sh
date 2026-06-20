#!/usr/bin/env bash
# Build the payroll report processor with GnuCOBOL.
#   cobc -x        : create an executable program (not a .so module)
#   -free          : free source format (matches '>>SOURCE FORMAT FREE')
#   -Wall          : turn on the helpful warning set
#   -o bin/payroll : output path
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if ! command -v cobc >/dev/null 2>&1; then
  echo "ERROR: 'cobc' (GnuCOBOL) is not installed." >&2
  echo "Install it, then re-run:" >&2
  echo "  Arch/CachyOS : sudo pacman -S gnucobol" >&2
  echo "  Debian/Ubuntu: sudo apt-get install gnucobol" >&2
  echo "  macOS (brew) : brew install gnucobol" >&2
  exit 127
fi

mkdir -p bin
echo "cobc $(cobc --version | head -1)"
cobc -x -free -Wall -o bin/payroll src/payroll.cob
echo "Built: $HERE/bin/payroll"
