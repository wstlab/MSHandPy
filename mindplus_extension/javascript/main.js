/**
 * 虚拟掌控板 - Mind+ 实时模式用户库
 *
 * 通信链路: Mind+ 扩展 -> WebSocket 127.0.0.1:7779 -> VM Server(7778) -> 悬浮虚拟板
 * 无需任何虚拟串口驱动 / com0com。
 *
 * 说明:
 *  - 命令积木(oled/rgb/蜂鸣器)即发即执行;
 *  - 查询积木(按键/触摸/光线/声音)走请求-应答, 返回板子实时状态;
 *  - 单连接串行队列, 避免实时模式下多积木并发时应答错配。
 */

// 兼容 Mind+ 沙箱(Scratch 常量)与普通 Scratch 环境(字符串)
const _BT = (typeof Scratch !== 'undefined' && Scratch.BlockType) ? Scratch.BlockType : {
    COMMAND: 'command',
    REPORTER: 'reporter',
    BOOLEAN: 'Boolean'
};

class VirtualMPython {
    constructor(runtime) {
        this.runtime = runtime;
        this.socket = null;
        this.host = '127.0.0.1';
        this.port = 7779;
        this.connected = false;

        this._queue = [];      // 待发送请求
        this._busy = false;   // 队列是否在等待应答
        this._beepTimer = null;
    }

    // ---------- 连接管理 ----------
    _openWebSocket(url) {
        return new Promise((resolve) => {
            let settled = false;
            const done = (ok) => {
                if (settled) return;
                settled = true;
                resolve(ok);
            };

            let ws;
            try {
                ws = new WebSocket(url);
            } catch (e) {
                console.error('[虚拟掌控板] 创建 WebSocket 失败:', e);
                done(false);
                return;
            }
            this.socket = ws;

            ws.onopen = () => {
                this.connected = true;
                console.info('[虚拟掌控板] 已连接 ' + url);
                done(true);
            };
            ws.onerror = (e) => {
                console.error('[虚拟掌控板] 连接错误:', e);
                this.connected = false;
                done(false);
            };
            ws.onclose = () => {
                this.connected = false;
                this.socket = null;
                this._queue = [];
                this._busy = false;
                console.info('[虚拟掌控板] 连接已断开');
            };

            // 连接握手 5 秒超时
            setTimeout(() => {
                if (!this.connected) {
                    try { ws.close(); } catch (e) { }
                    done(false);
                }
            }, 5000);
        });
    }

    async connectToVM(host, port) {
        // 已连着且参数没变, 直接成功
        if (this.connected && this.socket) return true;

        this.host = host || '127.0.0.1';
        const p = parseInt(port, 10);
        this.port = (!isNaN(p) && p > 0) ? p : 7779;

        // 清理旧连接
        if (this.socket) {
            try { this.socket.close(); } catch (e) { }
            this.socket = null;
        }
        this.connected = false;
        this._queue = [];
        this._busy = false;

        return await this._openWebSocket(`ws://${this.host}:${this.port}`);
    }

    disconnect() {
        if (this._beepTimer) {
            clearTimeout(this._beepTimer);
            this._beepTimer = null;
        }
        if (this.socket) {
            try { this.socket.close(); } catch (e) { }
            this.socket = null;
        }
        this.connected = false;
        this._queue = [];
        this._busy = false;
    }

    // ---------- 请求-应答串行队列 ----------
    _send(command) {
        return new Promise((resolve) => {
            if (!this.connected || !this.socket) {
                resolve({});
                return;
            }
            this._queue.push({ command, resolve });
            this._pump();
        });
    }

    _pump() {
        if (this._busy) return;
        const job = this._queue.shift();
        if (!job) return;
        this._busy = true;

        let finished = false;
        const finish = (resp) => {
            if (finished) return;
            finished = true;
            clearTimeout(timer);
            try { this.socket.removeEventListener('message', onMessage); } catch (e) { }
            this._busy = false;
            job.resolve(resp || {});
            // 继续处理队列中的下一条
            this._pump();
        };

        const onMessage = (event) => {
            let resp = null;
            try {
                resp = JSON.parse(event.data);
            } catch (e) {
                return; // 非 JSON 帧忽略, 继续等待真正的应答
            }
            finish(resp);
        };

        // 应答超时保护(4 秒), 防止 VM Server 异常时队列永久卡死
        const timer = setTimeout(() => finish({}), 4000);

        try {
            this.socket.addEventListener('message', onMessage);
            this.socket.send(JSON.stringify(job.command));
        } catch (e) {
            console.error('[虚拟掌控板] 发送失败:', e);
            finish({});
        }
    }

