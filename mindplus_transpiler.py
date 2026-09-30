"""
Mind+ C++ 代码转译器
将 Mind+ 上传模式生成的 Arduino 风格 C++ 代码自动转译为 MicroPython 代码
"""

import re

# Mind+ C++ 代码特征标记
_CPP_MARKERS = (
    '#include',
    'void setup',
    'void loop',
    'Serial.begin',
    'mPython.begin',
    'MPython.h',
)

# C++ 类型声明关键字
_CPP_TYPES = (
    r'(?:unsigned\s+)?(?:int|float|double|long|short|char|bool|byte|void|'
    r'String|uint8_t|uint16_t|uint32_t|int8_t|int16_t|int32_t|size_t)'
)


def is_mindplus_code(code):
    """检测代码是否为 Mind+ 生成的 C++ 代码"""
    if not code or not isinstance(code, str):
        return False
    return any(marker in code for marker in _CPP_MARKERS)


def _convert_expr(expr):
    """转换 C++ 表达式为 Python 表达式（保护字符串字面量）"""
    expr = expr.strip()
    # 先取出字符串字面量（"..."），处理期间用占位符保护，最后还原，
    # 避免 && / || / 注释符 等替换破坏字符串内容
    strings = []

    def _store(m):
        strings.append(m.group(0))
        return '\x00%d\x00' % (len(strings) - 1)

    expr = re.sub(r'"(?:[^"\\]|\\.)*"', _store, expr)
    # 布尔字面量
    expr = re.sub(r'\btrue\b', 'True', expr)
    expr = re.sub(r'\bfalse\b', 'False', expr)
    # 逻辑运算符（注意保留 !=）
    expr = expr.replace('&&', ' and ').replace('||', ' or ')
    expr = re.sub(r'!(?!=)', 'not ', expr)
    # 类型转换函数
    expr = re.sub(r'\bString\(', 'str(', expr)
    # x.toInt() -> int(x)（修复原实现留下悬空点的问题）
    expr = re.sub(r'([A-Za-z_]\w*)\.toInt\(\)', r'int(\1)', expr)
    # 数学函数
    expr = re.sub(r'\bsqrt\(', 'math.sqrt(', expr)
    expr = re.sub(r'\babs\(', 'abs(', expr)
    # 还原字符串字面量
    for i, s in enumerate(strings):
        expr = expr.replace('\x00%d\x00' % i, s)
    return expr


def _convert_api(expr):
    """统一转换 Mind+ 传感器/按键 API 调用（条件与语句共用）"""
    expr = re.sub(r'buttonA\.isPressed\(\)', 'button_a.is_pressed()', expr)
    expr = re.sub(r'buttonB\.isPressed\(\)', 'button_b.is_pressed()', expr)
    # 触摸按键（Mind+ 标识符为 touchPad_P 等，带下划线）
    for pad in ['P', 'Y', 'T', 'H', 'O', 'N']:
        expr = re.sub(r'touchPad_%s\.isPressed\(\)' % pad, 'touchpad_%s.is_pressed()' % pad.lower(), expr)
    expr = re.sub(r'accelerometer\.getX\(\)', 'accelerometer.get_x()', expr)
    expr = re.sub(r'accelerometer\.getY\(\)', 'accelerometer.get_y()', expr)
    expr = re.sub(r'accelerometer\.getZ\(\)', 'accelerometer.get_z()', expr)
    return expr


# display.setCursor 记录的行列状态（跨语句共享，print 时使用）
# 使用线程本地存储，避免多线程并发转译时状态互踩
import threading as _threading
_cursor_state_local = _threading.local()


def _get_cursor_state():
    if not hasattr(_cursor_state_local, 'state'):
        _cursor_state_local.state = {'x': 0, 'y': 0}
    return _cursor_state_local.state


def _strip_trailing_comment(line):
    """剥离行尾 // 注释，但保留字符串字面量内的 //"""
    in_str = False
    for i, c in enumerate(line):
        if c == '"':
            in_str = not in_str
        elif not in_str and c == '/' and i + 1 < len(line) and line[i + 1] == '/':
            return line[:i]
    return line


