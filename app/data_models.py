# -*- coding: utf-8 -*-
"""数据模型：报名记录、项目、班级，以及整体状态 AppState（自动持久化）。

第二轮变更：
- 术语：项目类型“竞赛”改为“径赛”（旧数据读取时自动迁移）。
- EventItem 新增 grade（年级）、show_venue（是否输出场地）、overlap（重叠标记）。
- session 默认改为空白（上/下午由用户勾选）。
- BUILTIN_EVENTS 扩充为完整预制清单（默认全部参与）。
- settings 新增 number_mode（号码范围模式）。
"""
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

from . import config


def new_id():
    return uuid.uuid4().hex[:12]


@dataclass
class Record:
    rid: str
    class_name: str = ""
    person: str = ""
    gender: str = ""
    event: str = ""
    group: str = ""
    time: str = ""
    venue: str = ""
    number: str = ""
    confidence: int = 100
    issues: list = field(default_factory=list)
    status: str = "pending"   # pending / edited / ignored
    raw_event: str = ""
    raw_class: str = ""
    conflict: bool = False

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        r = Record(rid=d.get("rid") or new_id())
        for k, v in d.items():
            if k != "rid" and hasattr(r, k):
                setattr(r, k, v)
        return r


@dataclass
class EventItem:
    eid: str
    name: str = ""
    etype: str = "径赛"       # 田赛 / 径赛
    group: str = "男"         # 男 / 女 / 混合
    grade: str = ""           # 年级：空 / 高一 / 高二 / 高三（或初中等）
    day: str = ""
    session: str = ""         # 空 / 上午 / 下午（默认空白）
    time: str = ""
    venue: str = ""
    rule: str = ""
    record: str = ""
    note: str = ""
    enabled: bool = True      # 是否参与秩序册
    show_venue: bool = True   # 是否输出场地
    overlap: bool = False     # 项目时间重叠标记（黄色）
    order: int = 0

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        e = EventItem(eid=d.get("eid") or new_id())
        for k, v in d.items():
            if k != "eid" and hasattr(e, k):
                setattr(e, k, v)
        return e


@dataclass
class ClassInfo:
    cid: str
    name: str = ""
    leader: str = ""
    num_range: str = ""       # 号码范围（可由“刷新号码范围”自动计算）
    enabled: bool = True
    show_roster: bool = True

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        c = ClassInfo(cid=d.get("cid") or new_id())
        for k, v in d.items():
            if k != "cid" and hasattr(c, k):
                setattr(c, k, v)
        return c


# ---------------- 预制完整项目清单（默认全部参与） ----------------
BUILTIN_EVENTS = [
    # 径赛（男/女）
    ("50米", "径赛", "男"), ("50米", "径赛", "女"),
    ("60米", "径赛", "男"), ("60米", "径赛", "女"),
    ("100米", "径赛", "男"), ("100米", "径赛", "女"),
    ("200米", "径赛", "男"), ("200米", "径赛", "女"),
    ("400米", "径赛", "男"), ("400米", "径赛", "女"),
    ("800米", "径赛", "男"), ("800米", "径赛", "女"),
    ("1500米", "径赛", "男"), ("1500米", "径赛", "女"),
    ("3000米", "径赛", "男"), ("3000米", "径赛", "女"),
    ("100米栏", "径赛", "男"), ("100米栏", "径赛", "女"),
    ("110米栏", "径赛", "男"), ("110米栏", "径赛", "女"),
    ("4x100米接力", "径赛", "混合"),
    ("4x400米接力", "径赛", "混合"),
    # 田赛（男/女）
    ("跳高", "田赛", "男"), ("跳高", "田赛", "女"),
    ("跳远", "田赛", "男"), ("跳远", "田赛", "女"),
    ("三级跳远", "田赛", "男"), ("三级跳远", "田赛", "女"),
    ("立定跳远", "田赛", "男"), ("立定跳远", "田赛", "女"),
    ("铅球", "田赛", "男"), ("铅球", "田赛", "女"),
    ("实心球", "田赛", "男"), ("实心球", "田赛", "女"),
    ("垒球", "田赛", "男"), ("垒球", "田赛", "女"),
    ("跳绳", "田赛", "男"), ("跳绳", "田赛", "女"),
]


def default_events():
    return [EventItem(new_id(), n, t, g) for (n, t, g) in BUILTIN_EVENTS]


class AppState:
    def __init__(self):
        self.records = []
        self.events = []
        self.classes = []
        self.settings = {}
        self._load()

    def _load(self):
        config.ensure_dirs()
        self.settings = config.load_settings()
        state = config.load_json(config.STATE_FILE, None)
        if state is None:
            self.events = default_events()
            self.save()
            return
        self.records = [Record.from_dict(d) for d in state.get("records", [])]
        self.events = [EventItem.from_dict(d) for d in state.get("events", [])]
        self.classes = [ClassInfo.from_dict(d) for d in state.get("classes", [])]
        if not self.events:
            self.events = default_events()
        # 旧数据迁移：项目类型“竞赛”->“径赛”
        for e in self.events:
            if e.etype == "竞赛":
                e.etype = "径赛"

    def save(self):
        config.save_json(config.STATE_FILE, {
            "records": [r.to_dict() for r in self.records],
            "events": [e.to_dict() for e in self.events],
            "classes": [c.to_dict() for c in self.classes],
        })
        config.save_settings(self.settings)

    def event_names(self):
        names = []
        for e in self.events:
            if e.name and e.name not in names:
                names.append(e.name)
        return names

    def find_event(self, name, group=None):
        for e in self.events:
            if e.name == name and (group is None or e.group == group):
                return e
        return None

    def add_event(self, **kw):
        e = EventItem(new_id(), **kw)
        self.events.append(e)
        return e

    def class_names(self):
        return sorted(c.name for c in self.classes)

    def ensure_class(self, name):
        if name and not any(c.name == name for c in self.classes):
            self.classes.append(ClassInfo(new_id(), name))

    def replace_records(self, records):
        self.records = records
        self.save()

    def record_by_id(self, rid):
        for r in self.records:
            if r.rid == rid:
                return r
        return None

    def export_events_json(self, path):
        config.save_json(path, [e.to_dict() for e in self.events])

    def import_events_json(self, path):
        data = config.load_json(path, None)
        if not isinstance(data, list):
            raise ValueError("项目配置文件格式不正确（应为 JSON 数组）")
        self.events = [EventItem.from_dict(d) for d in data]
        for e in self.events:
            if e.etype == "竞赛":
                e.etype = "径赛"
        self.save()
        return len(self.events)

    def export_classes_json(self, path):
        config.save_json(path, [c.to_dict() for c in self.classes])

    def import_classes_json(self, path):
        data = config.load_json(path, None)
        if not isinstance(data, list):
            raise ValueError("班级配置文件格式不正确（应为 JSON 数组）")
        self.classes = [ClassInfo.from_dict(d) for d in data]
        self.save()
        return len(self.classes)
