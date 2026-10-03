#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$project_root"
mkdir -p docs/images
"${KICAD_CLI:-kicad-cli}" pcb render \
  --output docs/images/dcjrig-board.png \
  --width 2400 --height 2000 --side top \
  --background transparent --quality high --floor --perspective \
  --rotate '-35,0,65' --pan 0,0.8,0 --zoom 0.80 --use-board-stackup-colors \
  --light-top 0.40 --light-side 0.30 --light-camera 0.20 \
  -D "KIPRJMOD=$project_root/kicad/rig" \
  kicad/rig/rig.kicad_pcb
