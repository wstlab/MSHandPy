import sys
import time
import os


class Pyboard:
    def __init__(self, device, baudrate=115200, wait=0):
        self.device = device
        self.baudrate = baudrate
        self.wait = wait
        self.serial = None
        self._connect()

    def _connect(self):
        if self.device == 'sim':
            self.serial = PyboardSimSerial()
        else:
            try:
                import serial
                self.serial = serial.Serial(self.device, baudrate=self.baudrate, timeout=1)
                time.sleep(self.wait)
            except ImportError:
                print("pyserial not installed, using simulator mode")
                self.serial = PyboardSimSerial()

    def close(self):
        if self.serial:
            self.serial.close()

    def read_until(self, min_num_bytes, ending, timeout=20, data_consumer=None):
        assert data_consumer is None or len(ending) == 1

        data = self.serial.read(min_num_bytes)
        if data_consumer:
            data_consumer(data)
        timeout_count = 0
        while True:
            if data.endswith(ending):
                break
            elif self.serial.inWaiting() > 0:
                new_data = self.serial.read(1)
                if data_consumer:
                    data_consumer(new_data)
                    data = new_data
                else:
                    data = data + new_data
                timeout_count = 0
            else:
                timeout_count += 1
                if timeout is not None and timeout_count >= 100 * timeout:
                    break
                time.sleep(0.01)
        return data

    def enter_raw_repl(self):
        self.serial.write(b"\r\n\x03\x03")
        time.sleep(0.1)
        n = self.serial.inWaiting()
        if n > 0:
            self.serial.read(n)
        self.serial.write(b"\r\n\x01")
        data = self.read_until(1, b"raw REPL; CTRL-B to exit\r\n>", timeout=10)
        if not data.endswith(b"raw REPL; CTRL-B to exit\r\n>"):
            raise Exception("could not enter raw repl")
        self.serial._buffer = b">" + self.serial._buffer

    def exit_raw_repl(self):
        self.serial.write(b"\r\x02")

    def follow(self, timeout, data_consumer=None):
        data = self.read_until(1, b"\x04", timeout=timeout, data_consumer=data_consumer)
        if not data.endswith(b"\x04"):
            raise Exception("timeout waiting for first EOF reception")
        data = data[:-1]

        data_err = self.read_until(1, b"\x04", timeout=timeout)
        if not data_err.endswith(b"\x04"):
            raise Exception("timeout waiting for second EOF reception")
        data_err = data_err[:-1]

        return data, data_err

    def exec_raw_no_follow(self, command):
        if isinstance(command, bytes):
            command_bytes = command
        else:
            command_bytes = bytes(command, "utf8")

        data = self.read_until(1, b">")
        if not data.endswith(b">"):
            raise Exception("could not enter raw repl")

        for i in range(0, len(command_bytes), 256):
            self.serial.write(command_bytes[i: min(i + 256, len(command_bytes))])
            time.sleep(0.01)
        self.serial.write(b"\x04")

        data = self.serial.read(2)
        if data != b"OK":
            raise Exception("could not exec command (response: %r)" % data)

    def exec_raw(self, command, timeout=20, data_consumer=None):
        self.exec_raw_no_follow(command)
        return self.follow(timeout, data_consumer)

    def exec_(self, command, data_consumer=None):
        ret, ret_err = self.exec_raw(command, data_consumer=data_consumer)
        if ret_err:
            raise Exception("exception", ret, ret_err)
        return ret

    def exec_file(self, filename):
        with open(filename, "rb") as f:
            pyfile = f.read()
        return self.exec_(pyfile)

    def fs_ls(self, src):
        cmd = (
            "import uos\r\nfor f in uos.listdir(%s):\r\n"
            "   print(f)"
            % (("'%s'" % src) if src else "")
        )
        self.exec_(cmd)

    def fs_get(self, src, dest):
        self.exec_("f=open('%s','rb')\nr=f.read" % src)
        with open(dest, "wb") as f:
            while True:
                data = bytearray()
                self.exec_("print(r(1024))", data_consumer=lambda d: data.extend(d))
                if data[-3:] == b"\r\n\x04":
                    data = data[:-3]
                data_str = data.decode('ascii', errors='ignore')
                try:
                    data = eval(data_str)
                except:
                    break
                if not data:
                    break
                f.write(data)
        self.exec_("f.close()")

    def fs_put(self, src, dest):
        self.exec_("f=open('%s','wb')\nw=f.write" % dest)
        with open(src, "rb") as f:
            while True:
                data = f.read(1024)
                if not data:
                    break
                self.exec_("w(" + repr(data) + ")")
        self.exec_("f.close()")

    def fs_rm(self, src):
        self.exec_("import uos\nuos.remove('%s')" % src)

    def fs_mkdir(self, dir):
        self.exec_("import uos\nuos.mkdir('%s')" % dir)

    def fs_rmdir(self, dir):
        self.exec_("import uos\nuos.rmdir('%s')" % dir)

    def reset(self):
        self.serial.write(b"\x04")
        time.sleep(0.5)


