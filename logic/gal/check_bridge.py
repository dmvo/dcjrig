#!/usr/bin/env python3
"""Check ODT bridge equations and GAL20V8A fuses against the bus contract.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Dimitri Varpusvuori

Uses only the Python standard library. Does not import the assembler or
use its pin/fuse reports. The fuse layout comes from Lattice's 1992
GAL20V8A/B data sheet, printed pages 2-32 and 2-33.
"""

import argparse
import itertools
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from prove_minimal import prove_minimum


PINS = (
    "AIO3 AIO2 AIO1 AIO0 BS0 BS1 nSCTL nBUF ADDR0 TIE10 TIE11 GND "
    "TIE13 TIE14 nREAD PARK16 PARK17 nWRITE PARK19 PARK20 nSELECT nBOOT TIE23 VCC"
).split()
INPUTS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 23)
OUTPUTS = tuple(range(15, 23))
FUNCTIONAL = (15, 18, 21, 22)
PARKED = (16, 17, 19, 20)
# Lattice simple-mode AND array: column for each non-inverted input.
# Its complement is the next column. The other columns are feedback paths.
COLUMNS = {1: 2, 2: 0, 3: 4, 4: 8, 5: 12, 6: 16, 7: 20, 8: 24,
           9: 28, 10: 32, 11: 36, 13: 38, 14: 34, 23: 6}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def contract(levels):
    """Pin levels required by DEC's transaction and bank tables.

    Numeric code sets deliberately avoid the source's Boolean expressions.
    All returned values are physical output levels, including active-low pins.
    """
    cycle = sum(levels[pin] << (4 - pin) for pin in range(1, 5))
    bank = 2 * levels[6] + levels[5]
    read_cycle = cycle in {8, 9, 10, 11, 12}
    write_cycle = cycle in {0, 1, 2, 3}
    return {
        15: int(not (read_cycle and levels[8] == 0)),
        16: 0,
        17: 0,
        18: int(not (write_cycle and levels[9] == 0 and levels[7] == 0)),
        19: 0,
        20: 0,
        21: int(bank != 2),
        22: int(cycle != 14),
    }


def read_source(path):
    lines = [line.split(';', 1)[0].strip() for line in path.read_text().splitlines()]
    lines = [line for line in lines if line]
    require(lines[0] == 'GAL20V8', 'Source must target GAL20V8')
    require(lines[2].split() + lines[3].split() == PINS, 'Source pin order changed')
    equations = []
    for line in lines[4:]:
        if line == 'DESCRIPTION':
            break
        if line.startswith('+'):
            require(bool(equations), 'Continuation without an equation')
            equations[-1] += line
        else:
            equations.append(line)
    parsed = {}
    inputs = {PINS[pin - 1] for pin in INPUTS} | {'GND', 'VCC'}
    for equation in equations:
        match = re.fullmatch(r'(/?)([A-Za-z][A-Za-z0-9]*)\s*=\s*(.+)', equation)
        require(match is not None, 'Unsupported equation: ' + equation)
        slash, name, expression = match.groups()
        require(name in PINS[14:22], 'Equation must drive an output: ' + name)
        pin = PINS.index(name) + 1
        require(pin not in parsed, 'Duplicate equation: ' + name)
        terms = []
        for term in expression.split('+'):
            literals = []
            for literal in term.split('*'):
                literal = literal.strip()
                require(re.fullmatch(r'/?[A-Za-z][A-Za-z0-9]*', literal),
                        'Unsupported literal: ' + literal)
                variable = literal.lstrip('/')
                require(variable in inputs, 'Not an input or constant: ' + variable)
                literals.append((variable, literal.startswith('/')))
            terms.append(literals)
        parsed[pin] = (bool(slash), terms)
    require(set(parsed) == set(OUTPUTS), 'Every output needs an equation')
    return parsed, lines[1]


def evaluate_source(equations, levels):
    signals = {PINS[pin - 1]: bool(level) for pin, level in levels.items()}
    signals.update(GND=False, VCC=True)
    result = {}
    for pin, (invert, terms) in equations.items():
        value = any(all(signals[name] != negative for name, negative in term)
                    for term in terms)
        result[pin] = int(value != invert)
    return result


