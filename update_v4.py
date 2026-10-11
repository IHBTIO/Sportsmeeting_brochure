# -*- coding: utf-8 -*-
"""运动会秩序册生成工具 第四轮更新。

用法：python update_v4.py
内容：
- 数据导入页改为多类型导入中枢：
  报名信息导入 / 校纪录导入 / 体质健康标准导入 / 其他表格导入，
  每种都带字段映射（额外列忽略、缺列留空，不会串数据），
  目标表为显式下拉，支持覆盖/追加。
- 秩序册模块：条款/人员组改为行内删除（每条右侧删除按钮）。
- 项目管理：表格加“操作”列，每行一个删除按钮。
- app/importer.py 增加通用映射行构建（build_rows_by_mapping）。
"""
import os
import py_compile
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

FILES = {}

# ============================================================
# app/importer.py（追加通用映射导入；其余不变，整体替换）
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
'''

# ============================================================
# ui/import_page.py（多类型导入中枢）
# ============================================================
FILES["ui/import_page.py"] = r'''# -*- coding: utf-8 -*-
"""数据导入页：多类型导入中枢。

顶部类型栏：报名信息 / 校纪录 / 体质健康标准 / 其他表格。
每种类型都走：选择文件 -> 预览 -> 字段映射（左列指向右字段）-> 导入。
映射后未指定的列直接忽略，额外列不会串数据。支持覆盖/追加。
"""
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGroupBox,
                               QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QStackedWidget, QTableWidget, QVBoxLayout,
                               QWidget)

from app.importer import (FIELDS, build_records, build_rows_by_mapping,
                          classes_from_records, guess_mapping,
                          guess_table_mapping, load_table)
from app import module_flags
from ui.widgets import setup_table, plain_item

TABLE_TARGETS = {
    "男子校纪录": ("records", "male"),
    "女子校纪录": ("records", "female"),
    "国家学生体质健康标准最高纪录": ("records", "national"),
    "颁奖仪式": ("awards", None),
}

TARGET_FIELDS = {
    "男子校纪录": ["项目", "纪录", "保持者", "年份"],
    "女子校纪录": ["项目", "纪录", "保持者", "年份"],
    "国家学生体质健康标准最高纪录": ["项目", "标准", "说明", "年份"],
    "颁奖仪式": ["项目", "领奖运动员名次", "集合地点", "集合时间",
                "颁奖时间", "颁奖嘉宾"],
}


def _mapping_box():
    box = QGroupBox("字段映射（表格列 指向 字段；未指定的列将被忽略）")
    v = QVBoxLayout(box)
    return box, v


class _MappingRow(QWidget):
    def __init__(self, field, combo):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(combo, 1)
        arrow = QLabel("→")
        arrow.setStyleSheet("color: #1a4f8a; font-weight: bold;")
        h.addWidget(arrow)
        lab = QLabel(field)
        lab.setStyleSheet("font-weight: bold;")
        h.addWidget(lab)


class BaseImportPanel(QWidget):
    """通用导入面板：选文件 + 预览 + 映射 + 模式 + 导入按钮。"""

    def __init__(self, state, main):
        super().__init__()
        self.state = state
        self.main = main
        self.df = None

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.btn_open = QPushButton("选择文件")
        self.btn_open.clicked.connect(self.choose_file)
        self.btn_import = QPushButton("导入")
        self.btn_import.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 4px 12px;")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self.do_import)
        self.lbl_file = QLabel("未选择文件")
        top.addWidget(self.btn_open)
        top.addWidget(self.btn_import)
        top.addStretch(1)
        top.addWidget(self.lbl_file)
        root.addLayout(top)

        self.preview = QTableWidget()
        setup_table(self.preview, ["（请先选择文件）"])
        root.addWidget(self.preview, 2)

        self.map_box, self.map_lay = _mapping_box()
        root.addWidget(self.map_box)
        self.combos = {}

        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["覆盖导入", "追加导入"])
        root.addWidget(self.cb_mode)

        self._build_extra(root)

    def _build_extra(self, root):
        pass

    # ---- 文件 ----
    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "",
            "表格 (*.xlsx *.xls *.csv);;所有文件 (*.*)")
        if not path:
            return
        try:
            self.df = load_table(path)
        except Exception as e:
            QMessageBox.critical(self, "读取失败", f"无法读取文件：\n{e}")
            return
        self.lbl_file.setText(path)
        self.show_preview()
        self.rebuild_mapping()
        self.btn_import.setEnabled(True)

    def show_preview(self):
        df = self.df
        setup_table(self.preview, list(df.columns))
        self.preview.setRowCount(0)
        for _, row in df.head(50).iterrows():
            i = self.preview.rowCount()
            self.preview.insertRow(i)
            for j, v in enumerate(row):
                self.preview.setItem(i, j, plain_item(v))

    # ---- 映射 ----
    def fields(self):
        return []

    def rebuild_mapping(self):
        while self.map_lay.count():
            it = self.map_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.combos = {}
        if self.df is None:
            return
        cols = [str(c).strip() for c in self.df.columns]
        guessed = self.guess_mapping(cols)
        for f in self.fields():
            cb = QComboBox()
            cb.addItem("（不使用）")
            cb.addItems(cols)
            if guessed.get(f) and guessed[f] in cols:
                cb.setCurrentText(guessed[f])
            self.combos[f] = cb
            self.map_lay.addWidget(_MappingRow(f, cb))

    def guess_mapping(self, cols):
        return guess_table_mapping(self.fields(), cols)

    def current_mapping(self):
        return {f: (cb.currentText() if cb.currentText() != "（不使用）" else "")
                for f, cb in self.combos.items()}

    def do_import(self):
        pass

    def refresh(self):
        pass


