# -*- coding: utf-8 -*-
"""自绘 UI 组件：圆角按钮、卡片、进度条、分段控件、滚动列表、内嵌弹窗、轻提示。

全部基于 Canvas 绘制，避免 tkinter 默认控件的粗糙外观；配色全部取自
theme.C，因此切换浅色 / 深色主题后重绘即可生效。
"""

import math
import tkinter as tk

from .theme import C, mix


# ---------------------------------------------------------------- 基础绘制

def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """在 Canvas 上画圆角矩形：按圆弧采样生成多边形，边缘平直、圆角干净。"""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    if r <= 0:
        return canvas.create_rectangle(x1, y1, x2, y2, **kw)
    steps = 6
    pts = []
    corners = ((x2 - r, y1 + r, -90.0), (x2 - r, y2 - r, 0.0),
               (x1 + r, y2 - r, 90.0), (x1 + r, y1 + r, 180.0))
    for cx, cy, start in corners:
        for i in range(steps + 1):
            a = math.radians(start + 90.0 * i / steps)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return canvas.create_polygon(pts, smooth=False, **kw)


def parent_bg(widget, fallback=None):
    try:
        return widget.cget("bg")
    except tk.TclError:
        return fallback or C["bg"]


def star_points(cx, cy, r_out, r_in, points=5):
    pts = []
    for i in range(points * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(-90 + i * 180.0 / points)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ---------------------------------------------------------------- 按钮

def button_colors(kind):
    """按当前主题返回 (背景, 文字, 悬停, 按下, 描边)。"""
    if kind == "primary":
        return C["primary"], C["on_color"], C["primary_hover"], C["primary_press"], None
    if kind == "secondary":
        return (C["surface"], C["primary"], C["primary_soft"],
                C["press_soft"], C["primary_border"])
    if kind == "outline":
        return C["surface"], C["text"], C["hover_soft"], C["press_soft"], C["border"]
    if kind == "ghost":
        return C["surface_alt"], C["text"], C["ghost_hover"], C["press_soft"], None
    if kind == "danger":
        return (C["danger"], C["on_color"], C["danger_hover"],
                mix(C["danger"], "#000000", 0.16), None)
    if kind == "danger_soft":
        return (C["danger_soft"], C["danger"],
                mix(C["danger_soft"], C["danger"], 0.14),
                mix(C["danger_soft"], C["danger"], 0.22), C["danger_border"])
    if kind == "success":
        return (C["success"], C["on_color"], C["success_hover"],
                mix(C["success"], "#000000", 0.16), None)
    if kind == "gold":
        return (C["surface"], C["gold"], C["gold_soft"],
                mix(C["gold_soft"], C["gold"], 0.18), C["gold_border"])
    if kind == "gold_soft":
        return (C["gold_soft"], C["gold"],
                mix(C["gold_soft"], C["gold"], 0.14),
                mix(C["gold_soft"], C["gold"], 0.24), C["gold_border"])
    if kind == "link":
        return C["surface"], C["primary"], C["primary_soft"], C["press_soft"], None
    return C["surface"], C["text"], C["hover_soft"], C["press_soft"], C["border"]


class Button(tk.Canvas):
    """圆角按钮，支持悬停 / 按下 / 禁用状态，宽度固定（切换文字时不会跳动）。"""

    def __init__(self, master, theme, text, command=None, kind="primary",
                 width=140, height=44, radius=12, font_px=14, bold=True, bg=None):
        super().__init__(master, width=theme.s(width), height=theme.s(height),
                         bg=bg or parent_bg(master), highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=0)
        self.T = theme
        self._cw, self._ch = theme.s(width), theme.s(height)
        self._r = theme.s(radius)
        self._kind = kind
        self._text = text
        self._font = theme.f(font_px, "bold" if bold else "normal")
        self._command = command
        self._state = "normal"     # normal | hover | press
        self._enabled = True
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    # -- 绘制
    def _colors(self):
        bg, fg, hover, press, border = button_colors(self._kind)
        if not self._enabled:
            return C["disabled_bg"], C["disabled_fg"], None
        if self._state == "hover":
            return hover, fg, border
        if self._state == "press":
            return press, fg, border
        return bg, fg, border

    def _draw(self):
        self.delete("all")
        fill, fg, border = self._colors()
        w, h, r = self._cw, self._ch, self._r
        round_rect(self, 1, 1, w - 1, h - 1, r, fill=fill,
                   outline=border or fill, width=1)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)

    # -- 状态
    def set_text(self, text, kind=None):
        self._text = text
        if kind:
            self._kind = kind
        self._draw()

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def _on_enter(self, _e=None):
        if self._enabled:
            self._state = "hover"
            self._draw()

    def _on_leave(self, _e=None):
        self._state = "normal"
        self._draw()

    def _on_press(self, _e=None):
        if self._enabled:
            self._state = "press"
            self._draw()

    def _on_release(self, _e=None):
        if not self._enabled:
            return
        inside = 0 <= self.winfo_pointerx() - self.winfo_rootx() <= self._cw and \
                 0 <= self.winfo_pointery() - self.winfo_rooty() <= self._ch
        self._state = "hover" if inside else "normal"
        self._draw()
        if inside and self._command:
            self._command()


