# SPDX-License-Identifier: MIT
GALETTE ?= galette
PYTHON ?= python3
KICAD_CLI ?= kicad-cli

.PHONY: all build check check-wiring

all: check

build: odt_bridge.pld
	mkdir -p build
	cp odt_bridge.pld build/odt_bridge.pld
	$(GALETTE) -c -f -p build/odt_bridge.pld

check: build
	$(PYTHON) check_bridge.py --jed build/odt_bridge.jed
	$(PYTHON) check_bridge.py --jed odt_bridge.jed
	cmp build/odt_bridge.jed odt_bridge.jed

check-wiring: check
	$(KICAD_CLI) sch export netlist --format kicadxml --output build/wiring.xml ../../kicad/rig/rig.kicad_sch
	$(PYTHON) check_bridge.py --jed build/odt_bridge.jed --netlist build/wiring.xml
