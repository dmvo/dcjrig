#!/usr/bin/env python3
"""DCJ11 processor checks through the built-in console ODT.

The rig has no memory, so every check uses ODT commands only:
general registers, PSW, stack pointers, memory management registers,
PIRQ, CCR and the DC319 DLART on the external bus.

Usage:
  python3 suite.py --cpu 1 --out RESULTS_DIR [--passes 3] [--port /dev/ttyUSB0]
  python3 suite.py --cpu 1 --out RESULTS_DIR --wait-banner [--timeout 1800]
  python3 suite.py --cpu 1 --out RESULTS_DIR --reset-check

See README.md for the meaning of each check.
"""
import argparse
import json
import os
import sys
import time

from odtlink import Odt, OdtError

M16 = 0o177777

# Writable bits measured on the first CPU and matching the J11 register
# descriptions. Bits outside a mask read as zero, except where noted.
PSW_MASK = 0o174757    # T bit (4) and bits 10:8 cannot be set from ODT
PDR_MASK = 0o177416    # bit 6 (W) clears on any write; 7, 5:4, 0 unused
MMR3_MASK = 0o000077
MMR0_WMASK = 0o160001  # abort flags 15:13 and enable bit 0; others read-only
CCR_MASK = 0o003377    # bit 8 (flush) reads zero

BANKS = {
    # name: (PDR base, PAR base)
    "KI": (0o17772300, 0o17772340),
    "KD": (0o17772320, 0o17772360),
    "SI": (0o17772200, 0o17772240),
    "SD": (0o17772220, 0o17772260),
    "UI": (0o17777600, 0o17777640),
    "UD": (0o17777620, 0o17777660),
}
PIRQ = 0o17777772
MMR0 = 0o17777572
MMR3 = 0o17772516
CCR = 0o17777746
CPUERR = 0o17777766
HITMISS = 0o17777752
RCSR, RBUF, XCSR, XBUF = 0o17777560, 0o17777562, 0o17777564, 0o17777566

MODES = {"K": 0o000000, "S": 0o040000, "U": 0o140000}


def patterns16():
    p = [0, M16, 0o125252, 0o052525, 0o146314, 0o031463]
    p += [1 << i for i in range(16)]
    p += [M16 ^ (1 << i) for i in range(16)]
    return p


def pirq_expected(w):
    req = w & 0o177000
    level = 0
    for n in range(7, 0, -1):
        if req & (1 << (8 + n)):
            level = n
            break
    return req | (level << 5) | (level << 1)


def a(addr):
    return "%o" % addr


