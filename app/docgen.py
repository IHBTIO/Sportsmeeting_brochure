# -*- coding: utf-8 -*-
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
