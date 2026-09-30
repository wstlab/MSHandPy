# Sim-Handpy 桌面版（Tkinter）

虚拟掌控板桌面版独立发行目录：基于 Python + Tkinter 的 mPython 掌控板完整模拟器，配合 Thonny / IDLE 使用，让青少年无需实体硬件即可学习掌控板编程。

## 快速开始（Windows）

**双击 `一键启动.bat`**，按提示选择两个菜单即可。启动流程：检测系统 Python（缺失则给出下载链接并退出）→ 按菜单 1 处理 venv/依赖 → 按菜单 2 启动各服务 → 播放两声「哔-哔」做声音自检 → 退出时若用 venv 则自动清理。

### 菜单 1 — 虚拟环境

| 选项 | 说明 |
|------|------|
| **[Y] Yes（推荐）** | 创建独立 `.venv`，自动装依赖（清华镜像优先，失败回退官方源），**退出时自动删除**，整个目录拷到任意 Windows 电脑、U盘均可直接运行 |
| **[N] No** | 直接用系统 Python，需已预装 `numpy / psutil / pyserial`（`pip install -r requirements.txt`）。启动更快但需自行维护依赖 |

### 菜单 2 — 启动模式

| 选项 | 模式 | 启动内容 |
|------|------|---------|
| **[1] Thonny**（默认） | `thonny` | VM Server(7778) + Virtual USB(7777) + 悬浮显示窗 + Thonny IDE。代码学习模式：在 Thonny 里写 Python，悬浮板实时反馈 |
| **[2] Mind+** | `mindplus` | VM Server + 悬浮显示窗 + Mind+ 桥接（`mindplus_usb.py`）。图形积木模式，经虚拟串口桥接 Mind+。**首次运行需管理员权限**装 com0com 并建 COM19↔COM20 端口对。此模式跳过 Virtual USB，由 `MindPlusDirectServer` 接管 7777 端口避免冲突 |
| **[3] Both** | `both` | Thonny + Mind+ 桥接同时启动，方便对比两种编程方式 |

> Mind+ 模式使用方法：① 实时模式——Mind+ 扩展用户库加载 `mindplus_extension/config.json`，积木连 127.0.0.1:7779；② 串口模式——Mind+「上传到设备」选虚拟串口；③ TCP 直连——127.0.0.1:7777。

> 环境要求：Windows 10/11 + Python 3.10+（加入 PATH）。Mind+ 模式另需 com0com（脚本会尝试自动下载安装，或手动安装：<https://sourceforge.net/projects/com0com/>）。目标电脑无需预装任何依赖（选 Y 时）。
>
> 依赖分两层：核心依赖（`requirements.txt`：numpy / opencv-python / psutil / wmi / pyserial，全部有 Windows 预编译包，必装必过）+ 可选依赖（`requirements-optional.txt`：PyAudio 麦克风检测、Pillow 录屏，安装失败仅提示、不影响运行）。

## 使用流程（配合 Thonny）

1. 双击 `一键启动.bat`，等待悬浮掌控板窗口出现（始终置顶）
2. 打开 Thonny →「文件」→「打开」→ 选择 `demo.py`（mPython 模式）或 `demo_pinpong.py`（PinPong 模式）
3. 点击 Thonny「运行」，观察虚拟板实时反馈
4. 编写自己的代码时，在开头加入（路径自动定位，无需手动填写）：

```python
import sys, os
base = os.path.dirname(os.path.abspath(__file__))  # 自动获取脚本所在目录
sys.path.insert(0, base)
sys.path.insert(0, os.path.join(base, 'clients'))
from mpython_client import connect
mp = connect()
```

5. 结束运行：关闭启动窗口或按 Ctrl+C，所有服务一并退出

## 目录结构

```
Sim-Handpy-桌面版/
├── 一键启动.bat            # 一键创建虚拟环境并启动（推荐入口）
├── requirements.txt        # 运行依赖（精简版，已剔除仅打包用的 PyInstaller）
├── start_vm.py             # 一键启动器（VM Server + Virtual USB + 悬浮窗 + Thonny）
├── vm_server.py            # 虚拟机服务端（端口 7778）
├── display_gui.py          # 悬浮虚拟掌控板窗口
├── integrated_vm.py        # 集成 IDE 版（编辑器 + 仿真一体）
├── mpython_vm.py           # mPython 虚拟机核心
├── mindplus_usb.py         # Mind+ USB 桥接服务
├── mindplus_transpiler.py  # Mind+ 图形化代码转译器
├── clients/                # 客户端库（mpython_client / pinpong_client）
├── simulator/              # 硬件模拟模块（GUI、多语言、MicroPython 模块）
├── mindplus_extension/     # Mind+ 扩展
├── demo.py / demo_pinpong.py       # 两种模式的演示代码
├── demo_selfrun.py         # 自包含一键演示（无需 Thonny）
├── thonny_demo.py          # Thonny 联动演示
├── test_verify.py          # Thonny 联动验证脚本（OLED/RGB/传感器/按键）
├── verify_thonny.py / test_thonny_run.py   # 链路验证工具
├── record_demo.py / record_thonny.py       # 无声录屏演示工具
└── LICENSE                 # MIT 许可证
```

## 注意事项

- 虚拟掌控板窗口必须保持打开；不要同时运行多个虚拟机服务实例（端口 7778）
- 端口冲突时可通过环境变量调整：`Sim-Handpy_VM_SERVER_PORT` / `Sim-Handpy_VM_USB_PORT`
- 界面支持 8 种语言，在窗口左上角切换
- 如需打包 exe：`pip install pyinstaller` 后自行打包（运行时不依赖 PyInstaller）

## 支持的硬件组件

| 组件 | mPython API | PinPong API |
|------|-------------|-------------|
| OLED | `mp.oled` | `get_oled()` |
| RGB LED | `mp.rgb` | `get_rgb()` |
| 按键 A/B | `mp.button_a` / `mp.button_b` | `Pin(Pin.P0, Pin.IN)` |
| 触摸按键 | `mp.touchPad_p` 等 P/Y/T/H/O/N | `Pin(Pin.P1, Pin.IN)` |
| 光线传感器 | `mp.light.read()` | `Sensor(Pin.P2)` |
| 声音传感器 | `mp.sound.read()` | `Sensor(Pin.P3)` |
| 加速度计 | `mp.accelerometer.get_x()` | `get_accel()` |
| 陀螺仪 | `mp.gyroscope` | `get_gyro()` |
| 地磁传感器 | `mp.magnetic` | `get_mag()` |
| 蜂鸣器 | `mp.buzzer.on(freq)` / `mp.buzzer.off()` / `mp.buzzer.play([(freq,ms),...])` | — |

> 蜂鸣器说明：`on(freq)` 让悬浮板持续发声（窗口 Buzzer 栏同步显示音调），`off()` 停止；`play()` 按节拍播放旋律列表，适合课堂演示音调与节拍编程。

---

主项目（含 Web 版编程学习课堂、完整文档）：`../Sim-Handpy-main/`
项目地址：https://github.com/lmxylyc/Sim-Handpy-VirtualBoard · 作者：林奕呈
