"""
Sim-Handpy - 高级主题系统
包含深色/浅色主题、语法高亮配色、玻璃态效果、现代化控件样式
"""

import tkinter as tk
from tkinter import ttk
import re
import sys


def _font_family(kind):
    """按平台选择可用字体族，避免 Windows 专属字体在 macOS/Linux 上回退错乱"""
    if sys.platform == 'darwin':
        families = {
            'main': '.AppleSystemUIFont',
            'mono': 'Menlo',
            'code': 'Menlo',
            'code_line': 'Monaco',
        }
    elif sys.platform.startswith('linux'):
        families = {
            'main': 'Noto Sans CJK SC',
            'mono': 'DejaVu Sans Mono',
            'code': 'DejaVu Sans Mono',
            'code_line': 'DejaVu Sans Mono',
        }
    else:
        families = {
            'main': 'Segoe UI',
            'mono': 'Consolas',
            'code': 'Cascadia Code',
            'code_line': 'Consolas',
        }
    return families.get(kind, 'main')


class DarkTheme:
    BG = "#11111b"
    BG_PANEL = "#181825"
    BG_CARD = "#1e1e2e"
    BG_INPUT = "#11111b"
    BG_HOVER = "#313244"
    BG_ELEVATED = "#252537"

    FG = "#cdd6f4"
    FG_MUTED = "#a6adc8"
    FG_DIM = "#6c7086"
    FG_ACCENT = "#89b4fa"

    ACCENT = "#89b4fa"
    ACCENT_HOVER = "#b4befe"
    ACCENT_DIM = "#585b70"

    SUCCESS = "#a6e3a1"
    WARNING = "#f9e2af"
    ERROR = "#f38ba8"
    INFO = "#89dceb"

    OLED_BG = "#0a0a12"
    OLED_FG = "#7ef9c4"
    OLED_FRAME = "#11111b"
    OLED_GLOW = "#7ef9c4"
    OLED_SCANLINE = "#1a1a28"

    RGB_OFF = "#313244"
    RGB_OUTLINE = "#45475a"

    BORDER = "#45475a"
    BORDER_LIGHT = "#585b70"
    BORDER_SUBTLE = "#313244"

    BUTTON_BG = "#313244"
    BUTTON_HOVER = "#45475a"
    BUTTON_FG = "#cdd6f4"

    EDITOR_BG = "#0f0f17"
    EDITOR_FG = "#cdd6f4"
    EDITOR_LINE = "#313244"
    EDITOR_LINE_NUM = "#45475a"
    EDITOR_CURSOR = "#89b4fa"
    EDITOR_SELECT = "#313254"
    EDITOR_CURRENT_LINE = "#1a1a28"

    OUTPUT_BG = "#0a0a12"
    OUTPUT_FG = "#bac2de"

    TREE_BG = "#1e1e2e"
    TREE_HEAD = "#313244"

    GLASS_BG = "#1a1a28"
    GLASS_BORDER = "#3a3a52"
    GLASS_SHADOW = "#00000066"

    SYN_KEYWORD = "#cba6f7"
    SYN_STRING = "#a6e3a1"
    SYN_NUMBER = "#fab387"
    SYN_COMMENT = "#6c7086"
    SYN_FUNCTION = "#89b4fa"
    SYN_CLASS = "#f9e2af"
    SYN_BUILTIN = "#94e2d5"
    SYN_OPERATOR = "#89dceb"
    SYN_DECORATOR = "#f38ba8"
    SYN_PROPERTY = "#f5c2e7"

    FONT_MAIN = (_font_family('main'), 10)
    FONT_MONO = (_font_family('mono'), 10)
    FONT_TITLE = (_font_family('main'), 13, "bold")
    FONT_SMALL = (_font_family('main'), 8)
    FONT_TINY = (_font_family('main'), 7)
    FONT_BTN = (_font_family('main'), 9)
    FONT_CODE = (_font_family('code'), 10)
    FONT_CODE_LINE = (_font_family('code_line'), 9)