class PyboardSimSerial:
    def __init__(self):
        self._buffer = b""
        self._repl_active = False
        self._raw_repl = False
        self._expect_enter = False

    def write(self, data):
        for byte in data:
            self._process_byte(byte)

    def read(self, size=1):
        if len(self._buffer) > 0:
            result = self._buffer[:size]
            self._buffer = self._buffer[size:]
            return result
        return b""

    def inWaiting(self):
        return len(self._buffer)

    def close(self):
        pass

    def _process_byte(self, byte):
        if not self._repl_active:
            if byte == 0x03:
                self._repl_active = True
                self._expect_enter = True
            elif byte == 0x01:
                self._repl_active = True
                self._raw_repl = True
                self._buffer += b"raw REPL; CTRL-B to exit\r\n>"
            return

        if self._expect_enter:
            if byte == 0x01:
                self._raw_repl = True
                self._buffer += b"raw REPL; CTRL-B to exit\r\n>"
            elif byte != 0x03 and byte != 0x0D and byte != 0x0A:
                self._expect_enter = False
            return

        if byte == 0x01:
            self._raw_repl = True
            self._buffer += b"raw REPL; CTRL-B to exit\r\n>"
            return

        if self._raw_repl:
            if byte == 0x02:
                self._raw_repl = False
                self._buffer += b"\r\n"
            elif byte == 0x03:
                self._buffer += b"\r\n>>> "
            elif byte == 0x04:
                self._buffer += b"OK\x04\x04>"
            elif byte == 0x0D:
                pass
            elif byte == 0x0A:
                pass
            else:
                pass


def main():
    if len(sys.argv) < 2:
        print("Usage: pyboard.py <device> [command]")
        sys.exit(1)

    device = sys.argv[1]

    if device == 'list':
        print("Available devices:")
        print("  sim - Simulator")
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            for port in ports:
                print(f"  {port.device} - {port.description}")
        except ImportError:
            pass
        sys.exit(0)

    pb = Pyboard(device)
    pb.enter_raw_repl()

    if len(sys.argv) == 2:
        pb.exec_("import os; print(os.listdir())")
    elif sys.argv[2] == 'run':
        if len(sys.argv) < 4:
            print("Usage: pyboard.py <device> run <file.py>")
            sys.exit(1)
        pb.exec_file(sys.argv[3])
    elif sys.argv[2] == 'put':
        if len(sys.argv) < 5:
            print("Usage: pyboard.py <device> put <src> <dest>")
            sys.exit(1)
        pb.fs_put(sys.argv[3], sys.argv[4])
    elif sys.argv[2] == 'get':
        if len(sys.argv) < 5:
            print("Usage: pyboard.py <device> get <src> <dest>")
            sys.exit(1)
        pb.fs_get(sys.argv[3], sys.argv[4])
    elif sys.argv[2] == 'ls':
        pb.fs_ls(sys.argv[3] if len(sys.argv) > 3 else '')
    elif sys.argv[2] == 'rm':
        pb.fs_rm(sys.argv[3])
    else:
        pb.exec_(' '.join(sys.argv[2:]))

    pb.exit_raw_repl()
    pb.close()


if __name__ == "__main__":
    main()