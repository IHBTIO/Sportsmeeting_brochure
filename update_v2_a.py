# -*- coding: utf-8 -*-
"""运动会秩序册生成工具 第二轮更新 脚本A（app 层）。

用法：python update_v2_a.py
作用：把 6 个 app 层文件写入项目，语法检查，自动迁移旧数据。
之后请继续运行 update_v2_b.py（ui 层），两者都完成后程序才可启动。
"""
import os
import py_compile
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

FILES = {}

# ============================================================
# app/recognizer.py
# ============================================================
FILES["app/recognizer.py"] = r'''# -*- coding: utf-8 -*-
"""智能识别模块：项目名、班级名、人名、性别的规范化与置信评分。

置信分：>=90 自动通过；60-89 建议核对；<60 人工审查（阈值可在界面改）。
识别开关关闭的类别：不做规范化，标红进人工审查（可在审查页批量忽略）。
"""
import re

SURNAMES = set(
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
    "和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁"
    "杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍"
    "虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚"
    "程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓"
    "牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘詹束龙叶"
    "幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双闻莘"
    "党翟谭贡劳逄姬申扶堵冉宰郦雍却璩桑桂濮牛寿通边扈燕冀郏浦尚农温别"
    "庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘"
    "欧阳诸葛上官司徒司空司马端木"
)

STANDARD_EVENTS = {
    "50米":        ("径赛", ["50m", "50米", "五十米"]),
    "60米":        ("径赛", ["60m", "60米", "六十米"]),
    "100米":       ("径赛", ["100m", "100米", "一百米", "百米"]),
    "200米":       ("径赛", ["200m", "200米", "二百米"]),
    "400米":       ("径赛", ["400m", "400米", "四百米"]),
    "800米":       ("径赛", ["800m", "800米", "八百米"]),
    "1500米":      ("径赛", ["1500m", "1500米", "一千五百米"]),
    "3000米":      ("径赛", ["3000m", "3000米", "三千米"]),
    "5000米":      ("径赛", ["5000m", "5000米", "五千米"]),
    "100米栏":     ("径赛", ["100米栏", "100m栏", "百米栏"]),
    "110米栏":     ("径赛", ["110米栏", "110m栏"]),
    "4x100米接力": ("径赛", ["4x100接力", "4乘100接力", "4*100接力", "400米接力", "4x100m接力"]),
    "4x400米接力": ("径赛", ["4x400接力", "4乘400接力", "4*400接力", "1600米接力", "4x400m接力"]),
    "跳高":        ("田赛", ["跳高", "highjump"]),
    "跳远":        ("田赛", ["跳远", "longjump"]),
    "三级跳远":    ("田赛", ["三级跳", "三级跳远"]),
    "立定跳远":    ("田赛", ["立定跳远", "立定跳"]),
    "铅球":        ("田赛", ["铅球", "shotput"]),
    "实心球":      ("田赛", ["实心球"]),
    "铁饼":        ("田赛", ["铁饼"]),
    "标枪":        ("田赛", ["标枪"]),
    "垒球":        ("田赛", ["垒球", "掷垒球"]),
    "跳绳":        ("田赛", ["跳绳", "一分钟跳绳"]),
}

_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNIT = {"十": 10, "百": 100, "千": 1000}


def _cn_to_int(s):
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        pass
    total, num = 0, 0
    for ch in s:
        if ch in _CN_DIGIT:
            num = _CN_DIGIT[ch]
        elif ch in _CN_UNIT:
            total += (num or 1) * _CN_UNIT[ch]
            num = 0
        else:
            return None
    return total + num


def _clean(s):
    return re.sub(r"\s+", "", str(s or "")).lower()


# ---------------- 各类识别（带开关） ----------------
def normalize_event(raw):
    """项目名 -> (标准名, 置信分)。"""
    s = _clean(raw)
    if not s:
        return "", 0
    core = re.sub(
        r"(男子|女子|男生|女生|男|女|混合|团体|个人|组|决赛|预赛|复赛|初中|高中|年级)",
        "", s)
    core = core.strip("*-—_·.")
    for name, (_t, aliases) in STANDARD_EVENTS.items():
        for alias in list(aliases) + [name]:
            if alias and (core == alias or s == alias):
                return name, 100
    best, best_len = None, 0
    for name, (_t, aliases) in STANDARD_EVENTS.items():
        for alias in list(aliases) + [name]:
            if alias and alias in core and len(alias) > best_len:
                best, best_len = name, len(alias)
    if best:
        return best, 85
    m = re.search(r"(\d+)\s*(米|m)", core)
    if m:
        dist = m.group(1)
        if "接力" in core and dist == "4":
            return "4x100米接力", 80
        name = f"{dist}米" + ("栏" if "栏" in core else "") \
               + ("接力" if "接力" in core else "")
        if name in STANDARD_EVENTS:
            return name, 85
        return name, 70
    m = re.search(r"([一二两三四五六七八九十百千]+)\s*(米|栏)", core)
    if m:
        num = _cn_to_int(m.group(1))
        if num:
            name = f"{num}米" + ("栏" if m.group(2) == "栏" else "") \
                   + ("接力" if "接力" in core else "")
            if name in STANDARD_EVENTS:
                return name, 85
            return name, 70
    return s, 40


_GRADE_MAP = [
    ("初一", r"(初[一1]|七年级|7年级)"),
    ("初二", r"(初[二2]|八年级|8年级)"),
    ("初三", r"(初[三3]|九年级|9年级)"),
    ("高一", r"(高[一1])"),
    ("高二", r"(高[二2])"),
    ("高三", r"(高[三3])"),
]


def normalize_class(raw):
    s = re.sub(r"\s+", "", str(raw or ""))
    if not s:
        return "", 0
    grade = None
    for std, pat in _GRADE_MAP:
        if re.search(pat, s):
            grade = std
            break
    m = re.search(r"[（(]\s*(\d{1,2})\s*[)）]", s)
    if not m:
        m = re.search(r"(\d{1,2})\s*班", s)
    num = m.group(1) if m else None
    if not num:
        nums = re.findall(r"\d{1,2}", s)
        if nums:
            num = nums[-1] if grade else nums[0]
    if num:
        if grade:
            return f"{grade}({int(num)})班", 100
        return f"{int(num)}班", 70
    return (s + "班") if not s.endswith("班") else s, 45


def validate_name(raw):
    s = str(raw or "").strip().replace(" ", "")
    if not s:
        return "", 0
    if not re.fullmatch(r"[\u4e00-\u9fa5·]{2,4}", s):
        if re.fullmatch(r"[A-Za-z]{2,20}", s):
            return s, 60
        return s, 30
    return (s, 100) if s[0] in SURNAMES else (s, 65)


def detect_gender(gender_raw, event_raw, group_raw):
    g = _clean(gender_raw)
    if g:
        if "男" in g or g in ("m", "male", "1", "man", "boy"):
            return "男", 100
        if "女" in g or g in ("f", "female", "0", "2", "woman", "girl"):
            return "女", 100
    e = _clean(event_raw)
    if "男子" in e or "男生" in e:
        return "男", 70
    if "女子" in e or "女生" in e:
        return "女", 70
    grp = _clean(group_raw)
    if grp:
        if "男" in grp:
            return "男", 70
        if "女" in grp:
            return "女", 70
    return "", 35


# ---------------- 综合分析（识别开关参与） ----------------
def analyze_row(class_raw, person_raw, gender_raw, event_raw, group_raw,
                switches=None):
    """对一行报名数据做识别。switches: {"event","class","name","gender": bool}

    开关关闭的类别：不规范化、保留原始值、置信压到 50（标红），
    问题文字带类别词（供审查页分组）。
    """
    sw = {"event": True, "class": True, "name": True, "gender": True}
    if switches:
        sw.update(switches)
    issues = []

    # 班级
    if sw["class"]:
        class_name, c_score = normalize_class(class_raw)
        if c_score < 90:
            issues.append(f"班级名无法完全识别（原始：{class_raw}）")
    else:
        class_name = str(class_raw or "").strip()
        c_score = 50
        issues.append(f"班级名识别已关闭，保留原始名称：{class_name}")

    # 姓名
    if sw["name"]:
        person, p_score = validate_name(person_raw)
        if p_score < 90:
            issues.append(f"姓名可疑（原始：{person_raw}）")
    else:
        person = str(person_raw or "").strip()
        p_score = 100   # 关闭识别不扣姓名分，交人工
        issues.append(f"姓名识别已关闭，保留原始名称：{person}")

    # 项目
    if sw["event"]:
        event, e_score = normalize_event(event_raw)
        if e_score < 90:
            issues.append(f"项目名可疑（原始：{event_raw}）")
    else:
        event = str(event_raw or "").strip()
        e_score = 50
        issues.append(f"项目名识别已关闭，保留原始名称：{event}")

    # 性别
    if sw["gender"]:
        gender, g_score = detect_gender(gender_raw, event_raw, group_raw)
        if not gender:
            issues.append("性别未知，需人工确认")
    else:
        gender = str(gender_raw or "").strip()
        if gender not in ("男", "女"):
            gender = ""
            g_score = 50
            issues.append("性别未填写（识别已关闭）")
        else:
            g_score = 100

    score = min(c_score, p_score, e_score)
    if not gender:
        score = min(score, 50)
    return {
        "class_name": class_name, "person": person, "gender": gender,
        "event": event, "score": score, "issues": issues,
        "raw_event": str(event_raw or ""), "raw_class": str(class_raw or ""),
    }
'''

