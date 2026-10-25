"""Preliminary DC319-AA checks: logic vectors at 5 V only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
HERE = BASE / 'build'
BUS = tuple(range(4, 20))
OUTPUTS = (25, 26, 29, 30, 33, 34, 35, 36)
INPUTS = (1, 2, 3, 21, 22, 23, 24, 27, 28, 31, 32, 37, 38, 39)
PIN = dict(rd=1, cs=2, wlb=3, a0=21, a1=22, a2=23, init=24,
           si=27, pbri=28, brs0=31, clk=32, brs1=37, brs2=38, test=39)


class Sequence:
    def __init__(self):
        self.s = dict(rd=1, cs=1, wlb=1, a0=0, a1=0, a2=0, init=0,
                      si=1, pbri=0, brs0=1, clk=0, brs1=1, brs2=1, test=1)
        self.rows, self.meta = [], []

    def add(self, label, drive=None, bus=None, checks=None, **changes):
        self.s.update(changes)
        row = ['Z'] * 40
        row[19], row[39] = 'G', 'V'
        for name, pin in PIN.items():
            row[pin - 1] = str(self.s[name])
        expect = dict(checks or {})
        reading = self.s['rd'] == 0 and self.s['cs'] == 0 and self.s['wlb'] == 1
        if drive is not None:
            assert self.s['rd'] == 1 and self.s['test'] == 0
            if self.rows:
                # Disable reading before the programmer drives the bus.
                assert self.rows[-1][0] == '1'
            for bit, pin in enumerate(BUS):
                row[pin - 1] = str((drive >> bit) & 1)
        else:
            if bus is None and not reading:
                bus = 'Z'
            if bus is not None:
                for bit, pin in enumerate(BUS):
                    expected = 'Z' if bus == 'Z' else ('H' if bus & (1 << bit) else 'L')
                    row[pin - 1] = expected
                    expect[pin] = expected
        for pin, expected in (checks or {}).items():
            assert pin in OUTPUTS and expected in 'HLZ'
            row[pin - 1] = expected
        assert len(row) == 40 and all(c in '01HLZGV' for c in row)
        assert row.count('V') == row.count('G') == 1
        assert row[19] == 'G' and row[39] == 'V'
        assert all(row[p - 1] in 'HLZ' for p in OUTPUTS)
        assert all(row[p - 1] in '01' for p in INPUTS)
        if reading:
            assert all(row[p - 1] in 'HLZ' for p in BUS)
            if self.rows:
                assert all(self.rows[-1][p - 1] in 'HLZ' for p in BUS)
        self.rows.append(row)
        self.meta.append(dict(label=label, expected=expect, drive=drive, reading=reading))

    def reset(self, prefix):
        for i in range(8):
            self.add(f'{prefix}: TEST=1 [{i}]', rd=1, cs=1, wlb=1, test=1,
                     init=0, clk=0, checks={p: 'Z' for p in OUTPUTS})
        for i in range(4):
            self.add(f'{prefix}: TEST=0 [{i}]', test=0)

    def read(self, reg, expected, label, a0=0, checks=None):
        self.add(label + ': address', rd=1, cs=1, wlb=1,
                 a0=a0, a1=reg & 1, a2=(reg >> 1) & 1)
        self.add(label + ': select', cs=0)
        self.add(label + ': read', rd=0, bus=expected, checks=checks)
        self.add(label + ': hold read', bus=expected, checks=checks)
        self.add(label + ': release /RD', rd=1)
        self.add(label + ': release /CS', cs=1)

    def write(self, reg, data, label, a0=0):
        self.add(label + ': setup', rd=1, cs=1, wlb=1,
                 a0=a0, a1=reg & 1, a2=(reg >> 1) & 1)
        self.add(label + ': data', drive=data)
        self.add(label + ': select', drive=data, cs=0)
        self.add(label + ': /WLB=0', drive=data, wlb=0)
        self.add(label + ': rising /WLB', drive=data, wlb=1)
        self.add(label + ': hold data', drive=data)
        self.add(label + ': release /CS', drive=data, cs=1)
        self.add(label + ': release bus')

    def clocks(self, count, label):
        assert self.s['cs'] == self.s['rd'] == self.s['wlb'] == 1
        for i in range(count):
            self.add(f'{label}: CLK {i} L', clk=0)
            self.add(f'{label}: CLK {i} H', clk=1)
        self.add(label + ': CLK stop L', clk=0)


def profiles():
    reset = Sequence()
    reset.reset('reset')
    for reg, name, value in [(0, 'RCSR', 0), (1, 'RBUF', 0), (2, 'XCSR', 0x80), (3, 'XBUF', 0)]:
        reset.read(reg, value, name + ' after TEST')
    reset.add('finish: TEST=1', test=1)
    assert all(row[p - 1] in 'HLZ' for row in reset.rows for p in BUS)

    smoke = Sequence()
    smoke.reset('reset')
    smoke.read(2, 0x80, 'XCSR after TEST')
    for value in (0x40, 0):
        smoke.write(0, value, f'RCSR <- {value:04x}')
        smoke.read(0, value, f'RCSR = {value:04x}')
    for value in (0x40, 0x01, 0):
        smoke.write(2, value, f'XCSR <- {value:04x}')
        smoke.read(2, 0x80 | value, f'XCSR = {0x80 | value:04x}')
    smoke.write(0, 0x40, 'RCSR before INIT')
    smoke.write(2, 0x45, 'XCSR before INIT')
    smoke.read(0, 0x40, 'RCSR before INIT')
    smoke.read(2, 0xc5, 'XCSR before INIT')
    smoke.add('INIT=1', init=1)
    smoke.add('INIT=1 hold')
    smoke.add('INIT=0', init=0)
    smoke.read(0, 0, 'RCSR after INIT')
    smoke.read(2, 0x80, 'XCSR after INIT')
    for value in (0x00, 0xff, 0x55, 0xaa):
        smoke.write(3, value, f'XBUF <- {value:04x}')
        smoke.read(3, value, f'XBUF = {value:04x}')
    smoke.reset('final reset')
    smoke.read(3, 0, 'XBUF after final TEST')
    smoke.add('finish: TEST=1', test=1)
    clock = Sequence()
    clock.reset('reset')
    clock.add('BRS=000, fastest baud setting', brs0=0, brs1=0, brs2=0)
    clock.write(0, 0x40, 'RCSR: enable receiver interrupt')
    clock.write(2, 0x44, 'XCSR: MAINT loopback and interrupt enable')
    clock.clocks(32, 'initial idle')
    clock.read(2, 0xc4, 'XCSR before transmit', checks={29: 'H', 30: 'H'})
    for value in (0xa5, 0x5a):
        clock.write(3, value, f'transmit {value:02x}: XBUF')
        clock.read(3, value, f'transmit {value:02x}: read XBUF')
        clock.clocks(384, f'transmit {value:02x}')
        clock.read(0, 0xc0, f'receive {value:02x}: RCSR DONE+IE', checks={26: 'H'})
        clock.read(1, value, f'receive {value:02x}: RBUF')
        clock.read(0, 0x40, f'receive {value:02x}: RCSR after RBUF read', checks={26: 'L'})
        clock.read(2, 0xc4, f'transmit {value:02x}: XCSR ready', checks={29: 'H', 30: 'H'})
    clock.reset('final reset')
    clock.read(0, 0, 'RCSR after final TEST')
    clock.read(1, 0, 'RBUF after final TEST')
    clock.read(2, 0x80, 'XCSR after final TEST')
    clock.read(3, 0, 'XBUF after final TEST')
    clock.add('finish: TEST=1', test=1)
    return {'DC319_RESET': reset, 'DC319_SMOKE': smoke, 'DC319_CLOCK': clock}


def prepare():
    HERE.mkdir(parents=True, exist_ok=True)
    root = ET.Element('logicic')
    db = ET.SubElement(root, 'database', type='LOGIC')
    manufacturer = ET.SubElement(db, 'manufacturer', name='Local DC319-AA preliminary test')
    metadata = {}
    for name, seq in profiles().items():
        ic = ET.SubElement(manufacturer, 'ic', name=name, type='5', voltage='5V', pins='40')
        for i, row in enumerate(seq.rows):
            ET.SubElement(ic, 'vector', id=str(i)).text = ' '.join(row)
        metadata[name] = seq.meta
        print(name, len(seq.rows), 'vectors; pin assignment and bus turnaround checked.')
    ET.indent(root)
    ET.ElementTree(root).write(HERE / 'vectors.xml', encoding='utf-8', xml_declaration=True)
    (HERE / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')


def bus_text(states):
    data = [states[p - 1] for p in BUS]
    if all(v in 'HL' for v in data):
        return f'0x{sum((v == "H") << bit for bit, v in enumerate(data)):04x}'
    return ''.join(reversed(data))


def analyze(path):
    ic = ET.parse(path).getroot().find('.//ic')
    assert ic is not None and ic.attrib['pins'] == '40' and ic.attrib['voltage'] == '5V'
    name = ic.attrib['name']
    seq = profiles()[name]
    observed = ic.findall('vector')
    assert len(observed) == len(seq.rows)
    errors, output_states = [], {p: Counter() for p in OUTPUTS}
    reads = 0
    for i, (node, expected, meta) in enumerate(zip(observed, seq.rows, seq.meta)):
        assert int(node.attrib['id']) == i
        states = node.text.split()
        assert len(states) == 40
        for p in INPUTS + (20, 40):
            assert states[p - 1] == expected[p - 1]
        for pin, want in meta['expected'].items():
            if states[pin - 1] != want:
                errors.append((i, meta['label'], pin, want, states[pin - 1]))
        for p in OUTPUTS:
            output_states[p][states[p - 1]] += 1
        if meta['reading']:
            reads += 1
            print(f'{i:04d} {meta["label"]}: DAL={bus_text(states)}; SO={states[29]}, XIRQ={states[28]}, RIRQ={states[25]}, BRKIRQ={states[32]}')
    print('Profile:', name, '; vectors:', len(observed), '; read steps:', reads)
    print('Mismatches with preliminary expectations:', len(errors))
    for item in errors[:40]:
        print(item)
    for p, counts in output_states.items():
        print('Pin', p, dict(counts))
    print('Measurement SHA256:', hashlib.sha256(Path(path).read_bytes()).hexdigest())
    result = dict(profile=name, vectors=len(observed), read_steps=reads, mismatches=errors,
                  output_states={str(p): dict(c) for p, c in output_states.items()})
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / (Path(path).stem + '.analysis.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')

    assert not errors, f'{len(errors)} mismatches'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--analyze', type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.analyze:
        analyze(args.analyze)