class LightTheme:
    BG = "#e6e9ef"
    BG_PANEL = "#dce0e8"
    BG_CARD = "#ffffff"
    BG_INPUT = "#ffffff"
    BG_HOVER = "#ccd0da"
    BG_ELEVATED = "#ffffff"

    FG = "#4c4f69"
    FG_MUTED = "#6c6f85"
    FG_DIM = "#9ca0b0"
    FG_ACCENT = "#1e66f5"

    ACCENT = "#1e66f5"
    ACCENT_HOVER = "#2a6cf5"
    ACCENT_DIM = "#bcc0cc"

    SUCCESS = "#40a02b"
    WARNING = "#df8e1d"
    ERROR = "#d20f39"
    INFO = "#179299"

    OLED_BG = "#11111b"
    OLED_FG = "#90d17d"
    OLED_FRAME = "#181825"
    OLED_GLOW = "#90d17d"
    OLED_SCANLINE = "#1a1a28"

    RGB_OFF = "#ccd0da"
    RGB_OUTLINE = "#bcc0cc"

    BORDER = "#bcc0cc"
    BORDER_LIGHT = "#e6e9ef"
    BORDER_SUBTLE = "#ccd0da"

    BUTTON_BG = "#ccd0da"
    BUTTON_HOVER = "#bcc0cc"
    BUTTON_FG = "#4c4f69"

    EDITOR_BG = "#ffffff"
    EDITOR_FG = "#4c4f69"
    EDITOR_LINE = "#e6e9ef"
    EDITOR_LINE_NUM = "#9ca0b0"
    EDITOR_CURSOR = "#1e66f5"
    EDITOR_SELECT = "#dce0e8"
    EDITOR_CURRENT_LINE = "#f7f8fa"

    OUTPUT_BG = "#ffffff"
    OUTPUT_FG = "#4c4f69"

    TREE_BG = "#ffffff"
    TREE_HEAD = "#e6e9ef"

    GLASS_BG = "#ffffff"
    GLASS_BORDER = "#bcc0cc"
    GLASS_SHADOW = "#00000015"

    SYN_KEYWORD = "#8e3c1d"
    SYN_STRING = "#40a02b"
    SYN_NUMBER = "#d20f39"
    SYN_COMMENT = "#9ca0b0"
    SYN_FUNCTION = "#1e66f5"
    SYN_CLASS = "#df8e1d"
    SYN_BUILTIN = "#179299"
    SYN_OPERATOR = "#1e66f5"
    SYN_DECORATOR = "#d20f39"
    SYN_PROPERTY = "#ea76cb"

    FONT_MAIN = (_font_family('main'), 10)
    FONT_MONO = (_font_family('mono'), 10)
    FONT_TITLE = (_font_family('main'), 13, "bold")
    FONT_SMALL = (_font_family('main'), 8)
    FONT_TINY = (_font_family('main'), 7)
    FONT_BTN = (_font_family('main'), 9)
    FONT_CODE = (_font_family('code'), 10)
    FONT_CODE_LINE = (_font_family('code_line'), 9)


PYTHON_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "break", "class",
    "continue", "def", "del", "elif", "else", "except", "finally", "for",
    "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "async", "await"
}

C_KEYWORDS = {
    "void", "int", "float", "char", "double", "long", "short", "unsigned",
    "signed", "if", "else", "for", "while", "do", "switch", "case", "break",
    "continue", "return", "goto", "struct", "union", "enum", "typedef",
    "const", "static", "extern", "register", "volatile", "sizeof", "#include",
    "#define", "#ifdef", "#ifndef", "#endif", "#else", "#elif"
}

PYTHON_BUILTINS = {
    "abs", "all", "any", "bin", "bool", "breakpoint", "bytearray", "bytes",
    "callable", "chr", "classmethod", "compile", "complex", "delattr",
    "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter", "float",
    "format", "frozenset", "getattr", "globals", "hasattr", "hash", "help",
    "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len",
    "list", "locals", "map", "max", "memoryview", "min", "next", "object",
    "oct", "open", "ord", "pow", "print", "property", "range", "repr",
    "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod",
    "str", "sum", "super", "tuple", "type", "vars", "zip", "__import__",
    "self", "cls"
}


