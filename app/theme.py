# -*- coding: utf-8 -*-
"""主题：双套配色（浅色 / 深色）、字体、尺寸缩放（高 DPI 适配）。

C 是全局可变配色字典，切换主题时就地更新，
所有组件在绘制时读取，因此无需重建即可换肤（界面会整体重绘）。
"""

import tkinter.font as tkfont

LIGHT = {
    "bg": "#F5F7FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F4FA",
    "overlay": "#E9EEF6",
    "border": "#E4E9F2",
    "divider": "#EDF0F6",
    "text": "#1B2130",
    "muted": "#77808F",
    "faint": "#A8B0BE",
    "primary": "#3B5BDB",
    "primary_hover": "#4C6EF5",
    "primary_press": "#3450C4",
    "primary_soft": "#EEF2FF",
    "primary_border": "#C9D5F8",
    "success": "#2F9E44",
    "success_hover": "#37B24D",
    "success_soft": "#EBFBEE",
    "success_border": "#CFEBD6",
    "danger": "#E03131",
    "danger_hover": "#F03E3E",
    "danger_soft": "#FFF2F2",
    "danger_border": "#FFD1D1",
    "gold": "#E8940C",
    "gold_soft": "#FFF8E8",
    "gold_border": "#F3DCAE",
    "disabled_bg": "#DCE1EA",
    "disabled_fg": "#9AA3B2",
    "shadow": "#E8EDF6",
    "row_hover": "#F7F9FD",
    "scroll_thumb": "#D9DFEA",
    "hover_soft": "#F4F7FD",
    "press_soft": "#E9EEF9",
    "ghost_hover": "#E7ECF5",
    "on_color": "#FFFFFF",
    "toast_bg": "#1B2130",
    "toast_fg": "#FFFFFF",
}

DARK = {
    "bg": "#0F1218",
    "surface": "#171C26",
    "surface_alt": "#202836",
    "overlay": "#0A0D12",
    "border": "#2A3242",
    "divider": "#232A38",
    "text": "#E9EDF5",
    "muted": "#97A2B4",
    "faint": "#68748A",
    "primary": "#5C7CFA",
    "primary_hover": "#7191FF",
    "primary_press": "#4A66D8",
    "primary_soft": "#222C4A",
    "primary_border": "#36436B",
    "success": "#4ECB71",
    "success_hover": "#63DB84",
    "success_soft": "#16291E",
    "success_border": "#2A4433",
    "danger": "#FF6B6B",
    "danger_hover": "#FF8080",
    "danger_soft": "#31202A",
    "danger_border": "#4A2C36",
    "gold": "#FFC94D",
    "gold_soft": "#2E2718",
    "gold_border": "#4A3F24",
    "disabled_bg": "#252C39",
    "disabled_fg": "#6A7488",
    "shadow": "#0B0E13",
    "row_hover": "#1D2430",
    "scroll_thumb": "#333C4D",
    "hover_soft": "#1E2531",
    "press_soft": "#242C3A",
    "ghost_hover": "#232B38",
    "on_color": "#FFFFFF",
    "toast_bg": "#E9EDF5",
    "toast_fg": "#12151C",
}

PALETTES = {"light": LIGHT, "dark": DARK}

# 全局配色（内容随主题就地替换，保持对象引用不变）
C = dict(LIGHT)

MODES = ("light", "dark")

# 字体候选（按平台习惯排序）
FONT_CANDIDATES = [
    "Microsoft YaHei UI", "Microsoft YaHei",     # Windows
    "PingFang SC", "Hiragino Sans GB",           # macOS
    "Noto Sans CJK SC", "Source Han Sans SC",    # Linux
    "WenQuanYi Micro Hei", "Segoe UI", "Helvetica Neue", "DejaVu Sans",
]

WIN_W, WIN_H = 900, 640


def apply_palette(mode):
    palette = PALETTES.get(mode, LIGHT)
    C.clear()
    C.update(palette)
    return mode


class Theme:
    """集中管理当前主题、字体与缩放后的尺寸。"""

    def __init__(self, root, mode="light"):
        self.root = root
        self.mode = apply_palette(mode if mode in PALETTES else "light")
        self.family = self._pick_family(root)
        self.scale = self._calc_scale(root)
        self._mono = self._pick_mono(root)

    # ------------------------------------------------------------------ 主题

    def is_dark(self):
        return self.mode == "dark"

    def set_mode(self, mode):
        if mode in PALETTES:
            self.mode = apply_palette(mode)
        return self.mode

    def toggle(self):
        return self.set_mode("light" if self.mode == "dark" else "dark")

    # ------------------------------------------------------------------ 内部

    @staticmethod
    def _pick_family(root):
        try:
            available = set(tkfont.families(root))
        except Exception:
            available = set()
        for name in FONT_CANDIDATES:
            if name in available:
                return name
        return "TkDefaultFont"

    @staticmethod
    def _pick_mono(root):
        try:
            available = set(tkfont.families(root))
        except Exception:
            available = set()
        for name in ("Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono"):
            if name in available:
                return name
        return "TkFixedFont"

    @staticmethod
    def _calc_scale(root):
        """按屏幕 DPI 等比放大，保证高分屏下不模糊、不越界。"""
        try:
            dpi = float(root.winfo_fpixels("1i"))
        except Exception:
            dpi = 96.0
        scale = dpi / 96.0
        if scale < 1.15:          # 100%~115% 统一按 1 倍处理，避免半像素发虚
            scale = 1.0
        try:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            scale = min(scale, sw * 0.94 / WIN_W, sh * 0.90 / WIN_H)
        except Exception:
            pass
        return max(1.0, scale)

    # ------------------------------------------------------------------ 工具

    def s(self, px):
        """缩放像素值。"""
        return int(round(px * self.scale))

    def f(self, px, weight="normal", family=None):
        """字体元组；负数表示像素字号，随缩放自动变化。"""
        return (family or self.family, -self.s(px), weight)

    def mono(self, px, weight="normal"):
        return (self._mono, -self.s(px), weight)

    def window_size(self):
        return self.s(WIN_W), self.s(WIN_H)

    def center(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2 - self.s(16))
        return x, y


def mix(hex_color, other, ratio):
    """颜色混合：ratio=0 返回原色，1 返回另一色。"""
    a = hex_color.lstrip("#")
    b = other.lstrip("#")
    out = []
    for i in (0, 2, 4):
        av = int(a[i:i + 2], 16)
        bv = int(b[i:i + 2], 16)
        out.append(int(round(av + (bv - av) * ratio)))
    return "#%02X%02X%02X" % tuple(out)


def shift(hex_color, amount):
    """变亮(正)/变暗(负)。"""
    target = "#FFFFFF" if amount > 0 else "#000000"
    return mix(hex_color, target, abs(amount))
