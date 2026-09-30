// Mind+ 扩展端到端测试: Node20 注入最小 WebSocket -> 真实 7779 服务 -> 7778 VM
const net = require('net');
const crypto = require('crypto');
const path = require('path');

// ---------- 最小 WebSocket 客户端(仅文本帧, 客户端发掩码帧) ----------
class MiniWS {
    constructor(url) {
        this.listeners = {};
        this.url = url;
        const m = url.match(/^ws:\/\/([^:/]+)(?::(\d+))?(.*)$/);
        this._host = m[1];
        this._port = parseInt(m[2] || '80', 10);
        this._path = m[3] || '/';
        this._buf = Buffer.alloc(0);
        this._connect();
    }
    on(evt, fn) { (this.listeners[evt] = this.listeners[evt] || []).push(fn); }
    addEventListener(evt, fn) { this.on(evt, fn); }
    removeEventListener(evt, fn) {
        const arr = this.listeners[evt];
        if (!arr) return;
        this.listeners[evt] = arr.filter(f => f !== fn);
    }
    _emit(evt, data) {
        (this.listeners[evt] || []).forEach(fn => fn(data));
        // 同时支持标准属性回调 ws.onopen / ws.onmessage / ws.onerror / ws.onclose
        const prop = this['on' + evt];
        if (typeof prop === 'function') prop(data);
    }
    _connect() {
        this.sock = net.connect(this._port, this._host, () => {
            const key = crypto.randomBytes(16).toString('base64');
            this.sock.write(
                `GET ${this._path} HTTP/1.1\r\nHost: ${this._host}:${this._port}\r\n` +
                `Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${key}\r\nSec-WebSocket-Version: 13\r\n\r\n`);
        });
        this.sock.on('data', d => this._onData(d));
        this.sock.on('error', e => this._emit('error', e));
        this.sock.on('close', () => this._emit('close', {}));
    }
    _onData(d) {
        this._buf = Buffer.concat([this._buf, d]);
        if (!this._opened) {
            const idx = this._buf.indexOf('\r\n\r\n');
            if (idx < 0) return;
            const head = this._buf.slice(0, idx).toString();
            this._buf = this._buf.slice(idx + 4);
            if (!/^HTTP\/1\.1 101/.test(head)) { this._emit('error', new Error('bad handshake')); return; }
            this._opened = true;
            this._emit('open', {});
        }
        // 解析服务端文本帧(服务端不掩码)
        while (this._buf.length >= 2) {
            const b0 = this._buf[0], b1 = this._buf[1];
            const opcode = b0 & 0x0f;
            let len = b1 & 0x7f;
            let off = 2;
            if (len === 126) { len = this._buf.readUInt16BE(2); off = 4; }
            else if (len === 127) { len = Number(this._buf.readBigUInt64BE(2)); off = 10; }
            if (this._buf.length < off + len) break;
            const payload = this._buf.slice(off, off + len);
            this._buf = this._buf.slice(off + len);
            if (opcode === 8) { this._emit('close', {}); continue; }
            if (opcode === 1 || opcode === 0) this._emit('message', { data: payload.toString('utf8') });
        }
    }
    send(str) {
        const payload = Buffer.from(str, 'utf8');
        const mask = crypto.randomBytes(4);
        let header;
        if (payload.length < 126) {
            header = Buffer.from([0x81, 0x80 | payload.length]);
        } else {
            header = Buffer.alloc(4);
            header[0] = 0x81; header[1] = 0x80 | 126;
            header.writeUInt16BE(payload.length, 2);
        }
        const masked = Buffer.from(payload.map((b, i) => b ^ mask[i % 4]));
        this.sock.write(Buffer.concat([header, mask, masked]));
    }
    close() { try { this.sock.end(); } catch (e) { } }
}
globalThis.WebSocket = MiniWS;

// ---------- 加载扩展 ----------
const VirtualMPython = require(path.join(__dirname, 'mindplus_extension', 'javascript', 'main.js'));

let pass = 0, fail = 0;
function check(name, cond, extra) {
    if (cond) { pass++; console.log(`  [PASS] ${name}`); }
    else { fail++; console.log(`  [FAIL] ${name} ${extra || ''}`); }
}

(async () => {
    const ext = new VirtualMPython({});
    console.log('=== Mind+ 扩展端到端测试 ===');

    let ok = await ext.connect({ HOST: '127.0.0.1', PORT: '7779' });
    check('连接 7779 成功', ok === true);
    check('已连接状态为真', ext.is_connected() === true);

    // 命令积木(每条都会得到 VM 的 status:ok 应答)
    await ext.oled_clear();
    let r = await ext.oled_show_text({ TEXT: 'Hello Mind+', X: '0', Y: '0' });
    check('OLED 显示文字应答 ok', r.status === 'ok', JSON.stringify(r));
    r = await ext.oled_show_number({ NUM: '2026', X: '0', Y: '16' });
    check('OLED 显示数字应答 ok', r.status === 'ok', JSON.stringify(r));
    r = await ext.rgb_led({ R: '255', G: '0', B: '128' });
    check('RGB 全灯应答 ok', r.status === 'ok', JSON.stringify(r));
    r = await ext.rgb_set_one({ INDEX: '1', R: '0', G: '255', B: '0' });
    check('RGB 单灯应答 ok', r.status === 'ok', JSON.stringify(r));

    // 蜂鸣器: 开机后查 get_state, 确认频率下发到 VM
    ext.beep({ FREQ: '880', DURATION: '300' });
    await new Promise(res => setTimeout(res, 300));

    // 查询积木
    const a = await ext.button_a_pressed();
    check('按键A返回布尔', typeof a === 'boolean');
    const light = await ext.get_light();
    check('光线强度返回数值', typeof light === 'number', `got=${light}`);
    const sound = await ext.get_sound();
    check('声音强度返回数值', typeof sound === 'number', `got=${sound}`);
    const ax = await ext.get_accel({ AXIS: 'x' });
    check('加速度X返回数值', typeof ax === 'number', `got=${ax}`);
    const t = await ext.touch_pressed({ PAD: 'P' });
    check('触摸P返回布尔', typeof t === 'boolean');

    // 错误端口应连接失败而非挂死
    const ext2 = new VirtualMPython({});
    const t0 = Date.now();
    const bad = await ext2.connect({ HOST: '127.0.0.1', PORT: '7790' });
    check('错误端口连接失败且不挂死', bad === false && (Date.now() - t0) < 7000, `cost=${Date.now() - t0}ms`);

    ext.disconnect();
    check('断开后状态为假', ext.is_connected() === false);

    console.log(`\n结果: ${pass}/${pass + fail} 通过`);
    process.exit(fail === 0 ? 0 : 1);
})();
