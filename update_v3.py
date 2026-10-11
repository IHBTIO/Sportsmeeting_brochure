# -*- coding: utf-8 -*-
"""运动会秩序册生成工具 第三轮更新（UI 修正 + 导入增强）。

用法：python update_v3.py
内容：
- 新增 app/text_import.py（txt/docx 纯文字提取、表格行导入）
- 新增 app/presets.py（预设库：只进下拉选项，不预填内容）
- 数据导入页：映射改为“表格列 → 字段”布局；导入按钮移到顶栏
- 智能识别并入设置页（导航 7 项）
- 秩序册模块页：长文本支持按钮导入 + 拖拽 txt/docx；预设下拉快速填写；
  条款可新建/删除；表格类模块支持从 Excel/CSV 导入
- 项目管理：参与列改为直接勾选；按钮顺序调整
- 班级管理：按钮按重要性分两行；JSON 移到右下角
- 全部输入框去掉示例式提示，只留功能性说明
- 删除 ui/recognize_page.py
"""
import os
import py_compile
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

FILES = {}

# ============================================================
# app/text_import.py（新增）
# ============================================================
FILES["app/text_import.py"] = r'''# -*- coding: utf-8 -*-
"""文本与表格导入辅助。

- load_text：从 txt/docx 提取纯文字（保留换行，不含表格与样式）。
  docx 的加粗、字号等排版无法带入纯文本框，段落结构保留。
- load_table_rows：从 Excel/CSV 读为行列表，按表头列数对齐
  （少补空、多截断、空行跳过）。
"""
import pandas as pd


def load_text(path):
    low = str(path).lower()
    if low.endswith(".docx"):
        from docx import Document
        doc = Document(path)
        lines = [p.text for p in doc.paragraphs]
        return "\n".join(ln for ln in lines if ln.strip())
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError("文本文件编码无法识别")


def load_table_rows(path, ncols):
    from .importer import load_table
    df = load_table(path)
    rows = []
    for _, row in df.iterrows():
        vals = ["" if pd.isna(v) else str(v).strip() for v in row]
        vals = (vals + [""] * ncols)[:ncols]
        if any(vals):
            rows.append(vals)
    return rows
'''

# ============================================================
# app/presets.py（新增）
# ============================================================
FILES["app/presets.py"] = r'''# -*- coding: utf-8 -*-
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
'''

# ============================================================
# ui/main_window.py（导航 7 项）
# ============================================================
FILES["ui/main_window.py"] = r'''# -*- coding: utf-8 -*-
"""主窗口：左侧导航 + 右侧内容区。"""
import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QHBoxLayout, QListWidget, QMainWindow,
                               QStackedWidget, QWidget)

from app.config import APP_NAME
from app.data_models import AppState
from ui.import_page import ImportPage
from ui.review_page import ReviewPage
from ui.project_page import ProjectPage
from ui.class_page import ClassPage
from ui.modules_page import ModulesPage
from ui.generate_page import GeneratePage
from ui.settings_page import SettingsPage

NAV = ["数据导入", "人工审查", "项目管理", "班级管理",
       "秩序册模块", "生成秩序册", "设置"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        self.setWindowTitle(APP_NAME)
        icon = self.state.settings.get("icon_path", "")
        if icon and os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.resize(1200, 750)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self.nav = QListWidget()
        self.nav.addItems(NAV)
        self.nav.setFixedWidth(140)
        self.nav.setCurrentRow(0)
        layout.addWidget(self.nav)

        self.stack = QStackedWidget()
        self.pages = {
            "数据导入": ImportPage(self.state, self),
            "人工审查": ReviewPage(self.state, self),
            "项目管理": ProjectPage(self.state, self),
            "班级管理": ClassPage(self.state, self),
            "秩序册模块": ModulesPage(self.state, self),
            "生成秩序册": GeneratePage(self.state, self),
            "设置": SettingsPage(self.state, self),
        }
        for name in NAV:
            self.stack.addWidget(self.pages[name])
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.statusBar().showMessage(
            f"当前共 {len(self.state.records)} 条报名记录")

    def goto(self, page_name):
        if page_name in NAV:
            self.nav.setCurrentRow(NAV.index(page_name))

    def refresh_all(self):
        for p in self.pages.values():
            if hasattr(p, "refresh"):
                p.refresh()
        self.statusBar().showMessage(
            f"当前共 {len(self.state.records)} 条报名记录")

    def closeEvent(self, event):
        self.state.save()
        super().closeEvent(event)
'''

