"""Local readback checks and T48 vectors; no programming operations."""
import argparse
import hashlib
import itertools
from pathlib import Path
import random
import re
import sys
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
HERE = BASE / 'build'
LOGIC = BASE.parents[2] / 'logic/gal'
sys.path.insert(0, str(LOGIC))
import check_bridge as reference


def parse_jed(path):
    data = Path(path).read_bytes()
    assert data.count(b'\x02') == data.count(b'\x03') == 1
    start, end = data.index(b'\x02'), data.index(b'\x03')
    assert sum(data[start:end + 1]) & 65535 == int(data[end + 1:].strip(), 16)
    records = [x.strip() for x in data[start + 1:end].decode('ascii').split('*')[1:] if x.strip()]
    assert records.count('QF2706') == 1
    assert records.count('G0') == 1
    defaults = [r for r in records if re.fullmatch(r'F[01]', r)]
    assert len(defaults) == 1
    fuses = [int(defaults[0][1])] * 2706
    used = set()
    checksum = []
    for r in records:
        if r in ('QP24', 'QF2706', 'G0', defaults[0]):
            continue
        if re.fullmatch(r'C[0-9A-Fa-f]{4}', r):
            checksum.append(int(r[1:], 16))
            continue
        match = re.fullmatch(r'L(\d+)\s+([01\s]+)', r)
        assert match, r
        address = int(match[1])
        for i, bit in enumerate(''.join(match[2].split())):
            k = address + i
            assert k < 2706 and k not in used
            used.add(k)
            fuses[k] = int(bit)
    total = sum(sum(b << k for k, b in enumerate(fuses[i:i + 8])) for i in range(0, 2706, 8)) & 65535
    assert checksum == [total], (checksum, total)
    return fuses


def canonical_jed(fuses):
    total = sum(sum(b << k for k, b in enumerate(fuses[i:i + 8])) for i in range(0, 2706, 8)) & 65535
    text = '\x02\nIndependent canonical readback\n*F0\n*G0\n*QF2706\n'
    for i in range(0, 2706, 64):
        text += '*L%04d %s\n' % (i, ''.join(str(x) for x in fuses[i:i + 64]))
    text += '*C%04X\n*\n\x03' % total
    encoded = text.encode('ascii')
    return encoded + ('%04X\n' % (sum(encoded) & 65535)).encode('ascii')


def expected(p):
    a = p[1] * 8 + p[2] * 4 + p[3] * 2 + p[4]
    bank = p[6] * 2 + p[5]
    return {15: int(not (8 <= a <= 12 and p[8] == 0)),
            16: 0, 17: 0,
            18: int(not (0 <= a <= 3 and p[9] == 0 and p[7] == 0)),
            19: 0, 20: 0, 21: int(bank != 2), 22: int(a != 14)}


def make_vector(p):
    assert set(p) == set(reference.INPUTS)
    output = expected(p)
    assert output == reference.contract(p)
    vector = [None] * 24
    for pin, level in p.items():
        vector[pin - 1] = str(level)
    for pin, level in output.items():
        vector[pin - 1] = 'H' if level else 'L'
    vector[11], vector[23] = 'G', 'V'
    assert all(x in '01HLGV' for x in vector)
    assert vector.count('G') == vector.count('V') == 1
    assert sum(x in 'HL' for x in vector) == 8
    return vector