def _convert_statement(line):
    """转换单行 C++ 语句为 Python（不处理控制结构）"""
    line = line.strip()
    if not line:
        return ''

    # 先剥离行尾 // 注释（否则会被 Python 解释为整除，产生语法错误）
    line = _strip_trailing_comment(line).strip()
    # 再去掉行尾分号
    line = line.rstrip(';').strip()
    if not line:
        return ''

    # 跳过初始化调用（虚拟机已初始化）
    if re.match(r'(mPython|mpython)\.begin\(\)', line):
        return None

    # 行注释
    if line.startswith('//'):
        return '# ' + line[2:].strip()

    # 去掉类型声明: int x = 0 -> x = 0
    line = re.sub(rf'^{_CPP_TYPES}\s+', '', line)
    line = re.sub(rf'\bconst\s+{_CPP_TYPES}\s+', '', line)

    # ---- 显示屏 API ----
    m = re.match(r'display\.print(?:ln)?\((.*)\)$', line)
    if m:
        # 使用最近一次 setCursor 设置的位置
        cs = _get_cursor_state()
        return 'oled.DispChar(str(%s), %s, %s); oled.show()' % (
            _convert_expr(m.group(1)), cs['x'], cs['y'])
    m = re.match(r'display\.setCursor\((.*),(.*)\)$', line)
    if m:
        # 记录光标位置（模拟器 OLED 无 set_cursor，print 时按此坐标绘制）
        cs = _get_cursor_state()
        cs['x'] = _convert_expr(m.group(1))
        cs['y'] = _convert_expr(m.group(2))
        return None
    m = re.match(r'display\.setCursorLine\((.*)\)$', line)
    if m:
        return f'oled.setCursorLine({_convert_expr(m.group(1))})'
    m = re.match(r'display\.printLine\((.*)\)$', line)
    if m:
        return f'oled.printLine(str({_convert_expr(m.group(1))}))'
    if re.match(r'display\.update\(\)$', line):
        return 'oled.show()'
    m = re.match(r'display\.fillScreen\((.*)\)$', line)
    if m:
        return f'oled.fill({m.group(1)})'
    if re.match(r'display\.clearDisplay\(\)$', line):
        return 'oled.fill(0); oled.show()'

    # ---- RGB 灯 API ----
    m = re.match(r'rgb\.setPixelColor\((\w+)\s*,\s*0x([0-9a-fA-F]{6})\)$', line)
    if m:
        hex_color = m.group(2)
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f'rgb[{m.group(1)}] = ({r}, {g}, {b}); rgb.write()'
    m = re.match(r'rgb\.setPixelColor\((\w+)\s*,\s*(.*)\)$', line)
    if m:
        return f'rgb[{m.group(1)}] = {_convert_expr(m.group(2))}; rgb.write()'
    if re.match(r'rgb\.show\(\)$', line):
        return 'rgb.write()'
    if re.match(r'rgb\.clear\(\)$', line):
        return 'rgb.fill((0, 0, 0)); rgb.write()'

    # ---- 延时 ----
    m = re.match(r'delay\((.*)\)$', line)
    if m:
        return f'sleep_ms(int({_convert_expr(m.group(1))}))'
    m = re.match(r'delayMicroseconds\((.*)\)$', line)
    if m:
        return f'sleep_us(int({_convert_expr(m.group(1))}))'

    # ---- 串口打印 ----
    m = re.match(r'Serial\.print(?:ln)?\((.*)\)$', line)
    if m:
        return f'print({_convert_expr(m.group(1))})'
    if re.match(r'Serial\.begin\(.*\)$', line):
        return None

    # ---- 数字引脚（Mind+ digitalWrite/digitalRead）----
    # 支持具名引脚对象（如 pin13.write_digital），数字字面量引脚忽略
    # （模拟器引脚已映射，无需显式写引脚）
    m = re.match(r'digitalWrite\((\w+)\s*,\s*(HIGH|LOW)\)$', line)
    if m:
        pin_name = m.group(1)
        if pin_name.isdigit():
            return None  # 数字引脚在模拟器中已映射，忽略
        return f'{pin_name}.write_digital({1 if m.group(2) == "HIGH" else 0})'
    m = re.match(r'digitalRead\((\w+)\)$', line)
    if m:
        pin_name = m.group(1)
        if pin_name.isdigit():
            return '0'  # 数字引脚读取在模拟器中返回默认值
        return f'{pin_name}.read_digital()'
    if re.match(r'pinMode\(.*\)$', line):
        # 模拟器引脚模式已预设，忽略显式设置
        return None

    # ---- 音乐/蜂鸣器 ----
    m = re.match(r'buzzer\.tone\((.*),(.*)\)$', line)
    if m:
        return f'music.pitch(int({_convert_expr(m.group(1))}), int({_convert_expr(m.group(2))}))'
    if re.match(r'buzzer\.noTone\(\)$', line):
        return 'music.stop()'

    # ---- 通用表达式/赋值 ----
    return _convert_api(_convert_expr(line))


def _convert_condition(cond):
    """转换 C++ 条件表达式为 Python"""
    return _convert_api(_convert_expr(cond))