class Suite:
    def __init__(self, odt, results):
        self.o = odt
        self.res = results
        self.cur = None

    # --- bookkeeping -------------------------------------------------
    def begin(self, name, desc):
        self.cur = {"name": name, "desc": desc, "checks": 0,
                    "fails": [], "info": {}, "error": None}
        self.t0 = time.time()

    def end(self):
        c = self.cur
        c["seconds"] = round(time.time() - self.t0, 2)
        c["result"] = "FAIL" if (c["fails"] or c["error"]) else "PASS"
        self.res.append(c)
        print("  %-28s %s  checks=%d fails=%d%s" % (
            c["name"], c["result"], c["checks"], len(c["fails"]),
            ("  ERROR " + c["error"]) if c["error"] else ""), flush=True)

    def check(self, what, got, exp):
        self.cur["checks"] += 1
        if got != exp:
            if len(self.cur["fails"]) < 200:
                self.cur["fails"].append({
                    "what": what,
                    "got": None if got is None else "%06o" % got,
                    "exp": None if exp is None else "%06o" % exp})

    def run(self, name, desc, fn):
        self.begin(name, desc)
        try:
            fn()
        except OdtError as e:
            self.cur["error"] = str(e)[:300]
            try:
                self.o.sync()
            except OdtError:
                pass
        self.end()

    # --- helpers ------------------------------------------------------
    def rw(self, loc, w, exp, label):
        self.o.deposit(loc, w)
        self.check("%s w=%06o" % (label, w), self.o.read(loc), exp)

    def set_psw(self, v):
        self.o.deposit("RS", v)

    # --- tests ---------------------------------------------------------
    def t_console(self):
        o = self.o
        o.drain(0.1)
        o.write(b"\r")
        buf, _ = o.read_until(rb"\r\n@$")
        self.check("bare CR gives ?", int(buf.startswith(b"?")), 1)
        # Odd address is rejected.
        self.check("odd address rejected", o.open("17777707"), None)
        # LF steps through registers and wraps R7 -> R0.
        o.open("R6")
        seq = [o.next_loc()[0], o.next_loc()[0]]
        o.close_loc()
        self.check("LF R6->R7->R0", int(seq == ["R7", "R0"]), 1)
        # LF steps an I/O page address by 2.
        o.open(a(BANKS["KI"][1]))
        labels = [o.next_loc()[0] for _ in range(7)]
        o.close_loc()
        exp = ["%o" % (BANKS["KI"][1] + 2 * i) for i in range(1, 8)]
        self.check("LF address +2", int(labels == exp), 1)
        self.cur["info"]["lf_labels"] = labels

    def gpr_patterns(self, regset):
        self.set_psw(regset << 11)
        for r in range(6):
            for p in patterns16():
                self.rw("R%d" % r, p, p, "set%d R%d" % (regset, r))
        self.set_psw(0)

    def t_gpr0(self):
        self.gpr_patterns(0)

    def t_gpr1(self):
        self.gpr_patterns(1)

    def t_regset_isolation(self):
        for k in range(2):
            for regset in (0, 1):
                self.set_psw(regset << 11)
                for r in range(6):
                    v = (0o010101 * (r + 1) + 0o100000 * regset) & M16
                    if k:
                        v ^= M16
                    self.o.deposit("R%d" % r, v)
            for regset in (0, 1):
                self.set_psw(regset << 11)
                for r in range(6):
                    v = (0o010101 * (r + 1) + 0o100000 * regset) & M16
                    if k:
                        v ^= M16
                    self.check("set%d R%d" % (regset, r),
                               self.o.read("R%d" % r), v)
        self.set_psw(0)

    def t_pc(self):
        for p in patterns16():
            self.rw("R7", p, p, "R7")

    def t_sp(self):
        for m, psw in MODES.items():
            self.set_psw(psw)
            for p in patterns16():
                self.rw("R6", p, p, "%sSP" % m)
        # Isolation: distinct values, then read each back.
        for k in range(2):
            vals = {"K": 0o011000, "S": 0o022000, "U": 0o033000}
            if k:
                vals = {m: v ^ M16 for m, v in vals.items()}
            for m, psw in MODES.items():
                self.set_psw(psw)
                self.o.deposit("R6", vals[m])
            for m, psw in MODES.items():
                self.set_psw(psw)
                self.check("%sSP isolation" % m, self.o.read("R6"), vals[m])
            # Register set must not affect R6.
            self.set_psw(0o004000)
            self.check("KSP with regset 1", self.o.read("R6"), vals["K"])
        self.set_psw(0o100000)
        self.cur["info"]["mode10_R6"] = "%06o" % self.o.read("R6")
        self.set_psw(0)

    def t_psw(self):
        for p in patterns16():
            self.rw("RS", p, p & PSW_MASK, "PSW")
        self.set_psw(0)

    def t_par(self):
        for bank, (_, par) in BANKS.items():
            for i in range(8):
                loc = a(par + 2 * i)
                for p in patterns16():
                    self.rw(loc, p, p, "%sPAR%d" % (bank, i))

    def t_pdr(self):
        for bank, (pdr, _) in BANKS.items():
            for i in range(8):
                loc = a(pdr + 2 * i)
                for p in patterns16():
                    self.rw(loc, p, p & PDR_MASK, "%sPDR%d" % (bank, i))

    def t_mmu_unique(self):
        """Distinct value in each of 96 registers, then read all back."""
        regs = []
        for bank, (pdr, par) in BANKS.items():
            for i in range(8):
                regs.append(("%sPAR%d" % (bank, i), par + 2 * i, M16))
                regs.append(("%sPDR%d" % (bank, i), pdr + 2 * i, PDR_MASK))
        for k in range(2):
            vals = {}
            for n, (name, addr, mask) in enumerate(regs):
                v = ((n * 0o2401) ^ (addr & 0o777) ^ 0o052525) & M16
                if k:
                    v ^= M16
                vals[name] = v & mask
                self.o.deposit(a(addr), v)
            for name, addr, mask in regs:
                self.check(name + " unique", self.o.read(a(addr)), vals[name])
        # Leave PARs and PDRs at zero.
        for name, addr, mask in regs:
            self.o.deposit(a(addr), 0)

    def t_mmr(self):
        saved = self.o.read(a(MMR0))
        ro = saved & ~MMR0_WMASK & M16
        for p in patterns16():
            self.rw(a(MMR0), p, (p & MMR0_WMASK) | ro, "MMR0")
        self.o.deposit(a(MMR0), 0)
        self.cur["info"]["mmr0_readonly_bits"] = "%06o" % ro
        for p in patterns16():
            self.rw(a(MMR3), p, p & MMR3_MASK, "MMR3")
        self.o.deposit(a(MMR3), 0)
        self.cur["info"]["MMR1"] = "%06o" % self.o.read("17777574")
        self.cur["info"]["MMR2"] = "%06o" % self.o.read("17777576")

    def t_pirq(self):
        for n in range(128):
            w = (n << 9) | (n & 0o777)   # also write junk into low bits
            self.rw(a(PIRQ), w, pirq_expected(w), "PIRQ")
        self.o.deposit(a(PIRQ), 0)
        self.check("PIRQ cleared", self.o.read(a(PIRQ)), 0)

    def t_ccr(self):
        for p in patterns16():
            self.rw(a(CCR), p, p & CCR_MASK, "CCR")
        self.o.deposit(a(CCR), 0)

    def t_readonly(self):
        self.check("CPU error reg", self.o.read(a(CPUERR)), 0)
        self.check("hit/miss reg", self.o.read(a(HITMISS)), 0)
        for p in (M16, 0o125252):
            self.rw(a(HITMISS), p, 0, "hit/miss write")
            self.rw(a(CPUERR), p, 0, "CPU error write")

    def t_bus_write(self):
        """Deposit each byte value into XBUF and check the transmitted byte."""
        o = self.o
        for ch in range(256):
            o.open(a(XBUF))
            s = b"%o" % ch
            o.write(s + b"\r")
            buf, _ = o.read_until(rb"\r\n@$")
            got = buf[len(s):-3]
            self.check("XBUF byte", got[0] if len(got) == 1 else None, ch)
            if len(got) != 1 and len(self.cur["fails"]) < 200:
                self.cur["fails"][-1]["raw"] = repr(buf)

    def t_bus_read(self):
        # ODT reads RBUF for every typed character; the last one is "/".
        for _ in range(8):
            self.check("RBUF holds '/'", self.o.read(a(RBUF)) & 0o377, 0o057)
        self.cur["info"]["RCSR"] = "%06o" % self.o.read(a(RCSR))
        self.cur["info"]["XCSR"] = "%06o" % self.o.read(a(XCSR))
        # Every octal digit and both register letters, typed and echoed.
        for p in (0o012345, 0o067012, 0o176543):
            self.rw("R0", p, p, "typed digits")

    def t_info(self):
        info = self.cur["info"]
        for addr in (0, 0o1000, 0o17757776, 0o17777744, 0o17777750):
            info["%08o" % addr] = "%06o" % self.o.read(a(addr))

    TESTS = [
        ("console", "ODT parser: ?, odd address, LF stepping", "t_console"),
        ("gpr_set0", "R0-R5, register set 0, 38 patterns", "t_gpr0"),
        ("gpr_set1", "R0-R5, register set 1, 38 patterns", "t_gpr1"),
        ("regset_isolation", "sets 0 and 1 hold separate values", "t_regset_isolation"),
        ("pc", "R7, 38 patterns", "t_pc"),
        ("stack_pointers", "KSP/SSP/USP patterns and isolation", "t_sp"),
        ("psw", "PSW writable bits 174757", "t_psw"),
        ("par", "48 PARs, 38 patterns each", "t_par"),
        ("pdr", "48 PDRs, mask 177416", "t_pdr"),
        ("mmu_unique", "96 MMU registers, no aliasing", "t_mmu_unique"),
        ("mmr0_mmr3", "MMR0 and MMR3 writable bits", "t_mmr"),
        ("pirq", "PIRQ priority encoder, 128 requests", "t_pirq"),
        ("ccr", "CCR writable bits 003377", "t_ccr"),
        ("readonly", "CPU error and hit/miss stay zero", "t_readonly"),
        ("bus_write", "256 bytes to DLART XBUF over DAL", "t_bus_write"),
        ("bus_read", "DLART RBUF and typed digits", "t_bus_read"),
        ("info", "floating bus reads, information only", "t_info"),
    ]

    def t_negative(self):
        """Deliberately wrong expectation: this test must FAIL."""
        self.rw("R0", 0o125252, 0o125253, "negative control")

    def run_all(self, negative=False):
        self.o.sync()
        tests = self.TESTS
        if negative:
            tests = [("negative_control", "must fail", "t_negative")]
        for name, desc, fn in tests:
            self.run(name, desc, getattr(self, fn))
        self.set_psw(0)


