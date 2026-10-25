"""Local 74F821 DIP24 test vectors and independent result checks; no programming."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
HERE = BASE / 'build'
MASK = (1 << 10) - 1
DATA_PINS = tuple(range(2, 12))
OUT_PINS = tuple(range(23, 13, -1))


def vector(data, clock, disable, expected):
    row = [None] * 24
    row[0] = str(disable)
    row[11], row[12], row[23] = 'G', str(clock), 'V'
    for bit, pin in enumerate(DATA_PINS):
        row[pin - 1] = str((data >> bit) & 1)
    for bit, pin in enumerate(OUT_PINS):
        row[pin - 1] = 'Z' if expected is None else ('H' if (expected >> bit) & 1 else 'L')
    assert all(x in '01HLZGV' for x in row)
    assert row.count('G') == row.count('V') == 1
    assert all(row[p - 1] in 'HLZ' for p in OUT_PINS)
    return row


def sequence(words):
    rows, phases = [], []
    def add(d, cp, oe, q, phase):
        rows.append(vector(d, cp, oe, q))
        phases.append(phase)
    add(0, 0, 1, None, 'initial_disabled')
    add(0, 1, 1, None, 'initial_capture')
    add(0, 1, 0, 0, 'initial_enable')
    add(0, 0, 0, 0, 'initial_fall')
    prior = 0
    for w in words:
        opposite = w ^ MASK
        add(w, 0, 0, prior, 'hold_low')
        add(w, 1, 0, w, 'capture_rising')
        add(opposite, 1, 0, w, 'hold_high_data_changed')
        add(opposite, 0, 0, w, 'falling_edge_does_not_capture')
        add(opposite, 0, 1, None, 'disable_outputs')
        add(opposite, 0, 0, w, 'reenable_preserves_state')
        add(opposite, 0, 1, None, 'disable_before_capture')
        add(opposite, 1, 1, None, 'capture_while_disabled')
        add(w, 1, 1, None, 'change_data_while_disabled')
        add(w, 1, 0, opposite, 'read_captured_while_disabled')
        add(w, 0, 0, opposite, 'second_falling_edge')
        prior = opposite
    validate_sequence(rows, len(words))
    return rows, phases


def validate_sequence(rows, word_count):
    """Simulate from input transitions, independently of the generator's phase expectations."""
    previous_clock, stored, previous_data = None, None, None
    captured_enabled, captured_disabled = set(), set()
    for i, row in enumerate(rows):
        cp, oe = int(row[12]), int(row[0])
        d = sum(int(row[p - 1]) << bit for bit, p in enumerate(DATA_PINS))
        if previous_clock == 0 and cp == 1:
            assert d == previous_data, ('Data changed with rising edge', i)
            stored = d
            (captured_disabled if oe else captured_enabled).add(d)
        for bit, pin in enumerate(OUT_PINS):
            expect = 'Z' if oe else ('H' if stored & (1 << bit) else 'L')
            assert row[pin - 1] == expect, (i, pin)
        previous_clock, previous_data = cp, d
    assert len(captured_enabled) == word_count
    assert len(captured_disabled) >= word_count


def prepare():
    HERE.mkdir(parents=True, exist_ok=True)
    smoke = list(dict.fromkeys([0, MASK, 0x155, 0x2AA] + [1 << b for b in range(10)] + [MASK ^ (1 << b) for b in range(10)]))
    full = list(range(1024))
    random.Random(82120261025).shuffle(full)
    root = ET.Element('logicic')
    db = ET.SubElement(root, 'database', type='LOGIC')
    mf = ET.SubElement(db, 'manufacturer', name='Local National 74F821 verification')
    metadata = {}
    for name, words in [('F821_SMOKE', smoke), ('F821_FULL', full)]:
        rows, phases = sequence(words)
        ic = ET.SubElement(mf, 'ic', name=name, type='5', voltage='5V', pins='24')
        for i, row in enumerate(rows):
            ET.SubElement(ic, 'vector', id=str(i)).text = ' '.join(row)
        metadata[name] = {'words': len(words), 'vectors': len(rows), 'phase_counts': dict(Counter(phases)), 'phases': phases}
    # Detect a deliberately incorrect expectation at O0 after deterministic initialization.
    negative_rows, _ = sequence([0])
    negative_rows = negative_rows[:3]
    assert negative_rows[-1][22] == 'L'
    negative_rows[-1][22] = 'H'
    ic = ET.SubElement(mf, 'ic', name='F821_NEGATIVE_CONTROL', type='5', voltage='5V', pins='24')
    for i, row in enumerate(negative_rows):
        ET.SubElement(ic, 'vector', id=str(i)).text = ' '.join(row)
    ET.indent(root)
    ET.ElementTree(root).write(HERE / 'vectors.xml', encoding='utf-8', xml_declaration=True)
    (HERE / 'vector-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Pin map: /OE=1, D0..D9=2..11, GND=12, CP=13, O0..O9=23..14, VCC=24.')
    for name, data in metadata.items():
        print(name, data['words'], 'words;', data['vectors'], 'vectors; validated edge-triggered model.')


def check(path):
    measured = ET.parse(path).getroot().find('.//ic')
    assert measured is not None
    name = measured.attrib['name']
    assert name in ('F821_SMOKE', 'F821_FULL')
    assert measured.attrib['pins'] == '24' and measured.attrib['voltage'] == '5V'
    expected = next(x for x in ET.parse(HERE / 'vectors.xml').getroot().iter('ic') if x.attrib['name'] == name)
    expected_rows, observed_rows = expected.findall('vector'), measured.findall('vector')
    meta = json.loads((HERE / 'vector-metadata.json').read_text())[name]
    assert len(expected_rows) == len(observed_rows) == meta['vectors']
    errors, counts = [], {pin: Counter() for pin in OUT_PINS}
    for i, (want, got) in enumerate(zip(expected_rows, observed_rows)):
        assert int(want.attrib['id']) == int(got.attrib['id']) == i
        w, g = want.text.split(), got.text.split()
        assert len(w) == len(g) == 24
        for p in range(1, 25):
            if w[p - 1] != g[p - 1]:
                errors.append((i, meta['phases'][i], p, w[p - 1], g[p - 1]))
        for p in OUT_PINS:
            counts[p][g[p - 1]] += 1
    if errors:
        print('MISMATCHES (vector, phase, pin, expected, actual):', errors[:30])
        raise AssertionError(f'{len(errors)} mismatches')
    print(f'PASS: {name}, {meta["words"]} data words, {meta["vectors"]} test vectors, all 10 outputs.')
    print('PASS: rising-edge capture, hold at both clock levels, no capture on falling edges, /OE tri-state and preserved internal state.')
    print('PASS: capture while /OE is high, followed by correct readout.')
    for bit, pin in enumerate(OUT_PINS):
        c = counts[pin]
        print(f'O{bit}, pin {pin}: H={c["H"]}, L={c["L"]}, Z={c["Z"]}, mismatches=0')
    print('Measured file SHA256:', hashlib.sha256(Path(path).read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.check:
        check(args.check)