    // ---------- 硬件积木封装 ----------
    oledClear() {
        return this._send({ action: 'oled_fill', color: 0 });
    }

    oledShowText(text, x, y, size) {
        // VM Server 按行(y/16)渲染, x 随协议携带
        return this._send({
            action: 'oled_text',
            text: String(text),
            x: parseInt(x, 10) || 0,
            y: parseInt(y, 10) || 0
        });
    }

    oledShowNumber(num, x, y) {
        return this._send({
            action: 'oled_text',
            text: String(num),
            x: parseInt(x, 10) || 0,
            y: parseInt(y, 10) || 0
        });
    }

    oledShow() {
        return this._send({ action: 'oled_show' });
    }

    oledFill(color) {
        return this._send({ action: 'oled_fill', color: parseInt(color, 10) || 0 });
    }

    // 三颗 RGB 灯统一设为同一颜色
    rgbLed(r, g, b) {
        const c = [
            Math.max(0, Math.min(255, parseInt(r, 10) || 0)),
            Math.max(0, Math.min(255, parseInt(g, 10) || 0)),
            Math.max(0, Math.min(255, parseInt(b, 10) || 0))
        ];
        return this._send({ action: 'rgb_write', colors: [c, c, c] });
    }

    // 设置单颗灯(0/1/2)
    rgbSetOne(index, r, g, b) {
        const c = [
            Math.max(0, Math.min(255, parseInt(r, 10) || 0)),
            Math.max(0, Math.min(255, parseInt(g, 10) || 0)),
            Math.max(0, Math.min(255, parseInt(b, 10) || 0))
        ];
        let idx = parseInt(index, 10);
        if (isNaN(idx)) idx = 0;
        idx = Math.max(0, Math.min(2, idx));
        return this._send({ action: 'rgb_set', index: idx, color: c });
    }

    _beep(freq, duration) {
        const f = Math.max(20, Math.min(20000, parseInt(freq, 10) || 523));
        const dur = Math.max(0, parseInt(duration, 10) || 0);
        this._send({ action: 'buzzer_on', freq: f });
        if (this._beepTimer) clearTimeout(this._beepTimer);
        // duration 毫秒后自动停音
        this._beepTimer = setTimeout(() => {
            this._send({ action: 'buzzer_off' });
            this._beepTimer = null;
        }, dur);
    }

    async buttonIsPressed(button) {
        const resp = await this._send({ action: 'button_read', button: button });
        return resp.pressed === true;
    }

    async touchIsPressed(pad) {
        const resp = await this._send({ action: 'touch_read', pad: String(pad) });
        return resp.pressed === true;
    }

    async getSensor(name) {
        const resp = await this._send({ action: 'sensor_read', sensor: name });
        const v = resp.value;
        if (v === undefined || v === null) return 0;
        // 加速度计/陀螺仪可能返回 [x,y,z]
        if (Array.isArray(v)) return JSON.stringify(v);
        return v;
    }