def vectors():
    HERE.mkdir(parents=True, exist_ok=True)
    full = [dict(zip(reference.INPUTS, bits)) for bits in itertools.product((0, 1), repeat=14)]
    assert len({tuple(p.values()) for p in full}) == 16384
    smoke = [p for p in full if all(p[i] == 0 for i in (10, 11, 13, 14, 23))]
    assert len(smoke) == 512
    random.Random(20261025).shuffle(full)
    root = ET.Element('logicic')
    db = ET.SubElement(root, 'database', type='LOGIC')
    manufacturer = ET.SubElement(db, 'manufacturer', name='DCJrig local verification')
    for name, rows in [('DCJRIG_ODT_SMOKE', smoke), ('DCJRIG_ODT_EXHAUSTIVE', full)]:
        ic = ET.SubElement(manufacturer, 'ic', name=name, type='5', voltage='5V', pins='24')
        for i, p in enumerate(rows):
            ET.SubElement(ic, 'vector', id=str(i)).text = ' '.join(make_vector(p))
    ic = ET.SubElement(manufacturer, 'ic', name='DCJRIG_ODT_NEGATIVE_CONTROL', type='5', voltage='5V', pins='24')
    row = make_vector(smoke[0])
    assert row[14] == 'H'
    row[14] = 'L'  # Incorrect expectation only; this pin remains an input to the tester.
    ET.SubElement(ic, 'vector', id='0').text = ' '.join(row)
    ET.indent(root)
    ET.ElementTree(root).write(HERE / 'vectors.xml', encoding='utf-8', xml_declaration=True)
    print('Prepared 512 board vectors, 16384 exhaustive vectors, and one intentional negative control.')
    print('All 8 outputs are observed; only 14 GAL inputs are driven; pin 12 GND, pin 24 +5 V.')


def compare(path):
    want = parse_jed(LOGIC / 'odt_bridge.jed')
    got = parse_jed(path)
    differences = [i for i, pair in enumerate(zip(want, got)) if pair[0] != pair[1]]
    assert not differences, 'Differing fuse addresses: ' + str(differences)
    HERE.mkdir(parents=True, exist_ok=True)
    dest = HERE / 'readback.canonical.jed'
    dest.write_bytes(canonical_jed(got))
    assert reference.read_jedec(dest) == got
    print('PASS: all 2706 fuse bits match, including architecture, output polarity, row enables and UES.')
    print('PASS: transmission and fuse checksums validated independently.')
    print('Fuse-bit SHA256:', hashlib.sha256(bytes(got)).hexdigest())
    print('Canonical readback:', dest)


def check_logic(path):
    measured_root = ET.parse(path).getroot()
    measured = measured_root.find('.//ic')
    assert measured is not None and measured.attrib['pins'] == '24'
    assert measured.attrib['voltage'] == '5V'
    name = measured.attrib['name']
    assert name in ('DCJRIG_ODT_SMOKE', 'DCJRIG_ODT_EXHAUSTIVE')
    expected_ic = next(x for x in ET.parse(HERE / 'vectors.xml').getroot().iter('ic')
                       if x.attrib['name'] == name)
    observed_rows = measured.findall('vector')
    expected_rows = expected_ic.findall('vector')
    count = 512 if name == 'DCJRIG_ODT_SMOKE' else 16384
    assert len(observed_rows) == len(expected_rows) == count
    observed_inputs = set()
    counts = {p: {'H': 0, 'L': 0} for p in reference.OUTPUTS}
    for i, (want, got) in enumerate(zip(expected_rows, observed_rows)):
        assert int(want.attrib['id']) == int(got.attrib['id']) == i
        w, g = want.text.split(), got.text.split()
        assert len(w) == len(g) == 24
        assert w == g, f'Vector {i}: wanted {w}, measured {g}'
        observed_inputs.add(tuple(g[p - 1] for p in reference.INPUTS))
        for p in reference.OUTPUTS:
            counts[p][g[p - 1]] += 1
    assert len(observed_inputs) == count
    print(f'PASS: {count} unique input combinations, all 8 physical output pins match.')
    print(f'{count * 8} output decisions, each sampled with pull-up and pull-down by T48.')
    for pin, states in counts.items():
        print(f'Pin {pin}: H={states["H"]}, L={states["L"]}, Z=0, mismatch=0')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vectors', action='store_true')
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--logic-check', type=Path)
    args = parser.parse_args()
    if args.vectors:
        vectors()
    if args.compare:
        compare(args.compare)
    if args.logic_check:
        check_logic(args.logic_check)