# ============================================================
# ui/import_page.py（映射改向、导入按钮顶栏）
# ============================================================
FILES["ui/import_page.py"] = r'''# -*- coding: utf-8 -*-
"""数据导入页：选文件 -> 预览 -> 字段映射 -> 导入（覆盖或追加）。"""
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGroupBox,
                               QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QTableWidget, QVBoxLayout, QWidget)

from app.importer import (FIELDS, build_records, guess_mapping, load_table,
                          classes_from_records)
from app import module_flags
from ui.widgets import setup_table, plain_item


class ImportPage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        self.df = None

        root = QVBoxLayout(self)

        # 顶栏：选择文件 + 导入按钮（并排、醒目）
        top = QHBoxLayout()
        self.btn_open = QPushButton("选择文件")
        self.btn_open.clicked.connect(self.choose_file)
        self.btn_import = QPushButton("导入并生成报名记录")
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

        # 字段映射：左=表格列（下拉），中间箭头，右=字段
        box = QGroupBox("字段映射（表格列 指向 字段）")
        v = QVBoxLayout(box)
        self.combos = {}
        for f in FIELDS:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            cb = QComboBox()
            cb.addItem("（不使用）")
            h.addWidget(cb, 1)
            arrow = QLabel("→")
            arrow.setStyleSheet("color: #1a4f8a; font-weight: bold;")
            h.addWidget(arrow)
            lab = QLabel(f)
            lab.setStyleSheet("font-weight: bold;")
            h.addWidget(lab)
            v.addWidget(row)
            self.combos[f] = cb
        self.chk_split = QCheckBox("一人多项目自动拆行")
        self.chk_split.setChecked(True)
        v.addWidget(self.chk_split)
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["覆盖导入", "追加导入"])
        v.addWidget(self.cb_mode)
        root.addWidget(box)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择报名表", "",
            "报名表 (*.xlsx *.xls *.csv);;所有文件 (*.*)")
        if not path:
            return
        try:
            self.df = load_table(path)
        except Exception as e:
            QMessageBox.critical(self, "读取失败", f"无法读取文件：\n{e}")
            return
        self.lbl_file.setText(path)
        self.show_preview()
        self.fill_mapping()
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

    def fill_mapping(self):
        mapping = guess_mapping(list(self.df.columns))
        cols = [str(c) for c in self.df.columns]
        for f, cb in self.combos.items():
            cb.clear()
            cb.addItem("（不使用）")
            cb.addItems(cols)
            if mapping.get(f) and mapping[f] in cols:
                cb.setCurrentText(mapping[f])

    def do_import(self):
        if self.df is None:
            return
        mapping = {f: (cb.currentText() if cb.currentText() != "（不使用）" else "")
                   for f, cb in self.combos.items()}
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
        yellow = sum(1 for r in records if red_line <= r.confidence < yellow_line)
        word = "追加" if append else "导入"
        QMessageBox.information(
            self, word + "完成",
            f"本次{word} {len(records)} 条，当前共 {len(self.state.records)} 条。\n"
            f"自动通过：{len(records) - red - yellow}\n"
            f"建议核对（黄色）：{yellow}\n"
            f"需人工审查（红色）：{red}")

    def refresh(self):
        pass
'''