    getInfo() {
        return {
            id: 'virtual_mpython',
            name: '虚拟掌控板',
            color: '#00a8ff',
            blockIconURI: null,
            blocks: [
                {
                    opcode: 'connect',
                    blockType: _BT.COMMAND,
                    text: '连接虚拟掌控板 [HOST]:[PORT]',
                    arguments: {
                        HOST: { type: 'string', defaultValue: '127.0.0.1' },
                        PORT: { type: 'string', defaultValue: '7779' }
                    }
                },
                {
                    opcode: 'disconnect',
                    blockType: _BT.COMMAND,
                    text: '断开虚拟掌控板连接'
                },
                {
                    opcode: 'is_connected',
                    blockType: _BT.BOOLEAN,
                    text: '虚拟掌控板已连接?'
                },
                '---',
                {
                    opcode: 'oled_clear',
                    blockType: _BT.COMMAND,
                    text: 'OLED 清屏'
                },
                {
                    opcode: 'oled_show_text',
                    blockType: _BT.COMMAND,
                    text: 'OLED 显示文字 [TEXT] 位置 ([X],[Y])',
                    arguments: {
                        TEXT: { type: 'string', defaultValue: 'Hello' },
                        X: { type: 'string', defaultValue: '0' },
                        Y: { type: 'string', defaultValue: '0' }
                    }
                },
                {
                    opcode: 'oled_show_number',
                    blockType: _BT.COMMAND,
                    text: 'OLED 显示数字 [NUM] 位置 ([X],[Y])',
                    arguments: {
                        NUM: { type: 'string', defaultValue: '0' },
                        X: { type: 'string', defaultValue: '0' },
                        Y: { type: 'string', defaultValue: '16' }
                    }
                },
                {
                    opcode: 'oled_fill',
                    blockType: _BT.COMMAND,
                    text: 'OLED 整屏填充 [COLOR] (0灭/1亮)',
                    arguments: {
                        COLOR: { type: 'string', defaultValue: '0' }
                    }
                },
                '---',
                {
                    opcode: 'rgb_led',
                    blockType: _BT.COMMAND,
                    text: 'RGB 灯全部设为 ([R],[G],[B])',
                    arguments: {
                        R: { type: 'string', defaultValue: '255' },
                        G: { type: 'string', defaultValue: '0' },
                        B: { type: 'string', defaultValue: '0' }
                    }
                },
                {
                    opcode: 'rgb_set_one',
                    blockType: _BT.COMMAND,
                    text: '第 [INDEX] 颗 RGB 灯设为 ([R],[G],[B])',
                    arguments: {
                        INDEX: { type: 'string', defaultValue: '0' },
                        R: { type: 'string', defaultValue: '0' },
                        G: { type: 'string', defaultValue: '255' },
                        B: { type: 'string', defaultValue: '0' }
                    }
                },
                {
                    opcode: 'beep',
                    blockType: _BT.COMMAND,
                    text: '蜂鸣器 [FREQ]Hz 响 [DURATION] 毫秒',
                    arguments: {
                        FREQ: { type: 'string', defaultValue: '523' },
                        DURATION: { type: 'string', defaultValue: '500' }
                    }
                },
                '---',
                {
                    opcode: 'button_a_pressed',
                    blockType: _BT.BOOLEAN,
                    text: '按键 A 被按下?'
                },
                {
                    opcode: 'button_b_pressed',
                    blockType: _BT.BOOLEAN,
                    text: '按键 B 被按下?'
                },
                {
                    opcode: 'touch_pressed',
                    blockType: _BT.BOOLEAN,
                    text: '触摸键 [PAD] 被触摸?',
                    arguments: {
                        PAD: { type: 'string', defaultValue: 'P', menu: 'touchPad' }
                    }
                },
                {
                    opcode: 'get_light',
                    blockType: _BT.REPORTER,
                    text: '光线强度'
                },
                {
                    opcode: 'get_sound',
                    blockType: _BT.REPORTER,
                    text: '声音强度'
                },
                {
                    opcode: 'get_accel',
                    blockType: _BT.REPORTER,
                    text: '加速度 [AXIS]',
                    arguments: {
                        AXIS: { type: 'string', defaultValue: 'x', menu: 'axis' }
                    }
                }
            ],
            menus: {
                touchPad: {
                    items: ['P', 'Y', 'T', 'H', 'O', 'N']
                },
                axis: {
                    items: ['x', 'y', 'z']
                }
            }
        };
    }

    // ---------- Mind+ 积木入口(参数名与 blocks 中大写字段对应) ----------
    connect(args) {
        return this.connectToVM(args.HOST, args.PORT);
    }

    disconnect(args) {
        // 积木入口: 直接执行断开逻辑(不可与内部方法同名, 否则无限递归)
        if (this._beepTimer) {
            clearTimeout(this._beepTimer);
            this._beepTimer = null;
        }
        if (this.socket) {
            try { this.socket.close(); } catch (e) { }
            this.socket = null;
        }
        this.connected = false;
        this._queue = [];
        this._busy = false;
    }

    is_connected() {
        return this.connected === true;
    }

    oled_clear() {
        return this.oledClear();
    }

    oled_show_text(args) {
        return this.oledShowText(args.TEXT, args.X, args.Y, 1);
    }

    oled_show_number(args) {
        return this.oledShowNumber(args.NUM, args.X, args.Y);
    }

    oled_fill(args) {
        return this.oledFill(args.COLOR);
    }

    rgb_led(args) {
        return this.rgbLed(args.R, args.G, args.B);
    }

    rgb_set_one(args) {
        return this.rgbSetOne(args.INDEX, args.R, args.G, args.B);
    }

    beep(args) {
        this._beep(args.FREQ, args.DURATION);
    }

    button_a_pressed() {
        return this.buttonIsPressed('A');
    }

    button_b_pressed() {
        return this.buttonIsPressed('B');
    }

    touch_pressed(args) {
        return this.touchIsPressed(args.PAD);
    }

    get_light() {
        return this.getSensor('light');
    }

    get_sound() {
        return this.getSensor('sound');
    }

    async get_accel(args) {
        const axis = String(args.AXIS || 'x').toLowerCase();
        const idx = { x: 0, y: 1, z: 2 }[axis] ?? 0;
        const resp = await this._send({ action: 'sensor_read', sensor: 'accelerometer' });
        const v = resp.value;
        if (Array.isArray(v)) return v[idx] ?? 0;
        return 0;
    }
}

module.exports = VirtualMPython;
