# -*- coding: utf-8 -*-
"""界面层：主页、答题、完成、题本选择、编辑、回收站、关于。"""

import os
import random
import time
import webbrowser

import tkinter as tk
from tkinter import filedialog

from . import storage
from .i18n import I18n, LANG_LABELS, LANGS
from .theme import C, Theme
from .widgets import (Button, Card, Chip, Dialog, IconButton, ListRow,
                      LogoMark, ProgressBar, PromptDialog, ScrollFrame,
                      Segmented, TextPanel, ThemeToggle, Toast, message_dialog)


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        storage.ensure_dirs()

        self.settings = storage.load_settings()
        self.i18n = I18n(self.settings.get("language", "en"))
        self.T = Theme(self, self.settings.get("theme", "light"))

        self.withdraw()
        self.configure(bg=C["bg"])
        w, h = self.T.window_size()
        x, y = self.T.center(w, h)
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self.resizable(False, False)
        self._apply_icon()

        self.body = tk.Frame(self, bg=C["bg"])
        self.body.pack(fill="both", expand=True)
        self.toast = Toast(self, self.T)

        # 运行状态
        self.screen = "start"
        self.current_bank = self.settings.get("last_bank")
        if self.current_bank and self.current_bank not in storage.list_banks():
            self.current_bank = None
        self.quiz = None
        self.editor = None
        self.trash_sel = None
        self._timer_job = None
        self._modal = None

        self.deiconify()
        self.show_start()
        self.bind("<Escape>", self._on_escape)
        self.bind("<space>", self._on_space)
        self.bind("<Return>", self._on_space)
        self.bind("<Left>", self._on_left)
        self.bind("<s>", self._on_star)
        self.bind("<S>", self._on_star)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(250, self._startup_check)

    # ------------------------------------------------------------ 基础设施

    def t(self, key, **kw):
        return self.i18n(key, **kw)

    def _apply_icon(self):
        ico = storage.resource_path("icon.ico")
        try:
            if os.path.isfile(ico):
                self.iconbitmap(ico)
        except tk.TclError:
            pass
        png = storage.resource_path(os.path.join("assets", "icon.png"))
        try:
            if os.path.isfile(png):
                self._icon_img = tk.PhotoImage(file=png)
                self.iconphoto(True, self._icon_img)
        except tk.TclError:
            pass

    def _save_settings(self):
        self.settings["language"] = self.i18n.lang
        self.settings["last_bank"] = self.current_bank
        self.settings["theme"] = self.T.mode
        storage.save_settings(self.settings)

    def _notify(self, message):
        """轻提示：有弹窗时显示在顶部，避免遮挡弹窗按钮。"""
        self.toast.show(message, top=self._modal is not None)

    def clear_body(self):
        self._stop_timer()
        for w in self.body.winfo_children():
            w.destroy()
        # 同步容器底色（换肤后新组件通过 parent_bg 取色）
        self.configure(bg=C["bg"])
        self.body.configure(bg=C["bg"])
        # 让 body 重新铺满父容器，触发整块区域重绘（避免换肤/换页残留旧像素）
        self.body.pack_forget()
        self.body.pack(fill="both", expand=True)
        if self._modal is not None:
            try:
                self._modal.destroy()
            except Exception:
                pass
            self._modal = None

    def _on_close(self):
        self._stop_timer()
        self.destroy()

    def _on_escape(self, _e=None):
        if self._modal is not None:
            return
        if self.screen == "quiz":
            self._confirm_exit_quiz()
        elif self.screen in ("edit", "trash", "about"):
            self.show_start()

    def _on_space(self, _e=None):
        if self._modal is not None or self.screen != "quiz":
            return
        self._quiz_answer_or_next()

    def _on_left(self, _e=None):
        if self._modal is not None or self.screen != "quiz":
            return
        self._quiz_prev()

    def _on_star(self, _e=None):
        if self._modal is not None or self.screen != "quiz":
            return
        self._toggle_favorite()

    def _open_modal(self, dialog):
        self._modal = dialog
        dialog.bind("<Destroy>", self._modal_destroyed, add="+")
        return dialog

    def _modal_destroyed(self, event):
        if event.widget is self._modal:
            self._modal = None

    # ------------------------------------------------------------ 公共头部

    def _header(self, parent, title, back=None, with_lang=True, compact=False):
        bar = tk.Frame(parent, bg=C["bg"])
        bar.pack(fill="x", padx=self.T.s(26), pady=(self.T.s(14), self.T.s(6)))

        left = tk.Frame(bar, bg=C["bg"])
        left.pack(side="left")
        if back is not None:
            IconButton(left, self.T, "←", command=back, size=32,
                       bg=C["bg"], fg=C["muted"]).pack(side="left", padx=(0, self.T.s(4)))
        else:
            LogoMark(left, self.T, size=26, bg=C["bg"]).pack(side="left",
                                                             padx=(0, self.T.s(9)))
        tk.Label(left, text=title, bg=C["bg"], fg=C["text"],
                 font=self.T.f(15, "bold")).pack(side="left")

        right = tk.Frame(bar, bg=C["bg"])
        right.pack(side="right")
        ThemeToggle(right, self.T, self.T.is_dark(), command=self._toggle_theme,
                    size=32, bg=C["bg"]).pack(side="right", padx=(self.T.s(6), 0))
        if with_lang:
            Segmented(right, self.T, [(k, LANG_LABELS[k]) for k in LANGS],
                      self.i18n.lang, self._set_language,
                      width=132, height=30, bg=C["bg"]).pack(side="right")
        return bar, left, right

    def _toggle_theme(self):
        mode = self.T.toggle()
        self.settings["theme"] = mode
        storage.save_settings(self.settings)
        self.configure(bg=C["bg"])
        self._rerender()
        self._force_repaint()

    def _force_repaint(self):
        """换肤后强制整窗重绘，避免残留旧配色（无合成器的环境下尤其明显）。"""
        try:
            self.update_idletasks()
            w, h = self.winfo_width(), self.winfo_height()
            self.geometry("%dx%d" % (w, max(1, h - 1)))
            self.update_idletasks()
            self.geometry("%dx%d" % (w, h))
            self.update_idletasks()
        except tk.TclError:
            pass

    def _set_language(self, lang):
        self.i18n.set(lang)
        self._save_settings()
        self._rerender()

    def _rerender(self):
        if self.screen == "start":
            self.show_start()
        elif self.screen == "quiz":
            self.show_quiz()
        elif self.screen == "complete":
            self.show_complete()
        elif self.screen == "edit":
            self.show_editor()
        elif self.screen == "trash":
            self.show_trash()
        elif self.screen == "about":
            self.show_about()

    # ------------------------------------------------------------ 启动检查

    def _startup_check(self):
        if not storage.list_banks():
            self._empty_library_dialog()

    def _empty_library_dialog(self):
        self._open_modal(message_dialog(
            self.body, self.T,
            self.t("empty_title"), self.t("empty_msg"),
            [(self.t("close"), "ghost", None),
             (self.t("add"), "primary", self._import_banks)],
            width=460, height=196, text_color=C["text"], font_px=13))

    def _import_banks(self):
        message_dialog(
            self.body, self.T, self.t("notice"), self.t("format_notice"),
            [(self.t("ok"), "primary", self._pick_files)],
            width=520, height=246, text_color=C["text"], font_px=12)

    def _pick_files(self):
        files = filedialog.askopenfilenames(
            parent=self, title=self.t("add_bank"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not files:
            return
        imported = storage.import_bank_files(files)
        if imported:
            if self.current_bank is None:
                self.current_bank = imported[0]
            self._save_settings()
            self._notify(self.t("saved"))
        self._rerender()

    # ------------------------------------------------------------ 主页

    def show_start(self):
        self.screen = "start"
        self.quiz = None          # 回到主页即视为结束本次答题，避免残留状态
        self.clear_body()
        self.title("%s v%s" % (self.t("app_title"), storage.APP_VERSION))
        banks = storage.list_banks()

        self._header(self.body, self.t("app_title"), with_lang=True)

        wrap = tk.Frame(self.body, bg=C["bg"])
        wrap.pack(fill="both", expand=True)

        center = tk.Frame(wrap, bg=C["bg"])
        center.pack(expand=True)

        # 主标题
        tk.Label(center, text=self.t("app_title"), bg=C["bg"], fg=C["text"],
                 font=self.T.f(42, "bold")).pack(pady=(0, self.T.s(6)))
        tk.Label(center, text=self.t("subtitle"), bg=C["bg"], fg=C["muted"],
                 font=self.T.f(13)).pack(pady=(0, self.T.s(26)))

        # 当前题本卡片
        card = Card(center, self.T, radius=14, padding=0)
        card.configure(width=self.T.s(420), height=self.T.s(86))
        card.pack(pady=(0, self.T.s(24)))
        card.pack_propagate(False)
        row = tk.Frame(card.inner, bg=C["surface"])
        row.pack(fill="both", expand=True, padx=self.T.s(20), pady=self.T.s(12))
        left = tk.Frame(row, bg=C["surface"])
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text=self.t("current_bank"), bg=C["surface"], fg=C["faint"],
                 font=self.T.f(10), anchor="w").pack(fill="x")
        name = self.current_bank if self.current_bank else self.t("no_bank")
        tk.Label(left, text=name, bg=C["surface"],
                 fg=C["text"] if self.current_bank else C["faint"],
                 font=self.T.f(16, "bold"), anchor="w").pack(fill="x")
        if self.current_bank:
            n = storage.count_valid(storage.bank_path(self.current_bank))
            Chip(row, self.T, self.t("total_label"), str(n), width=92, height=30,
                 bg_color=C["primary_soft"], fg=C["primary"]).pack(side="right",
                                                                   pady=self.T.s(8))

        # 开始按钮
        Button(center, self.T, self.t("start_btn"), command=self._start_from_home,
               kind="primary", width=250, height=56, radius=14,
               font_px=17).pack(pady=(0, self.T.s(18)))

        # 功能按钮
        actions = tk.Frame(center, bg=C["bg"])
        actions.pack()
        for text, cb, kind in (
                (self.t("switch_bank"), self._open_bank_selector, "secondary"),
                (self.t("add_bank"), self._import_banks, "outline"),
                (self.t("trash_btn"), self.show_trash, "outline"),
                (self.t("about_btn"), self.show_about, "outline")):
            Button(actions, self.T, text, command=cb, kind=kind,
                   width=126, height=40, font_px=12, bold=False
                   ).pack(side="left", padx=self.T.s(5))

        banks_text = (self.t("banks_total_one") if len(banks) == 1
                      else self.t("banks_total", n=len(banks)))
        tk.Label(wrap, text="%s · %s" % (banks_text,
                                         self.t("version", v=storage.APP_VERSION)),
                 bg=C["bg"], fg=C["faint"], font=self.T.f(11)
                 ).pack(side="bottom", pady=(0, self.T.s(10)))

        total_q = sum(storage.count_valid(storage.bank_path(n)) for n in banks)
        fav_count = len(storage.favorite_keys())
        stats = tk.Frame(wrap, bg=C["bg"])
        stats.pack(side="bottom", pady=(0, self.T.s(12)))
        for value, label in ((len(banks), self.t("stat_banks")),
                             (total_q, self.t("stat_questions")),
                             (fav_count, self.t("stat_favorites"))):
            tile = TextPanel(stats, self.T, radius=12, padding=8, height=74,
                             stack_sub=True, sub_below=True, shadow=False,
                             fill=C["surface"], border=C["border"])
            tile.configure(width=self.T.s(126))
            tile.pack(side="left", padx=self.T.s(6))
            tile.set(text=str(value), font_px=21, sub=label, sub_fg=C["muted"])

    def _start_from_home(self):
        banks = storage.list_banks()
        if not banks:
            self._empty_library_dialog()
            return
        if not self.current_bank or self.current_bank not in banks:
            # 未选择题本：先提示去选择，绝不静默开始答题
            if self.current_bank is not None:
                self.current_bank = None
                self._save_settings()
                self.show_start()
            self._need_bank_dialog()
            return
        self._begin_quiz(self.current_bank)

    def _need_bank_dialog(self):
        self._open_modal(message_dialog(
            self.body, self.T, self.t("pick_bank_title"), self.t("pick_bank_msg"),
            [(self.t("cancel"), "ghost", None),
             (self.t("go_select"), "primary", self._open_bank_selector)],
            width=460, height=204, icon="!", icon_color=C["gold"],
            text_color=C["text"]))

    # ------------------------------------------------------------ 题本选择

    def _open_bank_selector(self):
        banks = storage.list_banks()
        if not banks:
            self._empty_library_dialog()
            return

        sel = {"index": 0 if self.current_bank not in banks else banks.index(self.current_bank),
               "rows": []}

        width = 620
        height = max(330, min(540, 260 + 58 * len(banks)))
        dlg = Dialog(self.body, self.T, width, height, self.t("select_bank_title"),
                     on_close=None)
        self._open_modal(dlg)

        info = tk.Label(dlg.content,
                        text=(self.t("banks_total_one") if len(banks) == 1
                              else self.t("banks_total", n=len(banks))),
                        bg=C["surface"], fg=C["muted"], font=self.T.f(11), anchor="w")
        info.pack(fill="x", pady=(0, self.T.s(8)))

        scroller = ScrollFrame(dlg.content, self.T, bg=C["surface"])
        scroller.pack(fill="both", expand=True)

        def render_rows():
            scroller.clear()
            sel["rows"] = []
            for i, name in enumerate(banks):
                count = storage.count_valid(storage.bank_path(name))
                meta = self.t("n_questions", n=count)
                if name == storage.LIKE_NAME:
                    meta = "★ " + meta
                row = ListRow(scroller.inner, self.T, name, meta,
                              on_click=lambda idx=i: select(idx),
                              selected=(i == sel["index"]), height=58,
                              avatar=("★" if name == storage.LIKE_NAME else name[:1]))

                def on_double(idx=i):
                    select(idx)
                    choose()

                row._double = lambda e=None, f=on_double: f()
                row.pack(fill="x")
                tk.Frame(scroller.inner, height=1, bg=C["divider"]).pack(fill="x")
                sel["rows"].append(row)

        def select(idx):
            sel["index"] = idx
            for i, row in enumerate(sel["rows"]):
                row.set_selected(i == idx)

        def choose():
            idx = sel["index"]
            if idx is None or idx >= len(banks):
                self._notify(self.t("no_selection"))
                return
            self.current_bank = banks[idx]
            self._save_settings()
            dlg.destroy()
            # 只切换题本并返回主页；是否开始答题由用户再点「开始答题」决定
            self.show_start()
            self._notify(self.t("bank_selected", n=self.current_bank))

        def edit_current():
            idx = sel["index"]
            if idx is None:
                self._notify(self.t("no_selection"))
                return
            name = banks[idx]
            dlg.destroy()
            self._open_editor(name)

        def delete_current():
            idx = sel["index"]
            if idx is None:
                self._notify(self.t("no_selection"))
                return
            name = banks[idx]

            def do_delete():
                if storage.delete_bank(name):
                    if self.current_bank == name:
                        self.current_bank = None
                        self._save_settings()
                    banks.remove(name)
                    sel["index"] = 0 if banks else None
                    if not banks:
                        dlg.destroy()
                        self._empty_library_dialog()
                        return
                    render_rows()
                    self._refresh_home_hint()

            self._open_modal(message_dialog(
                self.body, self.T, self.t("delete_bank"),
                self.t("delete_bank_confirm", n=name),
                [(self.t("cancel"), "ghost", None),
                 (self.t("delete"), "danger", do_delete)],
                width=440, height=216, icon="!", icon_color=C["danger"],
                text_color=C["text"], font_px=12))

        def new_bank():
            PromptDialog(self.body, self.T, self.t("new_bank"),
                         self.t("new_bank_hint"), lambda value: create(value),
                         ok_text=self.t("ok"), cancel_text=self.t("cancel"))

        def create(value):
            name = value if value.lower().endswith(".txt") else value + ".txt"
            if os.path.exists(storage.bank_path(name)):
                self._notify(self.t("bank_exists"))
                return
            created = storage.create_bank(value)
            banks.append(created)
            banks.sort(key=lambda n: (n == storage.LIKE_NAME, n.lower()))
            sel["index"] = banks.index(created)
            dlg.destroy()
            self._open_editor(created)

        render_rows()

        # 底部按钮
        Button(dlg.footer, self.T, self.t("select"), command=choose, kind="primary",
               width=104, height=42, font_px=13).pack(side="right", padx=(self.T.s(8), 0))
        Button(dlg.footer, self.T, self.t("edit_bank"), command=edit_current, kind="secondary",
               width=96, height=42, font_px=13).pack(side="right", padx=(self.T.s(8), 0))
        Button(dlg.footer, self.T, self.t("delete_bank"), command=delete_current, kind="danger_soft",
               width=96, height=42, font_px=13).pack(side="right", padx=(self.T.s(8), 0))
        Button(dlg.footer, self.T, self.t("new_bank"), command=new_bank, kind="ghost",
               width=112, height=42, font_px=13).pack(side="left")

    def _refresh_home_hint(self):
        if self.screen == "start":
            self.show_start()

    # ------------------------------------------------------------ 答题

    def _begin_quiz(self, name):
        items = storage.load_bank(storage.bank_path(name))
        if not items:
            self._open_modal(message_dialog(
                self.body, self.T, self.t("notice"), self.t("empty_bank_file"),
                [(self.t("ok"), "primary", None)],
                width=420, height=196, icon="!", icon_color=C["gold"]))
            return
        shuffled = items[:]
        random.shuffle(shuffled)
        self.quiz = {
            "name": name,
            "items": shuffled,
            "idx": 0,
            "revealed": [False] * len(shuffled),
            "start": time.monotonic(),
            "elapsed": 0.0,
        }
        self.current_bank = name
        self._save_settings()
        self.show_quiz()

    def show_quiz(self):
        self.screen = "quiz"
        self.clear_body()
        self.title("%s · %s" % (self.t("app_title"), self.quiz["name"]))
        quiz = self.quiz

        bar, left, right = self._header(self.body, quiz["name"],
                                        back=self._confirm_exit_quiz, with_lang=True)

        self._chip_time = Chip(right, self.T, self.t("time_label"), "00:00",
                               width=104, height=30, bg=C["bg"])
        self._chip_total = Chip(right, self.T, self.t("total_label"), str(len(quiz["items"])),
                                width=92, height=30, bg=C["bg"])
        self._chip_done = Chip(right, self.T, self.t("answered_label"), "0",
                               width=88, height=30, bg=C["bg"],
                               bg_color=C["primary_soft"], fg=C["primary"])
        self._chip_done.pack(side="right", padx=(0, self.T.s(12)))
        self._chip_total.pack(side="right", padx=(0, self.T.s(6)))
        self._chip_time.pack(side="right", padx=(0, self.T.s(6)))

        # 进度条 + 百分比
        prow = tk.Frame(self.body, bg=C["bg"])
        prow.pack(fill="x", padx=self.T.s(26), pady=(self.T.s(6), self.T.s(12)))
        self._pct_label = tk.Label(prow, text="0%", bg=C["bg"], fg=C["faint"],
                                   font=self.T.f(10))
        self._pct_label.pack(side="right", padx=(self.T.s(10), 0))
        self._progress = ProgressBar(prow, self.T, height=6, bg=C["bg"])
        self._progress.pack(side="left", fill="x", expand=True, pady=self.T.s(5))

        # 题目面板（圆角 + 居中问题）
        self._q_panel = TextPanel(self.body, self.T, radius=18, padding=34,
                                  fill=C["surface"], shadow=True)
        self._q_panel.pack(fill="both", expand=True, padx=self.T.s(26), pady=(0, self.T.s(12)))

        # 答案面板（显答后整块变绿）
        self._a_panel = TextPanel(self.body, self.T, radius=16, padding=26,
                                  fill=C["surface_alt"], border=C["border"],
                                  shadow=False, height=136)
        self._a_panel.pack(fill="x", padx=self.T.s(26))

        # 操作按钮（位置固定，切换文字不移动）
        actions = tk.Frame(self.body, bg=C["bg"])
        actions.pack(pady=(self.T.s(14), 0))
        self._fav_btn = Button(actions, self.T, "☆ " + self.t("fav"),
                               command=self._toggle_favorite, kind="gold",
                               width=136, height=44, font_px=12)
        self._fav_btn.pack(side="left", padx=self.T.s(7))
        self._prev_btn = Button(actions, self.T, self.t("prev_btn"),
                                command=self._quiz_prev, kind="outline",
                                width=136, height=44, font_px=12)
        self._prev_btn.pack(side="left", padx=self.T.s(7))
        self._answer_btn = Button(actions, self.T, self.t("answer_btn"),
                                  command=self._quiz_answer_or_next, kind="primary",
                                  width=196, height=44, font_px=14)
        self._answer_btn.pack(side="left", padx=self.T.s(7))

        tk.Label(self.body, text=self.t("hint_keys"), bg=C["bg"], fg=C["faint"],
                 font=self.T.f(10)).pack(pady=(self.T.s(8), self.T.s(10)))

        self._render_quiz_state()
        self._start_timer()
        self.focus_set()

    def _fit_font(self, text, sizes):
        for limit, px in sizes:
            if len(text) <= limit:
                return px
        return sizes[-1][1]

    def _render_quiz_state(self):
        quiz = self.quiz
        n = len(quiz["items"])
        idx = quiz["idx"]
        q, a = quiz["items"][idx]
        revealed = quiz["revealed"][idx]

        qpx = self._fit_font(q, [(26, 26), (60, 22), (120, 18), (240, 15)])
        self._q_panel.set(text=q, font_px=qpx, bold=True,
                          sub=self.t("question_of", i=idx + 1, n=n))

        if revealed:
            apx = self._fit_font(a, [(40, 22), (90, 18), (180, 14), (400, 12)])
            self._a_panel.set(text=a, fg=C["success"], fill=C["success_soft"],
                              border=C["success_border"], font_px=apx, bold=True)
            self._answer_btn.set_text(self.t("next_btn"))
        else:
            self._a_panel.set(text=self.t("tap_to_reveal"), fg=C["faint"],
                              fill=C["surface_alt"], border=C["border"],
                              font_px=12, bold=False)
            self._answer_btn.set_text(self.t("answer_btn"))

        self._prev_btn.set_enabled(idx > 0)
        fav = (q, a) in storage.favorite_keys()
        self._fav_btn.set_text(("★ " if fav else "☆ ") +
                               (self.t("unfav") if fav else self.t("fav")),
                               kind="gold_soft" if fav else "gold")

        done = sum(1 for r in quiz["revealed"] if r)
        self._chip_done.set(value=str(done))
        self._chip_total.set(value=str(n))
        ratio = (idx + 1) / float(n) if n else 0
        self._progress.set(ratio)
        self._pct_label.configure(text="%d%%" % int(round(ratio * 100)))
        self._update_clock()

    def _quiz_answer_or_next(self):
        quiz = self.quiz
        if quiz is None:
            return
        if not quiz["revealed"][quiz["idx"]]:
            quiz["revealed"][quiz["idx"]] = True
            self._render_quiz_state()
        else:
            if quiz["idx"] >= len(quiz["items"]) - 1:
                self._finish_quiz()
            else:
                quiz["idx"] += 1
                self._render_quiz_state()

    def _quiz_prev(self):
        quiz = self.quiz
        if quiz and quiz["idx"] > 0:
            quiz["idx"] -= 1
            self._render_quiz_state()

    def _toggle_favorite(self):
        quiz = self.quiz
        if quiz is None:
            return
        item = quiz["items"][quiz["idx"]]
        favs = storage.favorite_keys()
        now_fav = item not in favs
        storage.set_favorite(item, now_fav)
        self._notify(self.t("fav_added") if now_fav else self.t("fav_removed"))
        self._render_quiz_state()

    def _confirm_exit_quiz(self):
        if self.quiz is None:
            self.show_start()
            return

        def leave():
            self._stop_timer()
            self.quiz = None
            self.show_start()

        self._open_modal(message_dialog(
            self.body, self.T, self.t("exit_quiz_title"), self.t("exit_quiz_msg"),
            [(self.t("keep_going"), "ghost", None),
             (self.t("exit_quiz_ok"), "danger", leave)],
            width=430, height=212, icon="!", icon_color=C["gold"],
            text_color=C["text"]))

    # -- 计时
    def _start_timer(self):
        self._stop_timer()
        self._tick()

    def _tick(self):
        if self.screen != "quiz" or self.quiz is None:
            self._timer_job = None
            return
        self._update_clock()
        self._timer_job = self.after(1000, self._tick)

    def _update_clock(self):
        if self.quiz is None or not hasattr(self, "_chip_time"):
            return
        elapsed = time.monotonic() - self.quiz["start"]
        self._chip_time.set(value=storage.fmt_time(elapsed))

    def _stop_timer(self):
        if self._timer_job is not None:
            try:
                self.after_cancel(self._timer_job)
            except Exception:
                pass
            self._timer_job = None

    # ------------------------------------------------------------ 完成

    def _finish_quiz(self):
        self._stop_timer()
        elapsed = time.monotonic() - self.quiz["start"]
        self.quiz["elapsed"] = elapsed
        self.show_complete()

    def show_complete(self):
        self.screen = "complete"
        self.clear_body()
        self.title("%s · %s" % (self.t("app_title"), self.t("done_title")))
        quiz = self.quiz
        elapsed = quiz.get("elapsed") or (time.monotonic() - quiz["start"])
        total = len(quiz["items"])

        self._header(self.body, self.t("app_title"), with_lang=True)

        center = tk.Frame(self.body, bg=C["bg"])
        center.pack(expand=True)

        ring = tk.Canvas(center, width=self.T.s(84), height=self.T.s(84),
                         bg=C["bg"], highlightthickness=0)
        ring.create_oval(2, 2, self.T.s(82), self.T.s(82), fill=C["success_soft"], outline="")
        ring.create_text(self.T.s(42), self.T.s(42), text="✓",
                         fill=C["success"], font=self.T.f(34, "bold"))
        ring.pack(pady=(0, self.T.s(10)))

        tk.Label(center, text=self.t("done_title"), bg=C["bg"], fg=C["text"],
                 font=self.T.f(26, "bold")).pack()
        tk.Label(center, text=self.t("done_sub", n=total), bg=C["bg"], fg=C["muted"],
                 font=self.T.f(12)).pack(pady=(self.T.s(4), self.T.s(18)))

        time_card = TextPanel(center, self.T, radius=16, padding=20,
                              height=132, shadow=True, stack_sub=True)
        time_card.configure(width=self.T.s(320))
        time_card.pack(pady=(0, self.T.s(26)))
        time_card.set(sub=self.t("done_time"), text=storage.fmt_time(elapsed),
                      fg=C["primary"], font_px=34)

        row = tk.Frame(center, bg=C["bg"])
        row.pack()
        Button(row, self.T, self.t("again"), command=self._restart_quiz, kind="primary",
               width=150, height=48, font_px=14).pack(side="left", padx=self.T.s(6))
        Button(row, self.T, self.t("back_home"), command=self.show_start, kind="secondary",
               width=150, height=48, font_px=14).pack(side="left", padx=self.T.s(6))

    def _restart_quiz(self):
        if self.quiz:
            self._begin_quiz(self.quiz["name"])

    # ------------------------------------------------------------ 编辑题本

    def _open_editor(self, name):
        self.editor = {
            "name": name,
            "items": storage.load_bank(storage.bank_path(name)),
            "selected": None,
            "query": "",
        }
        self.show_editor()

    def show_editor(self):
        self.screen = "edit"
        self.clear_body()
        ed = self.editor
        self.title("%s · %s" % (self.t("app_title"), self.t("edit_bank")))

        self._header(self.body, self.t("edit_title", name=ed["name"]),
                     back=self.show_start, with_lang=True)

        body = tk.Frame(self.body, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=self.T.s(26),
                  pady=(self.T.s(2), self.T.s(18)))

        # 左：搜索 + 列表
        left = Card(body, self.T, radius=14, padding=0)
        left.configure(width=self.T.s(370))
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        linner = tk.Frame(left.inner, bg=C["surface"])
        linner.pack(fill="both", expand=True, padx=self.T.s(14), pady=self.T.s(12))

        search_wrap = tk.Frame(linner, bg=C["surface_alt"])
        search_wrap.pack(fill="x", pady=(0, self.T.s(8)))
        self._search = tk.Entry(search_wrap, bd=0, relief="flat", bg=C["surface_alt"],
                                fg=C["text"], font=self.T.f(12),
                                insertbackground=C["primary"], highlightthickness=1,
                                highlightbackground=C["surface_alt"],
                                highlightcolor=C["primary"])
        self._search.pack(fill="x", padx=self.T.s(10), pady=self.T.s(7))
        self._search.insert(0, self.t("search_ph"))
        self._search.configure(fg=C["faint"])
        self._search.bind("<FocusIn>", self._search_focus_in)
        self._search.bind("<FocusOut>", self._search_focus_out)
        self._search.bind("<KeyRelease>", self._search_changed)

        self._ed_list = ScrollFrame(linner, self.T, bg=C["surface"])
        self._ed_list.pack(fill="both", expand=True)

        # 右：表单
        right = Card(body, self.T, radius=14, padding=0)
        right.pack(side="left", fill="both", expand=True, padx=(self.T.s(16), 0))
        rinner = tk.Frame(right.inner, bg=C["surface"])
        rinner.pack(fill="both", expand=True, padx=self.T.s(20), pady=self.T.s(18))

        self._ed_hint = tk.Label(rinner, text=self.t("editor_empty"), bg=C["surface"],
                                 fg=C["faint"], font=self.T.f(11), justify="left", anchor="w")
        self._ed_hint.pack(fill="x", pady=(0, self.T.s(10)))

        tk.Label(rinner, text=self.t("question"), bg=C["surface"], fg=C["muted"],
                 font=self.T.f(11, "bold"), anchor="w").pack(fill="x")
        self._q_edit = self._make_text(rinner, height=4, font_px=13)

        tk.Label(rinner, text=self.t("answer_label"), bg=C["surface"], fg=C["muted"],
                 font=self.T.f(11, "bold"), anchor="w").pack(fill="x", pady=(self.T.s(10), 0))
        self._a_edit = self._make_text(rinner, height=6, font_px=13)

        btns = tk.Frame(rinner, bg=C["surface"])
        btns.pack(fill="x", pady=(self.T.s(14), 0))
        Button(btns, self.T, self.t("add_q"), command=self._editor_add, kind="primary",
               width=104, height=42, font_px=12).pack(side="left", padx=(0, self.T.s(8)))
        Button(btns, self.T, self.t("save_q"), command=self._editor_save, kind="secondary",
               width=118, height=42, font_px=12).pack(side="left", padx=(0, self.T.s(8)))
        Button(btns, self.T, self.t("delete_q"), command=self._editor_delete, kind="danger_soft",
               width=96, height=42, font_px=12).pack(side="left")

        self._render_editor_list()

    def _make_text(self, parent, height=5, font_px=13):
        wrap = tk.Frame(parent, bg=C["surface_alt"])
        wrap.pack(fill="x", pady=(self.T.s(4), 0))
        txt = tk.Text(wrap, height=height, wrap="word", bd=0, relief="flat",
                      bg=C["surface_alt"], fg=C["text"], font=self.T.f(font_px),
                      insertbackground=C["primary"], highlightthickness=1,
                      highlightbackground=C["border"], highlightcolor=C["primary"],
                      padx=self.T.s(10), pady=self.T.s(8))
        txt.pack(fill="x")
        return txt

    def _search_focus_in(self, _e):
        if self._search.get() == self.t("search_ph"):
            self._search.delete(0, "end")
            self._search.configure(fg=C["text"])

    def _search_focus_out(self, _e):
        if not self._search.get().strip():
            self._search.delete(0, "end")
            self._search.insert(0, self.t("search_ph"))
            self._search.configure(fg=C["faint"])

    def _search_changed(self, _e=None):
        value = self._search.get()
        self.editor["query"] = "" if value == self.t("search_ph") else value.strip().lower()
        self._render_editor_list()

    def _filtered_indices(self):
        ed = self.editor
        q = ed["query"]
        if not q:
            return list(range(len(ed["items"])))
        return [i for i, (question, answer) in enumerate(ed["items"])
                if q in question.lower() or q in answer.lower()]

    def _render_editor_list(self):
        ed = self.editor
        self._ed_list.clear()
        indices = self._filtered_indices()
        if not indices:
            tk.Label(self._ed_list.inner, text=self.t("no_selection") if ed["items"] else self.t("editor_empty"),
                     bg=C["surface"], fg=C["faint"], font=self.T.f(11),
                     justify="left", wraplength=self.T.s(300)).pack(pady=self.T.s(20), padx=self.T.s(8))
            return
        for i in indices:
            q, a = ed["items"][i]
            row = ListRow(self._ed_list.inner, self.T, q, a[:40] + ("…" if len(a) > 40 else ""),
                          on_click=lambda idx=i: self._select_editor_item(idx),
                          selected=(ed["selected"] == i), height=60)
            row.pack(fill="x")
            tk.Frame(self._ed_list.inner, height=1, bg=C["divider"]).pack(fill="x")

    def _select_editor_item(self, idx):
        ed = self.editor
        ed["selected"] = idx
        q, a = ed["items"][idx]
        self._q_edit.delete("1.0", "end")
        self._q_edit.insert("1.0", q)
        self._a_edit.delete("1.0", "end")
        self._a_edit.insert("1.0", a)
        self._ed_hint.configure(text=self.t("question_of", i=idx + 1, n=len(ed["items"])))
        self._render_editor_list()

    def _editor_values(self):
        q = self._q_edit.get("1.0", "end").strip()
        a = self._a_edit.get("1.0", "end").strip()
        if not q or not a:
            self._notify(self.t("q_required"))
            return None
        return (q, a)

    def _persist_editor(self):
        ed = self.editor
        storage.save_bank(storage.bank_path(ed["name"]), ed["items"])
        self._notify(self.t("saved"))

    def _editor_add(self):
        values = self._editor_values()
        if values is None:
            return
        ed = self.editor
        ed["items"].append(values)
        ed["selected"] = len(ed["items"]) - 1
        self._persist_editor()
        self._q_edit.delete("1.0", "end")
        self._a_edit.delete("1.0", "end")
        self.editor["query"] = ""
        self._reset_search()
        self._render_editor_list()

    def _editor_save(self):
        ed = self.editor
        if ed["selected"] is None:
            self._notify(self.t("no_selection"))
            return
        values = self._editor_values()
        if values is None:
            return
        ed["items"][ed["selected"]] = values
        self._persist_editor()
        self._render_editor_list()

    def _editor_delete(self):
        ed = self.editor
        idx = ed["selected"]
        if idx is None:
            self._notify(self.t("no_selection"))
            return
        item = ed["items"].pop(idx)
        storage.move_question_to_trash(ed["name"], item)
        storage.save_bank(storage.bank_path(ed["name"]), ed["items"])
        ed["selected"] = min(idx, len(ed["items"]) - 1) if ed["items"] else None
        self._q_edit.delete("1.0", "end")
        self._a_edit.delete("1.0", "end")
        self._notify(self.t("question_deleted"))
        self._render_editor_list()

    def _reset_search(self):
        try:
            self._search.delete(0, "end")
            self._search.insert(0, self.t("search_ph"))
            self._search.configure(fg=C["faint"])
        except tk.TclError:
            pass

    # ------------------------------------------------------------ 回收站

    def show_trash(self):
        self.screen = "trash"
        self.clear_body()
        self.title("%s · %s" % (self.t("app_title"), self.t("trash_title")))

        self._header(self.body, self.t("trash_title"), back=self.show_start, with_lang=True)

        entries = storage.trash_entries()
        if self.trash_sel is not None and self.trash_sel >= len(entries):
            self.trash_sel = None

        body = tk.Frame(self.body, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=self.T.s(26),
                  pady=(self.T.s(2), self.T.s(14)))

        left = Card(body, self.T, radius=14, padding=0)
        left.configure(width=self.T.s(420))
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        linner = tk.Frame(left.inner, bg=C["surface"])
        linner.pack(fill="both", expand=True, padx=self.T.s(14), pady=self.T.s(12))

        tk.Label(linner, text=self.t("trash_hint"), bg=C["surface"], fg=C["muted"],
                 font=self.T.f(11), anchor="w").pack(fill="x", pady=(0, self.T.s(8)))

        scroller = ScrollFrame(linner, self.T, bg=C["surface"])
        scroller.pack(fill="both", expand=True)

        if not entries:
            empty = tk.Frame(scroller.inner, bg=C["surface"])
            empty.pack(pady=self.T.s(56))
            tk.Label(empty, text="—", bg=C["surface"], fg=C["border"],
                     font=self.T.f(28)).pack()
            tk.Label(empty, text=self.t("trash_empty"), bg=C["surface"], fg=C["faint"],
                     font=self.T.f(12)).pack(pady=(self.T.s(2), 0))
        else:
            for i, entry in enumerate(entries):
                if entry["kind"] == "bank":
                    title = entry["file"]
                    meta = "%s · %s" % (self.t("kind_bank"),
                                        self.t("n_questions", n=entry["count"]))
                else:
                    title = entry["question"]
                    meta = "%s · %s %s" % (self.t("kind_question"),
                                           self.t("from_word"), entry["file"])
                avatar = (entry["file"][:1] if entry["kind"] == "bank"
                          else entry["question"][:1])
                row = ListRow(scroller.inner, self.T, title, meta,
                              on_click=lambda idx=i: self._select_trash(idx),
                              selected=(self.trash_sel == i), height=60,
                              accent=C["danger"], avatar=avatar)
                row.pack(fill="x")
                tk.Frame(scroller.inner, height=1, bg=C["divider"]).pack(fill="x")

        # 右侧详情
        right = Card(body, self.T, radius=14, padding=0)
        right.pack(side="left", fill="both", expand=True, padx=(self.T.s(16), 0))
        rinner = tk.Frame(right.inner, bg=C["surface"])
        rinner.pack(fill="both", expand=True, padx=self.T.s(20), pady=self.T.s(18))

        if self.trash_sel is not None and self.trash_sel < len(entries):
            entry = entries[self.trash_sel]
            kind_text = self.t("kind_bank") if entry["kind"] == "bank" else self.t("kind_question")
            tk.Label(rinner, text=kind_text, bg=C["surface"], fg=C["danger"],
                     font=self.T.f(11, "bold"), anchor="w").pack(fill="x")
            title = entry["file"] if entry["kind"] == "bank" else entry["question"]
            tk.Label(rinner, text=title, bg=C["surface"], fg=C["text"],
                     font=self.T.f(16, "bold"), anchor="w", justify="left",
                     wraplength=self.T.s(330)).pack(fill="x", pady=(self.T.s(8), self.T.s(6)))
            if entry["kind"] == "bank":
                tk.Label(rinner, text=self.t("n_questions", n=entry["count"]),
                         bg=C["surface"], fg=C["muted"], font=self.T.f(12),
                         anchor="w").pack(fill="x")
            else:
                tk.Label(rinner, text=self.t("answer_label"), bg=C["surface"], fg=C["faint"],
                         font=self.T.f(10), anchor="w").pack(fill="x", pady=(self.T.s(6), 0))
                tk.Label(rinner, text=entry["answer"], bg=C["surface"], fg=C["success"],
                         font=self.T.f(13), anchor="w", justify="left",
                         wraplength=self.T.s(330)).pack(fill="x")
                tk.Label(rinner, text="%s %s" % (self.t("from_word"), entry["file"]),
                         bg=C["surface"], fg=C["faint"], font=self.T.f(10),
                         anchor="w").pack(fill="x", pady=(self.T.s(10), 0))
        else:
            tk.Label(rinner, text=self.t("trash_hint"), bg=C["surface"], fg=C["faint"],
                     font=self.T.f(12)).pack(expand=True)

        # 底部操作
        actions = tk.Frame(self.body, bg=C["bg"])
        actions.pack(fill="x", padx=self.T.s(26), pady=(0, self.T.s(16)))
        self._clear_btn = Button(actions, self.T, self.t("clear_trash"),
                                 command=self._clear_trash_dialog, kind="danger_soft",
                                 width=140, height=44, font_px=12)
        self._clear_btn.pack(side="left")
        Button(actions, self.T, self.t("back"), command=self.show_start, kind="ghost",
               width=100, height=44, font_px=12).pack(side="right")
        self._restore_btn = Button(actions, self.T, self.t("restore"),
                                   command=self._restore_selected, kind="primary",
                                   width=120, height=44, font_px=12)
        self._restore_btn.pack(side="right", padx=(0, self.T.s(8)))

        has_sel = self.trash_sel is not None and self.trash_sel < len(entries)
        self._restore_btn.set_enabled(has_sel)
        self._clear_btn.set_enabled(bool(entries))

    def _select_trash(self, idx):
        self.trash_sel = idx
        self.show_trash()

    def _restore_selected(self):
        entries = storage.trash_entries()
        if self.trash_sel is None or self.trash_sel >= len(entries):
            self._notify(self.t("no_selection"))
            return
        entry = entries[self.trash_sel]

        def do_restore():
            if storage.restore_entry(entry):
                self.trash_sel = None
                self._notify(self.t("restored"))
                self.show_trash()

        self._open_modal(message_dialog(
            self.body, self.T, self.t("restore"), self.t("restore_confirm"),
            [(self.t("cancel"), "ghost", None),
             (self.t("restore"), "primary", do_restore)],
            width=420, height=200, icon="↺", icon_color=C["success"],
            text_color=C["text"]))

    def _clear_trash_dialog(self):
        def do_clear():
            storage.clear_trash()
            self.trash_sel = None
            self.show_trash()

        self._open_modal(message_dialog(
            self.body, self.T, self.t("warning"), self.t("permanent_warning"),
            [(self.t("cancel"), "ghost", None),
             (self.t("delete"), "danger", do_clear)],
            width=470, height=252, icon="!", icon_color=C["danger"],
            text_color=C["danger"], font_px=13))

    # ------------------------------------------------------------ 关于

    def show_about(self):
        self.screen = "about"
        self.clear_body()
        self.title("%s · %s" % (self.t("app_title"), self.t("about_btn")))

        self._header(self.body, self.t("about_btn"), back=self.show_start, with_lang=True)

        card = Card(self.body, self.T, radius=16, padding=0)
        card.pack(fill="both", expand=True, padx=self.T.s(120), pady=(self.T.s(2), self.T.s(20)))

        inner = tk.Frame(card.inner, bg=C["surface"])
        inner.pack(fill="both", expand=True, padx=self.T.s(28), pady=self.T.s(22))

        tk.Label(inner, text=self.t("app_title"), bg=C["surface"], fg=C["text"],
                 font=self.T.f(26, "bold"), anchor="w").pack(fill="x")
        tk.Label(inner, text=self.t("subtitle"), bg=C["surface"], fg=C["muted"],
                 font=self.T.f(11), anchor="w").pack(fill="x", pady=(self.T.s(2), self.T.s(14)))

        info = tk.Frame(inner, bg=C["surface"])
        info.pack(fill="x")
        self._about_line(info, self.t("about_version"), "v" + storage.APP_VERSION)
        self._about_line(info, self.t("about_dev"), storage.APP_AUTHOR)
        self._about_line(info, "GitHub", storage.APP_REPO, link=True)

        tk.Frame(inner, height=1, bg=C["divider"]).pack(fill="x", pady=self.T.s(12))

        tk.Label(inner, text=self.t("about_license"), bg=C["surface"], fg=C["muted"],
                 font=self.T.f(11, "bold"), anchor="w").pack(fill="x")
        tk.Label(inner, text=self.t("about_license_text"), bg=C["surface"], fg=C["text"],
                 font=self.T.f(11), anchor="w", justify="left",
                 wraplength=self.T.s(560)).pack(fill="x", pady=(self.T.s(3), self.T.s(10)))

        tk.Label(inner, text=self.t("about_usage"), bg=C["surface"], fg=C["muted"],
                 font=self.T.f(11, "bold"), anchor="w").pack(fill="x")
        tk.Label(inner, text=self.t("about_usage_text"), bg=C["surface"], fg=C["text"],
                 font=self.T.f(11), anchor="w", justify="left",
                 wraplength=self.T.s(560)).pack(fill="x", pady=(self.T.s(3), 0))

        footer = tk.Frame(inner, bg=C["surface"])
        footer.pack(side="bottom", fill="x", pady=(self.T.s(10), 0))
        tk.Label(footer, text=self.t("about_copy"), bg=C["surface"], fg=C["faint"],
                 font=self.T.f(10), anchor="w").pack(side="left")
        tk.Label(footer, text=self.t("about_free"), bg=C["surface"], fg=C["danger"],
                 font=self.T.f(10), anchor="e").pack(side="right")

        Button(inner, self.T, self.t("about_open"), kind="secondary",
               width=150, height=40, font_px=12,
               command=lambda: webbrowser.open(storage.APP_REPO)
               ).pack(anchor="w", pady=(self.T.s(12), 0))

    def _about_line(self, parent, key, value, link=False):
        row = tk.Frame(parent, bg=C["surface"])
        row.pack(fill="x", pady=self.T.s(3))
        tk.Label(row, text=key, bg=C["surface"], fg=C["faint"], font=self.T.f(11),
                 width=10, anchor="w").pack(side="left")
        label = tk.Label(row, text=value, bg=C["surface"],
                         fg=C["primary"] if link else C["text"],
                         font=self.T.f(12, "bold" if not link else "normal"),
                         anchor="w", cursor="hand2" if link else "arrow")
        label.pack(side="left")
        if link:
            label.bind("<Button-1>", lambda e: webbrowser.open(value))


def run():
    app = App()
    app.mainloop()