# ============================================================
# app/data_models.py
# ============================================================
FILES["app/data_models.py"] = r'''# -*- coding: utf-8 -*-
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
'''

# ============================================================
# app/importer.py
# ============================================================
FILES["app/importer.py"] = r'''# -*- coding: utf-8 -*-
"""数据导入模块：读取 Excel/CSV，字段映射，一人多项目拆行。"""
import re

import pandas as pd

from .recognizer import analyze_row
from .data_models import Record, new_id

FIELDS = ["班级", "姓名", "性别", "项目", "组别", "赛程时间", "场地", "号码"]

COL_GUESS = {
    "班级": ["班级", "班别", "class", "班"],
    "姓名": ["姓名", "名字", "学生", "运动员", "name"],
    "性别": ["性别", "sex", "gender"],
    "项目": ["项目", "比赛项目", "参赛项目", "event", "项目名称"],
    "组别": ["组别", "组", "分组", "group"],
    "赛程时间": ["时间", "赛程时间", "比赛时间", "time"],
    "场地": ["场地", "地点", "比赛场地", "venue"],
    "号码": ["号码", "编号", "number", "num", "no"],
}

_SPLIT_RE = re.compile(r"[,，、;；/]\s*|\s{2,}")


def load_table(path):
    low = path.lower()
    if low.endswith(".csv"):
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                return pd.read_csv(path, encoding=enc, dtype=str).fillna("")
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        raise ValueError("CSV 文件编码无法识别（已尝试 UTF-8 / GBK）")
    return pd.read_excel(path, dtype=str).fillna("")


def guess_mapping(columns):
    mapping = {f: "" for f in FIELDS}
    cols = [str(c).strip() for c in columns]
    for fld, keys in COL_GUESS.items():
        if mapping[fld]:
            continue
        for c in cols:
            if any(k in c.lower() for k in keys) and c not in mapping.values():
                mapping[fld] = c
                break
    return mapping


def normalize_time_text(t):
    """把全角冒号等统一成半角（防止中英文切换造成的时间不匹配）。"""
    return str(t or "").strip().replace("：", ":").replace("．", ":")


def build_records(df, mapping, split_multi=True, switches=None):
    """按映射把 DataFrame 转为 Record 列表。一人多项目自动拆行。

    switches：识别开关 {"event","class","name","gender"}，来自智能识别页。
    """
    records = []
    for _, row in df.iterrows():
        def val(fld):
            col = mapping.get(fld, "")
            if not col or col not in df.columns:
                return ""
            return str(row[col]).strip()

        class_raw = val("班级")
        person_raw = val("姓名")
        if not class_raw and not person_raw:
            continue
        gender_raw = val("性别")
        event_raw = val("项目")
        group_raw = val("组别")
        time_raw = normalize_time_text(val("赛程时间"))
        venue_raw = val("场地")
        number_raw = val("号码")

        events = _SPLIT_RE.split(event_raw) if split_multi else [event_raw]
        events = [e.strip() for e in events if e and e.strip()]
        if not events:
            events = [""]

        for ev in events:
            info = analyze_row(class_raw, person_raw, gender_raw, ev,
                               group_raw, switches)
            records.append(Record(
                rid=new_id(),
                class_name=info["class_name"],
                person=info["person"],
                gender=info["gender"],
                event=info["event"],
                group=group_raw,
                time=time_raw,
                venue=venue_raw,
                number=number_raw,
                confidence=info["score"],
                issues=info["issues"],
                raw_event=info["raw_event"],
                raw_class=info["raw_class"],
            ))
    return records


def classes_from_records(records):
    names = []
    for r in records:
        if r.class_name and r.class_name not in names:
            names.append(r.class_name)
    return names
'''