class IconButton(tk.Canvas):
    """小方形图标按钮（用于返回、关闭）。"""

    def __init__(self, master, theme, glyph, command=None, size=34, bg=None,
                 fg=None, hover=None, radius=10, font_px=15):
        super().__init__(master, width=theme.s(size), height=theme.s(size),
                         bg=bg or parent_bg(master), highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=0)
        self.T = theme
        self._s = theme.s(size)
        self._glyph = glyph
        self._fg = fg
        self._hover = hover
        self._r = theme.s(radius)
        self._font = theme.f(font_px, "normal")
        self._command = command
        self._hot = False
        self._draw()
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonRelease-1>", self._click)

    def _draw(self):
        self.delete("all")
        if self._hot:
            round_rect(self, 1, 1, self._s - 1, self._s - 1, self._r,
                       fill=self._hover or C["surface_alt"], outline="")
        self.create_text(self._s / 2, self._s / 2, text=self._glyph,
                         fill=self._fg or C["muted"], font=self._font)

    def _enter(self, _e):
        self._hot = True
        self._draw()

    def _leave(self, _e):
        self._hot = False
        self._draw()

    def _click(self, _e):
        if self._command:
            self._command()


class ThemeToggle(tk.Canvas):
    """太阳 / 月亮切换按钮（纯绘制，不依赖字体图标）。"""

    def __init__(self, master, theme, dark, command, size=32, bg=None):
        super().__init__(master, width=theme.s(size), height=theme.s(size),
                         bg=bg or parent_bg(master), highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=0)
        self.T = theme
        self._s = theme.s(size)
        self._dark = dark
        self._command = command
        self._hot = False
        self._draw()
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonRelease-1>", lambda e: self._command())

    def _draw(self):
        self.delete("all")
        s = self._s
        if self._hot:
            round_rect(self, 1, 1, s - 1, s - 1, self.T.s(9),
                       fill=C["surface_alt"], outline="")
        cx = cy = s / 2
        color = C["text"] if self._hot else C["muted"]
        if self._dark:
            # 太阳：圆 + 8 条光线
            r = s * 0.16
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             outline=color, width=max(1, self.T.s(2)))
            for i in range(8):
                a = math.radians(i * 45)
                x1 = cx + math.cos(a) * s * 0.25
                y1 = cy + math.sin(a) * s * 0.25
                x2 = cx + math.cos(a) * s * 0.36
                y2 = cy + math.sin(a) * s * 0.36
                self.create_line(x1, y1, x2, y2, fill=color,
                                 width=max(1, self.T.s(2)), capstyle="round")
        else:
            # 月亮：实心圆 + 偏移的背景色圆，形成月牙
            r = s * 0.30
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             fill=color, outline="")
            off = s * 0.16
            self.create_oval(cx - r + off * 1.1, cy - r - off,
                             cx + r + off * 1.1, cy + r - off,
                             fill=parent_bg(self), outline="")

    def _enter(self, _e):
        self._hot = True
        self._draw()

    def _leave(self, _e):
        self._hot = False
        self._draw()


