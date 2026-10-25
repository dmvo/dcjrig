"""SN74AHCT541N functional test at 5 V."""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import random
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
HERE = BASE / 'build'
NAME = 'SN74AHCT541N_FUNCTION'
PAIRS = ((2, 18), (3, 17), (4, 16), (5, 15), (6, 14), (7, 13), (8, 12), (9, 11))
MODES = ((0, 0), (1, 0), (0, 0), (0, 1), (0, 0), (1, 1), (0, 0))


def expected_rows():
    words = list(range(256))
    random.Random(54120261025).shuffle(words)
    rows = []
    for word in words:
        for oe1, oe2 in MODES:
            row = [None] * 20
            row[0], row[18], row[9], row[19] = str(oe1), str(oe2), 'G', 'V'
            for bit, (a, y) in enumerate(PAIRS):
                level = (word >> bit) & 1
                row[a - 1] = str(level)
                row[y - 1] = 'Z' if oe1 or oe2 else ('H' if level else 'L')
            assert all(x in '01HLZGV' for x in row)
            assert row.count('G') == row.count('V') == 1
            rows.append(row)
    inputs = {tuple(row[p - 1] for p in (1, 2, 3, 4, 5, 6, 7, 8, 9, 19)) for row in rows}
    assert len(rows) == 1792 and len(inputs) == 1024
    for a, y in PAIRS:
        assert Counter(r[y - 1] for r in rows) == {'H': 512, 'L': 512, 'Z': 768}
        transitions = {(rows[i - 1][a - 1], rows[i][a - 1]) for i in range(1, len(rows))}
        assert {('0', '1'), ('1', '0')} <= transitions
    return rows


def prepare():
    HERE.mkdir(parents=True, exist_ok=True)
    root = ET.Element('logicic')
    db = ET.SubElement(root, 'database', type='LOGIC')
    mf = ET.SubElement(db, 'manufacturer', name='Local TI SN74AHCT541N functional test')
    ic = ET.SubElement(mf, 'ic', name=NAME, type='5', voltage='5V', pins='20')
    for i, row in enumerate(expected_rows()):
        ET.SubElement(ic, 'vector', id=str(i)).text = ' '.join(row)
    ET.indent(root)
    ET.ElementTree(root).write(HERE / 'vectors.xml', encoding='utf-8', xml_declaration=True)
    print('Prepared 1792 vectors covering all 1024 combinations of ten inputs.')
    print('Input -> output:', PAIRS, '; /OE1=1, /OE2=19, GND=10, VCC=20.')
    print('Each word: enabled -> /OE1=1 -> enabled -> /OE2=1 -> enabled -> both=1 -> enabled.')


def check(path):
    ics = list(ET.parse(path).getroot().iter('ic'))
    assert len(ics) == 1
    ic = ics[0]
    assert ic.attrib['name'] == NAME
    assert ic.attrib['pins'] == '20' and ic.attrib['voltage'] == '5V'
    measured = ic.findall('vector')
    expected = expected_rows()
    assert len(measured) == len(expected)
    counts = {y: Counter() for a, y in PAIRS}
    errors = []
    modes = Counter()
    for i, (want, got) in enumerate(zip(expected, measured)):
        assert int(got.attrib['id']) == i
        states = got.text.split()
        assert len(states) == 20
        for pin, (w, g) in enumerate(zip(want, states), 1):
            if w != g:
                errors.append((i, pin, w, g))
        modes[(states[0], states[18])] += 1
        enabled = (states[0], states[18]) == ('0', '0')
        for a, y in PAIRS:
            counts[y][states[y - 1]] += 1
            # Check the function separately against the inputs in the measurement file.
            truth = {'0': 'L', '1': 'H'}[states[a - 1]] if enabled else 'Z'
            if states[y - 1] != truth:
                errors.append((i, y, 'Truth-table mismatch'))
    if errors:
        print('MISMATCHES:', errors[:30])
        raise AssertionError(f'Mismatches: {len(errors)}')
    print('PASS: 256 words x 4 enable combinations; 1792 vectors, 14336 output states; mismatches=0.')
    print('Vector counts by /OE1, /OE2:', dict(modes))
    for channel, (a, y) in enumerate(PAIRS, 1):
        print(f'Channel {channel}: input {a}, output {y}; H={counts[y]["H"]}, L={counts[y]["L"]}, Z={counts[y]["Z"]}, mismatches=0')
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