class SyntaxHighlighter:
    def __init__(self, text_widget, theme):
        self.text = text_widget
        self.theme = theme
        self._tags_configured = False
        self._last_change = None
        self._configure_tags()

        self.text.bind('<KeyRelease>', self._on_key_release)
        self.text.bind('<ButtonRelease>', self._on_key_release)
        self.text.bind('<FocusIn>', lambda e: self.highlight_line())
        self.text.bind('<KeyPress>', self._on_key_press)
        self._highlight_job = None

    def _configure_tags(self):
        t = self.theme
        tag_configs = {
            'keyword': {'foreground': t.SYN_KEYWORD, 'font': (t.FONT_CODE[0], t.FONT_CODE[1], 'bold')},
            'string': {'foreground': t.SYN_STRING},
            'number': {'foreground': t.SYN_NUMBER},
            'comment': {'foreground': t.SYN_COMMENT},
            'function': {'foreground': t.SYN_FUNCTION},
            'class': {'foreground': t.SYN_CLASS, 'font': (t.FONT_CODE[0], t.FONT_CODE[1], 'bold')},
            'builtin': {'foreground': t.SYN_BUILTIN},
            'operator': {'foreground': t.SYN_OPERATOR},
            'decorator': {'foreground': t.SYN_DECORATOR},
            'property': {'foreground': t.SYN_PROPERTY},
            'tag': {'foreground': t.SYN_KEYWORD},
        }
        for tag, config in tag_configs.items():
            self.text.tag_configure(tag, **config)
        self._tags_configured = True

    def _on_key_press(self, event):
        if self._highlight_job:
            self.text.after_cancel(self._highlight_job)
        self._highlight_job = self.text.after(1, self.highlight_line)

    def _on_key_release(self, event):
        if self._highlight_job:
            self.text.after_cancel(self._highlight_job)
        self._highlight_job = self.text.after(5, self.highlight_line)

    def highlight_line(self, event=None):
        try:
            self._do_highlight()
        except Exception:
            pass

    def _do_highlight(self):
        text_content = self.text.get('1.0', tk.END)
        self.text.tag_remove('keyword', '1.0', tk.END)
        self.text.tag_remove('string', '1.0', tk.END)
        self.text.tag_remove('number', '1.0', tk.END)
        self.text.tag_remove('comment', '1.0', tk.END)
        self.text.tag_remove('function', '1.0', tk.END)
        self.text.tag_remove('class', '1.0', tk.END)
        self.text.tag_remove('builtin', '1.0', tk.END)
        self.text.tag_remove('operator', '1.0', tk.END)
        self.text.tag_remove('decorator', '1.0', tk.END)
        self.text.tag_remove('property', '1.0', tk.END)
        self.text.tag_remove('tag', '1.0', tk.END)

        is_cpp = self._is_cpp_code(text_content)

        if is_cpp:
            self._highlight_cpp(text_content)
        else:
            self._highlight_python(text_content)

        self._update_current_line()

    def _is_cpp_code(self, text):
        cpp_indicators = ['#include', 'void setup', 'void loop', 'Serial.begin',
                          'pinMode', 'digitalWrite', 'analogWrite', 'digitalRead']
        count = sum(1 for ind in cpp_indicators if ind in text)
        return count >= 2

    def _highlight_python(self, text):
        lines = text.split('\n')
        for line_num, line in enumerate(lines, 1):
            self._highlight_python_line(line, line_num)

    def _highlight_python_line(self, line, line_num):
        stripped = line.strip()
        col_offset = len(line) - len(line.lstrip())

        comment_match = re.search(r'#.*$', line)
        if comment_match:
            start_col = comment_match.start()
            end_col = comment_match.end()
            self._apply_tag('comment', line_num, start_col + 1, line_num, end_col + 1)
            line = line[:start_col]

        for m in re.finditer(r'"""|\'\'\'', line):
            self._apply_tag('string', line_num, m.start() + 1, line_num, m.end() + 1)

        for m in re.finditer(r'"[^"]*"|\'[^\']*\'', line):
            self._apply_tag('string', line_num, m.start() + 1, line_num, m.end() + 1)

        for m in re.finditer(r'\b(\d+\.?\d*[eE]?[+-]?\d*|0x[0-9a-fA-F]+|0b[01]+)\b', line):
            self._apply_tag('number', line_num, m.start() + 1, line_num, m.end() + 1)

        for m in re.finditer(r'@\w+', line):
            self._apply_tag('decorator', line_num, m.start() + 1, line_num, m.end() + 1)

        for m in re.finditer(r'\bdef\s+(\w+)', line):
            self._apply_tag('function', line_num, m.start(2) + 1, line_num, m.end(2) + 1)

        for m in re.finditer(r'\bclass\s+(\w+)', line):
            self._apply_tag('class', line_num, m.start(2) + 1, line_num, m.end(2) + 1)

        self._highlight_words(line, line_num, PYTHON_KEYWORDS, 'keyword')
        self._highlight_words(line, line_num, PYTHON_BUILTINS, 'builtin')

        for m in re.finditer(r'[+\-*/%=<>!&|^~]=?|\*\*|//', line):
            self._apply_tag('operator', line_num, m.start() + 1, line_num, m.end() + 1)

    def _highlight_cpp(self, text):
        lines = text.split('\n')
        for line_num, line in enumerate(lines, 1):
            self._highlight_cpp_line(line, line_num)

    def _highlight_cpp_line(self, line, line_num):
        comment_match = re.search(r'//.*$', line)
        if comment_match:
            start_col = comment_match.start()
            self._apply_tag('comment', line_num, start_col + 1, line_num, len(line) + 1)
            line = line[:start_col]

        block_start = line.find('/*')
        block_end = line.find('*/')
        if block_start >= 0 and block_end >= 0:
            self._apply_tag('comment', line_num, block_start + 1, line_num, block_end + 3)

        for m in re.finditer(r'"[^"]*"', line):
            self._apply_tag('string', line_num, m.start() + 1, line_num, m.end() + 1)

        for m in re.finditer(r"'[^']*'", line):
            self._apply_tag('string', line_num, m.start() + 1, line_num, m.end() + 1)

        for m in re.finditer(r'\b(\d+\.?\d*[eE]?[+-]?\d*|0x[0-9a-fA-F]+)\b', line):
            self._apply_tag('number', line_num, m.start() + 1, line_num, m.end() + 1)

        for m in re.finditer(r'void|int|float|char|double|long|if|else|for|while|switch|case|break|continue|return|struct|const|static|typedef', line):
            self._apply_tag('keyword', line_num, m.start() + 1, line_num, m.end() + 1)

        for m in re.finditer(r'\b(SERIAL|Serial|pinMode|digitalWrite|analogWrite|digitalRead|delay|millis|attachInterrupt|display|mPython|print|println|setCursorLine|setCursor)\b', line):
            self._apply_tag('builtin', line_num, m.start() + 1, line_num, m.end() + 1)

        for m in re.finditer(r'\b(\w+)\s*\(', line):
            word = m.group(1)
            if word not in C_KEYWORDS and word not in ('void', 'int', 'float', 'char'):
                self._apply_tag('function', line_num, m.start(1) + 1, line_num, m.end(1) + 1)

        for m in re.finditer(r'[+\-*/%=<>!&|^~]=?|&&|\|\|', line):
            self._apply_tag('operator', line_num, m.start() + 1, line_num, m.end() + 1)

        preproc_match = re.match(r'^\s*(#\w+)', line)
        if preproc_match:
            self._apply_tag('keyword', line_num, preproc_match.start(1) + 1, line_num, preproc_match.end(1) + 1)

    def _highlight_words(self, line, line_num, words, tag):
        for word in sorted(words, key=len, reverse=True):
            pattern = r'\b' + re.escape(word) + r'\b'
            for m in re.finditer(pattern, line):
                self._apply_tag(tag, line_num, m.start() + 1, line_num, m.end() + 1)

    def _apply_tag(self, tag, start_line, start_col, end_line, end_col):
        self.text.tag_add(tag, f'{start_line}.{start_col}', f'{end_line}.{end_col}')

    def _update_current_line(self):
        try:
            self.text.tag_remove('current_line', '1.0', tk.END)
            pos = self.text.index('insert')
            line = pos.split('.')[0]
            self.text.tag_add('current_line', f'{line}.0', f'{line}.end')
            self.text.tag_configure('current_line',
                                    background=self.theme.EDITOR_CURRENT_LINE)
        except Exception:
            pass


