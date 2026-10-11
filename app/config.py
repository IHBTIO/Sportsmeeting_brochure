# -*- coding: utf-8 -*-
"""配置与本地存储管理。

- 打包成 exe 后：数据放在 exe 所在目录的 data/（绿色便携）。
- 脚本运行时：数据放在项目目录的 data/。

文件：
- data/state.json       报名记录、项目、班级
- data/settings.json    用户设置
- data/modules.json     秩序册模块勾选状态与文本框架
- templates/            Word 模板目录
"""
import json
import os
import shutil
import sys

APP_NAME = "运动会秩序册生成工具"


def app_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DATA_DIR = os.path.join(app_base_dir(), "data")
TEMPLATE_DIR = os.path.join(app_base_dir(), "templates")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
MODULES_FILE = os.path.join(DATA_DIR, "modules.json")

DEFAULT_SETTINGS = {
    "signature": "",        # 兼容保留（封面署名备选）
    "school": "",           # 学校名称（封面/通知用）
    "year": "",             # 年份（留空用当前年）
    "term": "秋季",         # 届次/季节
    "email": "",
    "font": "宋体",
    "font_size": 12,
    "icon_path": "",
    "output_dir": "",
    "conflict_minutes": 20,
}


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    if getattr(sys, "frozen", False):
        bundled = os.path.join(sys._MEIPASS, "templates")
        if os.path.isdir(bundled):
            for f in os.listdir(bundled):
                dst = os.path.join(TEMPLATE_DIR, f)
                if not os.path.exists(dst) and f.lower().endswith(".docx"):
                    shutil.copy2(os.path.join(bundled, f), dst)


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, obj):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    s.update(load_json(SETTINGS_FILE, {}) or {})
    return s


def save_settings(settings: dict):
    save_json(SETTINGS_FILE, settings)


def list_templates() -> list:
    ensure_dirs()
    return sorted(f for f in os.listdir(TEMPLATE_DIR)
                  if f.lower().endswith(".docx"))