# ============================================================
# app/schedule.py
# ============================================================
FILES["app/schedule.py"] = r'''# -*- coding: utf-8 -*-
"""赛程模块：时间解析、排序、上下移动、冲突检测。

冲突分两级（第二轮要求）：
- 项目时间重叠（黄色）：同一天同时段，两个项目时间差 <= 阈值分钟。
- 运动员冲突（红色）：同一运动员的两个项目时间差 <= 阈值分钟。
- check_all()：一键检测，把两种合并跑完并设置标记。
时间解析兼容全角冒号“8：40”、“8.40”等写法。
"""
from collections import defaultdict


def _to_minutes(t):
    s = str(t or "").strip()
    for ch in ("：", "．", "。", ".", "－", "-"):
        if ch in s:
            s = s.replace(ch, ":")
    s = s.replace(" ", "")
    if not s:
        return None
    parts = s.split(":")
    if len(parts) == 2:
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return None
    if len(parts) == 1 and parts[0].isdigit():
        try:
            return int(parts[0]) * 60
        except ValueError:
            return None
    return None


def sort_events(events):
    """按 天 -> 上午/下午(空白最后) -> 时间 -> order 排序。"""
    def key(e):
        sess = {"上午": 0, "下午": 1}.get(e.session, 2)
        return (e.day or "zzz", sess, e.time or "99:99", e.order)
    return sorted(events, key=key)


def move_event(events, eid, direction):
    ordered = sort_events(events)
    idx = next((i for i, e in enumerate(ordered) if e.eid == eid), None)
    if idx is None:
        return False
    target = ordered[idx]
    group = [e for e in ordered
             if (e.day, e.session, e.time) == (target.day, target.session, target.time)]
    gi = group.index(target)
    ni = gi + direction
    if 0 <= ni < len(group):
        group[gi], group[ni] = group[ni], group[gi]
        for k, e in enumerate(group):
            e.order = k
        return True
    return False


def detect_event_overlaps(events, threshold_minutes=20):
    """项目时间重叠（黄色）。返回 {项目名: [重叠的其他项目名...]}。

    说明：同时段（上午/下午都填了才比）且同一天才比较；空白时段不比。
    """
    res = {}
    evs = [e for e in events
           if e.day and e.session and _to_minutes(e.time) is not None]
    for i in range(len(evs)):
        for j in range(i + 1, len(evs)):
            a, b = evs[i], evs[j]
            if a.day == b.day and a.session == b.session \
                    and abs(_to_minutes(a.time) - _to_minutes(b.time)) <= threshold_minutes:
                res.setdefault(a.name, []).append(b.name)
                res.setdefault(b.name, []).append(a.name)
    return res


def detect_conflicts(records, events, threshold_minutes=20):
    """运动员冲突（红色）。返回冲突记录 id 集合。"""
    conflict_ids = set()
    person_events = defaultdict(set)
    for r in records:
        if r.person and r.event:
            person_events[(r.class_name, r.person)].add(r.event)
    ev_time = {}
    for e in events:
        if e.time:
            ev_time[e.name] = (e.day, _to_minutes(e.time))

    for r in records:
        r.conflict = False

    for (cls, person), evs in person_events.items():
        evs = [e for e in evs if e in ev_time and ev_time[e][1] is not None]
        evs = sorted(evs, key=lambda e: ev_time[e])
        for i in range(len(evs)):
            for j in range(i + 1, len(evs)):
                d1, t1 = ev_time[evs[i]]
                d2, t2 = ev_time[evs[j]]
                if d1 == d2 and t1 is not None and t2 is not None \
                        and abs(t1 - t2) <= threshold_minutes:
                    for r in records:
                        if r.class_name == cls and r.person == person \
                                and r.event in (evs[i], evs[j]):
                            r.conflict = True
                            conflict_ids.add(r.rid)
    return conflict_ids


def check_all(records, events, threshold_minutes=20):
    """一键检测：运动员冲突（红）+ 项目重叠（黄）。

    返回 (conflict_ids, overlaps_dict, report_text)。
    """
    conflict_ids = detect_conflicts(records, events, threshold_minutes)
    overlaps = detect_event_overlaps(events, threshold_minutes)
    for e in events:
        e.overlap = e.name in overlaps
    people = sorted({(r.class_name, r.person) for r in records if r.conflict})
    lines = []
    if people:
        lines.append(f"运动员时间冲突（红色）{len(people)} 人：")
        for c, p in people:
            evs = [r.event for r in records
                   if r.conflict and r.class_name == c and r.person == p]
            lines.append(f"  {c} {p}：{'、'.join(sorted(set(evs)))}")
    if overlaps:
        lines.append(f"项目时间重叠（黄色）{len(overlaps)} 个：")
        for name, others in overlaps.items():
            lines.append(f"  {name} 与 {'、'.join(sorted(set(others)))} 时间过近")
    if not lines:
        lines.append("未发现冲突。")
    return conflict_ids, overlaps, "\n".join(lines)
'''