def apply_theme(root, theme_class=DarkTheme):
    t = theme_class()

    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except Exception:
        pass

    root.configure(bg=t.BG)

    style.configure('TFrame', background=t.BG)
    style.configure('TPanel', background=t.BG_PANEL)
    style.configure('TCard', background=t.BG_CARD)
    style.configure('TElevated', background=t.BG_ELEVATED)

    style.configure('TLabel', background=t.BG, foreground=t.FG, font=t.FONT_MAIN)
    style.configure('TMuted.TLabel', background=t.BG, foreground=t.FG_MUTED, font=t.FONT_SMALL)
    style.configure('TDim.TLabel', background=t.BG, foreground=t.FG_DIM, font=t.FONT_SMALL)
    style.configure('TAccent.TLabel', background=t.BG, foreground=t.FG_ACCENT, font=("Segoe UI", 10, "bold"))

    style.configure('TLabelframe', background=t.BG, foreground=t.FG, font=t.FONT_MAIN,
                    borderwidth=0, relief='flat')
    style.configure('TLabelframe.Label', background=t.BG, foreground=t.FG_ACCENT,
                    font=("Segoe UI", 10, "bold"))

    style.configure('Glass.TFrame', background=t.GLASS_BG, borderwidth=1,
                    relief='solid', bordercolor=t.GLASS_BORDER)

    style.configure('TButton',
                    background=t.BUTTON_BG,
                    foreground=t.BUTTON_FG,
                    font=t.FONT_BTN,
                    padding=(12, 6),
                    borderwidth=0,
                    focusthickness=0)
    style.map('TButton',
              background=[('active', t.BUTTON_HOVER), ('pressed', t.ACCENT_DIM)],
              foreground=[('disabled', t.FG_DIM)])

    style.configure('Accent.TButton',
                    background=t.ACCENT,
                    foreground=t.BG,
                    font=("Segoe UI", 10, "bold"),
                    padding=(14, 7),
                    borderwidth=0)
    style.map('Accent.TButton',
              background=[('active', t.ACCENT_HOVER), ('pressed', t.ACCENT_DIM)])

    style.configure('Success.TButton',
                    background=t.SUCCESS,
                    foreground=t.BG,
                    font=("Segoe UI", 9, "bold"),
                    padding=(10, 6),
                    borderwidth=0)
    style.map('Success.TButton',
              background=[('active', t.ACCENT_HOVER)])

    style.configure('Danger.TButton',
                    background=t.ERROR,
                    foreground=t.BG,
                    font=("Segoe UI", 9, "bold"),
                    padding=(10, 6),
                    borderwidth=0)

    style.configure('Glass.TButton',
                    background=t.BG_ELEVATED,
                    foreground=t.FG,
                    font=t.FONT_BTN,
                    padding=(12, 6),
                    borderwidth=0,
                    focusthickness=0)
    style.map('Glass.TButton',
              background=[('active', t.BG_HOVER)])

    style.configure('Icon.TButton',
                    background=t.BG_ELEVATED,
                    foreground=t.FG,
                    font=t.FONT_BTN,
                    padding=(8, 6),
                    borderwidth=0,
                    focusthickness=0)
    style.map('Icon.TButton',
              background=[('active', t.BG_HOVER)])

    style.configure('Tool.TButton',
                    background=t.BG_ELEVATED,
                    foreground=t.FG,
                    font=t.FONT_BTN,
                    padding=(10, 6),
                    borderwidth=1,
                    bordercolor=t.BORDER_SUBTLE,
                    focusthickness=0)
    style.map('Tool.TButton',
              background=[('active', t.BG_HOVER), ('pressed', t.ACCENT_DIM)])

    style.configure('TNotebook', background=t.BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure('TNotebook.Tab',
                    background=t.BG_ELEVATED,
                    foreground=t.FG_DIM,
                    padding=(18, 10),
                    font=t.FONT_BTN,
                    borderwidth=0)
    style.map('TNotebook.Tab',
              background=[('selected', t.BG_CARD), ('active', t.BG_HOVER)],
              foreground=[('selected', t.ACCENT), ('active', t.FG)])

    style.configure('TEntry',
                    fieldbackground=t.BG_INPUT,
                    foreground=t.FG,
                    insertcolor=t.FG,
                    borderwidth=1)
    style.map('TEntry',
              fieldbackground=[('focus', t.BG_INPUT)],
              bordercolor=[('focus', t.ACCENT)])

    style.configure('TCombobox',
                    fieldbackground=t.BG_INPUT,
                    background=t.BUTTON_BG,
                    foreground=t.FG,
                    arrowcolor=t.FG)

    style.configure('TScrollbar',
                    background=t.BG_ELEVATED,
                    troughcolor=t.BG_INPUT,
                    arrowcolor=t.FG_DIM,
                    borderwidth=0)
    style.configure('TScrollbar.vertical', width=12)
    style.configure('TScrollbar.horizontal', height=12)

    style.map('TScrollbar',
              background=[('active', t.BG_HOVER)])

    style.configure('TScale',
                    background=t.BG,
                    troughcolor=t.ACCENT_DIM,
                    sliderthickness=16)

    style.configure('TCheckbutton',
                    background=t.BG,
                    foreground=t.FG,
                    font=t.FONT_MAIN)

    style.configure('TRadiobutton',
                    background=t.BG,
                    foreground=t.FG,
                    font=t.FONT_MAIN)

    style.configure('TSeparator',
                    background=t.BORDER_SUBTLE)

    style.configure('Horizontal.TProgressbar',
                    background=t.ACCENT,
                    troughcolor=t.BG_INPUT,
                    borderwidth=0,
                    thickness=4)

    style.configure('Treeview',
                    background=t.TREE_BG,
                    foreground=t.FG,
                    fieldbackground=t.TREE_BG,
                    rowheight=26,
                    borderwidth=0,
                    font=t.FONT_MAIN)
    style.configure('Treeview.Heading',
                    background=t.TREE_HEAD,
                    foreground=t.FG,
                    font=("Segoe UI", 9, "bold"),
                    borderwidth=0)
    style.map('Treeview',
              background=[('selected', t.ACCENT_DIM)],
              foreground=[('selected', t.FG)])

    style.configure('Vertical.PanedWindow',
                    background=t.BG,
                    sashwidth=6,
                    sashrelief='flat')

    style.configure('Horizontal.PanedWindow',
                    background=t.BG,
                    sashwidth=6,
                    sashrelief='flat')

    style.configure('Menu',
                    background=t.BG_PANEL,
                    foreground=t.FG,
                    borderwidth=0,
                    tearoff=False)

    style.configure('MenuItem',
                    background=t.BG_PANEL,
                    foreground=t.FG)

    root.option_add('*Menu*background', t.BG_PANEL)
    root.option_add('*Menu*foreground', t.FG)
    root.option_add('*Menu*selectColor', t.BG)
    root.option_add('*Menu*selectBackground', t.ACCENT)

    return t


class GlassEffect:
    @staticmethod
    def create_glass_panel(parent, theme, width=None, height=None):
        frame = tk.Frame(parent, bg=theme.GLASS_BG, highlightbackground=theme.GLASS_BORDER,
                         highlightthickness=1, bd=0)
        if width:
            frame.configure(width=width)
        if height:
            frame.configure(height=height)
        return frame

    @staticmethod
    def create_glass_button(parent, theme, text, command, **kwargs):
        btn = tk.Button(parent, text=text, command=command,
                        bg=theme.BG_ELEVATED, fg=theme.FG,
                        activebackground=theme.BG_HOVER,
                        activeforeground=theme.FG,
                        font=("Segoe UI", 9),
                        relief='flat', bd=0,
                        padx=12, pady=6,
                        cursor='hand2',
                        **kwargs)
        return btn

    @staticmethod
    def create_canvas_button(parent, theme, text, command, width=100, height=32,
                              bg=None, fg=None, hover_bg=None, hover_fg=None, radius=8,
                              icon=None, accent=False):
        if bg is None:
            bg = theme.ACCENT if accent else theme.BG_ELEVATED
        if fg is None:
            fg = theme.BG if accent else theme.FG
        if hover_bg is None:
            hover_bg = theme.ACCENT_HOVER if accent else theme.BG_HOVER
        if hover_fg is None:
            hover_fg = fg

        canvas = tk.Canvas(parent, width=width, height=height,
                           bg=parent['bg'] if parent['bg'] else theme.BG,
                           highlightthickness=0, bd=0, cursor='hand2')

        def draw_button():
            canvas.delete('all')
            GlassEffect._draw_rounded_rect(canvas, 1, 1, width - 1, height - 1,
                                           radius, fill=bg, outline=theme.BORDER_SUBTLE)
            if icon:
                canvas.create_text(width // 2 - 8, height // 2,
                                    text=icon, fill=fg,
                                    font=("Segoe UI", 12), anchor='center')
                canvas.create_text(width // 2 + 4, height // 2,
                                    text=text, fill=fg,
                                    font=("Segoe UI", 9), anchor='center')
            else:
                canvas.create_text(width // 2, height // 2,
                                    text=text, fill=fg,
                                    font=("Segoe UI", 9), anchor='center')

        def on_hover(event):
            canvas.delete('all')
            GlassEffect._draw_rounded_rect(canvas, 1, 1, width - 1, height - 1,
                                           radius, fill=hover_bg, outline=theme.ACCENT)
            if icon:
                canvas.create_text(width // 2 - 8, height // 2,
                                    text=icon, fill=hover_fg,
                                    font=("Segoe UI", 12), anchor='center')
                canvas.create_text(width // 2 + 4, height // 2,
                                    text=text, fill=hover_fg,
                                    font=("Segoe UI", 9), anchor='center')
            else:
                canvas.create_text(width // 2, height // 2,
                                    text=text, fill=hover_fg,
                                    font=("Segoe UI", 9), anchor='center')

        def on_leave(event):
            draw_button()

        def on_click(event):
            command()

        def update_style(new_bg=None, new_fg=None, new_hover_bg=None, new_hover_fg=None, new_text=None):
            nonlocal bg, fg, hover_bg, hover_fg, text
            if new_bg is not None:
                bg = new_bg
            if new_fg is not None:
                fg = new_fg
            if new_hover_bg is not None:
                hover_bg = new_hover_bg
            if new_hover_fg is not None:
                hover_fg = new_hover_fg
            if new_text is not None:
                text = new_text
            draw_button()

        draw_button()
        canvas.bind('<Enter>', on_hover)
        canvas.bind('<Leave>', on_leave)
        canvas.bind('<Button-1>', on_click)
        canvas.update_button_style = update_style
        canvas._btn_command = command
        canvas._btn_theme = theme
        canvas._btn_radius = radius
        canvas._btn_icon = icon
        canvas._btn_width = width
        canvas._btn_height = height
        return canvas

    @staticmethod
    def _draw_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x2 - r, y1,
            x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r,
            x1, y1 + r, x1, y1
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    @staticmethod
    def create_icon_button(parent, theme, icon_text, tooltip, command, size=34,
                            bg=None, hover_bg=None, fg=None):
        if bg is None:
            bg = theme.BG_ELEVATED
        if hover_bg is None:
            hover_bg = theme.BG_HOVER
        if fg is None:
            fg = theme.FG

        canvas = tk.Canvas(parent, width=size, height=size,
                           bg=parent['bg'] if parent['bg'] else theme.BG,
                           highlightthickness=0, bd=0, cursor='hand2')

        r = 8
        def draw():
            canvas.delete('all')
            GlassEffect._draw_rounded_rect(canvas, 1, 1, size - 1, size - 1,
                                           r, fill=bg, outline=theme.BORDER_SUBTLE)
            canvas.create_text(size // 2, size // 2, text=icon_text,
                               fill=fg, font=("Segoe UI", 11), anchor='center')

        def on_hover(e):
            canvas.delete('all')
            GlassEffect._draw_rounded_rect(canvas, 1, 1, size - 1, size - 1,
                                           r, fill=hover_bg, outline=theme.ACCENT)
            canvas.create_text(size // 2, size // 2, text=icon_text,
                               fill=fg, font=("Segoe UI", 11), anchor='center')

        def on_leave(e):
            draw()

        def on_click(e):
            command()

        draw()
        canvas.bind('<Enter>', on_hover)
        canvas.bind('<Leave>', on_leave)
        canvas.bind('<Button-1>', on_click)

        tooltip_label = tk.Label(parent, text=tooltip, bg=theme.BG_PANEL,
                                 fg=theme.FG, font=("Segoe UI", 8), padx=4, pady=2)
        tooltip_label.place_forget()

        def show_tip(e):
            x = canvas.winfo_rootx() + size + 2
            y = canvas.winfo_rooty()
            tooltip_label.place(x=x, y=y)

        def hide_tip(e):
            tooltip_label.place_forget()

        canvas.bind('<Enter>', show_tip, add='+')
        canvas.bind('<Leave>', hide_tip, add='+')

        return canvas

    @staticmethod
    def create_status_indicator(parent, theme, color, size=10):
        canvas = tk.Canvas(parent, width=size + 8, height=size + 8,
                           bg=parent['bg'] if parent['bg'] else theme.BG,
                           highlightthickness=0, bd=0)
        canvas.create_oval(4, 4, size + 4, size + 4,
                           fill=color, outline='')
        canvas.create_oval(2, 2, size + 6, size + 6,
                           fill='', outline=color, width=1)
        return canvas


def create_line_number_widget(parent, theme, text_widget):
    canvas = tk.Canvas(parent, width=40,
                        bg=theme.EDITOR_BG, highlightthickness=0, bd=0)
    return canvas


GLassEffect = GlassEffect
