"""SN74AHCT14N functional test: six independent inverters."""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
HERE = BASE / 'build'
PAIRS = ((1, 2), (3, 4), (5, 6), (9, 8), (11, 10), (13, 12))
WORDS = list(range(64)) + list(range(63, -1, -1))
NAME = 'SN74AHCT14N_FUNCTION'


def expected_rows():
    rows = []
    for word in WORDS:
        row = [None] * 14
        row[6], row[13] = 'G', 'V'
        for bit, (a, y) in enumerate(PAIRS):
            value = (word >> bit) & 1
            row[a - 1] = str(value)
            row[y - 1] = 'L' if value else 'H'
        assert all(x in '01HLGV' for x in row)
        assert row.count('V') == row.count('G') == 1
        rows.append(row)
    assert len(rows) == 128 and len(set(WORDS)) == 64
    for a, y in PAIRS:
        assert Counter(r[a - 1] for r in rows) == {'0': 64, '1': 64}
        assert Counter(r[y - 1] for r in rows) == {'L': 64, 'H': 64}
        transitions = {(rows[i - 1][a - 1], rows[i][a - 1]) for i in range(1, len(rows))}
        assert {('0', '1'), ('1', '0')} <= transitions
    return rows


def prepare():
    HERE.mkdir(parents=True, exist_ok=True)
    rows = expected_rows()
    root = ET.Element('logicic')
    db = ET.SubElement(root, 'database', type='LOGIC')
    mf = ET.SubElement(db, 'manufacturer', name='Local TI SN74AHCT14N functional test')
    ic = ET.SubElement(mf, 'ic', name=NAME, type='5', voltage='5V', pins='14')
    for i, row in enumerate(rows):
        ET.SubElement(ic, 'vector', id=str(i)).text = ' '.join(row)
    ET.indent(root)
    ET.ElementTree(root).write(HERE / 'vectors.xml', encoding='utf-8', xml_declaration=True)
    print('Prepared 128 vectors: all 64 input combinations forward and backward, 5 V.')
    print('Input -> output:', PAIRS, '; GND=7, VCC=14. All outputs are only read.')


def check(path):
    ics = list(ET.parse(path).getroot().iter('ic'))
    assert len(ics) == 1
    ic = ics[0]
    assert ic.attrib['name'] == NAME and ic.attrib['pins'] == '14'
    assert ic.attrib['voltage'] == '5V'
    measured = ic.findall('vector')
    expected = expected_rows()
    assert len(measured) == len(expected)
    errors = []
    counts = {y: Counter() for a, y in PAIRS}
    for i, (want, got) in enumerate(zip(expected, measured)):
        assert int(got.attrib['id']) == i
        states = got.text.split()
        assert len(states) == 14
        for pin, (w, g) in enumerate(zip(want, states), 1):
            if w != g:
                errors.append((i, pin, w, g))
        for a, y in PAIRS:
            counts[y][states[y - 1]] += 1
            # Check the truth table separately using physical input and output pins.
            if (states[a - 1], states[y - 1]) not in {('0', 'H'), ('1', 'L')}:
                errors.append((i, a, y, 'Inversion mismatch'))
    if errors:
        print('MISMATCHES:', errors[:30])
        raise AssertionError(f'Mismatches: {len(errors)}')
    print('PASS: all 64 input combinations, 128 vectors, 768 output states.')
    for gate, (a, y) in enumerate(PAIRS, 1):
        print(f'Channel {gate}: input {a}, output {y}; H={counts[y]["H"]}, L={counts[y]["L"]}, mismatches=0')
    print('Each input switches in both directions within the sequence.')
    print('Measurement SHA256:', hashlib.sha256(Path(path).read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.check:
        check(args.check)