# ============================================================
# ui/settings_page.py（并入智能识别）
# ============================================================
FILES["ui/settings_page.py"] = r'''# -*- coding: utf-8 -*-
"""设置页：智能识别（子分组）+ 常规设置。"""
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget)

from app import config, module_flags


class SettingsPage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        self.f = module_flags.get_flags()["recognize"]

        root = QVBoxLayout(self)

        # ---- 智能识别 ----
        box1 = QGroupBox("智能识别")
        form1 = QFormLayout(box1)
        self.cbs = {}
        for key, text in [("event", "项目名识别（建议保持勾选）"),
                          ("class", "班级名识别"),
                          ("name", "人名识别"),
                          ("gender", "性别识别")]:
            cb = QCheckBox(text)
            cb.setChecked(bool(self.f.get(key, True)))

            def sync(on, k=key):
                if k == "event" and not on:
                    QMessageBox.warning(
                        self, "重要提醒",
                        "项目名识别非常重要，建议保持勾选。\n"
                        "取消后，导入的项目将按原始名称标红进入人工审查，"
                        "可在审查页按问题分组集中处理并批量忽略。")
                self.f[k] = on
                module_flags.save_flags()

            cb.toggled.connect(sync)
            self.cbs[key] = cb
            form1.addRow(cb)
        self.sp_yellow = QSpinBox()
        self.sp_yellow.setRange(50, 100)
        self.sp_yellow.setValue(int(self.f.get("yellow", 90)))
        self.sp_red = QSpinBox()
        self.sp_red.setRange(0, 59)
        self.sp_red.setValue(int(self.f.get("red", 60)))

        def sync_yellow(v):
            self.f["yellow"] = v
            module_flags.save_flags()

        def sync_red(v):
            self.f["red"] = v
            module_flags.save_flags()

        self.sp_yellow.valueChanged.connect(sync_yellow)
        self.sp_red.valueChanged.connect(sync_red)
        form1.addRow("自动通过线", self.sp_yellow)
        form1.addRow("标红线", self.sp_red)
        root.addWidget(box1)

        # ---- 常规设置 ----
        box2 = QGroupBox("常规设置")
        form2 = QFormLayout(box2)
        self.lbl_out = QLabel(self.state.settings.get("output_dir", "")
                              or "（未设置）")
        b_out = QPushButton("选择默认输出目录")
        b_out.clicked.connect(self.pick_out)
        form2.addRow("默认输出目录：", self.lbl_out)
        form2.addRow("", b_out)
        self.cb_font = QComboBox()
        self.cb_font.setEditable(True)
        self.cb_font.addItems(["宋体", "黑体", "仿宋", "楷体", "微软雅黑"])
        self.cb_font.setCurrentText(self.state.settings.get("font", "宋体"))
        self.sp_size = QSpinBox()
        self.sp_size.setRange(9, 28)
        self.sp_size.setValue(int(self.state.settings.get("font_size", 12)))
        font_row = QHBoxLayout()
        font_row.addWidget(self.cb_font)
        font_row.addWidget(QLabel("字号："))
        font_row.addWidget(self.sp_size)
        form2.addRow("默认字体：", font_row)
        self.sp_conflict = QSpinBox()
        self.sp_conflict.setRange(5, 120)
        self.sp_conflict.setValue(
            int(self.state.settings.get("conflict_minutes", 20)))
        form2.addRow("冲突判定分钟数：", self.sp_conflict)
        self.cb_number = QComboBox()
        self.cb_number.addItems(["全校累计（各班连续编号）",
                                 "班内独立（每班从 1 开始）"])
        self.cb_number.setCurrentIndex(
            1 if self.state.settings.get("number_mode", "") == "班内独立" else 0)
        form2.addRow("号码范围模式：", self.cb_number)
        root.addWidget(box2)

        btns = QHBoxLayout()
        b_save = QPushButton("保存设置")
        b_save.clicked.connect(self.save)
        b_exp = QPushButton("导出配置 JSON")
        b_exp.clicked.connect(self.export_cfg)
        b_imp = QPushButton("导入配置 JSON")
        b_imp.clicked.connect(self.import_cfg)
        btns.addWidget(b_save)
        btns.addWidget(b_exp)
        btns.addWidget(b_imp)
        btns.addStretch(1)
        root.addLayout(btns)
        root.addStretch(1)

    def save(self):
        self.state.settings.update({
            "output_dir": self.lbl_out.text() if self.lbl_out.text() != "（未设置）" else "",
            "font": self.cb_font.currentText().strip() or "宋体",
            "font_size": self.sp_size.value(),
            "conflict_minutes": self.sp_conflict.value(),
            "number_mode": "班内独立" if self.cb_number.currentIndex() == 1
                           else "全校累计",
        })
        self.state.save()
        QMessageBox.information(self, "成功", "设置已保存。")

    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "选择默认输出目录")
        if d:
            self.lbl_out.setText(d)

    def export_cfg(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出配置",
                                              "工具配置.json", "JSON (*.json)")
        if path:
            config.save_json(path, self.state.settings)
            QMessageBox.information(self, "成功", f"已导出到 {path}")

    def import_cfg(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON (*.json)")
        if not path:
            return
        data = config.load_json(path, None)
        if not isinstance(data, dict):
            QMessageBox.critical(self, "失败", "配置文件格式不正确。")
            return
        self.state.settings.update(data)
        self.state.save()
        QMessageBox.information(self, "成功", "配置已导入，重启后完全生效。")

    def refresh(self):
        pass
'''

