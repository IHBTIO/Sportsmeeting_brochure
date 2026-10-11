# -*- coding: utf-8 -*-
"""秩序册模块勾选状态管理（v2）。

v2 变更（第二轮要求）：
- 版本号 2；旧版（v1）保存的文本预置内容全部清空，布尔勾选状态保留。
- 封面图片默认不勾选；导语默认为空。
- 所有文本默认为空（不预置任何内容，除测试文件）。
- 输出规则：模块勾选且其中有实际内容才生成该章节框架+内容。
"""
import copy

from . import config

MODULE_ORDER = [
    ("cover", "封面"),
    ("notice", "通知"),
    ("rules", "竞赛规则"),
    ("committee", "竞赛委员会"),
    ("referees", "裁判员名单"),
    ("awards", "颁奖仪式"),
    ("schedule", "竞赛日程表"),
    ("rosters", "代表队名单及号码对照表"),
    ("grouping", "竞赛分组"),
    ("class_list", "各班参赛名单"),
    ("event_list", "各项目参赛人员"),
    ("appendix", "附录"),
    ("records", "校纪录"),
]

DEFAULT_MODULES = {
    "version": 2,
    "recognize": {
        "event": True, "class": True, "name": True, "gender": True,
        "yellow": 90, "red": 60,
    },
    "cover": {
        "enabled": True,
        "image_enabled": False,    # 图片默认不勾选
        "slogan_enabled": True,
        "image_path": "",
        "slogan": "",              # 导语默认不填写
        "date_text": "",
    },
    "notice": {
        "enabled": True,
        "title": "",
        "body": "",
    },
    "rules": {
        "enabled": True,
        "clauses": [
            {"checked": True, "title": "比赛时间", "text": ""},
            {"checked": True, "title": "参加单位及分组", "text": ""},
            {"checked": True, "title": "比赛项目", "text": ""},
            {"checked": True, "title": "团体项目补充说明", "text": ""},
            {"checked": True, "title": "报名人数及限报项数", "text": ""},
            {"checked": True, "title": "取消比赛成绩的规则", "text": ""},
            {"checked": True, "title": "班主任要求", "text": ""},
            {"checked": True, "title": "计分方法", "text": ""},
            {"checked": True, "title": "名次录取方式", "text": ""},
            {"checked": True, "title": "报名时间及报名格式", "text": ""},
            {"checked": True, "title": "体育道德风尚奖评定办法", "text": ""},
            {"checked": True, "title": "解释权", "text": ""},
            {"checked": True, "title": "报名表填写办法", "text": ""},
        ],
    },
    "committee": {
        "enabled": True,
        "groups": [
            {"checked": True, "name": "主任委员", "members": ""},
            {"checked": True, "name": "宣传报道组", "members": ""},
            {"checked": True, "name": "裁判竞赛组", "members": ""},
            {"checked": True, "name": "安全保卫组", "members": ""},
            {"checked": True, "name": "后勤保障组", "members": ""},
            {"checked": True, "name": "道德风尚评议组", "members": ""},
            {"checked": True, "name": "资格审查组", "members": ""},
            {"checked": True, "name": "奖牌颁发组", "members": ""},
            {"checked": True, "name": "场地器材组", "members": ""},
        ],
    },
    "referees": {
        "enabled": True,
        "groups": [
            {"checked": True, "name": "总裁判长、副总裁判长", "members": ""},
            {"checked": True, "name": "赛前控制中心", "members": ""},
            {"checked": True, "name": "裁判员、学生裁判、终点记录员", "members": ""},
            {"checked": True, "name": "铅球、跳高、跳远、立定、50米团体裁判", "members": ""},
            {"checked": True, "name": "赛后控制中心", "members": ""},
            {"checked": True, "name": "引体向上裁判", "members": ""},
            {"checked": True, "name": "仰卧起坐裁判", "members": ""},
            {"checked": True, "name": "裁判安排和开幕式裁判时间", "members": ""},
            {"checked": True, "name": "指定班级表演节目", "members": ""},
        ],
    },
    "awards": {
        "enabled": True,
        "headers": ["项目", "领奖运动员名次", "集合地点", "集合时间", "颁奖时间", "颁奖嘉宾"],
        "rows": [],
    },
    "schedule": {
        "enabled": True,
        "split_field_track": True,
        "show_time": True,
        "show_count": True,
    },
    "rosters": {
        "enabled": True,
        "only_checked_classes": False,
    },
    "grouping": {
        "enabled": True,
        "only_checked_events": False,
    },
    "class_list": {"enabled": True},
    "event_list": {"enabled": True},
    "appendix": {
        "enabled": True,
        "items": [
            {"checked": True, "title": "裁判员守则", "text": ""},
            {"checked": True, "title": "运动员守则", "text": ""},
            {"checked": True, "title": "道德风尚奖评选方法", "text": ""},
            {"checked": True, "title": "田径运动员技术等级标准", "text": ""},
        ],
    },
    "records": {
        "enabled": True,
        "male": True, "female": True, "national": True,
        "male_headers": ["项目", "纪录", "保持者", "年份"], "male_rows": [],
        "female_headers": ["项目", "纪录", "保持者", "年份"], "female_rows": [],
        "national_headers": ["项目", "标准", "说明", "年份"], "national_rows": [],
    },
}

_cache = None


def _keep_booleans_only(v):
    """v1 -> v2 迁移：只保留布尔与数字（勾选状态/阈值），文本全部清空。"""
    if isinstance(v, bool) or isinstance(v, int) or isinstance(v, float):
        return v
    if isinstance(v, dict):
        return {k: _keep_booleans_only(x) for k, x in v.items()}
    return None   # 字符串/列表丢弃


def _prune_none(v):
    if isinstance(v, dict):
        return {k: _prune_none(x) for k, x in v.items() if x is not None}
    return v


def _merge(base, saved):
    out = {}
    for k, v in base.items():
        if isinstance(v, dict) and isinstance(saved.get(k), dict):
            out[k] = _merge(v, saved[k])
        elif k in saved:
            out[k] = saved[k]
        else:
            out[k] = copy.deepcopy(v)
    return out


def get_flags():
    global _cache
    if _cache is None:
        saved = config.load_json(config.MODULES_FILE, {})
        if isinstance(saved, dict) and saved.get("version", 1) < 2:
            # 旧版：只保留勾选状态，预置文本清空
            saved = _prune_none(_keep_booleans_only(saved)) or {}
        _cache = _merge(DEFAULT_MODULES, saved if isinstance(saved, dict) else {})
        _cache["version"] = 2
    return _cache


def save_flags():
    if _cache is not None:
        config.save_json(config.MODULES_FILE, _cache)


def enabled_modules():
    f = get_flags()
    return [(k, t) for k, t in MODULE_ORDER if f.get(k, {}).get("enabled", True)]