class SignupPanel(BaseImportPanel):
    """报名信息导入（原功能整体保留）。"""

    def _build_extra(self, root):
        self.chk_split = QCheckBox("一人多项目自动拆行")
        self.chk_split.setChecked(True)
        self.cb_mode.parentWidget().layout().insertWidget(
            self.cb_mode.parentWidget().layout().indexOf(self.cb_mode),
            self.chk_split) if False else None
        # 插入到模式选择之前
        root = self.layout()
        idx = root.indexOf(self.cb_mode)
        root.insertWidget(idx, self.chk_split)
        self.btn_import.setText("导入并生成报名记录")

    def fields(self):
        return FIELDS

    def guess_mapping(self, cols):
        return guess_mapping(cols)

    def do_import(self):
        if self.df is None:
            return
        mapping = self.current_mapping()
        if not mapping.get("姓名") or not mapping.get("项目"):
            QMessageBox.warning(self, "映射不完整",
                                "请至少指定“姓名”和“项目”两列的映射。")
            return
        switches = module_flags.get_flags().get("recognize", {})
        records = build_records(self.df, mapping, self.chk_split.isChecked(),
                                switches)
        if not records:
            QMessageBox.warning(self, "无有效数据", "按当前映射没有生成任何记录。")
            return
        for cls in classes_from_records(records):
            self.state.ensure_class(cls)
        append = self.cb_mode.currentIndex() == 1
        if append:
            self.state.records.extend(records)
        else:
            self.state.records = records
        self.state.save()
        self.main.refresh_all()

        yellow_line = int(switches.get("yellow", 90))
        red_line = int(switches.get("red", 60))
        red = sum(1 for r in records if r.confidence < red_line)
        yellow = sum(1 for r in records
                     if red_line <= r.confidence < yellow_line)
        word = "追加" if append else "导入"
        QMessageBox.information(
            self, word + "完成",
            f"本次{word} {len(records)} 条，当前共 {len(self.state.records)} 条。\n"
            f"自动通过：{len(records) - red - yellow}\n"
            f"建议核对（黄色）：{yellow}\n"
            f"需人工审查（红色）：{red}")


class TablePanel(BaseImportPanel):
    """通用表格导入：目标表显式下拉，映射后写入秩序册模块对应表格。"""

    def __init__(self, state, main, target_keys):
        self.target_keys = target_keys   # 可选目标表名列表
        super().__init__(state, main)

    def _build_extra(self, root):
        row = QHBoxLayout()
        row.addWidget(QLabel("目标表："))
        self.cb_target = QComboBox()
        self.cb_target.addItems(self.target_keys)
        self.cb_target.currentTextChanged.connect(lambda _t: self.rebuild_mapping())
        row.addWidget(self.cb_target, 1)
        root.insertLayout(0, row)

    def fields(self):
        return TARGET_FIELDS.get(self.target(), [])

    def target(self):
        return self.cb_target.currentText() if hasattr(self, "cb_target") \
            else self.target_keys[0]

    def do_import(self):
        if self.df is None:
            return
        mapping = self.current_mapping()
        if not any(mapping.values()):
            QMessageBox.warning(self, "映射为空",
                                "请至少指定一个字段的映射。")
            return
        rows = build_rows_by_mapping(self.df, mapping, self.fields())
        if not rows:
            QMessageBox.warning(self, "无有效数据", "按当前映射没有生成任何行。")
            return
        # 首行与字段名一致时视为表头，跳过
        if rows[0] == self.fields():
            rows = rows[1:]
        if not rows:
            QMessageBox.information(self, "提示", "只有表头，没有数据。")
            return

        target = self.target()
        mod_key, sub_key = TABLE_TARGETS[target]
        flags = module_flags.get_flags()
        mod = flags[mod_key]
        if sub_key:
            mod[sub_key] = True   # 自动勾选该子表
            store = mod.setdefault(sub_key + "_rows", [])
        else:
            store = mod.setdefault("rows", [])
        append = self.cb_mode.currentIndex() == 1
        if append:
            store.extend(rows)
        else:
            store[:] = rows
        module_flags.save_flags()
        word = "追加" if append else "导入"
        ret = QMessageBox.question(
            self, word + "完成",
            f"已{word} {len(rows)} 行到「{target}」。\n"
            f"当前该表共 {len(store)} 行。\n\n是否前往“秩序册模块”查看？")
        if ret == QMessageBox.Yes:
            self.main.goto("秩序册模块")