# ============================================================
# ui/modules_page.py（导入/拖拽/预设/新建、表格导入）
# ============================================================
FILES["ui/modules_page.py"] = r'''# -*- coding: utf-8 -*-
"""秩序册模块页。

- 每个模块一个分组框，母标题加大加粗。
- 勾选 = 参与生成；取消 = 完全跳过。
- 长文本：可点“导入”选 txt/docx，也可把文件直接拖进文本框（只提取文字）。
- 预设：只出现在下拉选项，选择后填入，不自动写入。
- 条款/条目/分组：可新建、删除最后一条。
- 表格类（颁奖仪式、校纪录）：支持从 Excel/CSV 导入。
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


# ---------------- 条款编辑器（带预设/新建/导入） ----------------
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
        b_del = QPushButton("删除最后一条")
        b_del.clicked.connect(self.del_last)
        bar.addWidget(b_new)
        bar.addWidget(b_del)
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

    def del_last(self):
        if self.clauses:
            self.clauses.pop()
            self.on_save()
            self.rebuild()

    def rebuild(self):
        while self.rows_lay.count():
            it = self.rows_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for c in self.clauses:
            self.rows_lay.addWidget(_clause_row(c, self.on_save))


def _clause_row(data, on_change):
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
    return w


# ---------------- 人员组编辑器（带新建/导入） ----------------
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
        b_del = QPushButton("删除最后一组")
        b_del.clicked.connect(self.del_last)
        bar.addWidget(b_new)
        bar.addWidget(b_del)
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

    def del_last(self):
        if self.groups:
            self.groups.pop()
            self.on_save()
            self.rebuild()

    def rebuild(self):
        while self.rows_lay.count():
            it = self.rows_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for g in self.groups:
            self.rows_lay.addWidget(_member_group(g, self.on_save))


def _member_group(data, on_change):
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
    return gb


# ---------------- 表格编辑器（带导入） ----------------
def _table_editor(headers, rows, on_change):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels([str(h) for h in headers])

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
            "改动即时保存。"))
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
# ui/project_page.py（参与列勾选、按钮顺序调整）
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
          "场地", "规则说明", "校记录", "备注", "参与"]
S_HEAD = ["比赛日", "时段", "时间", "类型", "年级", "项目", "组别", "场地", "状态"]
ENABLED_COL = len(P_HEAD) - 1

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
                ("删除选中", self.del_event, False),
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
        self.table.blockSignals(False)

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

    def del_event(self):
        ev = self.selected_event()
        if not ev:
            return
        if QMessageBox.question(self, "确认",
                                f"确定删除项目“{ev.name}”吗？") == QMessageBox.Yes:
            self.state.events.remove(ev)
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

# ============================================================
# ui/class_page.py（按钮分两行，JSON 右下角）
# ============================================================
FILES["ui/class_page.py"] = r'''# -*- coding: utf-8 -*-
"""班级管理页。"""
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox,
                               QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QMessageBox, QPushButton,
                               QFormLayout, QVBoxLayout, QWidget)

from app.data_models import ClassInfo, new_id
from app.recognizer import normalize_class