# ============================================================
# app/module_flags.py
# ============================================================
FILES["app/module_flags.py"] = r'''# -*- coding: utf-8 -*-
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
'''

# ============================================================
# app/docgen.py
# ============================================================
FILES["app/docgen.py"] = r'''# -*- coding: utf-8 -*-
"""Word 秩序册生成模块（python-docx）。

输出规则（第二轮）：
- 只输出勾选（enabled）的模块。
- 勾选且其中有实际内容才输出该章节（纯文本模块内容为空则跳过）。
- 日程表含年级列；场地按项目 show_venue 决定是否输出。
"""
import os
from collections import defaultdict
from datetime import date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from . import config, module_flags
from .schedule import sort_events


# ---------------- 排版工具 ----------------
def _apply_font(doc, settings):
    font = settings.get("font") or "宋体"
    size = int(settings.get("font_size") or 12)
    style = doc.styles["Normal"]
    style.font.name = font
    style.font.size = Pt(size)
    rpr = style.element.get_or_add_rPr()
    rpr.get_or_add_rFonts().set(qn("w:eastAsia"), font)


def _run_font(run, font, size=None, bold=None):
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def _heading(doc, text, level=1, font="黑体"):
    p = doc.add_heading("", level=level)
    run = p.add_run(text)
    size = {1: 16, 2: 14, 3: 12}.get(level, 12)
    _run_font(run, font, size, True)
    return p


def _center(doc, text, font="黑体", size=16, bold=True):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    _run_font(run, font, size, bold)
    return p


def _text_para(doc, text, font="宋体", size=12, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    _run_font(run, font, size, bold)
    return p


def _table(doc, headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    for j, h in enumerate(headers):
        t.cell(0, j).text = str(h)
    for row in rows:
        cells = t.add_row().cells
        for j, v in enumerate(row):
            cells[j].text = "" if v is None else str(v)
    return t


def _school_year(settings):
    school = settings.get("school") or settings.get("signature") or ""
    year = settings.get("year") or str(date.today().year)
    term = settings.get("term") or "秋季"
    return school, year, term


# ---------------- 各模块 ----------------
def _mod_cover(doc, state, flags, settings, font):
    school, year, term = _school_year(settings)
    f = flags["cover"]
    for _ in range(4):
        doc.add_paragraph()
    if school:
        _center(doc, school, size=22)
    _center(doc, f"{year}年{term}田径运动会", size=26)
    _center(doc, "秩  序  册", size=30)
    if f.get("image_enabled") and f.get("image_path") \
            and os.path.exists(f["image_path"]):
        try:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(f["image_path"], width=Inches(3.2))
        except Exception:
            pass
    if f.get("slogan_enabled") and f.get("slogan"):
        doc.add_paragraph()
        _center(doc, f["slogan"], font="宋体", size=14, bold=False)
    for _ in range(6):
        doc.add_paragraph()
    date_text = f.get("date_text") or f"{year}年{date.today().month}月"
    _center(doc, date_text, font="宋体", size=14, bold=False)
    if school:
        _center(doc, school, font="宋体", size=14, bold=False)
    doc.add_page_break()


def _toc(doc, flags):
    _heading(doc, "目  录", level=1)
    idx = 0
    for _key, title in module_flags.MODULE_ORDER:
        if flags.get(_key, {}).get("enabled", True):
            idx += 1
            p = doc.add_paragraph(f"{idx}、{title}")
            p.paragraph_format.left_indent = Pt(24)
    doc.add_page_break()


def _mod_notice(doc, state, flags, settings, font):
    f = flags["notice"]
    if not (f.get("title") or f.get("body")):
        return   # 勾选但无内容：跳过
    school, year, term = _school_year(settings)
    try:
        title = (f.get("title") or "").format(school=school, year=year, term=term)
    except (KeyError, IndexError):
        title = f.get("title") or ""
    if title:
        _center(doc, title, font="黑体", size=16)
    for line in (f.get("body") or "").splitlines():
        if line.strip():
            _text_para(doc, line)
    doc.add_page_break()


def _mod_rules(doc, state, flags, settings, font):
    clauses = [c for c in flags["rules"].get("clauses", [])
               if c.get("checked", True) and (c.get("title") or c.get("text"))]
    if not clauses:
        return
    _heading(doc, "竞赛规则", level=1)
    for c in clauses:
        if c.get("title"):
            _heading(doc, c["title"], level=2)
        for line in (c.get("text") or "").splitlines():
            if line.strip():
                _text_para(doc, line)
    doc.add_page_break()


def _mod_committee(doc, state, flags, settings, font):
    groups = [g for g in flags["committee"].get("groups", [])
              if g.get("checked", True) and g.get("name")]
    if not groups:
        return
    _heading(doc, "竞赛委员会", level=1)
    for g in groups:
        _heading(doc, g["name"], level=2)
        if g.get("members"):
            _text_para(doc, g["members"])
    doc.add_page_break()


def _mod_referees(doc, state, flags, settings, font):
    groups = [g for g in flags["referees"].get("groups", [])
              if g.get("checked", True) and g.get("name")]
    if not groups:
        return
    _heading(doc, "裁判员名单", level=1)
    for g in groups:
        _heading(doc, g["name"], level=2)
        if g.get("members"):
            _text_para(doc, g["members"])
    doc.add_page_break()


def _mod_awards(doc, state, flags, settings, font):
    f = flags["awards"]
    rows = [r for r in (f.get("rows") or []) if any(str(v or "").strip() for v in r)]
    if not rows:
        return
    _heading(doc, "颁奖仪式", level=1)
    headers = f.get("headers") or ["项目", "领奖运动员名次", "集合地点",
                                   "集合时间", "颁奖时间", "颁奖嘉宾"]
    _table(doc, headers, rows)
    doc.add_page_break()


def _mod_schedule(doc, state, flags, settings, font):
    _heading(doc, "竞赛日程表", level=1)
    f = flags["schedule"]
    split = f.get("split_field_track", True)
    show_time = f.get("show_time", True)
    ordered = sort_events([e for e in state.events
                           if e.day and getattr(e, "enabled", True)])
    if not ordered:
        _text_para(doc, "（暂无赛程安排）")
        return
    by_day = defaultdict(list)
    for e in ordered:
        by_day[e.day].append(e)
    for day in sorted(by_day):
        _heading(doc, day, level=2)
        by_sess = defaultdict(list)
        for e in by_day[day]:
            by_sess[e.session or "未定时段"].append(e)
        for sess in sorted(by_sess, key=lambda s: {"上午": 0, "下午": 1}.get(s, 2)):
            _heading(doc, sess, level=3)
            evs = by_sess[sess]
            def row_of(e):
                r = [e.time or "—"] if show_time else []
                r += [e.grade or "—", e.name, e.group]
                if getattr(e, "show_venue", True):
                    r.append(e.venue or "—")
                return r
            if split:
                for label, etype in [("田赛", "田赛"), ("径赛", "径赛")]:
                    part = [e for e in evs if e.etype == etype]
                    if not part:
                        continue
                    _text_para(doc, label + "：", font="黑体", size=11, bold=True)
                    headers = (["时间"] if show_time else []) + ["年级", "项目", "组别"]
                    if any(getattr(e, "show_venue", True) for e in part):
                        headers.append("场地")
                    _table(doc, headers, [row_of(e) for e in part])
            else:
                headers = (["时间"] if show_time else []) + ["类型", "年级", "项目", "组别"]
                if any(getattr(e, "show_venue", True) for e in evs):
                    headers.append("场地")
                _table(doc, headers, [row_of(e) for e in evs])
    doc.add_page_break()


def _mod_rosters(doc, state, flags, settings, font):
    _heading(doc, "代表队名单及号码对照表", level=1)
    only = flags["rosters"].get("only_checked_classes", False)
    persons = {}
    for r in state.records:
        k = (r.class_name or "未分班", r.person)
        d = persons.setdefault(k, {"gender": r.gender, "number": r.number,
                                   "events": []})
        if r.event and r.event not in d["events"]:
            d["events"].append(r.event)
    classes = {c.name: c for c in state.classes}
    class_names = sorted({k[0] for k in persons})
    if only:
        class_names = [n for n in class_names
                       if classes.get(n) is None or classes.get(n).enabled]
    for cls in class_names:
        info = classes.get(cls)
        if info is not None and not info.show_roster:
            continue
        _heading(doc, cls, level=2)
        leader = info.leader if info is not None else ""
        num_range = info.num_range if info is not None else ""
        _text_para(doc, f"领队：{leader}" if leader else "领队：（待填写）")
        _text_para(doc, f"号码：{num_range}" if num_range else "号码：（待分配）")
        for g, label in [("男", "男子"), ("女", "女子")]:
            rows = []
            for (cn, person), d in sorted(persons.items()):
                if cn != cls or d["gender"] != g:
                    continue
                rows.append([len(rows) + 1, person, d["number"] or "—",
                             "、".join(d["events"]) or "—"])
            if rows:
                _heading(doc, label, level=3)
                _table(doc, ["序号", "姓名", "号码", "参赛项目"], rows)
    doc.add_page_break()


def _mod_grouping(doc, state, flags, settings, font):
    _heading(doc, "竞赛分组", level=1)
    only = flags["grouping"].get("only_checked_events", False)
    by_event = defaultdict(list)
    for r in state.records:
        if r.event:
            by_event[r.event].append(r)
    names = sorted(by_event)
    if only:
        names = [n for n in names
                 if state.find_event(n) is None
                 or state.find_event(n).enabled]
    if not names:
        _text_para(doc, "（暂无报名数据）")
        return
    for ev_name in names:
        recs = sorted(by_event[ev_name], key=lambda x: (x.class_name, x.person))
        _heading(doc, f"{ev_name}（{len(recs)}人）", level=2)
        line = "；".join(f"{i + 1} {r.person}（{r.class_name}）"
                        for i, r in enumerate(recs))
        _text_para(doc, "一组：" + line if line else "（无参赛人员）")
    doc.add_page_break()


def _mod_class_list(doc, state, flags, settings, font):
    _heading(doc, "各班参赛名单", level=1)
    if not state.records:
        _text_para(doc, "（暂无报名数据）")
        return
    by_class = defaultdict(list)
    for r in state.records:
        by_class[r.class_name or "未分班"].append(r)
    for cls in sorted(by_class):
        _heading(doc, f"{cls} 参赛名单", level=2)
        rows = [[i + 1, r.person, r.gender or "—", r.event or "—", r.group or "—"]
                for i, r in enumerate(sorted(by_class[cls], key=lambda x: x.person))]
        _table(doc, ["序号", "姓名", "性别", "项目", "组别"], rows)
    doc.add_page_break()


def _mod_event_list(doc, state, flags, settings, font):
    _heading(doc, "各项目参赛人员", level=1)
    if not state.records:
        _text_para(doc, "（暂无报名数据）")
        return
    by_event = defaultdict(list)
    for r in state.records:
        if r.event:
            by_event[r.event].append(r)
    for ev in sorted(by_event):
        _heading(doc, ev, level=2)
        men = [r for r in by_event[ev] if r.gender == "男"]
        women = [r for r in by_event[ev] if r.gender == "女"]
        others = [r for r in by_event[ev] if r.gender not in ("男", "女")]
        if men:
            _heading(doc, "男子组", level=3)
            _table(doc, ["序号", "班级", "姓名", "组别"],
                   [[i + 1, r.class_name, r.person, r.group or "—"]
                    for i, r in enumerate(sorted(men, key=lambda x: x.class_name))])
        if women:
            _heading(doc, "女子组", level=3)
            _table(doc, ["序号", "班级", "姓名", "组别"],
                   [[i + 1, r.class_name, r.person, r.group or "—"]
                    for i, r in enumerate(sorted(women, key=lambda x: x.class_name))])
        if others:
            _heading(doc, "混合/待定", level=3)
            _table(doc, ["序号", "班级", "姓名", "性别", "组别"],
                   [[i + 1, r.class_name, r.person, r.gender or "—", r.group or "—"]
                    for i, r in enumerate(sorted(others, key=lambda x: x.class_name))])
    doc.add_page_break()


def _mod_appendix(doc, state, flags, settings, font):
    items = [it for it in flags["appendix"].get("items", [])
             if it.get("checked", True) and (it.get("title") or it.get("text"))]
    if not items:
        return
    _heading(doc, "附录", level=1)
    for it in items:
        if it.get("title"):
            _heading(doc, it["title"], level=2)
        for line in (it.get("text") or "").splitlines():
            if line.strip():
                _text_para(doc, line)
    doc.add_page_break()


def _mod_records(doc, state, flags, settings, font):
    r = flags["records"]
    subs = [("male", "男子校纪录"), ("female", "女子校纪录"),
            ("national", "国家学生体质健康标准最高纪录")]
    any_out = False
    for sub, title in subs:
        if not r.get(sub, True):
            continue
        rows = [row for row in (r.get(sub + "_rows") or [])
                if any(str(v or "").strip() for v in row)]
        if not rows:
            continue
        any_out = True
        _heading(doc, title, level=2)
        headers = r.get(sub + "_headers") or ["项目", "纪录", "保持者", "年份"]
        _table(doc, headers, rows)
    if any_out:
        _heading(doc, "校纪录", level=1)
    # 注：标题先输出的顺序问题这里做妥协：实际输出顺序为标题在各表前
    doc.add_page_break()


_GENERATORS = {
    "notice": _mod_notice, "rules": _mod_rules, "committee": _mod_committee,
    "referees": _mod_referees, "awards": _mod_awards, "schedule": _mod_schedule,
    "rosters": _mod_rosters, "grouping": _mod_grouping,
    "class_list": _mod_class_list, "event_list": _mod_event_list,
    "appendix": _mod_appendix, "records": _mod_records,
}


def generate_document(path, state, template_name=""):
    settings = state.settings
    font = settings.get("font") or "宋体"
    flags = module_flags.get_flags()

    if template_name and template_name != "默认模板":
        tpl = os.path.join(config.TEMPLATE_DIR, template_name)
        doc = Document(tpl) if os.path.exists(tpl) else Document()
    else:
        doc = Document()
    _apply_font(doc, settings)

    if flags.get("cover", {}).get("enabled", True):
        _mod_cover(doc, state, flags, settings, font)
    _toc(doc, flags)

    for key, _title in module_flags.MODULE_ORDER:
        if key == "cover":
            continue
        if not flags.get(key, {}).get("enabled", True):
            continue
        _GENERATORS[key](doc, state, flags, settings, font)

    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    doc.save(path)
    return path
'''


def main():
    print("运动会秩序册生成工具 第二轮更新 脚本A（app 层）")
    print("=" * 50)
    ok = 0
    fail = []
    for rel, content in FILES.items():
        path = os.path.join(BASE, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            py_compile.compile(path, doraise=True)
            print(f"  [OK] {rel}（{len(content)} 字符，语法检查通过）")
            ok += 1
        except py_compile.PyCompileError as e:
            print(f"  [失败] {rel}")
            print(str(e))
            fail.append(rel)
    print("=" * 50)
    if fail:
        print(f"完成 {ok} 个，失败 {len(fail)} 个：{fail}")
        print("请把上方错误信息发回给助手。")
        sys.exit(1)
    print(f"全部 {ok} 个文件写入并检查通过。")
    print("注意：现在还不能启动程序（ui 层未更新）。")
    print("请继续运行第二部分：update_v2_b.py")


if __name__ == "__main__":
    main()