class ImportPage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        root = QVBoxLayout(self)

        # 顶部类型栏
        type_bar = QHBoxLayout()
        self.type_btns = []
        self.panels = [
            ("报名信息导入", SignupPanel(state, main_win)),
            ("校纪录导入", TablePanel(state, main_win,
                                     ["男子校纪录", "女子校纪录"])),
            ("体质健康标准导入", TablePanel(
                state, main_win, ["国家学生体质健康标准最高纪录"])),
            ("其他表格导入", TablePanel(
                state, main_win, ["颁奖仪式", "男子校纪录", "女子校纪录",
                                  "国家学生体质健康标准最高纪录"])),
        ]
        self.stack = QStackedWidget()
        for i, (name, panel) in enumerate(self.panels):
            b = QPushButton(name)
            b.setCheckable(True)
            if i == 0:
                b.setChecked(True)
                b.setStyleSheet("font-weight: bold;")
            b.clicked.connect(lambda _c, idx=i: self.switch_to(idx))
            type_bar.addWidget(b)
            self.type_btns.append(b)
            self.stack.addWidget(panel)
        root.addLayout(type_bar)
        root.addWidget(self.stack, 1)

    def switch_to(self, idx):
        for i, b in enumerate(self.type_btns):
            b.setChecked(i == idx)
            b.setStyleSheet("font-weight: bold;" if i == idx else "")
        self.stack.setCurrentIndex(idx)

    def refresh(self):
        pass