class ClassDialog(QDialog):
    def __init__(self, parent, info=None):
        super().__init__(parent)
        self.setWindowTitle("班级")
        form = QFormLayout(self)
        self.ed_name = QLineEdit(info.name if info else "")
        self.ed_leader = QLineEdit(info.leader if info else "")
        self.ed_num = QLineEdit(info.num_range if info else "")
        self.ed_num.setPlaceholderText("留空可点“刷新号码范围”自动计算")
        self.cb_enabled = QCheckBox("参与秩序册")
        self.cb_roster = QCheckBox("输出名单")
        if info:
            self.cb_enabled.setChecked(info.enabled)
            self.cb_roster.setChecked(info.show_roster)
        else:
            self.cb_enabled.setChecked(True)
            self.cb_roster.setChecked(True)
        form.addRow("班级名称：", self.ed_name)
        form.addRow("领队：", self.ed_leader)
        form.addRow("号码范围：", self.ed_num)
        form.addRow(self.cb_enabled)
        form.addRow(self.cb_roster)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def values(self):
        return dict(name=self.ed_name.text().strip(),
                    leader=self.ed_leader.text().strip(),
                    num_range=self.ed_num.text().strip(),
                    enabled=self.cb_enabled.isChecked(),
                    show_roster=self.cb_roster.isChecked())


class ClassPage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        root = QVBoxLayout(self)
        self.lbl = QLabel()
        root.addWidget(self.lbl)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _i: self.edit_selected())
        root.addWidget(self.list, 1)

        # 第一行：主要操作（加大）
        main_row = QHBoxLayout()
        for text, slot in [("新增班级", self.add_class),
                           ("编辑选中", self.edit_selected),
                           ("删除选中", self.del_selected)]:
            b = QPushButton(text)
            b.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px 12px;")
            b.clicked.connect(slot)
            main_row.addWidget(b)
        main_row.addStretch(1)
        root.addLayout(main_row)

        # 第二行：工具类（普通）
        tool_row = QHBoxLayout()
        for text, slot in [("统一命名格式", self.normalize_all),
                           ("从报名数据补充", self.fill_from_records),
                           ("刷新号码范围", self.refresh_numbers)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            tool_row.addWidget(b)
        tool_row.addStretch(1)
        root.addLayout(tool_row)
        root.addStretch(1)

        # 右下角：JSON
        json_row = QHBoxLayout()
        json_row.addStretch(1)
        b_imp = QPushButton("导入班级JSON")
        b_imp.clicked.connect(self.import_json)
        b_exp = QPushButton("导出班级JSON")
        b_exp.clicked.connect(self.export_json)
        json_row.addWidget(b_exp)
        json_row.addWidget(b_imp)
        root.addLayout(json_row)
        self.refresh()

    def refresh(self):
        self.lbl.setText("共 %d 个班级（双击可编辑）" % len(self.state.classes))
        self.list.clear()
        for c in sorted(self.state.classes, key=lambda x: x.name):
            tag = "" if c.enabled else "（不参与）"
            num = f" [{c.num_range}]" if c.num_range else ""
            self.list.addItem(f"{c.name}{num}{tag}")

    def _selected(self):
        item = self.list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择一个班级。")
            return None
        name = item.text().split("（")[0].split(" [")[0].strip()
        return next((c for c in self.state.classes if c.name == name), None)

    def add_class(self):
        dlg = ClassDialog(self)
        if dlg.exec() == QDialog.Accepted:
            v = dlg.values()
            if v["name"]:
                self.state.classes.append(ClassInfo(new_id(), **v))
                self.state.save()
                self.refresh()

    def edit_selected(self):
        info = self._selected()
        if not info:
            return
        dlg = ClassDialog(self, info)
        if dlg.exec() == QDialog.Accepted:
            v = dlg.values()
            if v["name"]:
                for k, val in v.items():
                    setattr(info, k, val)
                self.state.save()
                self.refresh()

    def del_selected(self):
        info = self._selected()
        if not info:
            return
        if QMessageBox.question(self, "确认",
                                f"确定删除班级“{info.name}”吗？") == QMessageBox.Yes:
            self.state.classes.remove(info)
            self.state.save()
            self.refresh()

    def normalize_all(self):
        changed = 0
        for c in self.state.classes:
            new, score = normalize_class(c.name)
            if new and new != c.name and score >= 70:
                c.name = new
                changed += 1
        self.state.save()
        self.refresh()
        QMessageBox.information(self, "完成", f"已统一 {changed} 个班级的命名格式。")

    def fill_from_records(self):
        n = 0
        for r in self.state.records:
            if r.class_name and not any(c.name == r.class_name
                                        for c in self.state.classes):
                self.state.ensure_class(r.class_name)
                n += 1
        self.state.save()
        self.refresh()
        QMessageBox.information(self, "完成", f"从报名数据补充了 {n} 个班级。")

    def refresh_numbers(self):
        mode = self.state.settings.get("number_mode", "全校累计")
        counts = {c.name: 0 for c in self.state.classes}
        for r in self.state.records:
            if r.class_name in counts:
                counts[r.class_name] += 1
        ret = QMessageBox.question(
            self, "确认", f"按模式「{mode}」按各班已报名人数重新计算全部号码范围？"
            "\n（手动填写过的也会被覆盖）")
        if ret != QMessageBox.Yes:
            return
        start = 1
        for name in sorted(counts):
            c = next(c for c in self.state.classes if c.name == name)
            n = counts[name]
            if n <= 0:
                continue
            if mode == "班内独立":
                c.num_range = f"{1:04d}~{n:04d}"
            else:
                c.num_range = f"{start:04d}~{start + n - 1:04d}"
                start += n
        self.state.save()
        self.refresh()
        QMessageBox.information(self, "完成", "号码范围已刷新（人数为 0 的班级跳过）。")

    def import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入班级配置", "",
                                              "JSON (*.json)")
        if not path:
            return
        try:
            n = self.state.import_classes_json(path)
            QMessageBox.information(self, "成功", f"已导入 {n} 个班级。")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "失败", str(e))

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出班级配置",
                                              "班级配置.json", "JSON (*.json)")
        if not path:
            return
        self.state.export_classes_json(path)
        QMessageBox.information(self, "成功", f"已导出到 {path}")