def read_jedec(path):
    data = path.read_bytes()
    require(data.count(b'\x02') == data.count(b'\x03') == 1,
            'JEDEC must have one STX/ETX frame')
    start, end = data.index(b'\x02'), data.index(b'\x03')
    require(start < end, 'Invalid JEDEC framing')
    tail = data[end + 1:].strip()
    require(re.fullmatch(rb'[0-9a-fA-F]{4}', tail), 'Missing transmission checksum')
    require(sum(data[start:end + 1]) & 0xffff == int(tail, 16),
            'JEDEC transmission checksum mismatch')
    # galette writes a descriptive header, followed by star-separated records.
    records = [r.strip() for r in data[start + 1:end].decode('ascii').split('*')[1:]]
    records = [r for r in records if r]
    require(records.count('QF2706') == 1, 'Expected 2706 GAL20V8 fuses')
    require(records.count('G0') == 1, 'Security fuse must be disabled')
    defaults = [r for r in records if re.fullmatch(r'F[01]', r)]
    require(len(defaults) == 1, 'Expected one default-fuse record')
    fuses = [int(defaults[0][1])] * 2706
    assigned = set()
    checksums = []
    for record in records:
        if record in {'QF2706', 'G0', defaults[0]}:
            continue
        if re.fullmatch(r'C[0-9a-fA-F]{4}', record):
            checksums.append(int(record[1:], 16))
            continue
        match = re.fullmatch(r'L(\d+)\s+([01\s]+)', record)
        require(match is not None, 'Unsupported JEDEC record: ' + record)
        address = int(match[1])
        bits = ''.join(match[2].split())
        for offset, bit in enumerate(bits):
            index = address + offset
            require(index < len(fuses) and index not in assigned,
                    'Overlapping or out-of-range fuse address')
            assigned.add(index)
            fuses[index] = int(bit)
    packed = [sum(bit << j for j, bit in enumerate(fuses[i:i + 8]))
              for i in range(0, len(fuses), 8)]
    require(checksums == [sum(packed) & 0xffff], 'JEDEC fuse checksum mismatch')
    require(fuses[2704:] == [1, 0], 'Expected simple combinatorial mode')
    require(fuses[2632:2640] == [0] * 8, 'All eight pads must be driven outputs')
    return fuses


def decode_terms(fuses):
    """Decode the AND plane without reading the .pld expressions."""
    wires = {}
    for pin, column in COLUMNS.items():
        wires[column] = (pin, 1)
        wires[column + 1] = (pin, 0)
    products = []
    for row in range(64):
        bits = fuses[row * 40:(row + 1) * 40]
        # A connected signal and its complement make this product false.
        contradictory = any(bits[c:c + 2] == [0, 0] for c in range(0, 40, 2))
        if not fuses[2640 + row] or contradictory:
            products.append(None)
            continue
        connected = [c for c, fuse in enumerate(bits) if fuse == 0]
        require(all(c in wires for c in connected),
                'Unexpected output feedback in product row ' + str(row))
        products.append([wires[c] for c in connected])
    return products


def evaluate_fuses(fuses, products, levels):
    result = {}
    for cell in range(8):
        active = any(term is not None and all(levels[p] == v for p, v in term)
                     for term in products[8 * cell:8 * cell + 8])
        result[22 - cell] = int(active if fuses[2560 + cell] else not active)
    return result