'''

# ============================================================
# ui/modules_page.py（行内删除）
# ============================================================
FILES["ui/modules_page.py"] = r'''# -*- coding: utf-8 -*-
"""秩序册模块页。

- 每个模块一个分组框，母标题加大加粗。
- 勾选 = 参与生成；取消 = 完全跳过。
- 长文本：可点“导入”选 txt/docx，也可把文件直接拖到文本框（只提取文字）。
- 预设：只出现在下拉选项，选择后填入，不自动写入。
- 条款/条目/分组：行内删除（每条右侧删除按钮）。
- 表格类：支持从 Excel/CSV 导入（在“数据导入”页也可导入）。
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton,
                               QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from app import module_flags, presets, text_import

TITLE_STYLE = (
    "QGroupBox::title { subcontrol-origin: margin; "
    "font-size: 15px; font-weight: bold; color: #1a4f8a; padding: 2px 6px; }"
    "QGroupBox { margin-top: 12px; }")

TEXT_FILTER = "文本 (*.txt *.docx);;所有文件 (*.*)"
TABLE_FILTER = "表格 (*.xlsx *.xls *.csv);;所有文件 (*.*)"


class DropTextEdit(QPlainTextEdit):
    """支持把 txt/docx 文件拖进来导入文字。"""
    dropped = Signal(str)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            e.acceptProposedAction()
            self.dropped.emit(urls[0].toLocalFile())


def _load_text_to(path, ed, parent):
    try:
        ed.setPlainText(text_import.load_text(path))
    except Exception as e:
        QMessageBox.warning(parent, "导入失败", str(e))


def _pick_text(ed, parent):
    path, _ = QFileDialog.getOpenFileName(parent, "导入文本", "", TEXT_FILTER)
    if path:
        _load_text_to(path, ed, parent)


# ---------------- 条款编辑器（预设 + 新建 + 行内删除） ----------------
class ClausesEditor(QWidget):
    def __init__(self, clauses, on_save, preset_list=None):
        super().__init__()
        self.clauses = clauses
        self.on_save = on_save
        self.presets = preset_list or []
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        if self.presets:
            self.cb = QComboBox()
            self.cb.addItem("（预设）")
            for t, _txt in self.presets:
                self.cb.addItem(t)
            bar.addWidget(self.cb, 1)
            b_use = QPushButton("填入预设")
            b_use.clicked.connect(self.apply_preset)
            bar.addWidget(b_use)
        b_new = QPushButton("新建一条")
        b_new.clicked.connect(self.new_clause)
        bar.addWidget(b_new)
        bar.addStretch(1)
        v.addLayout(bar)
        self.rows_area = QWidget()
        self.rows_lay = QVBoxLayout(self.rows_area)
        self.rows_lay.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.rows_area)
        self.rebuild()

    def apply_preset(self):
        i = self.cb.currentIndex()
        if i <= 0:
            return
        title, text = self.presets[i - 1]
        self.clauses.append({"checked": True, "title": title, "text": text})
        self.on_save()
        self.rebuild()

    def new_clause(self):
        self.clauses.append({"checked": True, "title": "", "text": ""})
        self.on_save()
        self.rebuild()

    def del_clause(self, idx):
        if 0 <= idx < len(self.clauses):
            self.clauses.pop(idx)
            self.on_save()
            self.rebuild()

    def rebuild(self):
        while self.rows_lay.count():
            it = self.rows_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for i, c in enumerate(self.clauses):
            self.rows_lay.addWidget(
                _clause_row(c, self.on_save,
                            lambda idx=i: self.del_clause(idx)))


def _clause_row(data, on_change, on_delete=None):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    cb = QCheckBox()
    cb.setChecked(bool(data.get("checked", True)))
    ed_title = QLineEdit(data.get("title", ""))
    ed_title.setFixedWidth(160)
    ed_text = DropTextEdit(data.get("text", ""))
    ed_text.setFixedHeight(56)
    ed_text.dropped.connect(lambda p: _load_text_to(p, ed_text, w))
    b_imp = QPushButton("导入")
    b_imp.clicked.connect(lambda: _pick_text(ed_text, w))
    b_del = QPushButton("删除")
    b_del.clicked.connect(lambda: on_delete() if on_delete else None)

    def sync():
        data["checked"] = cb.isChecked()
        data["title"] = ed_title.text()
        data["text"] = ed_text.toPlainText()
        on_change()

    cb.toggled.connect(lambda _on: sync())
    ed_title.textChanged.connect(lambda _t: sync())
    ed_text.textChanged.connect(sync)
    lay.addWidget(cb)
    lay.addWidget(ed_title)
    lay.addWidget(ed_text, 1)
    lay.addWidget(b_imp)
    if on_delete is not None:
        lay.addWidget(b_del)
    return w


# ---------------- 人员组编辑器（新建 + 行内删除） ----------------
class GroupsEditor(QWidget):
    def __init__(self, groups, on_save):
        super().__init__()
        self.groups = groups
        self.on_save = on_save
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        b_new = QPushButton("新建一组")
        b_new.clicked.connect(self.new_group)
        bar.addWidget(b_new)
        bar.addStretch(1)
        v.addLayout(bar)
        self.rows_area = QWidget()
        self.rows_lay = QVBoxLayout(self.rows_area)
        self.rows_lay.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.rows_area)
        self.rebuild()

    def new_group(self):
        self.groups.append({"checked": True, "name": "", "members": ""})
        self.on_save()
        self.rebuild()

    def del_group(self, idx):
        if 0 <= idx < len(self.groups):
            self.groups.pop(idx)
            self.on_save()
            self.rebuild()

    def rebuild(self):
        while self.rows_lay.count():
            it = self.rows_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for i, g in enumerate(self.groups):
            self.rows_lay.addWidget(
                _member_group(g, self.on_save,
                              lambda idx=i: self.del_group(idx)))


def _member_group(data, on_change, on_delete=None):
    gb = QGroupBox()
    gb.setCheckable(True)
    gb.setChecked(bool(data.get("checked", True)))
    lay = QHBoxLayout(gb)
    ed_name = QLineEdit(data.get("name", ""))
    ed_name.setFixedWidth(220)
    ed_members = DropTextEdit(data.get("members", ""))
    ed_members.setFixedHeight(52)
    ed_members.dropped.connect(lambda p: _load_text_to(p, ed_members, gb))
    b_imp = QPushButton("导入")
    b_imp.clicked.connect(lambda: _pick_text(ed_members, gb))
    b_del = QPushButton("删除本组")
    b_del.clicked.connect(lambda: on_delete() if on_delete else None)

    def sync():
        data["checked"] = gb.isChecked()
        data["name"] = ed_name.text()
        data["members"] = ed_members.toPlainText()
        on_change()

    gb.toggled.connect(lambda _on: sync())
    ed_name.textChanged.connect(lambda _t: sync())
    ed_members.textChanged.connect(sync)
    lay.addWidget(QLabel("名称："))
    lay.addWidget(ed_name)
    lay.addWidget(ed_members, 1)
    lay.addWidget(b_imp)
    if on_delete is not None:
        lay.addWidget(b_del)
    return gb


# ---------------- 表格编辑器（带导入） ----------------
def _table_editor(headers, rows, on_change):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels([str(h) for h in headers])
    table.horizontalHeader().setStretchLastSection(True)

    def populate():
        table.blockSignals(True)
        table.setRowCount(0)
        for row in rows:
            i = table.rowCount()
            table.insertRow(i)
            for j, val in enumerate(row):
                table.setItem(i, j,
                              QTableWidgetItem(str(val if val is not None else "")))
        table.blockSignals(False)

    def sync():
        rows.clear()
        for i in range(table.rowCount()):
            rows.append([table.item(i, j).text() if table.item(i, j) else ""
                         for j in range(table.columnCount())])
        on_change()

    populate()
    table.cellChanged.connect(lambda *_: sync())

    def add_row():
        table.blockSignals(True)
        i = table.rowCount()
        table.insertRow(i)
        for j in range(table.columnCount()):
            table.setItem(i, j, QTableWidgetItem(""))
        table.blockSignals(False)
        sync()

    def del_row():
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)
            sync()

    def import_rows():
        path, _ = QFileDialog.getOpenFileName(w, "导入表格", "", TABLE_FILTER)
        if not path:
            return
        try:
            new_rows = text_import.load_table_rows(path, len(headers))
        except Exception as e:
            QMessageBox.warning(w, "导入失败", str(e))
            return
        if not new_rows:
            QMessageBox.information(w, "提示", "文件中没有数据行。")
            return
        if [str(h) for h in headers] == new_rows[0]:
            new_rows = new_rows[1:]
        if not new_rows:
            QMessageBox.information(w, "提示", "只有表头一行，没有数据。")
            return
        rows[:] = new_rows
        on_change()
        populate()

    btns = QHBoxLayout()
    for text, slot in [("添加一行", add_row), ("删除选中行", del_row),
                       ("导入表格", import_rows)]:
        b = QPushButton(text)
        b.clicked.connect(slot)
        btns.addWidget(b)
    btns.addStretch(1)
    v.addWidget(table)
    v.addLayout(btns)
    return w


# ---------------- 页面 ----------------
class ModulesPage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        self.flags = module_flags.get_flags()

        outer = QVBoxLayout(self)
        outer.addWidget(QLabel(
            "勾选 = 参与生成；取消勾选 = 完全跳过。\n"
            "长文本可点“导入”选文件，或直接把 txt/docx 拖到文本框上。\n"
            "改动即时保存。表格类数据也可在“数据导入”页导入。"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_lay = QVBoxLayout(body)
        for key, title in module_flags.MODULE_ORDER:
            body_lay.addWidget(self._build(key, title))
        body_lay.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    def _save(self):
        module_flags.save_flags()

    def _build(self, key, title):
        f = self.flags[key]
        gb = QGroupBox(title)
        gb.setCheckable(True)
        gb.setChecked(bool(f.get("enabled", True)))
        gb.setStyleSheet(TITLE_STYLE)

        def sync_enabled(on, k=key):
            self.flags[k]["enabled"] = on
            self._save()

        gb.toggled.connect(sync_enabled)
        lay = QVBoxLayout(gb)
        getattr(self, "_build_" + key)(lay, f)
        return gb

    def _flag_cb(self, f, key, text):
        cb = QCheckBox(text)
        cb.setChecked(bool(f.get(key, True)))

        def sync(on):
            f[key] = on
            self._save()

        cb.toggled.connect(sync)
        return cb

    # ---------- 各模块 ----------
    def _build_cover(self, lay, f):
        form = QFormLayout()
        cb_img = self._flag_cb(f, "image_enabled", "插入封面图片")
        row = QHBoxLayout()
        ed_path = QLineEdit(f.get("image_path", ""))

        def sync_path():
            f["image_path"] = ed_path.text()
            self._save()

        ed_path.textChanged.connect(lambda _t: sync_path())
        b = QPushButton("浏览")
        b.clicked.connect(lambda: self._pick_image(ed_path))
        row.addWidget(ed_path, 1)
        row.addWidget(b)
        form.addRow(cb_img, row)
        cb_slogan = self._flag_cb(f, "slogan_enabled", "显示导语")
        ed_slogan = QLineEdit(f.get("slogan", ""))

        def sync_slogan():
            f["slogan"] = ed_slogan.text()
            self._save()

        ed_slogan.textChanged.connect(lambda _t: sync_slogan())
        form.addRow(cb_slogan, ed_slogan)
        ed_date = QLineEdit(f.get("date_text", ""))
        ed_date.setPlaceholderText("留空自动当年当月")

        def sync_date():
            f["date_text"] = ed_date.text()
            self._save()

        ed_date.textChanged.connect(lambda _t: sync_date())
        form.addRow("封面日期：", ed_date)
        lay.addLayout(form)
        lay.addWidget(QLabel("学校名称、年份、届次在“生成秩序册”页填写。"))

    def _pick_image(self, ed_path):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择封面图片", "", "图片 (*.png *.jpg *.jpeg *.bmp)")
        if path:
            ed_path.setText(path)

    def _build_notice(self, lay, f):
        form = QFormLayout()
        ed_title = QLineEdit(f.get("title", ""))
        ed_title.setPlaceholderText("支持 {school} {year} {term} 占位符")
        ed_body = DropTextEdit(f.get("body", ""))
        ed_body.setFixedHeight(110)
        ed_body.dropped.connect(lambda p: _load_text_to(p, ed_body, self))
        b_imp = QPushButton("导入正文")
        b_imp.clicked.connect(lambda: _pick_text(ed_body, self))

        def sync_title():
            f["title"] = ed_title.text()
            self._save()

        def sync_body():
            f["body"] = ed_body.toPlainText()
            self._save()

        ed_title.textChanged.connect(lambda _t: sync_title())
        ed_body.textChanged.connect(sync_body)
        form.addRow("标题：", ed_title)
        form.addRow("正文：", ed_body)
        form.addRow("", b_imp)
        lay.addLayout(form)

    def _build_rules(self, lay, f):
        lay.addWidget(ClausesEditor(f.get("clauses", []), self._save,
                                    presets.list_rule_presets()))

    def _build_committee(self, lay, f):
        lay.addWidget(GroupsEditor(f.get("groups", []), self._save))

    def _build_referees(self, lay, f):
        lay.addWidget(GroupsEditor(f.get("groups", []), self._save))

    def _build_awards(self, lay, f):
        rows = f.setdefault("rows", [])
        lay.addWidget(_table_editor(f.get("headers", []), rows, self._save))

    def _build_schedule(self, lay, f):
        lay.addWidget(self._flag_cb(f, "split_field_track", "田赛/径赛分开显示"))
        lay.addWidget(self._flag_cb(f, "show_time", "显示时间"))
        lay.addWidget(self._flag_cb(f, "show_count", "显示人数、组数"))
        lay.addWidget(QLabel("日程数据来自“项目管理”右侧的赛程设置。"))

    def _build_rosters(self, lay, f):
        lay.addWidget(self._flag_cb(f, "only_checked_classes", "只输出勾选的班级"))
        lay.addWidget(QLabel("班级参与、领队、号码范围在“班级管理”页编辑。"))

    def _build_grouping(self, lay, f):
        lay.addWidget(self._flag_cb(f, "only_checked_events", "只输出勾选的项目"))

    def _build_class_list(self, lay, f):
        lay.addWidget(QLabel("按班级输出参赛名单表格。"))

    def _build_event_list(self, lay, f):
        lay.addWidget(QLabel("按项目输出参赛人员，分男子/女子。"))

    def _build_appendix(self, lay, f):
        lay.addWidget(ClausesEditor(f.get("items", []), self._save,
                                    presets.APPENDIX_PRESETS))

    def _build_records(self, lay, f):
        for k, title in [("male", "男子校纪录"), ("female", "女子校纪录"),
                         ("national", "国家学生体质健康标准最高纪录")]:
            sub = QGroupBox(title)
            sub.setCheckable(True)
            sub.setChecked(bool(f.get(k, True)))
            sublay = QVBoxLayout(sub)
            rows = f.setdefault(k + "_rows", [])
            sublay.addWidget(_table_editor(f.get(k + "_headers", []), rows,
                                           self._save))

            def sync(on, k=k):
                f[k] = on
                self._save()

            sub.toggled.connect(sync)
            lay.addWidget(sub)

    def refresh(self):
        pass
'''

# ============================================================
# ui/project_page.py（操作列行内删除）
# ============================================================
FILES["ui/project_page.py"] = r'''# -*- coding: utf-8 -*-
"""项目管理页（左）+ 赛程管理（右）。"""
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPlainTextEdit,
                               QPushButton, QSplitter, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from app.data_models import default_events
from app.importer import normalize_time_text
from app.schedule import (check_all, detect_event_overlaps, move_event,
                          sort_events)
from ui.widgets import setup_table, plain_item

P_HEAD = ["名称", "类型", "组别", "年级", "比赛日", "时段", "时间",
          "场地", "规则说明", "校记录", "备注", "参与", "操作"]
ENABLED_COL = len(P_HEAD) - 2
OP_COL = len(P_HEAD) - 1
S_HEAD = ["比赛日", "时段", "时间", "类型", "年级", "项目", "组别", "场地", "状态"]

YELLOW = QColor(255, 244, 189)
RED = QColor(255, 205, 205)
GRADES = ["", "高一", "高二", "高三", "初一", "初二", "初三"]


class EventDialog(QDialog):
    def __init__(self, parent, ev=None):
        super().__init__(parent)
        self.setWindowTitle("编辑项目" if ev else "新增项目")
        form = QFormLayout(self)
        self.ed_name = QLineEdit(ev.name if ev else "")
        self.cb_type = QComboBox()
        self.cb_type.addItems(["径赛", "田赛"])
        self.cb_group = QComboBox()
        self.cb_group.addItems(["男", "女", "混合"])
        self.cb_grade = QComboBox()
        self.cb_grade.setEditable(True)
        self.cb_grade.addItems(GRADES)
        self.cb_session = QComboBox()
        self.cb_session.addItems(["", "上午", "下午"])
        self.ed_day = QLineEdit(ev.day if ev else date.today().isoformat())
        self.ed_time = QLineEdit(ev.time if ev else "")
        self.ed_time.setPlaceholderText("时:分")
        self.ed_venue = QLineEdit(ev.venue if ev else "")
        self.ed_record = QLineEdit(ev.record if ev else "")
        self.ed_note = QLineEdit(ev.note if ev else "")
        self.ed_rule = QPlainTextEdit(ev.rule if ev else "")
        self.cb_enabled = QCheckBox("参与秩序册")
        self.cb_venue = QCheckBox("输出场地")
        if ev:
            self.cb_type.setCurrentText(ev.etype)
            self.cb_group.setCurrentText(ev.group)
            self.cb_grade.setCurrentText(ev.grade or "")
            self.cb_session.setCurrentText(ev.session or "")
            self.cb_enabled.setChecked(ev.enabled)
            self.cb_venue.setChecked(getattr(ev, "show_venue", True))
        else:
            self.cb_enabled.setChecked(True)
            self.cb_venue.setChecked(True)
        form.addRow("名称：", self.ed_name)
        form.addRow("类型：", self.cb_type)
        form.addRow("组别：", self.cb_group)
        form.addRow("年级：", self.cb_grade)
        form.addRow("比赛日：", self.ed_day)
        form.addRow("时段：", self.cb_session)
        form.addRow("时间：", self.ed_time)
        form.addRow("场地：", self.ed_venue)
        form.addRow("输出场地：", self.cb_venue)
        form.addRow("校记录：", self.ed_record)
        form.addRow("备注：", self.ed_note)
        form.addRow("规则说明：", self.ed_rule)
        form.addRow(self.cb_enabled)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def values(self):
        return dict(name=self.ed_name.text().strip(),
                    etype=self.cb_type.currentText(),
                    group=self.cb_group.currentText(),
                    grade=self.cb_grade.currentText().strip(),
                    day=self.ed_day.text().strip(),
                    session=self.cb_session.currentText(),
                    time=normalize_time_text(self.ed_time.text()),
                    venue=self.ed_venue.text().strip(),
                    record=self.ed_record.text().strip(),
                    note=self.ed_note.text().strip(),
                    rule=self.ed_rule.toPlainText().strip(),
                    enabled=self.cb_enabled.isChecked(),
                    show_venue=self.cb_venue.isChecked())


class TimelineDialog(QDialog):
    def __init__(self, parent, events):
        super().__init__(parent)
        self.setWindowTitle("赛程时间轴预览")
        self.resize(700, 500)
        lay = QVBoxLayout(self)
        days = sorted({e.day for e in events if e.day})
        if not days:
            lay.addWidget(QLabel("（暂无赛程）"))
            return
        for day in days:
            lay.addWidget(QLabel(f"—— {day} ——"))
            evs = [e for e in events if e.day == day]
            by_time = {}
            for e in evs:
                by_time.setdefault(e.time or "（未定时间）", []).append(e)
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["时间", "田赛", "径赛"])
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            table.setRowCount(0)
            for t in sorted(by_time, key=lambda x: (x == "（未定时间）", x)):
                i = table.rowCount()
                table.insertRow(i)
                table.setItem(i, 0, plain_item(t))
                field = "；".join(f"{e.name}({e.grade or ''}{e.group})"
                                 for e in by_time[t] if e.etype == "田赛")
                track = "；".join(f"{e.name}({e.grade or ''}{e.group})"
                                 for e in by_time[t] if e.etype == "径赛")
                table.setItem(i, 1, plain_item(field))
                table.setItem(i, 2, plain_item(track))
            lay.addWidget(table)


class ProjectPage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        self._ids = []
        self._sids = []

        root = QVBoxLayout(self)
        split = QSplitter()
        root.addWidget(split, 1)

        # ---------- 左：项目管理 ----------
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(6, 6, 6, 6)
        self.lbl = QLabel()
        lv.addWidget(self.lbl)
        btns = QHBoxLayout()
        for text, slot, big in [
                ("编辑选中", self.edit_event, True),
                ("新增项目", self.add_event, False),
                ("启用/禁用选中", self.toggle_event, False),
                ("恢复默认项目", self.reset_events, False)]:
            b = QPushButton(text)
            if big:
                b.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px 12px;")
            b.clicked.connect(slot)
            btns.addWidget(b)
        btns.addStretch(1)
        lv.addLayout(btns)
        self.table = QTableWidget()
        setup_table(self.table, P_HEAD)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_event())
        self.table.cellChanged.connect(self.on_cell_changed)
        lv.addWidget(self.table, 1)
        json_row = QHBoxLayout()
        json_row.addStretch(1)
        b_exp = QPushButton("导出项目JSON")
        b_exp.clicked.connect(self.export_json)
        b_imp = QPushButton("导入项目JSON")
        b_imp.clicked.connect(self.import_json)
        json_row.addWidget(b_exp)
        json_row.addWidget(b_imp)
        lv.addLayout(json_row)
        split.addWidget(left)

        # ---------- 右：赛程管理 ----------
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(6, 6, 6, 6)
        rv.addWidget(QLabel("赛程管理"))
        self.sched = QTableWidget()
        setup_table(self.sched, S_HEAD)
        rv.addWidget(self.sched, 1)
        self.report = QLabel("点“一键检测冲突”后此处显示结果。")
        self.report.setWordWrap(True)
        rv.addWidget(self.report)
        sbtns = QHBoxLayout()
        for text, slot in [("上移", lambda: self.move(-1)),
                           ("下移", lambda: self.move(1)),
                           ("一键检测冲突", self.check_conflicts),
                           ("时间轴预览", self.show_timeline)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            sbtns.addWidget(b)
        sbtns.addStretch(1)
        rv.addLayout(sbtns)
        split.addWidget(right)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        self.refresh()

    def refresh(self):
        self.refresh_projects()
        self.refresh_schedule()

    def refresh_projects(self):
        evs = self.state.events
        self.lbl.setText(
            f"共 {len(evs)} 个项目（参与 {sum(1 for e in evs if e.enabled)}）")
        self.table.blockSignals(True)
        setup_table(self.table, P_HEAD)
        self.table.setRowCount(0)
        self._ids = []
        for e in evs:
            i = self.table.rowCount()
            self.table.insertRow(i)
            self._ids.append(e.eid)
            values = [e.name, e.etype, e.group, e.grade, e.day, e.session,
                      e.time, e.venue, e.rule, e.record, e.note]
            for j, v in enumerate(values):
                self.table.setItem(i, j, plain_item(v))
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable
                          | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if e.enabled else Qt.Unchecked)
            self.table.setItem(i, ENABLED_COL, item)
            b_del = QPushButton("删除")
            b_del.clicked.connect(lambda _c, row=i: self.del_row(row))
            self.table.setCellWidget(i, OP_COL, b_del)
        self.table.blockSignals(False)

    def del_row(self, row):
        if row < 0 or row >= len(self._ids):
            return
        eid = self._ids[row]
        ev = next((e for e in self.state.events if e.eid == eid), None)
        if ev is None:
            return
        if QMessageBox.question(self, "确认",
                                f"确定删除项目“{ev.name}”吗？") == QMessageBox.Yes:
            self.state.events.remove(ev)
            self.state.save()
            self.refresh()

    def on_cell_changed(self, row, col):
        if col != ENABLED_COL or row >= len(self._ids):
            return
        ev = next((e for e in self.state.events if e.eid == self._ids[row]), None)
        if ev is None:
            return
        item = self.table.item(row, col)
        ev.enabled = (item.checkState() == Qt.Checked)
        self.state.save()
        self.lbl.setText(
            f"共 {len(self.state.events)} 个项目"
            f"（参与 {sum(1 for e in self.state.events if e.enabled)}）")

    def refresh_schedule(self):
        evs = sort_events(self.state.events)
        setup_table(self.sched, S_HEAD)
        self.sched.setRowCount(0)
        self._sids = []
        conflict_events = {r.event for r in self.state.records if r.conflict}
        overlaps = detect_event_overlaps(self.state.events)
        for e in evs:
            i = self.sched.rowCount()
            self.sched.insertRow(i)
            self._sids.append(e.eid)
            status = ""
            if e.name in conflict_events:
                status = "运动员冲突"
            if e.name in overlaps:
                status = (status + " " if status else "") + "时间重叠"
            values = [e.day, e.session or "—", e.time or "—", e.etype,
                      e.grade or "—", e.name, e.group,
                      e.venue if getattr(e, "show_venue", True) else "（不输出）",
                      status]
            items = [plain_item(v) for v in values]
            if status:
                color = RED if e.name in conflict_events else YELLOW
                for it in items:
                    it.setBackground(QBrush(color))
            for j, it in enumerate(items):
                self.sched.setItem(i, j, it)

    def selected_event(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "提示", "请先在左侧项目表中选择一个项目。")
            return None
        eid = self._ids[row]
        return next((e for e in self.state.events if e.eid == eid), None)

    def add_event(self):
        dlg = EventDialog(self)
        if dlg.exec() == QDialog.Accepted:
            v = dlg.values()
            if not v["name"]:
                QMessageBox.warning(self, "提示", "项目名称不能为空。")
                return
            self.state.add_event(**v)
            self.state.save()
            self.refresh()

    def edit_event(self):
        ev = self.selected_event()
        if not ev:
            return
        dlg = EventDialog(self, ev)
        if dlg.exec() == QDialog.Accepted:
            v = dlg.values()
            if not v["name"]:
                QMessageBox.warning(self, "提示", "项目名称不能为空。")
                return
            for k, val in v.items():
                setattr(ev, k, val)
            self.state.save()
            self.refresh()

    def toggle_event(self):
        ev = self.selected_event()
        if not ev:
            return
        ev.enabled = not ev.enabled
        self.state.save()
        self.refresh()

    def reset_events(self):
        if QMessageBox.question(
                self, "确认",
                "恢复为内置默认项目清单？当前项目配置将被覆盖。") == QMessageBox.Yes:
            self.state.events = default_events()
            self.state.save()
            self.refresh()

    def import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入项目配置", "",
                                              "JSON (*.json)")
        if not path:
            return
        try:
            n = self.state.import_events_json(path)
            QMessageBox.information(self, "成功", f"已导入 {n} 个项目。")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "失败", str(e))

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出项目配置",
                                              "项目配置.json", "JSON (*.json)")
        if not path:
            return
        self.state.export_events_json(path)
        QMessageBox.information(self, "成功", f"已导出到 {path}")

    def move(self, direction):
        row = self.sched.currentRow()
        if row < 0 or row >= len(self._sids):
            QMessageBox.information(self, "提示", "请先在右侧赛程表选中一个项目。")
            return
        eid = self._sids[row]
        if move_event(self.state.events, eid, direction):
            self.state.save()
            self.refresh()
            if eid in self._sids:
                self.sched.setCurrentCell(self._sids.index(eid), 0)

    def check_conflicts(self):
        threshold = int(self.state.settings.get("conflict_minutes", 20))
        _ids, overlaps, report = check_all(
            self.state.records, self.state.events, threshold)
        self.state.save()
        self.refresh_schedule()
        self.report.setText(report)
        QMessageBox.information(self, "冲突检测结果", report)

    def show_timeline(self):
        dlg = TimelineDialog(self, sort_events(self.state.events))
        dlg.exec()
'''


def main():
    print("运动会秩序册生成工具 第四轮更新")
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
            print(f"  [OK] {rel}")
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
    print("运行 python main.py 启动程序。")
    print("注意：秩序册模块页改动后，重新打开程序即生效（数据不变）。")


if __name__ == "__main__":
    main()
