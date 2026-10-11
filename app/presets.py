# -*- coding: utf-8 -*-
"""预设库。

预设只出现在界面的下拉选项里，供选择填入，绝不自动写进内容。
用户可把常用条款“另存为预设”（存 data/presets.json）。
"""
import json
import os

from . import config

# 竞赛规则常用条款预设（通用写法，填入后可改）
RULE_PRESETS = [
    ("计分方法", "各单项取前八名，按 9、7、6、5、4、3、2、1 计分；接力项目加倍计分。"),
    ("名次录取方式", "各单项录取前八名；不足八人（队）的按实际参赛人数减一录取。"),
    ("报名人数及限报项数", "每班每项限报二人，每人限报二项（接力项目不限）。"),
    ("取消比赛成绩的规则", "抢跑两次取消该项比赛资格；无故弃权者取消后续各项比赛资格。"),
    ("团体项目计分", "团体项目名次计分加倍；总分相同，以第一名多者列前。"),
    ("班主任要求", "各班班主任须对本班报名表严格把关，确认学生健康状况适合参赛。"),
    ("体育道德风尚奖评定办法", "按赛前组织、赛场作风、赛后退场等综合评定，大会评委会最终确定。"),
    ("解释权", "本规程解释权及未尽事宜由大会组委会负责。"),
]

# 附录常用条目预设
APPENDIX_PRESETS = [
    ("裁判员守则", "严格执行竞赛规则，秉公执裁；严肃、认真、公正、准确。"),
    ("运动员守则", "尊重裁判、尊重对手、尊重观众；赛出风格、赛出水平。"),
    ("道德风尚奖评选方法", "由道德风尚评议组根据各队比赛作风、组织纪律等评定。"),
]

PRESETS_FILE = os.path.join(config.DATA_DIR, "presets.json")


def _load_user():
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def list_rule_presets():
    user = _load_user().get("rules", [])
    return RULE_PRESETS + [(p.get("title", ""), p.get("text", ""))
                           for p in user]


def save_rule_preset(title, text):
    data = _load_user()
    data.setdefault("rules", []).append({"title": title, "text": text})
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
