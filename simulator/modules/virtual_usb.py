import socket
import threading
import time
import sys
import os
import json

IS_WINDOWS = sys.platform.startswith('win')
IS_MACOS = sys.platform == 'darwin'

def _default_serial():
    if IS_WINDOWS:
        return "COM20"
    elif IS_MACOS:
        return "/dev/cu.mpVirt2"
    else:
        return "/tmp/vcom2"

_proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _proj_root)
sys.path.insert(0, os.path.join(_proj_root, 'simulator'))
sys.path.insert(0, os.path.join(_proj_root, 'simulator', 'modules'))

from mindplus_transpiler import is_mindplus_code, transpile

CH9102_VID = "1A86"
CH9102_PID = "5512"


class VirtualUSB:
    def __init__(self, host='127.0.0.1', port=7777):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self._conn = None
        self._buffer = b""
        self._repl_active = False
        self._raw_repl = False
        self._cmd_buffer = b""
        self._thread = None
        self._vm_server_host = '127.0.0.1'
        self._vm_server_port = 7778
        
        self._clients = []
        self._connected = False
        self._connection_callback = None
        self._lock = threading.Lock()

    def start(self):
        self.running = True
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        self.server.settimeout(1.0)
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        for conn in self._clients:
            try:
                conn.close()
            except:
                pass
        self._clients.clear()
        if self._conn:
            try:
                self._conn.close()
            except:
                pass
        if self.server:
            try:
                self.server.close()
            except:
                pass

    def set_connection_callback(self, callback):
        self._connection_callback = callback

    def is_connected(self):
        return self._connected

    def get_device_info(self):
        return {
            'vid': CH9102_VID,
            'pid': CH9102_PID,
            'device_name': 'USB Serial Port (CH9102)',
            'port': self.port
        }

    def _send_to_vm(self, command):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((self._vm_server_host, self._vm_server_port))
            sock.sendall(json.dumps(command).encode('utf-8') + b"\n")
            response = ""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                response += data.decode('utf-8')
                if "\n" in response:
                    response = response.split("\n")[0]
                    break
            sock.close()
            return json.loads(response) if response else {'status': 'error', 'message': 'No response'}
        except Exception as e:
            return {'status': 'error', 'message': f'VM server not available: {e}'}

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                conn.settimeout(0.1)
                with self._lock:
                    self._clients.append(conn)
                    # 第一个连接作为激活 REPL 连接
                    if self._conn is None:
                        self._conn = conn
                        self._buffer = b""
                        self._repl_active = False
                        self._raw_repl = False
                        self._cmd_buffer = b""
                        self._connected = True
                if self._connected and conn is self._conn and self._connection_callback:
                    self._connection_callback(True)
                # 每个连接独立线程处理，避免单个客户端阻塞后饿死其他客户端
                threading.Thread(target=self._handle_connection, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[virtual_usb] accept 异常: {e}")

    def _handle_connection(self, conn):
        while self.running:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                if conn is self._conn:
                    for byte in data:
                        self._process_byte(byte)
                    self._send_response()
                else:
                    # 非激活连接（如串口桥）：数据转发给当前激活连接
                    if self._conn:
                        try:
                            self._conn.send(data)
                        except Exception:
                            pass
            except socket.timeout:
                continue
            except Exception:
                break

        with self._lock:
            if conn in self._clients:
                self._clients.remove(conn)
            if conn is self._conn:
                self._conn = None
                self._connected = False
        if not self._connected and self._connection_callback:
            self._connection_callback(False)

    def _process_byte(self, byte):
        if not self._repl_active:
            if byte == 0x03:
                self._repl_active = True
                self._buffer += b"\r\n"
                # Ctrl+C：中断正在执行的用户代码
                self._send_to_vm({'action': 'stop_execution'})
            elif byte == 0x01:
                self._repl_active = True
                self._raw_repl = True
                self._buffer += b"raw REPL; CTRL-B to exit\r\n>"
            return

        if self._raw_repl:
            if byte == 0x02:
                self._raw_repl = False
                self._buffer += b"\r\n"
            elif byte == 0x03:
                self._buffer += b"\r\n>>> "
                self._send_to_vm({'action': 'stop_execution'})
            elif byte == 0x04:
                result = self._execute_code()
                self._buffer += b"OK" + result + b"\x04\x04>"
            elif byte == 0x0D:
                self._cmd_buffer += b"\n"
            elif byte == 0x0A:
                pass
            else:
                self._cmd_buffer += bytes([byte])
        else:
            # 普通 REPL 模式：Ctrl+C 同样触发中断
            if byte == 0x03:
                self._buffer += b"\r\n"
                self._send_to_vm({'action': 'stop_execution'})

    def _execute_code(self):
        if not self._cmd_buffer:
            return b""
        code = self._cmd_buffer.decode('utf-8', errors='ignore')
        self._cmd_buffer = b""
        
        try:
            if is_mindplus_code(code):
                code = transpile(code)
            
            result = self._send_to_vm({'action': 'execute', 'code': code})
            output = result.get('output', '')
            return str(output).encode('utf-8')
        except Exception as e:
            return str(e).encode('utf-8')

    def _send_response(self):
        if self._conn and self._buffer:
            try:
                self._conn.send(self._buffer)
            except:
                pass
            self._buffer = b""


class SerialToTCPBridge:
    def __init__(self, tcp_host='127.0.0.1', tcp_port=7777, serial_port=None, baudrate=115200):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.serial_port = serial_port or _default_serial()
        self.baudrate = baudrate
        self.running = False
        self._thread = None
        self._serial = None
        self._tcp_socket = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._bridge_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
            self._serial = None
        if self._tcp_socket:
            try:
                self._tcp_socket.close()
            except:
                pass
            self._tcp_socket = None

    def _bridge_loop(self):
        import serial
        while self.running:
            try:
                self._serial = serial.Serial(
                    self.serial_port, 
                    self.baudrate, 
                    timeout=0.1,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_1,
                    bytesize=serial.EIGHTBITS
                )
                
                while self.running:
                    try:
                        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        tcp_socket.connect((self.tcp_host, self.tcp_port))
                        self._tcp_socket = tcp_socket
                        
                        self._data_loop(tcp_socket)
                        
                    except ConnectionRefusedError:
                        time.sleep(1)
                    except:
                        time.sleep(2)
                        
                    self._tcp_socket = None
                    
            except serial.SerialException:
                time.sleep(3)
            except:
                time.sleep(2)
            
            if self._serial:
                try:
                    self._serial.close()
                except:
                    pass
                self._serial = None

    def _data_loop(self, tcp_socket):
        tcp_socket.settimeout(0.01)
        self._serial.timeout = 0.01
        
        while self.running and self._serial and tcp_socket:
            try:
                serial_data = self._serial.read(1024)
                if serial_data:
                    tcp_socket.send(serial_data)
            except:
                pass
            
            try:
                tcp_data = tcp_socket.recv(1024)
                if tcp_data:
                    self._serial.write(tcp_data)
            except:
                pass
            
            time.sleep(0.001)


_virtual_usb = None


def start_virtual_usb(host='127.0.0.1', port=7777):
    global _virtual_usb
    _virtual_usb = VirtualUSB(host, port)
    _virtual_usb.start()
    return _virtual_usb


def stop_virtual_usb():
    global _virtual_usb
    if _virtual_usb:
        _virtual_usb.stop()
        _virtual_usb = None


def get_virtual_usb():
    return _virtual_usb