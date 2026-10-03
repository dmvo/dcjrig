#!/usr/bin/env python3
"""Read-only height check for components in the DCJ11 socket gap.

Usage: python3 mechanical/zif/check_height.py [board.kicad_pcb]
Set each affected component's Height_mm field to its maximum assembled height
ABOVE the PCB, including a socket, spacers and tolerances. No 3D collision claim:
the script checks declared heights; it does not infer them from rendering meshes.
Exit 0 = all affected components checked; 1 = height/geometry unknown or fails;
2 = missing footprint/area, wrong board or unavailable KiCad Python runtime.
"""
from pathlib import Path
import os
import re
import sys
import tempfile
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[2]
NAME = 'DCJ11_DIP60_2xTextool_264-4493_ZIF'
AREA = 'DCJ11_UNDER_CPU_H11'
LIMIT = Decimal('11')


def import_kicad():
    try:
        import pcbnew
        if int(pcbnew.Version().split('.')[0]) >= 10:
            return pcbnew
    except ImportError:
        pass
    # This workspace uses a private KiCad installation with its own Python.
    runtime = Path.home()/'.local/opt/kicad/current/AppDir/AppRun'
    if runtime.exists() and not os.environ.get('DCJRIG_HEIGHT_RUNTIME'):
        env = dict(os.environ, DCJRIG_HEIGHT_RUNTIME='1')
        with tempfile.TemporaryDirectory(prefix='dcjrig-height-') as tmp:
            import subprocess
            env['KICAD_CONFIG_HOME'] = tmp
            result = subprocess.run([str(runtime), 'python3.11', str(Path(__file__).resolve()),
                                     *sys.argv[1:]], env=env)
        raise SystemExit(result.returncode)
    raise SystemExit('Need KiCad 10 Python (pcbnew); no compatible runtime found.')


def overlap(pcbnew, a, b):
    poly = pcbnew.SHAPE_POLY_SET(a)
    poly.BooleanIntersection(b)
    return poly.OutlineCount() > 0


def bounds_poly(pcbnew, fp):
    # Only used conservatively to locate parts lacking a valid courtyard.
    bb = fp.GetBoundingBox(False, False)
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    for x,y in [(bb.GetLeft(),bb.GetTop()),(bb.GetRight(),bb.GetTop()),
                (bb.GetRight(),bb.GetBottom()),(bb.GetLeft(),bb.GetBottom())]:
        p.Append(x,y)
    return p


def run(board_path, pcbnew):
    board = pcbnew.LoadBoard(str(board_path))
    if not board:
        print('Cannot load board:', board_path)
        return 2
    footprints = list(board.GetFootprints())
    cpus = [f for f in footprints if str(f.GetFPID().GetLibItemName()) == NAME]
    if not cpus:
        print('No DCJ11 paired-ZIF footprint found. Check the footprint assigned to U1.')
        return 2
    failures, checked = 0, 0
    for cpu in cpus:
        areas = [z for z in cpu.Zones() if z.GetZoneName() == AREA]
        if len(areas) != 1:
            print(f'{cpu.GetReference()}: height area missing; update footprint from library.')
            return 2
        area = areas[0].Outline()
        layer = pcbnew.F_CrtYd if cpu.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd
        for fp in footprints:
            if fp == cpu or fp.GetLayer() != cpu.GetLayer():
                continue
            fp.BuildCourtyardCaches()
            poly = fp.GetCourtyard(layer)
            missing_outline = poly.OutlineCount() == 0
            if missing_outline:
                poly = bounds_poly(pcbnew, fp)
            if not overlap(pcbnew, area, poly):
                continue
            checked += 1
            ref = fp.GetReference()
            if missing_outline:
                print(f'UNKNOWN {ref}: no valid courtyard; bounding box intersects CPU area.')
                failures += 1
                continue
            raw = fp.GetFieldText('Height_mm') if fp.HasField('Height_mm') else ''
            m = re.fullmatch(r'\s*(\d+(?:[.,]\d+)?)\s*(?:mm)?\s*', raw)
            if not m or Decimal(m[1].replace(',','.')) <= 0:
                print(f'UNKNOWN {ref}: set Height_mm to maximum assembled height including socket.')
                failures += 1
                continue
            height = Decimal(m[1].replace(',','.'))
            if height > LIMIT:
                print(f'FAIL {ref}: {height} mm > {LIMIT} mm under {cpu.GetReference()}.')
                failures += 1
            else:
                print(f'OK {ref}: {height} mm <= {LIMIT} mm (allowance {LIMIT-height} mm).')
    print(f'Checked {checked} components; {failures} failed or unknown. Declared heights only.')
    return 1 if failures else 0


if __name__ == '__main__':
    pcbnew = import_kicad()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'kicad/rig/rig.kicad_pcb'
    if not path.is_file():
        print('Board does not exist:', path)
        raise SystemExit(2)
    raise SystemExit(run(path.resolve(), pcbnew))
