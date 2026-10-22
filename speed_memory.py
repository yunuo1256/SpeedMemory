import os
import sys


def _hide_console():
    """Windows 下隐藏随程序出现的控制台窗口（源码运行 / 非 windowed 打包均有效）。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)      # SW_HIDE
    except Exception:
        pass


def _enable_high_dpi():
    """Windows 高 DPI 感知，避免界面发虚。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def main():
    _hide_console()
    _enable_high_dpi()
    # 允许源码目录直接运行（python speed_memory.py）
    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)
    from app.views import run
    run()


if __name__ == "__main__":
    main()
