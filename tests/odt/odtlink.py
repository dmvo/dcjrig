"""Minimal DCJ11 console ODT link over a POSIX serial port (no pyserial)."""
import os, re, select, termios, time

PROMPT = b"\r\n@"


class OdtError(Exception):
    pass


class Odt:
    def __init__(self, port="/dev/ttyUSB0", baud=38400, log=None, timeout=2.0):
        self.fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        a = termios.tcgetattr(self.fd)
        a[0] = 0; a[1] = 0
        a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        a[3] = 0
        speed = getattr(termios, "B%d" % baud)
        a[4] = a[5] = speed
        a[6][termios.VMIN] = 0; a[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW, a)
        termios.tcflush(self.fd, termios.TCIOFLUSH)
        self.log = log
        self.timeout = timeout

    def close(self):
        os.close(self.fd)

    def _log(self, tag, data):
        if self.log:
            self.log.write("%.3f %s %r\n" % (time.time(), tag, data))
            self.log.flush()

    def write(self, data):
        self._log(">>", data)
        os.write(self.fd, data)

    def read_until(self, pattern, timeout=None):
        """Read until regex (bytes) matches the accumulated buffer."""
        end = time.time() + (timeout or self.timeout)
        buf = b""
        rx = re.compile(pattern, re.S)
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.02)
            if r:
                chunk = os.read(self.fd, 4096)
                buf += chunk
                if timeout and timeout > 10:
                    # Long waits: log every byte as it arrives.
                    self._log("<<raw", chunk)
                m = rx.search(buf)
                if m:
                    self._log("<<", buf)
                    return buf, m
        self._log("<<TIMEOUT", buf)
        raise OdtError("timeout waiting for %r, got %r" % (pattern, buf))

    def drain(self, t=0.2):
        end = time.time() + t
        buf = b""
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.02)
            if r:
                buf += os.read(self.fd, 4096)
        if buf:
            self._log("<<drain", buf)
        return buf

    def sync(self):
        """Get a fresh prompt. A bare CR at the prompt answers ?CRLF@."""
        self.drain(0.1)
        self.write(b"\r")
        self.read_until(rb"\r\n@$")
        self.drain(0.05)

    def open(self, loc):
        """Open a location (address string or Rn / RS). Return value or None if ?."""
        loc = loc.encode() if isinstance(loc, str) else loc
        self.write(loc + b"/")
        buf, m = self.read_until(rb"/([0-7]{6}) $|\?\r\n@$")
        if m.group(1) is None:
            return None
        return int(m.group(1), 8)

    def close_loc(self, value=None):
        """Close the open location with CR, optionally depositing value."""
        s = b"" if value is None else (b"%o" % value)
        self.write(s + b"\r")
        self.read_until(rb"\r\n@$")

    def next_loc(self, value=None):
        """Close with LF and open the next location. Return (label, value)."""
        s = b"" if value is None else (b"%o" % value)
        self.write(s + b"\n")
        buf, m = self.read_until(rb"\r\n([0-7RS]+)/([0-7]{6}) $|\?\r\n@$")
        if m.group(1) is None:
            return None
        return m.group(1).decode(), int(m.group(2), 8)

    def read(self, loc):
        v = self.open(loc)
        if v is None:
            return None
        self.close_loc()
        return v

    def deposit(self, loc, value):
        v = self.open(loc)
        if v is None:
            return False
        self.close_loc(value)
        return True
