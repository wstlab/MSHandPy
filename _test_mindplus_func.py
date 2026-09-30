# -*- coding: utf-8 -*-
"""Mind+ 全链路功能测试（反复运行直到成功）

测试三条链路:
  A. VM Server      TCP 7778  JSON 行协议 (ping / execute / 硬件指令)
  B. Mind+ 直连     TCP 7777  Raw REPL 字节协议 (Mind+ 上传/TCP 直连走的协议)
  C. WebSocket      TCP 7779  实时模式扩展走的协议
"""
import socket
import json
import time
import sys
import os
import base64
import hashlib
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS, FAIL = "PASS", "FAIL"
results = []


def report(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def wait_port(host, port, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            s.connect((host, port))
            s.close()
            return True
        except OSError:
            time.sleep(0.3)
        finally:
            try:
                s.close()
            except Exception:
                pass
    return False


# ---------- A. VM Server 7778 ----------
def vm_cmd(cmd, timeout=8.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(("127.0.0.1", 7778))
    s.sendall(json.dumps(cmd).encode("utf-8") + b"\n")
    buf = b""
    while b"\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    s.close()
    return json.loads(buf.decode("utf-8").split("\n")[0])


def test_vm_server():
    print("\n[A] VM Server (127.0.0.1:7778)")
    if not wait_port("127.0.0.1", 7778):
        report("7778 端口监听", False, "连接不上")
        return
    report("7778 端口监听", True)

    try:
        r = vm_cmd({"action": "ping"})
        report("ping 响应", r.get("status") == "ok", str(r)[:120])
    except Exception as e:
        report("ping 响应", False, repr(e))

    try:
        r = vm_cmd({"action": "execute", "code": "print('VM_HELLO_' + str(6*7))"})
        out = r.get("output", "")
        ok = r.get("status") == "ok" and "VM_HELLO_42" in out
        report("execute print 代码", ok, f"status={r.get('status')} output={out!r}")
    except Exception as e:
        report("execute print 代码", False, repr(e))

    try:
        r = vm_cmd({"action": "execute",
                    "code": "oled.DispChar('Mind+OK', 0, 0); oled.show()"})
        report("execute OLED 显示", r.get("status") == "ok", str(r)[:120])
    except Exception as e:
        report("execute OLED 显示", False, repr(e))

    try:
        r = vm_cmd({"action": "execute",
                    "code": "rgb[0]=(0,40,0); rgb.write()"})
        report("execute RGB 灯", r.get("status") == "ok", str(r)[:120])
    except Exception as e:
        report("execute RGB 灯", False, repr(e))

    try:
        r = vm_cmd({"action": "execute", "code": "1/0"})
        # 现有协议（类 REPL 语义）：异常信息放入 output，服务不中断、不崩连接
        blob = str(r.get("output", "")) + str(r.get("message", ""))
        ok = "division by zero" in blob or r.get("status") == "error"
        report("execute 异常代码被捕获且服务存活", ok, str(r)[:150])
    except Exception as e:
        report("execute 异常代码被捕获且服务存活", False, repr(e))


# ---------- B. Mind+ Direct 7777 (Raw REPL) ----------
def recv_until(sock, marker, timeout=8.0):
    sock.settimeout(timeout)
    buf = b""
    end = time.time() + timeout
    while marker not in buf and time.time() < end:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
    return buf


def test_direct_server():
    print("\n[B] Mind+ 直连 Raw REPL (127.0.0.1:7777)")
    if not wait_port("127.0.0.1", 7777):
        report("7777 端口监听", False, "连接不上")
        return
    report("7777 端口监听", True)

    # B1: 普通 Python 代码经 raw REPL 执行
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(("127.0.0.1", 7777))
        banner = recv_until(s, b">", timeout=2.0)
        # 0x01 进入 raw REPL
        s.sendall(bytes([0x01]))
        time.sleep(0.3)
        greeting = recv_until(s, b">", timeout=2.0)
        report("进入 raw REPL", b"raw REPL" in greeting or b">" in greeting,
               repr(greeting[:60]))

        code = b"print('DIRECT_HELLO')"
        s.sendall(code + bytes([0x0D]))   # CR 结束行
        s.sendall(bytes([0x04]))          # Ctrl-D 执行
        resp = recv_until(s, b"\x04\x04>", timeout=8.0)
        ok = resp.startswith(b"OK") and b"DIRECT_HELLO" in resp
        report("raw REPL 执行 Python 代码", ok, repr(resp[:120]))
        s.close()
    except Exception as e:
        report("raw REPL 执行 Python 代码", False, repr(e))
        try:
            s.close()
        except Exception:
            pass

    # B2: Mind+ 生成的 C++ 代码 -> 转译 -> 执行
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(("127.0.0.1", 7777))
        recv_until(s, b">", timeout=2.0)
        s.sendall(bytes([0x01]))
        time.sleep(0.3)
        recv_until(s, b">", timeout=2.0)

        cpp = (
            "#include <MPython.h>\n"
            "void setup(){\n"
            "  mPython.begin();\n"
            "  display.setCursor(0,0);\n"
            "  display.printLine(\"CPP_TRANSPILED_OK\");\n"
            "}\n"
            "void loop(){\n"
            "  delay(100);\n"
            "}\n"
        )
        payload = cpp.encode("utf-8").replace(b"\n", b"\r")
        s.sendall(payload + bytes([0x04]))
        resp = recv_until(s, b"\x04\x04>", timeout=10.0)
        # 转译后的代码里含 while True + sleep_ms，会一直跑，服务端 execute 有 3s 超时，
        # 关键是不能返回错误/traceback
        bad = b"Traceback" in resp or b"Error" in resp or not resp.startswith(b"OK")
        report("Mind+ C++ 代码转译执行", not bad, repr(resp[:150]))
        s.close()
    except Exception as e:
        report("Mind+ C++ 代码转译执行", False, repr(e))
        try:
            s.close()
        except Exception:
            pass

    # B3: 回归测试——一个空闲(不发数据)连接占着时，新连接仍能立即被接受并服务
    idle = None
    try:
        idle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        idle.settimeout(3)
        idle.connect(("127.0.0.1", 7777))
        time.sleep(0.5)  # 服务端已 accept 该空闲连接

        t0 = time.time()
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.settimeout(3)
        s2.connect(("127.0.0.1", 7777))
        accepted_ms = (time.time() - t0) * 1000
        s2.sendall(bytes([0x01]))
        time.sleep(0.3)
        greeting = recv_until(s2, b">", timeout=2.0)
        s2.sendall(b"print('CONCURRENT_OK')" + bytes([0x0D, 0x04]))
        resp = recv_until(s2, b"\x04\x04>", timeout=8.0)
        ok = b"CONCURRENT_OK" in resp and accepted_ms < 2000
        report("空闲连接不阻塞新连接(并发)", ok,
               f"accept={accepted_ms:.0f}ms resp={resp[:60]!r}")
        s2.close()
    except Exception as e:
        report("空闲连接不阻塞新连接(并发)", False, repr(e))
        try:
            s2.close()
        except Exception:
            pass
    finally:
        if idle:
            try:
                idle.close()
            except Exception:
                pass

    # B4: 有限 C++ 代码（仅 setup，无 loop）应在 3s 内正常返回，输出串口内容
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(("127.0.0.1", 7777))
        recv_until(s, b">", timeout=2.0)
        s.sendall(bytes([0x01]))
        time.sleep(0.3)
        recv_until(s, b">", timeout=2.0)

        cpp = (
            "#include <MPython.h>\n"
            "void setup(){\n"
            "  mPython.begin();\n"
            "  rgb.setPixelColor(0, 0x00FF00);\n"
            "  display.setCursor(0,0);\n"
            '  display.println("HI");\n'
            '  Serial.println("SERIAL_FINITE_OK");\n'
            "  delay(50);\n"
            "}\n"
        )
        payload = cpp.encode("utf-8").replace(b"\n", b"\r")
        s.sendall(payload + bytes([0x04]))
        resp = recv_until(s, b"\x04\x04>", timeout=8.0)
        bad = (not resp.startswith(b"OK")) or b"Error" in resp \
            or b"Traceback" in resp or b"\xe8\xb6\x85\xe6\x97\xb6" in resp
        ok = (not bad) and b"SERIAL_FINITE_OK" in resp
        report("有限 C++ 代码转译立即执行", ok, repr(resp[:150]))
        s.close()
    except Exception as e:
        report("有限 C++ 代码转译立即执行", False, repr(e))
        try:
            s.close()
        except Exception:
            pass


# ---------- C. WebSocket 7779 ----------
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def ws_send_text(sock, text):
    data = text.encode("utf-8")
    key = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0"
    mask_key = key[:4]
    masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))
    if len(data) < 126:
        header = bytes([0x81, 0x80 | len(data)])
    elif len(data) < 65536:
        header = bytes([0x81, 0x80 | 126]) + struct.pack(">H", len(data))
    else:
        header = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", len(data))
    sock.sendall(header + mask_key + masked)


def ws_recv_text(sock, timeout=5.0):
    sock.settimeout(timeout)
    header = sock.recv(2)
    if len(header) < 2:
        return None
    opcode = header[0] & 0x0F
    ln = header[1] & 0x7F
    if ln == 126:
        ln = struct.unpack(">H", sock.recv(2))[0]
    elif ln == 127:
        ln = struct.unpack(">Q", sock.recv(8))[0]
    buf = b""
    while len(buf) < ln:
        chunk = sock.recv(ln - len(buf))
        if not chunk:
            break
        buf += chunk
    if opcode == 8:
        return None
    return buf.decode("utf-8", errors="ignore")


def test_websocket():
    print("\n[C] WebSocket 实时模式 (127.0.0.1:7779)")
    if not wait_port("127.0.0.1", 7779):
        report("7779 端口监听", False, "连接不上")
        return
    report("7779 端口监听", True)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(("127.0.0.1", 7779))
        nonce = base64.b64encode(os.urandom(16)).decode()
        req = (
            "GET / HTTP/1.1\r\n"
            "Host: 127.0.0.1:7779\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {nonce}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        s.sendall(req.encode())
        resp = s.recv(4096).decode("utf-8", errors="ignore")
        accept = base64.b64encode(
            hashlib.sha1((nonce + WS_MAGIC).encode()).digest()).decode()
        report("WebSocket 握手", "101" in resp and accept in resp, resp.split("\r\n")[0])

        ws_send_text(s, json.dumps({"action": "ping"}))
        txt = ws_recv_text(s, timeout=5.0)
        ok = txt is not None and json.loads(txt).get("status") == "ok"
        report("WS ping 转发", ok, repr(txt)[:120])

        ws_send_text(s, json.dumps({"action": "execute",
                                    "code": "print('WS_HELLO')"}))
        txt = ws_recv_text(s, timeout=8.0)
        ok = txt is not None and "WS_HELLO" in json.loads(txt).get("output", "")
        report("WS execute 转发", ok, repr(txt)[:120])
        s.close()
    except Exception as e:
        report("WebSocket 链路", False, repr(e))
        try:
            s.close()
        except Exception:
            pass


if __name__ == "__main__":
    print("=" * 60)
    print("  Mind+ 全链路功能测试")
    print("=" * 60)
    test_vm_server()
    test_direct_server()
    test_websocket()

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print("\n" + "=" * 60)
    print(f"  结果: {passed}/{total} 通过")
    print("=" * 60)
    for name, ok, detail in results:
        if not ok:
            print(f"  FAIL: {name} -- {detail}")
    sys.exit(0 if passed == total else 1)