'''

# ============================================================
# ui/generate_page.py（占位提示清理）
# ============================================================
FILES["ui/generate_page.py"] = r'''# -*- coding: utf-8 -*-
"""生成秩序册页。"""
import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from app import config, docgen, module_flags


class GeneratePage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        root = QVBoxLayout(self)

        box = QGroupBox("输出信息")
        form = QFormLayout(box)
        self.ed_school = QLineEdit(self.state.settings.get("school", ""))
        self.ed_school.setPlaceholderText("留空则封面不显示学校")
        self.ed_year = QLineEdit(self.state.settings.get("year", ""))
        self.ed_year.setPlaceholderText("留空自动当年年份")
        self.ed_term = QLineEdit(self.state.settings.get("term", ""))
        self.ed_term.setPlaceholderText("留空默认秋季")
        self.ed_sign = QLineEdit(self.state.settings.get("signature", ""))
        self.ed_sign.setPlaceholderText("学校为空时封面使用")
        self.ed_email = QLineEdit(self.state.settings.get("email", ""))
        self.ed_email.setPlaceholderText("可选")
        form.addRow("学校名称：", self.ed_school)
        form.addRow("年份：", self.ed_year)
        form.addRow("届次/季节：", self.ed_term)
        form.addRow("备用署名：", self.ed_sign)
        form.addRow("邮箱：", self.ed_email)
        root.addWidget(box)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("输出路径："))
        self.ed_path = QLineEdit()
        default_dir = self.state.settings.get("output_dir") or os.getcwd()
        self.ed_path.setText(os.path.join(default_dir, "运动会秩序册.docx"))
        row1.addWidget(self.ed_path, 1)
        b = QPushButton("浏览")
        b.clicked.connect(self.browse)
        row1.addWidget(b)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("模板："))
        self.cb_tpl = QComboBox()
        row2.addWidget(self.cb_tpl)
        b2 = QPushButton("刷新模板列表")
        b2.clicked.connect(self.refresh_templates)
        row2.addWidget(b2)
        row2.addStretch(1)
        root.addLayout(row2)

        root.addStretch(1)
        self.btn_gen = QPushButton("生成秩序册（Word 文档）")
        self.btn_gen.setStyleSheet("font-size: 16px; padding: 8px;")
        self.btn_gen.clicked.connect(self.generate)
        root.addWidget(self.btn_gen)
        root.addStretch(2)
        self.refresh_templates()

    def refresh_templates(self):
        self.cb_tpl.clear()
        self.cb_tpl.addItem("默认模板")
        self.cb_tpl.addItems(config.list_templates())

    def browse(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存秩序册", self.ed_path.text() or "运动会秩序册.docx",
            "Word 文档 (*.docx)")
        if path:
            if not path.lower().endswith(".docx"):
                path += ".docx"
            self.ed_path.setText(path)

    def generate(self):
        self.state.settings.update({
            "school": self.ed_school.text().strip(),
            "year": self.ed_year.text().strip(),
            "term": self.ed_term.text().strip() or "秋季",
            "signature": self.ed_sign.text().strip(),
            "email": self.ed_email.text().strip(),
        })
        self.state.save()

        flags = module_flags.get_flags()
        on = [t for k, t in module_flags.MODULE_ORDER
              if flags.get(k, {}).get("enabled", True)]
        off = [t for k, t in module_flags.MODULE_ORDER
               if not flags.get(k, {}).get("enabled", True)]
        text = "将输出 %d 个模块：\n%s\n" % (
            len(on), "\n".join("  " + t for t in on))
        if off:
            text += "\n将跳过 %d 个模块：\n%s\n" % (
                len(off), "\n".join("  " + t for t in off))
        text += "\n注：勾选但未填写内容的纯文本模块也不会输出。"
        ret = QMessageBox.question(self, "生成前确认", text + "\n确认生成？")
        if ret != QMessageBox.Yes:
            return

        if not self.state.records:
            ret = QMessageBox.question(
                self, "警告", "当前没有任何报名记录，仍然生成吗？")
            if ret != QMessageBox.Yes:
                return
        path = self.ed_path.text().strip()
        if not path:
            QMessageBox.warning(self, "提示", "请先填写输出路径。")
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        try:
            docgen.generate_document(path, self.state,
                                     self.cb_tpl.currentText())
        except Exception as e:
            QMessageBox.critical(self, "生成失败", f"生成秩序册时出错：\n{e}")
            return
        self.state.settings["output_dir"] = os.path.dirname(path) or ""
        self.state.save()
        ret = QMessageBox.question(
            self, "生成成功", f"秩序册已生成：\n{path}\n\n是否打开所在文件夹？")
        if ret == QMessageBox.Yes:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(os.path.dirname(path) or "."))

    def refresh(self):
        pass
'''


def main():
    print("运动会秩序册生成工具 第三轮更新")
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

    # 删除已并入设置的智能识别页
    old = os.path.join(BASE, "ui", "recognize_page.py")
    if os.path.exists(old):
        os.remove(old)
        print("  [OK] 已删除 ui/recognize_page.py")

    # 清理 review_page 中残留的示例式占位提示
    rp = os.path.join(BASE, "ui", "review_page.py")
    if os.path.exists(rp):
        with open(rp, "r", encoding="utf-8") as f:
            src = f.read()
        src2 = src.replace('setPlaceholderText("如：08:30")',
                           'setPlaceholderText("时:分")')
        if src2 != src:
            with open(rp, "w", encoding="utf-8") as f:
                f.write(src2)
            print("  [OK] 已清理 ui/review_page.py 的示例式提示")

    print("=" * 50)
    if fail:
        print(f"完成 {ok} 个，失败 {len(fail)} 个：{fail}")
        print("请把上方错误信息发回给助手。")
        sys.exit(1)
    print(f"全部 {ok} 个文件写入并检查通过。")
    print("运行 python main.py 启动程序（导航应为 7 项）。")


if __name__ == "__main__":
    main()
