import sys
import time
import select
import os
from machine import Pin, UART


class Serial:
    def __init__(self, id=2, baudrate=2000000, rx_pin=14, tx_pin=12, timeout=2000, timeout_char=10):
        self.uart = UART(id, baudrate, rx=rx_pin, tx=tx_pin, timeout=timeout, rxbuf=4096)
        self._buffer = b""

    def close(self):
        self.uart.deinit()

    def read(self, size=1):
        data = self.uart.read(size)
        if data is None:
            data = b""
        return data

    def write(self, data):
        return self.uart.write(data)

    def inWaiting(self):
        return len(self.uart._buffer) if hasattr(self.uart, '_buffer') else 0


class RemoteException(Exception):
    pass


def stdout_write_bytes(b):
    b = b.replace(b"\x04", b"")
    sys.stdout.write(b.decode('utf-8', errors='ignore'))


class REPL:
    def __init__(self, serial):
        self.serial = serial
        self.debug = False

    def close(self):
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

    def enter_raw_repl(self, timeout=20, soft_rest=False):
        self.serial.write(b"\r\n\x03\x03")

        n = self.serial.inWaiting()
        if n == 0:
            self.serial.write(b"\x02")

        while n > 0:
            self.serial.read(n)
            n = self.serial.inWaiting()

        self.serial.write(b"\r\n\x01")
        data = self.read_until(1, b"raw REPL; CTRL-B to exit\r\n>", timeout)
        if not data.endswith(b"raw REPL; CTRL-B to exit\r\n>"):
            raise RemoteException("could not enter raw repl")

        if soft_rest:
            self.serial.write(b"\x04")
            data = self.read_until(1, b"soft reboot\r\n", timeout)
            if not data.endswith(b"soft reboot\r\n"):
                raise RemoteException("could not enter raw repl")
            data = self.read_until(1, b"raw REPL; CTRL-B to exit\r\n", timeout)
            if not data.endswith(b"raw REPL; CTRL-B to exit\r\n"):
                raise RemoteException("could not enter raw repl")

        self.serial.write(b'import os')
        self.serial.write(b'\x04')
        self.follow(10)

    def exit_raw_repl(self):
        self.serial.write(b"\r\x02")

    def follow(self, timeout, data_consumer=None):
        data = self.read_until(1, b"\x04", timeout=timeout, data_consumer=data_consumer)
        if not data.endswith(b"\x04"):
            raise RemoteException("timeout waiting for first EOF reception")
        data = data[:-1]

        data_err = self.read_until(1, b"\x04", timeout=timeout)
        if not data_err.endswith(b"\x04"):
            raise RemoteException("timeout waiting for second EOF reception")
        data_err = data_err[:-1]

        return data, data_err

    def exec_raw_no_follow(self, command):
        if isinstance(command, bytes):
            command_bytes = command
        else:
            command_bytes = bytes(command, "utf8")
        if self.debug:
            print("CMD: {:s}".format(command_bytes))

        data = self.read_until(1, b">")
        if not data.endswith(b">"):
            raise RemoteException("could not enter raw repl")

        for i in range(0, len(command_bytes), 256):
            self.serial.write(command_bytes[i: min(i + 256, len(command_bytes))])
            time.sleep(0.01)
        self.serial.write(b"\x04")

        data = self.serial.read(2)
        if data != b"OK":
            raise RemoteException("could not exec command (response: %r)" % data)

    def exec_raw(self, command, timeout=20, data_consumer=None):
        self.exec_raw_no_follow(command)
        return self.follow(timeout, data_consumer)

    def eval(self, expression):
        ret = self.exec_("print({0})".format(expression))
        ret = ret.strip()
        return ret

    def exec_(self, command, data_consumer=None):
        ret, ret_err = self.exec_raw(command, data_consumer=data_consumer)
        if ret_err:
            raise RemoteException("exception", ret, ret_err)
        return ret

    def exec_file(self, filename):
        with open(filename, "rb") as f:
            pyfile = f.read()
        return self.exec_(pyfile)

    def fs_ls(self, src):
        cmd = (
            "import uos\r\nfor f in uos.listdir(%s):\r\n"
            "   print('{:12} {}{}'.format(f[3] if len(f)>3 else 0,f[0],'/' if f[1]&0x4000 else ''))"
            % (("'%s'" % src) if src else "")
        )
        self.exec_(cmd, data_consumer=stdout_write_bytes)

    def fs_cat(self, src, chunk_size=256):
        cmd = (
            "with open('%s') as f:\n while 1:\n"
            "  b=f.read(%u)\n  if not b:break\n  print(b,end='')" % (
                src, chunk_size)
        )
        self.exec_(cmd, data_consumer=stdout_write_bytes)

    def fs_get(self, src, dest, chunk_size=1024):
        self.exec_("f=open('%s','rb')\nr=f.read" % src)
        with open(dest, "wb") as f:
            while True:
                data = bytearray()
                self.exec_("print(r(%u))" % chunk_size, data_consumer=lambda d: data.extend(d))
                assert data[-3:] == b"\r\n\x04"
                data = eval(str(data[:-3], "ascii"))
                if data == bytearray(b""):
                    break
                f.write(data)
        self.exec_("f.close()")

    def fs_put(self, src, dest, chunk_size=1024):
        self.exec_("f=open('%s','wb')\nw=f.write" % dest)
        with open(src, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                if sys.version_info < (3,):
                    self.exec_("w(b" + repr(data) + ")")
                else:
                    self.exec_("w(" + repr(data) + ")")
        self.exec_("f.close()")

    def fs_mkdir(self, dir):
        self.exec_("import uos\nuos.mkdir('%s')" % dir)

    def fs_rmdir(self, dir):
        self.exec_("import uos\nuos.rmdir('%s')" % dir)

    def fs_rm(self, src):
        self.exec_("import uos\nuos.remove('%s')" % src)