def wait_banner(odt, timeout):
    """Wait for the start-up message: CRLF, 6-digit PC, CRLF, @."""
    buf, m = odt.read_until(rb"([0-7]{6})\r\n@$", timeout=timeout)
    return buf, m.group(1).decode()


def set_markers(o):
    """Load recognizable values before a reset, to see what INIT clears."""
    o.sync()
    o.deposit("RS", 0)
    for r in range(6):
        o.deposit("R%d" % r, 0o070707 + r)
    o.deposit("R6", 0o001234)
    o.deposit("R7", 0o004321)
    o.deposit(a(PIRQ), 0o001000)
    o.deposit(a(MMR3), 0o000060)
    o.deposit(a(BANKS["KI"][1]), 0o012345)
    o.deposit(a(BANKS["KI"][0]), 0o077406)
    o.deposit(a(CCR), 0o000001)
    o.deposit(a(MMR0), 0o160000)   # abort flags only; MMU stays off
    o.deposit("RS", 0o000340)


def snapshot(o):
    o.sync()
    s = {}
    for loc in ["RS", "R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"]:
        s[loc] = "%06o" % o.read(loc)
    for name, addr in (("PIRQ", PIRQ), ("MMR0", MMR0), ("MMR3", MMR3),
                       ("KIPAR0", BANKS["KI"][1]), ("KIPDR0", BANKS["KI"][0]),
                       ("CCR", CCR), ("CPUERR", CPUERR)):
        s[name] = "%06o" % o.read(a(addr))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpu", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=38400)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--wait-banner", action="store_true",
                    help="wait for a start-up message, then run the suite")
    ap.add_argument("--reset-check", action="store_true",
                    help="set markers, ask for SW1, compare state after reset")
    ap.add_argument("--negative-control", action="store_true",
                    help="run one deliberately wrong check; exit 0 only if it fails")
    ap.add_argument("--timeout", type=float, default=1800)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    kind = ("reset" if args.reset_check else
            "negative" if args.negative_control else "suite")
    base = os.path.join(args.out, "cpu%s-%s-%s" % (args.cpu, kind, stamp))
    log = open(base + ".serial.log", "w")
    odt = Odt(args.port, args.baud, log=log)
    report = {"cpu": args.cpu, "started": stamp, "port": args.port,
              "baud": args.baud, "kind": kind}

    if args.reset_check:
        set_markers(odt)
        report["before"] = snapshot(odt)
        odt.drain(0.2)
        print("ACTION: PRESS RESET (SW1)", flush=True)
        buf, pc = wait_banner(odt, args.timeout)
        print("RESET SEEN: banner PC=%s raw=%r" % (pc, buf[-40:]), flush=True)
        report["banner_pc"] = pc
        report["banner_raw"] = repr(buf[-80:])
        report["after"] = snapshot(odt)
        # INIT clears PSW, PIRQ, MMR3, CCR and the writable MMR0 bits.
        # MMR0 bits 6:1 are read-only status and may keep their value.
        # The start-up message shows the PC, which INIT does not change.
        after = dict(report["after"])
        after["MMR0 & 160001"] = "%06o" % (int(after["MMR0"], 8) & MMR0_WMASK)
        after["banner PC"] = pc
        exp = {"RS": "000000", "PIRQ": "000000", "MMR0 & 160001": "000000",
               "MMR3": "000000", "CCR": "000000", "CPUERR": "000000",
               "banner PC": report["before"]["R7"]}
        report["checks"] = {k: {"exp": v, "got": after[k],
                                "ok": after[k] == v}
                            for k, v in exp.items()}
        report["result"] = ("PASS" if all(c["ok"] for c in
                            report["checks"].values()) else "FAIL")
        for k in report["before"]:
            print("  %-7s before %s after %s" % (
                k, report["before"][k], report["after"][k]))
        print("RESET CHECK:", report["result"],
              {k: c for k, c in report["checks"].items() if not c["ok"]})
    else:
        if args.wait_banner:
            print("WAITING FOR START-UP MESSAGE", flush=True)
            buf, pc = wait_banner(odt, args.timeout)
            print("BANNER SEEN: PC=%s" % pc, flush=True)
            report["banner_pc"] = pc
            time.sleep(0.5)
        report["passes"] = []
        for p in range(args.passes):
            print("PASS %d/%d" % (p + 1, args.passes), flush=True)
            results = []
            t0 = time.time()
            Suite(odt, results).run_all(args.negative_control)
            report["passes"].append({"seconds": round(time.time() - t0, 1),
                                     "tests": results})
        allres = [t for p in report["passes"] for t in p["tests"]]
        report["checks"] = sum(t["checks"] for t in allres)
        report["failures"] = sum(len(t["fails"]) + bool(t["error"])
                                 for t in allres)
        report["result"] = "PASS" if report["failures"] == 0 else "FAIL"
        if args.negative_control:
            ok = report["failures"] == 1
            report["result"] = "PASS" if ok else "FAIL"
            print("NEGATIVE CONTROL:", "detected" if ok else "NOT detected")
        else:
            print("SUITE %s: %d checks, %d failures" % (
                report["result"], report["checks"], report["failures"]))

    report["finished"] = time.strftime("%Y%m%d-%H%M%S")
    with open(base + ".json", "w") as f:
        json.dump(report, f, indent=1)
    print("RESULTS", base + ".json")
    odt.close()
    log.close()
    sys.exit(0 if report["result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