class LogoMark(tk.Canvas):
    """左上角品牌标记：圆角方块 + 五角星。"""

    def __init__(self, master, theme, size=28, bg=None):
        super().__init__(master, width=theme.s(size), height=theme.s(size),
                         bg=bg or parent_bg(master), highlightthickness=0, bd=0)
        s = theme.s(size)
        round_rect(self, 0, 0, s - 1, s - 1, theme.s(8), fill=C["primary"], outline="")
        self.create_polygon(star_points(s / 2, s / 2 + theme.s(1),
                                        s * 0.30, s * 0.13),
                            fill="#FFFFFF", outline="")


# ---------------------------------------------------------------- 分段控件（语言切换）

class Segmented(tk.Canvas):
    def __init__(self, master, theme, options, value, on_change, width=150, height=30, bg=None):
        super().__init__(master, width=theme.s(width), height=theme.s(height),
                         bg=bg or parent_bg(master), highlightthickness=0, bd=0)
        self.T = theme
        self._cw, self._ch = theme.s(width), theme.s(height)
        self._segments = options          # [(key, label), ...]
        self._value = value
        self._on_change = on_change
        self._hover_index = None
        self._draw()
        self.bind("<ButtonRelease-1>", self._click)
        self.bind("<Motion>", self._motion)

    def set_value(self, value):
        self._value = value
        self._draw()

    def _seg_w(self):
        return self._cw / max(1, len(self._segments))

    def _draw(self):
        self.delete("all")
        round_rect(self, 1, 1, self._cw - 1, self._ch - 1, self._ch / 2,
                   fill=C["surface_alt"], outline="")
        sw = self._seg_w()
        for i, (key, label) in enumerate(self._segments):
            x1 = i * sw
            active = key == self._value
            if active:
                pad = self.T.s(2)
                round_rect(self, x1 + pad, pad, x1 + sw - pad, self._ch - pad,
                           (self._ch - 2 * pad) / 2, fill=C["surface"], outline="")
            color = C["primary"] if active else (
                C["text"] if i == self._hover_index else C["muted"])
            self.create_text(x1 + sw / 2, self._ch / 2, text=label,
                             fill=color, font=self.T.f(12, "bold" if active else "normal"))

    def _motion(self, e):
        idx = int(e.x // self._seg_w())
        idx = max(0, min(len(self._segments) - 1, idx))
        if idx != self._hover_index:
            self._hover_index = idx
            self._draw()

    def _click(self, e):
        idx = int(e.x // self._seg_w())
        idx = max(0, min(len(self._segments) - 1, idx))
        key = self._segments[idx][0]
        if key != self._value:
            self._value = key
            self._draw()
            if self._on_change:
                self._on_change(key)


# ---------------------------------------------------------------- 统计芯片

class Chip(tk.Canvas):
    """圆角信息胶囊：标签 + 数值。"""

    def __init__(self, master, theme, label, value, width=96, height=32,
                 fg=None, bg_color=None, bg=None):
        super().__init__(master, width=theme.s(width), height=theme.s(height),
                         bg=bg or parent_bg(master), highlightthickness=0, bd=0)
        self.T = theme
        self._cw, self._ch = theme.s(width), theme.s(height)
        self._label = label
        self._value = value
        self._fg = fg or C["text"]
        self._bg_color = bg_color or C["surface_alt"]
        self._draw()

    def set(self, label=None, value=None):
        if label is not None:
            self._label = label
        if value is not None:
            self._value = str(value)
        self._draw()

    def _draw(self):
        self.delete("all")
        round_rect(self, 1, 1, self._cw - 1, self._ch - 1, self._ch / 2,
                   fill=self._bg_color, outline="")
        self.create_text(self.T.s(12), self._ch / 2, text=self._label, anchor="w",
                         fill=C["muted"], font=self.T.f(11))
        self.create_text(self._cw - self.T.s(12), self._ch / 2, text=str(self._value),
                         anchor="e", fill=self._fg, font=self.T.f(13, "bold"))


# ---------------------------------------------------------------- 卡片

class Card(tk.Frame):
    """圆角卡片：Canvas 绘制背景，内部 Frame 承载内容。"""

    def __init__(self, master, theme, radius=16, padding=0, fill=None,
                 border=None, shadow=True, bg=None):
        super().__init__(master, bg=bg or parent_bg(master))
        self.T = theme
        self._radius = theme.s(radius)
        self._fill = fill or C["surface"]
        self._border = border or C["border"]
        self._shadow = shadow
        self._bg = bg or parent_bg(master)
        self.canvas = tk.Canvas(self, bg=self._bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        pad = theme.s(padding)
        self._pad = pad
        self.inner = tk.Frame(self, bg=self._fill)
        self.inner.place(x=pad, y=pad, width=1, height=1)
        self.canvas.bind("<Configure>", self._redraw)

    def _redraw(self, _e=None):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 2 or h <= 2:
            return
        pad = self._pad + 1          # 内缩 1px，保证描边可见
        self.inner.place_configure(x=pad, y=pad,
                                   width=max(1, w - 2 * pad),
                                   height=max(1, h - 2 * pad))
        if self._shadow:
            round_rect(self.canvas, 1, self.T.s(4), w - 1, h, self._radius,
                       fill=C["shadow"], outline="")
        round_rect(self.canvas, 1, 1, w - 1, h - self.T.s(3), self._radius,
                   fill=self._fill, outline=self._border, width=1)

    def set_fill(self, fill, border=None):
        self._fill = fill
        self.inner.configure(bg=fill)
        if border:
            self._border = border
        self._redraw()


# ---------------------------------------------------------------- 进度条

class ProgressBar(tk.Canvas):
    def __init__(self, master, theme, height=6, bg=None, color=None, track=None):
        super().__init__(master, height=theme.s(height), bg=bg or parent_bg(master),
                         highlightthickness=0, bd=0)
        self.T = theme
        self._ch = theme.s(height)
        self._ratio = 0.0
        self._color = color
        self._track = track
        self.bind("<Configure>", self._redraw)

    def set(self, ratio):
        self._ratio = max(0.0, min(1.0, ratio))
        self._redraw()

    def _redraw(self, _e=None):
        self.delete("all")
        w = self.winfo_width()
        h = self._ch
        if w <= 4:
            return
        r = h / 2
        round_rect(self, 0, 0, w, h, r, fill=self._track or C["border"], outline="")
        fw = max(h, w * self._ratio) if self._ratio > 0 else 0
        if fw > 0:
            round_rect(self, 0, 0, fw, h, r,
                       fill=self._color or C["primary"], outline="")


# ---------------------------------------------------------------- 滚动容器

class ScrollFrame(tk.Frame):
    """竖向滚动容器，内部用 .inner 添加控件；右侧为自绘细滚动条。"""

    def __init__(self, master, theme, bg=None, scrollbar=True):
        bg = bg or C["surface"]
        super().__init__(master, bg=bg)
        self.T = theme
        self._bg = bg
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self._bar = None
        if scrollbar:
            self._bar = tk.Canvas(self, width=theme.s(6), bg=bg,
                                  highlightthickness=0, bd=0)
            self._bar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)
        self.inner.bind("<Enter>", self._bind_wheel)
        self.inner.bind("<Leave>", self._unbind_wheel)

    def _on_inner(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._draw_bar(*self.canvas.yview())

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)
        self._draw_bar(*self.canvas.yview())

    def _on_scroll(self, first, last):
        self._draw_bar(float(first), float(last))

    def _draw_bar(self, first, last):
        if self._bar is None:
            return
        self._bar.delete("all")
        h = self._bar.winfo_height()
        w = self._bar.winfo_width()
        if h < 20 or (last - first) >= 0.999:
            return
        y1 = max(0.0, first * h)
        y2 = min(float(h), last * h)
        if y2 - y1 < self.T.s(26):
            y2 = y1 + self.T.s(26)
            if y2 > h:
                y2 = h
                y1 = max(0, h - self.T.s(26))
        round_rect(self._bar, 0, y1, w, y2, w / 2, fill=C["scroll_thumb"], outline="")

    def _bind_wheel(self, _e=None):
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", self._wheel_linux)
        self.canvas.bind_all("<Button-5>", self._wheel_linux)

    def _unbind_wheel(self, _e=None):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _wheel(self, e):
        delta = -1 * int(e.delta / 120 * 3) if abs(e.delta) >= 120 else -1 * (1 if e.delta > 0 else -1)
        self.canvas.yview_scroll(delta, "units")

    def _wheel_linux(self, e):
        self.canvas.yview_scroll(-3 if e.num == 4 else 3, "units")

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.canvas.yview_moveto(0)


# ---------------------------------------------------------------- 列表行

class ListRow(tk.Frame):
    """可点击的列表项：头像 + 标题 + 副标题 + 右侧标记，带悬停 / 选中反馈。"""

    def __init__(self, master, theme, title, meta="", on_click=None, selected=False,
                 height=60, accent=None, trailing="", avatar=None):
        super().__init__(master, bg=C["surface"], height=theme.s(height),
                         cursor="hand2", highlightthickness=0)
        self.pack_propagate(False)
        self.T = theme
        self._on_click = on_click
        self._selected = selected
        self._hover = False
        self._accent = accent or C["primary"]
        self._avatar_text = avatar

        self._bar = tk.Frame(self, width=theme.s(3), bg=C["surface"])
        self._bar.pack(side="left", fill="y")

        self._avatar = None
        if avatar is not None:
            size = theme.s(30)
            self._avatar = tk.Canvas(self, width=size, height=size, bg=C["surface"],
                                     highlightthickness=0, bd=0)
            self._avatar.pack(side="left", padx=(theme.s(10), 0))

        body = tk.Frame(self, bg=C["surface"])
        body.pack(side="left", fill="both", expand=True,
                  padx=(theme.s(10), theme.s(8)), pady=theme.s(7))
        self._title = tk.Label(body, text=title, bg=C["surface"], fg=C["text"],
                               font=theme.f(13, "bold"), anchor="w", justify="left")
        self._title.pack(fill="x")
        self._meta = tk.Label(body, text=meta, bg=C["surface"], fg=C["muted"],
                              font=theme.f(11), anchor="w", justify="left")
        self._meta.pack(fill="x")

        self._trail = tk.Label(self, text=trailing, bg=C["surface"], fg=C["faint"],
                               font=theme.f(11), anchor="e")
        self._trail.pack(side="right", padx=theme.s(10))

        targets = [self, self._bar, body, self._title, self._meta, self._trail]
        if self._avatar is not None:
            targets.append(self._avatar)
        for w in targets:
            w.bind("<Button-1>", self._click)
            w.bind("<Double-Button-1>", self._double)
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)

        self._paint()

    def _draw_avatar(self):
        if self._avatar is None:
            return
        s = int(self._avatar.cget("width"))
        self._avatar.delete("all")
        bg = C["primary_soft"] if not self._selected else C["surface"]
        self._avatar.create_oval(0, 0, s, s, fill=bg, outline="")
        self._avatar.create_text(s / 2, s / 2, text=(self._avatar_text or "?")[:1].upper(),
                                 fill=C["primary"], font=self.T.f(13, "bold"))

    def _paint(self):
        bg = C["primary_soft"] if self._selected else (
            C["row_hover"] if self._hover else C["surface"])
        for w in (self, self._bar, self._title, self._meta, self._trail):
            w.configure(bg=bg)
        for child in self.winfo_children():
            try:
                child.configure(bg=bg)
            except tk.TclError:
                pass
        if self._avatar is not None:
            self._avatar.configure(bg=bg)
            self._draw_avatar()
        self._bar.configure(bg=self._accent if self._selected else bg)
        self._title.configure(fg=C["primary"] if self._selected else C["text"])

    def set_selected(self, value):
        self._selected = value
        self._paint()

    def _enter(self, _e):
        self._hover = True
        self._paint()

    def _leave(self, _e):
        self._hover = False
        self._paint()

    def _click(self, _e=None):
        if self._on_click:
            self._on_click()

    def _double(self, _e=None):
        if self._on_click:
            self._on_click(double=True)


# ---------------------------------------------------------------- 文本面板

class TextPanel(tk.Canvas):
    """圆角面板 + 居中可换行文本，可选小标题（上方或下方）。"""

    def __init__(self, master, theme, radius=16, padding=28, bg=None,
                 fill=None, border=None, shadow=True, height=None,
                 stack_sub=False, sub_below=False):
        super().__init__(master, bg=bg or parent_bg(master), highlightthickness=0, bd=0)
        self.T = theme
        self._radius = theme.s(radius)
        self._pad = theme.s(padding)
        self._fill = fill or C["surface"]
        self._border = border or C["border"]
        self._shadow = shadow
        self._stack = stack_sub
        self._sub_below = sub_below
        self._text = ""
        self._fg = C["text"]
        self._font = theme.f(20, "bold")
        self._sub = ""
        self._sub_fg = C["faint"]
        self._sub_font = theme.f(11)
        if height:
            self.configure(height=theme.s(height))
        self.bind("<Configure>", self._redraw)

    def set(self, text=None, fg=None, fill=None, border=None, font_px=None,
            bold=True, sub=None, sub_fg=None):
        if text is not None:
            self._text = text
        if fg is not None:
            self._fg = fg
        if fill is not None:
            self._fill = fill
        if border is not None:
            self._border = border
        if font_px is not None:
            self._font = self.T.f(font_px, "bold" if bold else "normal")
        if sub is not None:
            self._sub = sub
        if sub_fg is not None:
            self._sub_fg = sub_fg
        self._redraw()

    def _redraw(self, _e=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 4 or h <= 4:
            return
        if self._shadow:
            round_rect(self, 1, self.T.s(4), w - 1, h, self._radius,
                       fill=C["shadow"], outline="")
        round_rect(self, 1, 1, w - 1, h - self.T.s(3), self._radius,
                   fill=self._fill, outline=self._border, width=1)

        if self._sub and self._stack:
            if self._sub_below:
                self.create_text(w / 2, h / 2 - self.T.s(12), text=self._text,
                                 anchor="center", fill=self._fg, font=self._font,
                                 justify="center",
                                 width=max(self.T.s(80), w - 2 * self._pad))
                self.create_text(w / 2, h / 2 + self.T.s(22), text=self._sub,
                                 anchor="center", fill=self._sub_fg,
                                 font=self._sub_font)
            else:
                self.create_text(w / 2, h / 2 - self.T.s(26), text=self._sub,
                                 anchor="center", fill=self._sub_fg,
                                 font=self._sub_font)
                self.create_text(w / 2, h / 2 + self.T.s(12), text=self._text,
                                 anchor="center", fill=self._fg, font=self._font,
                                 justify="center",
                                 width=max(self.T.s(80), w - 2 * self._pad))
            return

        top = self._pad
        if self._sub:
            self.create_text(self._pad, top, text=self._sub, anchor="nw",
                             fill=self._sub_fg, font=self._sub_font)
            top += self.T.s(26)
        avail = max(self.T.s(20), h - top - self._pad)
        self.create_text(w / 2, top + avail / 2, text=self._text, anchor="center",
                         fill=self._fg, font=self._font, justify="center",
                         width=max(self.T.s(80), w - 2 * self._pad))


# ---------------------------------------------------------------- 轻提示

class Toast:
    """底部轻提示：每次创建独立浮层，1.8 秒后销毁（避免残留重绘）。"""

    def __init__(self, master, theme):
        self.master = master
        self.T = theme
        self._frame = None
        self._job = None

    def show(self, message, ms=1800, top=False):
        self._hide()
        frame = tk.Frame(self.master, bg=C["toast_bg"])
        tk.Label(frame, text=message, bg=C["toast_bg"], fg=C["toast_fg"],
                 font=self.T.f(12), padx=self.T.s(18), pady=self.T.s(9)).pack()
        # 统一显示在顶部居中，避免遮挡底部的答题按钮（可连续点击）
        frame.place(relx=0.5, rely=0.012, anchor="n")
        frame.lift()
        self._frame = frame
        self._job = self.master.after(ms, self._hide)

    def _hide(self):
        if self._job is not None:
            try:
                self.master.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if self._frame is not None:
            self._frame.destroy()
            self._frame = None
            try:
                self.master.update_idletasks()
                self.master.update()
            except Exception:
                pass

    def place_forget(self):
        """兼容旧调用。"""
        self._hide()


# ---------------------------------------------------------------- 内嵌弹窗

class Dialog(tk.Frame):
    """页内模态弹窗：浅色遮罩 + 居中圆角卡片。"""

    def __init__(self, master, theme, width, height, title="", on_close=None,
                 icon="", icon_color=None):
        super().__init__(master, bg=C["overlay"])
        self.T = theme
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.lift()
        self._on_close = on_close

        self.card = Card(self, theme, radius=18, padding=0, bg=C["overlay"])
        self.card.place(relx=0.5, rely=0.5, anchor="center",
                        width=theme.s(width), height=theme.s(height))
        body = self.card.inner

        header = tk.Frame(body, bg=C["surface"])
        header.pack(fill="x", padx=theme.s(22), pady=(theme.s(18), 0))
        if icon:
            tk.Label(header, text=icon, bg=C["surface"], fg=icon_color or C["primary"],
                     font=theme.f(17, "bold")).pack(side="left", padx=(0, theme.s(8)))
        tk.Label(header, text=title, bg=C["surface"], fg=C["text"],
                 font=theme.f(15, "bold"), anchor="w").pack(side="left")
        if on_close:
            IconButton(header, theme, "✕", command=self.close, size=30,
                       bg=C["surface"], fg=C["faint"]).pack(side="right")

        # 先固定底部按钮区，再让内容区填充剩余空间，避免窗口偏小时按钮被挤掉
        self.footer = tk.Frame(body, bg=C["surface"])
        self.footer.pack(side="bottom", fill="x", padx=theme.s(22),
                         pady=(theme.s(4), theme.s(18)))
        self.content = tk.Frame(body, bg=C["surface"])
        self.content.pack(fill="both", expand=True, padx=theme.s(22),
                          pady=(theme.s(10), theme.s(6)))

    def close(self):
        if self._on_close:
            self._on_close()
        self.destroy()


def message_dialog(master, theme, title, message, buttons, width=460, height=260,
                   icon="", icon_color=None, text_color=None,
                   font_px=12, on_close=None):
    """通用提示/确认弹窗。buttons: [(文字, kind, 回调), ...]"""

    dlg = Dialog(master, theme, width, height, title, on_close=on_close,
                 icon=icon, icon_color=icon_color)

    tk.Label(dlg.content, text=message, bg=C["surface"], fg=text_color or C["muted"],
             font=theme.f(font_px), justify="left", anchor="nw",
             wraplength=theme.s(width - 52)).pack(fill="both", expand=True)

    for text, kind, cb in reversed(buttons):
        def handler(callback=cb):
            dlg.destroy()
            if callback:
                callback()
        Button(dlg.footer, theme, text, command=handler, kind=kind,
               width=118, height=40, font_px=13).pack(side="right", padx=(theme.s(8), 0))
    return dlg


class PromptDialog(Dialog):
    """单行输入弹窗。"""

    def __init__(self, master, theme, title, hint, on_ok, initial="",
                 ok_text="OK", cancel_text="Cancel"):
        super().__init__(master, theme, 460, 240, title)
        tk.Label(self.content, text=hint, bg=C["surface"], fg=C["muted"],
                 font=theme.f(12), justify="left", anchor="nw",
                 wraplength=theme.s(408)).pack(fill="x", pady=(0, theme.s(10)))
        self.entry = tk.Entry(self.content, font=theme.f(13), relief="flat",
                              bg=C["surface_alt"], fg=C["text"],
                              insertbackground=C["primary"], highlightthickness=1,
                              highlightbackground=C["border"],
                              highlightcolor=C["primary"])
        self.entry.pack(fill="x", ipady=theme.s(8))
        self.entry.insert(0, initial)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self._ok())

        Button(self.footer, theme, ok_text, command=self._ok, kind="primary",
               width=110, height=40, font_px=13).pack(side="right", padx=(theme.s(8), 0))
        Button(self.footer, theme, cancel_text, command=self.close, kind="ghost",
               width=110, height=40, font_px=13).pack(side="right")
        self._on_ok = on_ok

    def _ok(self):
        value = self.entry.get().strip()
        if value:
            self.destroy()
            self._on_ok(value)
