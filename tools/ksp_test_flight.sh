#!/usr/bin/env bash
# Teste automático: espera o menu principal do KSP, carrega o save "gargantua_test",
# entra na tracking station e voa a nave da posição IDX da lista.
# Uso: tools/ksp_test_flight.sh [saida.png] [IDX]
# Requer o universal-modder (`um win ...`) e a janela do KSP em 2560x1080.
# shortcut: coordenadas fixas para 2560x1080 e para a ordem atual dos saves; para outra resolução, medir de novo.
set -euo pipefail
KSP="/c/Program Files (x86)/Steam/steamapps/common/Kerbal Space Program"
L="$KSP/KSP.log"
OUT="${1:-$TEMP/ksp_flight.png}"
IDX="${2:-0}"  # posição da nave na lista da tracking station (0 = primeira)
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
sleep 10  # a animação do menu engole cliques logo no início
drive "click 944 516" "sleep 2500"                         # Iniciar jogo
drive "click 1080 378" "sleep 2500"                        # Retomar jogo salvo (o texto anima; centro estável)
drive "click 1280 492" "sleep 800" "click 1426 780"        # gargantua_test -> Carregar
wait_for SPACECENTER 240; sleep 8
drive "click 1700 540"                                     # Tracking station
wait_for TRACKSTATION 120; sleep 15
drive "click 678 90" "sleep 600" "click 140 $Y" "sleep 1200" "click 204 1048"  # fecha MemGraph, nave, Voar
wait_for FLIGHT 180; sleep 25
um win shot --exe KSP_x64.exe "$OUT" --scale 0.5 | tail -1