def check_wiring(path):
    root = ET.parse(path).getroot()
    values = {c.get('ref'): c.findtext('value') for c in root.findall('./components/comp')}
    gals = [ref for ref, value in values.items() if value == 'GAL20V8A-15LP']
    require(len(gals) == 1, 'Expected exactly one GAL20V8A-15LP')
    gal = gals[0]
    nets = {}
    for net in root.findall('./nets/net'):
        for node in net.findall('node'):
            key = (node.get('ref'), int(node.get('pin')))
            require(key not in nets, 'Duplicate netlist pin: ' + str(key))
            nets[key] = net.get('name')
    required = {
        1: '/LAIO3', 2: '/LAIO2', 3: '/LAIO1', 4: '/LAIO0',
        5: '/LBS0', 6: '/LBS1', 7: '/~{SCTL}', 8: '/~{BUFCTL}',
        9: '/A0', 10: 'GND', 11: 'GND', 12: 'GND', 13: 'GND', 14: 'GND',
        15: '/~{OE}', 18: '/~{WEL}', 21: '/~{IO}', 22: '/~{GPREAD}',
        23: 'GND', 24: 'VCC',
    }
    for pin, name in required.items():
        require(nets.get((gal, pin)) == name, f'{gal} pin {pin} must connect to {name}')
    for pin in PARKED:
        name = nets.get((gal, pin), '')
        require(name.startswith('unconnected-') and list(nets.values()).count(name) == 1,
                f'{gal} pin {pin} must be unconnected')
    links = {
        1: [('U4', 20)], 2: [('U4', 21)], 3: [('U4', 22)], 4: [('U4', 23)],
        5: [('U4', 19)], 6: [('U4', 18)], 7: [('U1', 38)],
        8: [('U1', 41), ('U5', 1)], 9: [('U4', 17), ('U2', 21)],
        15: [('U2', 1)],
        18: [('U2', 3)], 21: [('U2', 2)], 22: [('U5', 19)],
    }
    for pin, peers in links.items():
        for peer in peers:
            require(nets.get(peer) == nets[(gal, pin)],
                    f'{gal} pin {pin} must share a net with {peer[0]} pin {peer[1]}')
    for pin in (28, 32):
        require(nets.get(('U1', pin)) == 'GND', f'U1 pin {pin} must be grounded')
    require(nets.get(('U3', 1)) == nets[('U1', 38)], 'DV inverter must receive /SCTL')
    dv_ends = {nets[('U3', 2)], nets[('U1', 42)]}
    require(any({nets.get((ref, 1)), nets.get((ref, 2))} == dv_ends
                for ref, value in values.items() if ref.startswith('R') and value == '0'),
            'DV must connect to the inverter through a zero-ohm resistor')
    require(values.get('U3') == 'SN74AHCT14N', 'DV timing assumes SN74AHCT14N')
    print(f'Schematic: {gal} pin map, controls, grounded inputs and DV path match.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).with_name('odt_bridge.pld'))
    parser.add_argument('--jed', type=Path, default=Path(__file__).with_name('odt_bridge.jed'))
    parser.add_argument('--netlist', type=Path, help='Fresh KiCad XML netlist, optional')
    args = parser.parse_args()
    equations, signature = read_source(args.source)
    fuses = read_jedec(args.jed)
    stored_signature = ''.join(chr(int(''.join(map(str, fuses[i:i + 8])), 2))
                               for i in range(2568, 2632, 8))
    require(stored_signature == signature, 'Source and JEDEC signatures differ')
    products = decode_terms(fuses)
    for bits in itertools.product((0, 1), repeat=len(INPUTS)):
        levels = dict(zip(INPUTS, bits))
        expected = contract(levels)
        source = evaluate_source(equations, levels)
        actual = evaluate_fuses(fuses, products, levels)
        require(source == expected, f'Source mismatch for input levels {levels}: {source}')
        require(actual == expected, f'JEDEC mismatch for input levels {levels}: {actual}')
        require(actual[15] or actual[18], 'Read and write overlap')
        require(actual[15] or actual[22], 'DLART read and startup buffer overlap')
        require(actual[15] or levels[8] == 0, 'DLART read while CPU drives DAL')
    print('PASS: 512 board input combinations x 32 spare-input states = 16384 cases.')
    print('Source and JEDEC match the contract; checksums, mode and bus enables pass.')
    prove_minimum(contract, PINS, equations, products, fuses)
    if args.netlist:
        check_wiring(args.netlist)
    print('This checks steady logic levels. The logic has NOT been tested on real hardware.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ET.ParseError) as error:
        print('FAIL:', error, file=sys.stderr)
        sys.exit(1)
