#!/usr/bin/env python3
"""Recheck saved component measurements without accessing any hardware."""
import hashlib
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)


def main():
    if not __debug__:
        raise RuntimeError('Run without -O: component checks use assertions.')
    for line in (HERE / 'SHA256SUMS.txt').read_text().splitlines():
        expected, name = line.split('  ', 1)
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Changed measurement or design file: {name}')
    print('Recorded measurements and design hashes match.', flush=True)
    run(ROOT / 'logic/gal/check_bridge.py')
    for name in ('74f821', '74ahct14', '74ahct541'):
        case = HERE / name
        run(case / 'check.py', '--prepare')
        run(case / 'check.py', '--check', case / 'measured.xml')
    case = HERE / 'gal20v8'
    run(case / 'check.py', '--vectors')
    run(case / 'check.py', '--compare', case / 'readback.jed')
    run(case / 'check.py', '--logic-check', case / 'measured.xml')
    case = HERE / 'dc319'
    run(case / 'check.py', '--prepare')
    for name in ('reset-measured.xml', 'registers-measured.xml', 'clock-measured.xml'):
        run(case / 'check.py', '--analyze', case / name)
    run(case / 'serial_frames.py')
    print('Saved measurements match the checked expectations.')
    print('DC319 nominal-clock operation and assembled-board operation remain unverified.')


if __name__ == '__main__':
    main()
