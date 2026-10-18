#!/usr/bin/env bash
# Automated test: waits for the KSP main menu, loads the "gargantua_test" save,
# enters the tracking station and flies the vessel at position IDX in the list.
# Usage: tools/ksp_test_flight.sh [output.png] [IDX]
# Requires universal-modder (`um win ...`) and the KSP window at 2560x1080.
# shortcut: fixed coordinates for 2560x1080 and for the current save order; for another resolution, measure again.
set -euo pipefail
KSP="/c/Program Files (x86)/Steam/steamapps/common/Kerbal Space Program"
L="$KSP/KSP.log"
OUT="${1:-$TEMP/ksp_flight.png}"
IDX="${2:-0}"  # vessel position in the tracking station list (0 = first)
Y=$((124 + 50 * IDX))

wait_for() {  # wait_for <scene> <seconds>
  local c; c=$(grep -c "to $1" "$L" 2>/dev/null || true)
  [ "${3:-}" = "fresh" ] && c=0
  for _ in $(seq 1 "$2"); do
    [ "$(grep -c "to $1" "$L" 2>/dev/null || true)" -gt "$c" ] && return 0
    sleep 1
  done
  echo "timeout esperando $1" >&2; return 1
}

drive() { um win drive --proc KSP_x64 "focus" "$@" >/dev/null 2>&1; }

wait_for MAINMENU 1500 fresh
sleep 10  # the menu animation swallows clicks right at the start
drive "click 944 516" "sleep 2500"                         # Start Game
drive "click 1080 378" "sleep 2500"                        # Resume Saved (the text animates; its centre is stable)
drive "click 1280 492" "sleep 800" "click 1426 780"        # gargantua_test -> Load
wait_for SPACECENTER 240; sleep 8
drive "click 1700 540"                                     # Tracking station
wait_for TRACKSTATION 120; sleep 15
drive "click 678 90" "sleep 600" "click 140 $Y" "sleep 1200" "click 204 1048"  # close MemGraph, vessel, Fly
wait_for FLIGHT 180; sleep 25
um win shot --exe KSP_x64.exe "$OUT" --scale 0.5 | tail -1
