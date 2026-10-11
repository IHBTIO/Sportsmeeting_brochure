# -*- coding: utf-8 -*-
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

# 通用表格导入的列名关键词（校纪录/颁奖等）
TABLE_COL_GUESS = {
    "项目": ["项目", "竞赛项目", "赛事", "比赛项目"],
    "纪录": ["纪录", "成绩", "最高", "校纪录"],
    "标准": ["标准", "达标", "及格"],
    "说明": ["说明", "备注", "注"],
    "保持者": ["保持者", "姓名", "创造者", "保持人"],
    "年份": ["年份", "年度", "年"],
    "领奖运动员名次": ["名次", "领奖", "运动员名次"],
    "集合地点": ["集合地点", "地点", "集合"],
    "集合时间": ["集合时间"],
    "颁奖时间": ["颁奖时间"],
    "颁奖嘉宾": ["嘉宾", "颁奖嘉宾"],
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


def guess_table_mapping(fields, columns):
    """通用表格列名猜测（按关键词子串匹配，不重复占用列）。"""
    mapping = {f: "" for f in fields}
    used = set()
    for f in fields:
        for c in columns:
            c = str(c).strip()
            if c in used:
                continue
            keys = TABLE_COL_GUESS.get(f, [f])
            if any(k in c for k in keys):
                mapping[f] = c
                used.add(c)
                break
    return mapping


def build_rows_by_mapping(df, mapping, fields):
    """按映射从 DataFrame 构建行：未映射列忽略，缺列留空，空行跳过。"""
    rows = []
    cols = list(df.columns)
    for _, row in df.iterrows():
        vals = []
        empty = True
        for f in fields:
            col = mapping.get(f, "")
            if not col or col not in cols:
                v = ""
            else:
                raw = row[col]
                v = "" if (raw is None or pd.isna(raw)) else str(raw).strip()
            if v:
                empty = False
            vals.append(v)
        if not empty:
            rows.append(vals)
    return rows


def normalize_time_text(t):
    return str(t or "").strip().replace("：", ":").replace("．", ":")


def build_records(df, mapping, split_multi=True, switches=None):
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