def transpile(code):
    """将 Mind+ C++ 代码转译为 MicroPython 代码"""
    _get_cursor_state()['x'] = 0
    _get_cursor_state()['y'] = 0
    lines = code.split('\n')
    py_lines = [
        '# 由 Mind+ C++ 代码自动转译为 MicroPython',
        'from mpython import *',
        'import time',
        'import math',
        '',
    ]

    indent = 0
    in_function = False  # 是否在 setup/loop 函数体内
    in_block_comment = False  # 是否处于 /* ... */ 块注释中

    for raw_line in lines:
        line = raw_line.strip()

        # 空行、预处理指令、mPython.begin 直接跳过
        if not line:
            continue
        if line.startswith('#include') or line.startswith('#define'):
            continue

        # 块注释：支持 /* ... */ 跨多行
        if in_block_comment:
            if '*/' in line:
                in_block_comment = False
            continue
        if '/*' in line:
            if '*/' not in line:
                in_block_comment = True
            continue

        # setup() 函数入口（兼容 void setup() { 多行 与 void setup(){ ... } 单行）
        m = re.match(r'void\s+setup\s*\([^)]*\)(.*)$', line)
        if m:
            py_lines.append('# ===== setup() 初始化代码 =====')
            in_function = True
            indent = 0
            rest = m.group(1).strip()
            if rest.startswith('{') and rest.endswith('}'):
                inner = rest[1:-1].strip()
                if inner:
                    for stmt in inner.split(';'):
                        stmt = stmt.strip()
                        if stmt:
                            converted = _convert_statement(stmt + ';')
                            if converted:
                                py_lines.append('    ' * indent + converted)
                continue
            continue

        # loop() 函数入口（兼容多行与单行体）
        m = re.match(r'void\s+loop\s*\([^)]*\)(.*)$', line)
        if m:
            py_lines.append('')
            py_lines.append('# ===== loop() 循环代码 =====')
            py_lines.append('while True:')
            in_function = True
            indent = 1
            rest = m.group(1).strip()
            if rest.startswith('{') and rest.endswith('}'):
                inner = rest[1:-1].strip()
                if inner:
                    for stmt in inner.split(';'):
                        stmt = stmt.strip()
                        if stmt:
                            converted = _convert_statement(stmt + ';')
                            if converted:
                                py_lines.append('    ' * indent + converted)
                continue
            continue

        # 处理大括号结构
        if line == '{':
            continue

        # else / else if
        m = re.match(r'}\s*else\s+if\s*\((.*)\)\s*\{?$', line)
        if m:
            indent = max(indent - 1, 0)
            py_lines.append('    ' * indent + f'elif {_convert_condition(m.group(1))}:')
            indent += 1
            continue

        # else if 独立成行（上一行 } 已单独处理过缩进，这里不再减）
        m = re.match(r'else\s+if\s*\((.*)\)\s*\{?$', line)
        if m:
            py_lines.append('    ' * indent + f'elif {_convert_condition(m.group(1))}:')
            indent += 1
            continue

        m = re.match(r'}\s*else\s*\{?$', line)
        if m:
            indent = max(indent - 1, 0)
            py_lines.append('    ' * indent + 'else:')
            indent += 1
            continue

        # else 独立成行（上一行 } 已单独处理过缩进，这里不再减）
        m = re.match(r'else\s*\{?$', line)
        if m:
            py_lines.append('    ' * indent + 'else:')
            indent += 1
            continue

        # 块结束
        if re.match(r'^\}+\s*;?$', line):
            indent = max(indent - 1, 0)
            if indent == 0:
                in_function = False
            continue

        # if 语句
        m = re.match(r'if\s*\((.*)\)\s*\{?$', line)
        if m:
            py_lines.append('    ' * indent + f'if {_convert_condition(m.group(1))}:')
            indent += 1
            continue

        # while 语句
        m = re.match(r'while\s*\((.*)\)\s*\{?$', line)
        if m:
            py_lines.append('    ' * indent + f'while {_convert_condition(m.group(1))}:')
            indent += 1
            continue

        # for (int i = 0; i < N; i++) 风格循环
        m = re.match(r'for\s*\(\s*(?:int\s+)?(\w+)\s*=\s*(.+?);\s*\1\s*<\s*(.+?);\s*\1(?:\+\+|\s*\+=\s*(\d+))\s*\)\s*\{?$', line)
        if m:
            var, start, end, step = m.group(1), m.group(2), m.group(3), m.group(4) or '1'
            py_lines.append('    ' * indent + f'for {var} in range(int({_convert_expr(start)}), int({_convert_expr(end)}), {step}):')
            indent += 1
            continue

        # 普通语句
        converted = _convert_statement(line)
        if converted:
            py_lines.append('    ' * indent + converted)

    return '\n'.join(py_lines) + '\n'
