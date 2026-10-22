# -*- coding: utf-8 -*-
"""数据层：题本解析/读写、回收站、设置。所有文件操作在此集中处理。"""

import json
import os
import re
import shutil
import sys

APP_VERSION = "1.0.0"
APP_AUTHOR = "yunuo1256"
APP_REPO = "https://github.com/yunuo1256"


def app_dir():
    """打包后取 exe 所在目录；源码运行取项目根目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE = app_dir()
QUESTIONS_DIR = os.path.join(BASE, "questions")
TRASH_DIR = os.path.join(BASE, "Trash")
TRASH_BANKS_DIR = os.path.join(TRASH_DIR, "banks")
TRASH_QUESTIONS_DIR = os.path.join(TRASH_DIR, "questions")
SETTINGS_FILE = os.path.join(BASE, "settings.json")
ICON_FILE = os.path.join(BASE, "icon.ico")


def resource_path(rel):
    """资源文件路径：优先 exe 同级目录，其次打包临时目录（PyInstaller）。"""
    candidates = [os.path.join(BASE, rel)]
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidates.append(os.path.join(meipass, rel))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, rel))
    for path in candidates:
        if os.path.exists(path):
            return os.path.normpath(path)
    return os.path.join(BASE, rel)
LIKE_NAME = "like.txt"

# 序号.问题---答案 （允许全角点号、多余空格、三个及以上横杠）
LINE_RE = re.compile(r"^\s*(\d+)\s*[\.．、]\s*(.+?)\s*-{3,}\s*(.*)$")


def like_path():
    return os.path.join(QUESTIONS_DIR, LIKE_NAME)


def ensure_dirs():
    for d in (QUESTIONS_DIR, TRASH_BANKS_DIR, TRASH_QUESTIONS_DIR):
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------- 解析与读写

def parse_line(line):
    """返回 (问题, 答案)；格式不合法返回 None。"""
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    q = m.group(2).strip()
    a = m.group(3).strip()
    if not q:
        return None
    return (q, a)


def format_line(idx, q, a):
    return "%d.%s---%s" % (idx, q, a)


def load_bank(path):
    items = []
    if not os.path.isfile(path):
        return items
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                row = parse_line(line)
                if row:
                    items.append(row)
    except OSError:
        return []
    return items


def save_bank(path, items):
    """原子写入：先写临时文件再替换，避免中途失败损坏题本。"""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for i, (q, a) in enumerate(items, 1):
            f.write(format_line(i, q, a) + "\n")
    os.replace(tmp, path)


def count_valid(path):
    return len(load_bank(path))


# ---------------------------------------------------------------- 题本列表

def list_banks():
    if not os.path.isdir(QUESTIONS_DIR):
        return []
    names = []
    for name in os.listdir(QUESTIONS_DIR):
        if name.lower().endswith(".txt") and os.path.isfile(os.path.join(QUESTIONS_DIR, name)):
            names.append(name)
    # like.txt 置底，其余按名称排序
    names.sort(key=lambda n: (n == LIKE_NAME, n.lower()))
    return names


def bank_path(name):
    return os.path.join(QUESTIONS_DIR, name)


def unique_bank_name(name):
    """避免同名覆盖：xxx.txt -> xxx(1).txt"""
    base, ext = os.path.splitext(name)
    candidate = name
    i = 1
    while os.path.exists(bank_path(candidate)):
        candidate = "%s(%d)%s" % (base, i, ext)
        i += 1
    return candidate


def import_bank_files(paths):
    """把外部 txt 复制进题库，返回成功导入的文件名列表。"""
    ensure_dirs()
    imported = []
    for src in paths:
        if not os.path.isfile(src):
            continue
        name = unique_bank_name(os.path.basename(src))
        try:
            shutil.copy2(src, bank_path(name))
            imported.append(name)
        except OSError:
            pass
    return imported


def create_bank(name):
    """新建空题本，返回实际文件名。"""
    ensure_dirs()
    if not name.lower().endswith(".txt"):
        name += ".txt"
    name = unique_bank_name(name)
    save_bank(bank_path(name), [])
    return name


def delete_bank(name):
    """题本整体移入回收站。"""
    os.makedirs(TRASH_BANKS_DIR, exist_ok=True)
    src = bank_path(name)
    if not os.path.exists(src):
        return False
    dst = os.path.join(TRASH_BANKS_DIR, name)
    if os.path.exists(dst):
        base, ext = os.path.splitext(name)
        i = 1
        while os.path.exists(dst):
            dst = os.path.join(TRASH_BANKS_DIR, "%s(%d)%s" % (base, i, ext))
            i += 1
    shutil.move(src, dst)
    return True


# ---------------------------------------------------------------- 收藏

def favorite_keys():
    return set(load_bank(like_path()))


def set_favorite(item, enabled):
    """收藏/取消收藏，写入 like.txt；原题本不受影响。"""
    ensure_dirs()
    items = load_bank(like_path())
    exists = item in items
    if enabled and not exists:
        items.append(item)
        save_bank(like_path(), items)
        return True
    if not enabled and exists:
        items = [x for x in items if x != item]
        save_bank(like_path(), items)
        return True
    return False


# ---------------------------------------------------------------- 回收站

def move_question_to_trash(bank_name, item, position=None):
    """把单道题追加到 Trash/questions/<bank>.txt。"""
    os.makedirs(TRASH_QUESTIONS_DIR, exist_ok=True)
    path = os.path.join(TRASH_QUESTIONS_DIR, bank_name)
    items = load_bank(path)
    if position is None or position > len(items):
        items.append(item)
    else:
        items.insert(position, item)
    save_bank(path, items)


def trash_entries():
    """返回回收站条目列表：[{kind, name, index, question, answer, source, display}]"""
    entries = []
    if os.path.isdir(TRASH_BANKS_DIR):
        for name in sorted(os.listdir(TRASH_BANKS_DIR)):
            if name.lower().endswith(".txt"):
                entries.append({
                    "kind": "bank",
                    "file": name,
                    "question": "",
                    "answer": "",
                    "count": count_valid(os.path.join(TRASH_BANKS_DIR, name)),
                })
    if os.path.isdir(TRASH_QUESTIONS_DIR):
        for name in sorted(os.listdir(TRASH_QUESTIONS_DIR)):
            path = os.path.join(TRASH_QUESTIONS_DIR, name)
            for idx, (q, a) in enumerate(load_bank(path)):
                entries.append({
                    "kind": "question",
                    "file": name,
                    "index": idx,
                    "question": q,
                    "answer": a,
                })
    return entries


def restore_entry(entry):
    """恢复一条回收站条目，返回 True/False。"""
    if entry["kind"] == "bank":
        src = os.path.join(TRASH_BANKS_DIR, entry["file"])
        if not os.path.exists(src):
            return False
        name = unique_bank_name(entry["file"])
        shutil.move(src, bank_path(name))
        return True

    src = os.path.join(TRASH_QUESTIONS_DIR, entry["file"])
    items = load_bank(src)
    idx = entry["index"]
    if not (0 <= idx < len(items)):
        return False
    item = items.pop(idx)
    target = bank_path(entry["file"])
    bank_items = load_bank(target)
    bank_items.append(item)
    save_bank(target, bank_items)
    if items:
        save_bank(src, items)
    else:
        try:
            os.remove(src)
        except OSError:
            pass
    return True


def clear_trash():
    for d in (TRASH_BANKS_DIR, TRASH_QUESTIONS_DIR):
        if os.path.isdir(d):
            for name in os.listdir(d):
                p = os.path.join(d, name)
                try:
                    if os.path.isfile(p):
                        os.remove(p)
                except OSError:
                    pass
    ensure_dirs()


def trash_count():
    return len(trash_entries())


# ---------------------------------------------------------------- 设置

DEFAULT_SETTINGS = {"language": "en", "last_bank": None, "theme": "light"}


def load_settings():
    data = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            data.update({k: raw.get(k, v) for k, v in DEFAULT_SETTINGS.items()})
    except (OSError, ValueError):
        pass
    if data.get("language") not in ("en", "zh_cn", "zh_tw"):
        data["language"] = "en"
    if data.get("theme") not in ("light", "dark"):
        data["theme"] = "light"
    return data


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def fmt_time(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)
