# -*- coding: utf-8 -*-
"""
VM WebSocket Server - Mind+ 实时模式连接服务
监听端口 7779，接受 Mind+ WebSocket 连接，将指令转发到 VM Server (7778)。
使用标准库实现，无需安装额外依赖。
"""
import socket
import threading
import json
import os
import hashlib
import base64

VM_SERVER_HOST = '127.0.0.1'
VM_SERVER_PORT = 7778
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class VMWebSocketServer:
    def __init__(self, host='127.0.0.1', port=7779):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self._thread = None
        self._clients = []

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
        for c in self._clients:
            try:
                c.close()
            except:
                pass
        self._clients.clear()
        if self.server:
            try:
                self.server.close()
            except:
                pass

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr),
                                 daemon=True).start()
            except socket.timeout:
                continue
            except:
                if self.running:
                    pass

    def _handle_client(self, conn, addr):
        try:
            # WebSocket 握手
            data = conn.recv(4096)
            if not data:
                return
            request = data.decode('utf-8', errors='ignore')

            if 'Sec-WebSocket-Key' not in request:
                conn.close()
                return

            # 提取 WebSocket-Key
            key = None
            for line in request.split('\r\n'):
                if line.lower().startswith('sec-websocket-key:'):
                    key = line.split(':', 1)[1].strip()
                    break

            if not key:
                conn.close()
                return

            # 计算握手响应
            response_key = base64.b64encode(
                hashlib.sha1((key + WS_MAGIC).encode()).digest()
            ).decode()
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {response_key}\r\n\r\n"
            )
            conn.send(response.encode())
            self._clients.append(conn)

            # 消息循环
            while self.running:
                msg = self._recv_ws_frame(conn)
                if msg is None:
                    break
                # 转发到 VM Server
                result = self._send_to_vm(msg)
                if result:
                    self._send_ws_frame(conn, json.dumps(result))
        except:
            pass
        finally:
            if conn in self._clients:
                self._clients.remove(conn)
            try:
                conn.close()
            except:
                pass

    def _recv_ws_frame(self, conn):
        """接收一个 WebSocket 帧，返回解码后的文本（None 表示连接关闭）"""
        try:
            header = conn.recv(2)
            if len(header) < 2:
                return None
            opcode = header[0] & 0x0F
            masked = (header[1] & 0x80) != 0
            payload_len = header[1] & 0x7F

            if payload_len == 126:
                ext = conn.recv(2)
                payload_len = int.from_bytes(ext, 'big')
            elif payload_len == 127:
                ext = conn.recv(8)
                payload_len = int.from_bytes(ext, 'big')

            mask = b''
            if masked:
                mask = conn.recv(4)

            data = b''
            while len(data) < payload_len:
                chunk = conn.recv(payload_len - len(data))
                if not chunk:
                    return None
                data += chunk

            if masked:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))

            # opcode 8 = close
            if opcode == 8:
                return None

            return data.decode('utf-8', errors='ignore')
        except:
            return None

    def _send_ws_frame(self, conn, text):
        """发送一个 WebSocket 文本帧"""
        data = text.encode('utf-8')
        header = bytearray([0x81])  # FIN + text frame
        if len(data) < 126:
            header.append(len(data))
        elif len(data) < 65536:
            header.append(126)
            header.extend(len(data).to_bytes(2, 'big'))
        else:
            header.append(127)
            header.extend(len(data).to_bytes(8, 'big'))
        try:
            conn.send(bytes(header) + data)
        except:
            pass

    def _send_to_vm(self, command_str):
        """将 JSON 指令转发到 VM Server"""
        try:
            command = json.loads(command_str)
        except:
            return {'status': 'error', 'message': 'Invalid JSON'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((VM_SERVER_HOST, VM_SERVER_PORT))
            sock.sendall(json.dumps(command).encode('utf-8') + b"\n")
            response = b""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                response += data
                if b"\n" in response:
                    response = response.split(b"\n")[0]
                    break
            sock.close()
            return json.loads(response.decode('utf-8')) if response else {
                'status': 'error', 'message': 'No response from VM Server'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


if __name__ == "__main__":
    server = VMWebSocketServer()
    server.start()
    print(f"WebSocket server listening on {server.host}:{server.port}")
    print("Press Ctrl+C to stop")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("Stopped")
