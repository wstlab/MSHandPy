import os
import sys
import time

def _get_data_dir():
    if getattr(sys, '_MEIPASS', None):
        return os.path.join(os.path.expanduser('~'), '.simhandpy')
    return os.path.join(os.path.dirname(__file__), '..')

class VfsLfs2:
    def __init__(self, bdev):
        self._bdev = bdev
        self._root = bdev._root if hasattr(bdev, '_root') else '/sim_flash'
    
    def mkdir(self, path):
        full_path = os.path.join(self._root, path.lstrip('/'))
        os.makedirs(full_path, exist_ok=True)
    
    def rmdir(self, path):
        full_path = os.path.join(self._root, path.lstrip('/'))
        os.rmdir(full_path)
    
    def remove(self, path):
        full_path = os.path.join(self._root, path.lstrip('/'))
        os.remove(full_path)
    
    def listdir(self, path=''):
        full_path = os.path.join(self._root, path.lstrip('/'))
        if not os.path.exists(full_path):
            raise OSError(2)
        return os.listdir(full_path)
    
    @staticmethod
    def mkfs(bdev):
        root = bdev._root if hasattr(bdev, '_root') else '/sim_flash'
        os.makedirs(root, exist_ok=True)
        return VfsLfs2(bdev)


class FlashBdev:
    SEC_SIZE = 512
    
    def __init__(self):
        self._root = os.path.join(_get_data_dir(), 'flash')
        os.makedirs(self._root, exist_ok=True)
    
    def ioctl(self, cmd, arg):
        if cmd == 5:
            return bytearray(self.SEC_SIZE)
        return 0
    
    def readblocks(self, block_num, buf):
        block_path = os.path.join(self._root, f'block_{block_num:08d}')
        if os.path.exists(block_path):
            with open(block_path, 'rb') as f:
                data = f.read(len(buf))
                buf[:len(data)] = data
        else:
            buf[:] = b'\xff' * len(buf)
    
    def writeblocks(self, block_num, buf):
        block_path = os.path.join(self._root, f'block_{block_num:08d}')
        with open(block_path, 'wb') as f:
            f.write(buf)


bdev = FlashBdev()

_mounts = {}

def mount(vfs, path):
    _mounts[path] = vfs

def umount(path):
    if path in _mounts:
        del _mounts[path]

def listdir(path='.'):
    if path in _mounts:
        return _mounts[path].listdir(path)
    return os.listdir(path)

def mkdir(path):
    os.makedirs(path, exist_ok=True)

def rmdir(path):
    os.rmdir(path)

def remove(path):
    os.remove(path)

def rename(src, dst):
    os.rename(src, dst)

def chdir(path):
    os.chdir(path)

def getcwd():
    return os.getcwd()

def stat(path):
    st = os.stat(path)
    return (st.st_mode, st.st_ino, 0, st.st_size, st.st_atime, st.st_mtime, st.st_ctime)

def uname():
    return ('mPython', '1.0.0', 'v1.15-xxx', '2026-07-22', 'ESP32')

def urandom(n):
    import random
    return bytes([random.randint(0, 255) for _ in range(n)])

def sync():
    pass

def dupterm(stream, index=0):
    pass


class dupterm_notice:
    pass


def check_bootsec():
    buf = bytearray(bdev.ioctl(5, 0))
    bdev.readblocks(0, buf)
    for b in buf:
        if b != 0xFF:
            return False
    return True


def fs_corrupted():
    print("WARNING: 模拟文件系统损坏，将重新格式化")
    time.sleep(0.5)
    bdev.writeblocks(0, bytearray([0xFF] * bdev.SEC_SIZE))


def setup():
    check_bootsec()
    print("Performing initial setup")
    # 模块以不同名称被导入（uos / simulator.modules.uos），统一经 globals() 引用
    _m = globals()
    _m['VfsLfs2'].mkfs(bdev)
    vfs = _m['VfsLfs2'](bdev)
    _m['mount'](vfs, "/")
    with open("boot.py", "w") as f:
        f.write("""\
# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()
""")
    return vfs