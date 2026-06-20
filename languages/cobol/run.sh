#!/usr/bin/env bash
# Build (if needed) and run the payroll report.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

bash "$HERE/build.sh"
echo "-------------------------------------------------------------------"
"$HERE/bin/payroll"
