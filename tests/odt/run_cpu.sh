#!/bin/bash
# Full procedure for one CPU: 3 suite passes, negative control, reset check.
# Usage: run_cpu.sh CPU_NUMBER RESULTS_DIR [--wait-banner]
set -u
cpu=$1; out=$2; wait=${3:-}
cd "$(dirname "$0")"
rc=0
python3 -u suite.py --cpu "$cpu" --out "$out" --passes 3 $wait || rc=1
python3 -u suite.py --cpu "$cpu" --out "$out" --passes 1 --negative-control || rc=1
python3 -u suite.py --cpu "$cpu" --out "$out" --reset-check || rc=1
echo "CPU $cpu OVERALL: $([ $rc = 0 ] && echo PASS || echo FAIL)"
exit $rc
