# -*- coding: utf-8 -*-
"""运动会秩序册生成工具 第二轮更新 脚本B（ui 层）。

用法：python update_v2_b.py（需先运行过 update_v2_a.py）
作用：写入 ui 层 8 个文件与测试数据脚本，删除废弃的 schedule_page.py。
完成后运行 python main.py 启动程序。
"""
import os
import py_compile
import sys
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))

FILES = {}

# ============================================================
# ui/main_window.py（导航 8 项，删除赛程管理）
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
from ui.recognize_page import RecognizePage
from ui.review_page import ReviewPage
from ui.project_page import ProjectPage
from ui.class_page import ClassPage
from ui.modules_page import ModulesPage
from ui.generate_page import GeneratePage
from ui.settings_page import SettingsPage

NAV = ["数据导入", "智能识别", "人工审查", "项目管理", "班级管理",
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
            "智能识别": RecognizePage(self.state, self),
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
# ui/import_page.py（覆盖/追加两种导入方式）
# ============================================================
FILES["ui/import_page.py"] = r'''# -*- coding: utf-8 -*-
"""数据导入页：选文件 -> 预览 -> 字段映射 -> 导入（覆盖或追加）。"""
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QTableWidget, QVBoxLayout, QWidget)

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
        top = QHBoxLayout()
        self.btn_open = QPushButton("选择文件（Excel / CSV）")
        self.btn_open.clicked.connect(self.choose_file)
        self.lbl_file = QLabel("未选择文件")
        top.addWidget(self.btn_open)
        top.addWidget(self.lbl_file, 1)
        root.addLayout(top)

        self.preview = QTableWidget()
        setup_table(self.preview, ["（请先选择文件）"])
        root.addWidget(QLabel("文件预览（前 50 行）："))
        root.addWidget(self.preview, 2)

        box = QGroupBox("字段映射")
        form = QFormLayout(box)
        self.combos = {}
        for f in FIELDS:
            cb = QComboBox()
            cb.addItem("（不使用）")
            self.combos[f] = cb
            form.addRow(f + "：", cb)
        self.chk_split = QCheckBox("一人多项目自动拆行（项目列用逗号/顿号分隔时）")
        self.chk_split.setChecked(True)
        form.addRow(self.chk_split)
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["覆盖导入（替换现有全部记录）",
                               "追加导入（各班分开的表逐个追加）"])
        form.addRow("导入方式：", self.cb_mode)
        root.addWidget(box)

        bottom = QHBoxLayout()
        self.btn_import = QPushButton("导入并生成报名记录")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self.do_import)
        self.btn_review = QPushButton("去人工审查")
        self.btn_review.clicked.connect(lambda: self.main.goto("人工审查"))
        bottom.addWidget(self.btn_import)
        bottom.addWidget(self.btn_review)
        bottom.addStretch(1)
        root.addLayout(bottom)

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
        all_recs = self.state.records
        red = sum(1 for r in records if r.confidence < red_line)
        yellow = sum(1 for r in records if red_line <= r.confidence < yellow_line)
        word = "追加" if append else "导入"
        QMessageBox.information(
            self, word + "完成",
            f"本次{word} {len(records)} 条，当前共 {len(all_recs)} 条报名记录。\n"
            f"自动通过：{len(records) - red - yellow} 条\n"
            f"建议核对（黄色）：{yellow} 条\n"
            f"需人工审查（红色）：{red} 条\n\n"
            "建议先到“人工审查”页处理黄色和红色记录。")

    def refresh(self):
        pass
'''

# ============================================================
# ui/review_page.py（班级下拉、问题分组、批量忽略、增删记录）
# ============================================================
FILES["ui/review_page.py"] = r'''# -*- coding: utf-8 -*-
"""人工审查页。

- 班级字段用可编辑下拉（选项来自班级管理，避免手打出错）。
- 左侧问题分组列表：点击分组只看该类问题，可整组批量忽略
  （直接采用原始名称，置信 100）。
- 阈值来自智能识别页设置。
- 支持手动新增、删除记录。
"""
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QMessageBox, QPushButton,
                               QSplitter, QTableWidget, QVBoxLayout, QWidget)

from app import module_flags
from app.data_models import Record, new_id
from app.importer import normalize_time_text
from ui.widgets import conf_item, setup_table, plain_item, CONF_COLORS

HEADERS = ["置信分", "状态", "班级", "姓名", "性别", "项目",
           "组别", "时间", "场地", "问题"]
STATUS_TEXT = {"pending": "待处理", "edited": "已核对",
               "ignored": "已忽略", "approved": "已通过"}

GROUPS = ["全部", "班级问题", "姓名问题", "项目问题", "性别问题",
          "识别已关闭", "时间冲突"]


def _record_groups(r):
    """按问题文字判断记录所属的问题分组（可属于多组）。"""
    gs = set()
    for issue in (r.issues or []):
        if "识别已关闭" in issue:
            gs.add("识别已关闭")
            continue
        if "班级" in issue:
            gs.add("班级问题")
        if "姓名" in issue:
            gs.add("姓名问题")
        if "项目" in issue:
            gs.add("项目问题")
        if "性别" in issue:
            gs.add("性别问题")
    if r.conflict:
        gs.add("时间冲突")
    return gs


class RecordDialog(QDialog):
    """手动新增记录（班级/项目/场地用可编辑下拉，能选能打字）。"""

    def __init__(self, parent, state):
        super().__init__(parent)
        self.setWindowTitle("新增报名记录")
        form = QFormLayout(self)
        self.cb_class = QComboBox()
        self.cb_class.setEditable(True)
        self.cb_class.addItems(state.class_names())
        self.ed_person = QLineEdit()
        self.cb_gender = QComboBox()
        self.cb_gender.addItems(["", "男", "女"])
        self.cb_event = QComboBox()
        self.cb_event.setEditable(True)
        self.cb_event.addItems(state.event_names())
        self.ed_group = QLineEdit()
        self.ed_time = QLineEdit()
        self.ed_time.setPlaceholderText("如：08:30")
        self.ed_venue = QComboBox()
        self.ed_venue.setEditable(True)
        venues = sorted({e.venue for e in state.events if e.venue})
        self.ed_venue.addItems(venues)
        self.ed_number = QLineEdit()
        form.addRow("班级：", self.cb_class)
        form.addRow("姓名：", self.ed_person)
        form.addRow("性别：", self.cb_gender)
        form.addRow("项目：", self.cb_event)
        form.addRow("组别：", self.ed_group)
        form.addRow("时间：", self.ed_time)
        form.addRow("场地：", self.ed_venue)
        form.addRow("号码：", self.ed_number)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def values(self):
        return dict(class_name=self.cb_class.currentText().strip(),
                    person=self.ed_person.text().strip(),
                    gender=self.cb_gender.currentText(),
                    event=self.cb_event.currentText().strip(),
                    group=self.ed_group.text().strip(),
                    time=normalize_time_text(self.ed_time.text()),
                    venue=self.ed_venue.currentText().strip(),
                    number=self.ed_number.text().strip())


class ReviewPage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        self._rows = []
        self.current = None

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.chk_all = QCheckBox("显示全部记录（取消则只显示待处理）")
        self.chk_all.toggled.connect(lambda _on: self.refresh())
        top.addWidget(self.chk_all)
        top.addStretch(1)
        b_add = QPushButton("新增记录")
        b_add.clicked.connect(self.add_record)
        b_del = QPushButton("删除选中记录")
        b_del.clicked.connect(self.del_record)
        b_ign = QPushButton("批量忽略本组（直接采用原始名称）")
        b_ign.clicked.connect(self.batch_ignore)
        top.addWidget(b_add)
        top.addWidget(b_del)
        top.addWidget(b_ign)
        root.addLayout(top)

        split = QSplitter()
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(QLabel("问题分组："))
        self.group_list = QListWidget()
        self.group_list.addItems(GROUPS)
        self.group_list.setCurrentRow(0)
        self.group_list.currentRowChanged.connect(lambda _i: self.refresh())
        self.group_list.setFixedWidth(130)
        lv.addWidget(self.group_list)
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.lbl = QLabel()
        rv.addWidget(self.lbl)
        self.table = QTableWidget()
        setup_table(self.table, HEADERS)
        self.table.cellClicked.connect(self.on_click)
        rv.addWidget(self.table, 1)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        root.addWidget(split, 1)

        box = QGroupBox("修改记录（点击左侧记录后在此编辑，保存后置信 100）")
        form = QFormLayout(box)
        self.cb_class = QComboBox()
        self.cb_class.setEditable(True)
        self.ed_person = QLineEdit()
        self.cb_gender = QComboBox()
        self.cb_gender.addItems(["（未知）", "男", "女"])
        self.cb_event = QComboBox()
        self.cb_event.setEditable(True)
        self.ed_group = QLineEdit()
        self.ed_time = QLineEdit()
        self.ed_venue = QComboBox()
        self.ed_venue.setEditable(True)
        form.addRow("班级：", self.cb_class)
        form.addRow("姓名：", self.ed_person)
        form.addRow("性别：", self.cb_gender)
        form.addRow("项目：", self.cb_event)
        form.addRow("组别：", self.ed_group)
        form.addRow("时间：", self.ed_time)
        form.addRow("场地：", self.ed_venue)
        self.btn_save = QPushButton("保存修改")
        self.btn_save.clicked.connect(self.save_edit)
        form.addRow(self.btn_save)
        root.addWidget(box)

    # ---------- 筛选 ----------
    def _filtered(self):
        rec = module_flags.get_flags().get("recognize", {})
        yellow = int(rec.get("yellow", 90))
        group = self.group_list.currentItem().text()
        rows = self.state.records
        if not self.chk_all.isChecked():
            rows = [r for r in rows
                    if r.confidence < yellow or r.conflict
                    or (r.issues and r.status == "pending")]
        if group != "全部":
            rows = [r for r in rows if group in _record_groups(r)]
        return rows

    def refresh(self):
        rows = self._filtered()
        self._rows = rows
        rec = module_flags.get_flags().get("recognize", {})
        yellow = int(rec.get("yellow", 90))
        red = int(rec.get("red", 60))
        group = self.group_list.currentItem().text()
        self.lbl.setText(
            f"当前分组「{group}」：{len(rows)} 条记录"
            f"（阈值：黄 {yellow} / 红 {red}）")
        setup_table(self.table, HEADERS)
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            vals = [r.confidence, STATUS_TEXT.get(r.status, r.status),
                    r.class_name, r.person, r.gender or "—", r.event,
                    r.group, r.time, r.venue, "；".join(r.issues)]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, conf_item(v, r.confidence, r.conflict))

    # ---------- 编辑 ----------
    def on_click(self, row, _col):
        if 0 <= row < len(self._rows):
            self.current = self._rows[row]
            r = self.current
            self.cb_class.clear()
            self.cb_class.addItems(self.state.class_names())
            self.cb_class.setCurrentText(r.class_name)
            self.ed_person.setText(r.person)
            self.cb_gender.setCurrentText(
                r.gender if r.gender in ("男", "女") else "（未知）")
            self.cb_event.clear()
            self.cb_event.addItems(self.state.event_names())
            if r.event and r.event not in self.state.event_names():
                self.cb_event.addItem(r.event)
            self.cb_event.setCurrentText(r.event or "")
            self.ed_group.setText(r.group)
            self.ed_time.setText(r.time)
            self.ed_venue.setCurrentText(r.venue)

    def save_edit(self):
        if not self.current:
            QMessageBox.information(self, "提示", "请先在表格中点击一条记录。")
            return
        r = self.current
        r.class_name = self.cb_class.currentText().strip()
        r.person = self.ed_person.text().strip()
        g = self.cb_gender.currentText()
        r.gender = "" if g == "（未知）" else g
        r.event = self.cb_event.currentText().strip()
        r.group = self.ed_group.text().strip()
        r.time = normalize_time_text(self.ed_time.text())
        r.venue = self.ed_venue.currentText().strip()
        r.confidence = 100
        r.issues = []
        r.status = "edited"
        self.state.ensure_class(r.class_name)
        self.state.save()
        self.refresh()

    # ---------- 增删 ----------
    def add_record(self):
        dlg = RecordDialog(self, self.state)
        if dlg.exec() == QDialog.Accepted:
            v = dlg.values()
            if not v["person"] or not v["event"]:
                QMessageBox.warning(self, "提示", "姓名和项目不能为空。")
                return
            r = Record(rid=new_id(), confidence=100, status="edited", **v)
            self.state.records.append(r)
            self.state.ensure_class(r.class_name)
            self.state.save()
            self.refresh()

    def del_record(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            QMessageBox.information(self, "提示", "请先选中一条记录。")
            return
        r = self._rows[row]
        ret = QMessageBox.question(
            self, "确认", f"确定删除「{r.class_name} {r.person} {r.event}」吗？")
        if ret == QMessageBox.Yes:
            self.state.records.remove(r)
            self.state.save()
            self.refresh()

    # ---------- 批量忽略 ----------
    def batch_ignore(self):
        group = self.group_list.currentItem().text()
        if group == "全部":
            QMessageBox.information(
                self, "提示", "请先在左侧选择一个具体的问题分组，再批量忽略。")
            return
        rows = [r for r in self._rows if group in _record_groups(r)]
        if not rows:
            QMessageBox.information(self, "提示", "该分组当前没有记录。")
            return
        ret = QMessageBox.question(
            self, "确认批量忽略",
            f"将忽略「{group}」分组的 {len(rows)} 条记录：\n"
            "班级/项目直接采用原始名称，置信记 100，不再提示。\n确定？")
        if ret != QMessageBox.Yes:
            return
        for r in rows:
            if r.raw_class:
                r.class_name = r.raw_class
            if r.raw_event:
                r.event = r.raw_event
            r.confidence = 100
            r.issues = []
            r.status = "ignored"
        self.state.save()
        self.refresh()
        self.main.statusBar().showMessage(f"已批量忽略 {len(rows)} 条记录。")
'''

# ============================================================
# ui/project_page.py（左右分栏：项目 + 赛程，时间轴预览，一键检测冲突）
# ============================================================
FILES["ui/project_page.py"] = r'''# -*- coding: utf-8 -*-
"""项目管理页（左）+ 赛程管理（右）。

- 左：项目表格，按钮在表格上方（编辑按钮加大加粗），JSON 导入导出在右下角。
- 右：赛程列表 + 上移/下移 + 一键检测冲突 + 时间轴预览。
- 时段默认空白；年级可选高一/高二/高三；新增项目比赛日自动填今天。
"""
from datetime import date

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPlainTextEdit,
                               QPushButton, QSplitter, QTableWidget,
                               QVBoxLayout, QWidget)

from app.data_models import default_events
from app.importer import normalize_time_text
from app.schedule import (check_all, detect_event_overlaps, move_event,
                          sort_events)
from ui.widgets import setup_table, plain_item

P_HEAD = ["名称", "类型", "组别", "年级", "比赛日", "时段", "时间",
          "场地", "规则说明", "校记录", "备注", "参与"]
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
        self.cb_session.addItems(["", "上午", "下午"])   # 默认空白
        self.ed_day = QLineEdit(ev.day if ev else date.today().isoformat())
        self.ed_day.setPlaceholderText("如：第一天 或 2026-10-12")
        self.ed_time = QLineEdit(ev.time if ev else "")
        self.ed_time.setPlaceholderText("如：08:40")
        self.ed_venue = QLineEdit(ev.venue if ev else "")
        self.ed_record = QLineEdit(ev.record if ev else "")
        self.ed_note = QLineEdit(ev.note if ev else "")
        self.ed_note.setPlaceholderText("备注（如：50米团体按实际人数减1人取平均值）")
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
    """时间轴预览（简化表格版）：每天一张表，行=时间点，列=田赛/径赛。"""

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
                field = "；".join(
                    f"{e.name}({e.grade or ''}{e.group})"
                    for e in by_time[t] if e.etype == "田赛")
                track = "；".join(
                    f"{e.name}({e.grade or ''}{e.group})"
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
                ("新增项目", self.add_event, False),
                ("编辑选中", self.edit_event, True),
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
        lv.addWidget(self.table, 1)
        json_row = QHBoxLayout()
        json_row.addStretch(1)
        b_imp = QPushButton("导入项目JSON")
        b_imp.clicked.connect(self.import_json)
        b_exp = QPushButton("导出项目JSON")
        b_exp.clicked.connect(self.export_json)
        json_row.addWidget(b_exp)
        json_row.addWidget(b_imp)
        lv.addLayout(json_row)
        split.addWidget(left)

        # ---------- 右：赛程管理 ----------
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(6, 6, 6, 6)
        rv.addWidget(QLabel("赛程管理（按 天 -> 时段 -> 时间 排序）"))
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

    # ---------- 左表 ----------
    def refresh(self):
        self.refresh_projects()
        self.refresh_schedule()

    def refresh_projects(self):
        evs = self.state.events
        self.lbl.setText(
            f"共 {len(evs)} 个项目（参与 {sum(1 for e in evs if e.enabled)}）"
            f"（田赛 {sum(1 for e in evs if e.etype == '田赛')} / "
            f"径赛 {sum(1 for e in evs if e.etype == '径赛')}）")
        setup_table(self.table, P_HEAD)
        self.table.setRowCount(0)
        self._ids = []
        for e in evs:
            i = self.table.rowCount()
            self.table.insertRow(i)
            self._ids.append(e.eid)
            values = [e.name, e.etype, e.group, e.grade, e.day, e.session,
                      e.time, e.venue, e.rule, e.record, e.note,
                      "是" if e.enabled else "否"]
            for j, v in enumerate(values):
                self.table.setItem(i, j, plain_item(v))

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

    # ---------- 右侧赛程 ----------
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
# ui/class_page.py（号码范围刷新：两种模式）
# ============================================================
FILES["ui/class_page.py"] = r'''# -*- coding: utf-8 -*-
"""班级管理页：增删改、统一命名、号码范围计算、JSON 导入导出。"""
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
        self.ed_name.setPlaceholderText("如：初一(3)班")
        self.ed_leader = QLineEdit(info.leader if info else "")
        self.ed_leader.setPlaceholderText("领队（如班主任姓名）")
        self.ed_num = QLineEdit(info.num_range if info else "")
        self.ed_num.setPlaceholderText("如：0001~0016（留空可点“刷新号码范围”自动算）")
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
        btns = QHBoxLayout()
        for text, slot in [
                ("新增班级", self.add_class),
                ("编辑选中", self.edit_selected),
                ("删除选中", self.del_selected),
                ("统一命名格式", self.normalize_all),
                ("从报名数据补充", self.fill_from_records),
                ("刷新号码范围", self.refresh_numbers),
                ("导入班级JSON", self.import_json),
                ("导出班级JSON", self.export_json)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)
        btns.addStretch(1)
        root.addLayout(btns)
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
        """按报名人数计算号码范围（模式在设置页选择）。"""
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
# ui/generate_page.py（输出信息移入本页）
# ============================================================
FILES["ui/generate_page.py"] = r'''# -*- coding: utf-8 -*-
"""生成秩序册页：输出信息 -> 确认模块清单 -> 生成 -> 打开文件夹。"""
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

        box = QGroupBox("输出信息（用于封面和通知，留空则跳过相应内容）")
        form = QFormLayout(box)
        self.ed_school = QLineEdit(self.state.settings.get("school", ""))
        self.ed_school.setPlaceholderText("学校名称，如：某某中学")
        self.ed_year = QLineEdit(self.state.settings.get("year", ""))
        self.ed_year.setPlaceholderText("如：2026（留空自动用当前年份）")
        self.ed_term = QLineEdit(self.state.settings.get("term", ""))
        self.ed_term.setPlaceholderText("届次/季节，如：秋季、第38届")
        self.ed_sign = QLineEdit(self.state.settings.get("signature", ""))
        self.ed_sign.setPlaceholderText("备用署名（学校为空时封面用它）")
        self.ed_email = QLineEdit(self.state.settings.get("email", ""))
        self.ed_email.setPlaceholderText("联系邮箱（可选）")
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

# ============================================================
# ui/settings_page.py（精简：输出目录/字体/冲突分钟数/号码模式）
# ============================================================
FILES["ui/settings_page.py"] = r'''# -*- coding: utf-8 -*-
"""设置页（精简版）：默认输出目录、默认字体、冲突判定分钟数、号码范围模式。"""
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QSpinBox, QVBoxLayout, QWidget)

from app import config


class SettingsPage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "封面/通知用的学校名称、年份等已移到“生成秩序册”页。\n"
            "修改后请点“保存设置”。"))

        box = QGroupBox("设置")
        form = QFormLayout(box)
        self.lbl_out = QLabel(self.state.settings.get("output_dir", "")
                              or "（未设置）")
        b_out = QPushButton("选择默认输出目录")
        b_out.clicked.connect(self.pick_out)
        form.addRow("默认输出目录：", self.lbl_out)
        form.addRow("", b_out)
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
        form.addRow("默认字体：", font_row)
        self.sp_conflict = QSpinBox()
        self.sp_conflict.setRange(5, 120)
        self.sp_conflict.setValue(
            int(self.state.settings.get("conflict_minutes", 20)))
        self.sp_conflict.setToolTip(
            "同一运动员两项目 / 同时段两项目时间差小于该分钟数即报警")
        form.addRow("冲突判定分钟数：", self.sp_conflict)
        self.cb_number = QComboBox()
        self.cb_number.addItems(["全校累计（各班连续编号）",
                                 "班内独立（每班从 1 开始）"])
        mode = self.state.settings.get("number_mode", "全校累计")
        self.cb_number.setCurrentIndex(
            1 if mode == "班内独立" else 0)
        form.addRow("号码范围模式：", self.cb_number)
        root.addWidget(box)

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
# ui/modules_page.py（母标题醒目、无预置文本）
# ============================================================
FILES["ui/modules_page.py"] = r'''# -*- coding: utf-8 -*-
"""秩序册模块页。

- 每个模块一个分组框：母标题（分组框标题）加大加粗，醒目。
- 勾选 = 参与秩序册；取消勾选 = 生成时完全跳过（框架也不输出）。
- 文本内容需自行填写；勾选且填写了内容才会生成“框架 + 内容”。
"""
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QScrollArea, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from app import module_flags

TITLE_STYLE = (
    "QGroupBox::title { subcontrol-origin: margin; "
    "font-size: 15px; font-weight: bold; color: #1a4f8a; "
    "padding: 2px 6px; }"
    "QGroupBox { font-size: 13px; margin-top: 12px; }")


def _clause_row(data, on_change):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    cb = QCheckBox()
    cb.setChecked(bool(data.get("checked", True)))
    ed_title = QLineEdit(data.get("title", ""))
    ed_title.setFixedWidth(160)
    ed_text = QPlainTextEdit(data.get("text", ""))
    ed_text.setPlaceholderText("（正文，可打字填写）")
    ed_text.setFixedHeight(56)

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
    return w


def _member_group(data, on_change):
    gb = QGroupBox()
    gb.setCheckable(True)
    gb.setChecked(bool(data.get("checked", True)))
    lay = QHBoxLayout(gb)
    ed_name = QLineEdit(data.get("name", ""))
    ed_name.setFixedWidth(240)
    ed_members = QPlainTextEdit(data.get("members", ""))
    ed_members.setPlaceholderText("人员名单（多人用顿号或换行分隔）")
    ed_members.setFixedHeight(52)

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
    return gb


def _table_editor(headers, rows, on_change):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels([str(h) for h in headers])
    table.setRowCount(0)
    table.blockSignals(True)
    for row in rows:
        i = table.rowCount()
        table.insertRow(i)
        for j, v in enumerate(row):
            table.setItem(i, j, QTableWidgetItem(str(v if v is not None else "")))
    table.blockSignals(False)

    def sync():
        rows.clear()
        for i in range(table.rowCount()):
            rows.append([table.item(i, j).text() if table.item(i, j) else ""
                         for j in range(table.columnCount())])
        on_change()

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

    btns = QHBoxLayout()
    b_add = QPushButton("添加一行")
    b_add.clicked.connect(add_row)
    b_del = QPushButton("删除选中行")
    b_del.clicked.connect(del_row)
    btns.addWidget(b_add)
    btns.addWidget(b_del)
    btns.addStretch(1)
    lay.addWidget(table)
    lay.addLayout(btns)
    return w


class ModulesPage(QWidget):
    def __init__(self, state, main_win):
        super().__init__()
        self.state = state
        self.main = main_win
        self.flags = module_flags.get_flags()

        outer = QVBoxLayout(self)
        outer.addWidget(QLabel(
            "勾选模块 = 参与生成（输出框架）；取消勾选 = 完全跳过。\n"
            "勾选且填写了内容，才会生成“框架 + 内容”的完整章节。\n"
            "所有改动即时保存，关闭再开仍在。"))
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

    # ---------- 各模块内容 ----------
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
        ed_slogan.setPlaceholderText("导语，如：成大师风骨，铸健全人格")

        def sync_slogan():
            f["slogan"] = ed_slogan.text()
            self._save()

        ed_slogan.textChanged.connect(lambda _t: sync_slogan())
        form.addRow(cb_slogan, ed_slogan)
        ed_date = QLineEdit(f.get("date_text", ""))
        ed_date.setPlaceholderText("封面日期，如：2026年10月（留空自动按当前月份）")

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
        ed_title.setPlaceholderText("通知标题，支持 {school} {year} {term} 占位符")
        ed_body = QPlainTextEdit(f.get("body", ""))
        ed_body.setPlaceholderText("通知正文（可多行，空则不输出本模块内容）")
        ed_body.setFixedHeight(110)

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
        lay.addLayout(form)

    def _build_rules(self, lay, f):
        lay.addWidget(QLabel("每条条款可单独勾选；勾选且填了标题/正文才输出。"))
        for c in f.get("clauses", []):
            lay.addWidget(_clause_row(c, self._save))

    def _build_committee(self, lay, f):
        for g in f.get("groups", []):
            lay.addWidget(_member_group(g, self._save))

    def _build_referees(self, lay, f):
        for g in f.get("groups", []):
            lay.addWidget(_member_group(g, self._save))

    def _build_awards(self, lay, f):
        lay.addWidget(QLabel("颁奖仪式表（生成时单独占一页；空表不输出）。"))
        rows = f.setdefault("rows", [])
        lay.addWidget(_table_editor(f.get("headers", []), rows, self._save))

    def _build_schedule(self, lay, f):
        lay.addWidget(self._flag_cb(f, "split_field_track", "田赛/径赛分开显示"))
        lay.addWidget(self._flag_cb(f, "show_time", "显示时间"))
        lay.addWidget(self._flag_cb(f, "show_count", "显示人数、组数（下一版本生效）"))
        lay.addWidget(QLabel("日程数据来自“项目管理”右侧的赛程设置。"))

    def _build_rosters(self, lay, f):
        lay.addWidget(self._flag_cb(f, "only_checked_classes", "只输出勾选的班级"))
        lay.addWidget(QLabel("班级参与、领队、号码范围在“班级管理”页编辑。"))

    def _build_grouping(self, lay, f):
        lay.addWidget(self._flag_cb(f, "only_checked_events", "只输出勾选的项目"))

    def _build_class_list(self, lay, f):
        lay.addWidget(QLabel("按班级输出参赛名单表格（数据来自报名记录）。"))

    def _build_event_list(self, lay, f):
        lay.addWidget(QLabel("按项目输出参赛人员，分男子/女子（数据来自报名记录）。"))

    def _build_appendix(self, lay, f):
        for it in f.get("items", []):
            lay.addWidget(_clause_row(it, self._save))

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
# make_test_data.py（每种错误一条 + 号码列）
# ============================================================
FILES["make_test_data.py"] = r'''# -*- coding: utf-8 -*-
"""生成测试用报名数据表（每种错误类型只出现一次）。"""
import os

import pandas as pd

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT_DIR, exist_ok=True)

rows = []


def add(cls, name, gender, ev, num="", grp="", t="08:30", v="田径场"):
    rows.append({"班级": cls, "姓名": name, "性别": gender, "项目": ev,
                 "号码": num, "组别": grp, "赛程时间": t, "场地": v})


clean = [("初一(1)班", "张三", "男", "100米", "0101"),
         ("初一(1)班", "李梅", "女", "100米", "0102"),
         ("初二(3)班", "王五", "男", "铅球", "0301"),
         ("初二(3)班", "赵琳", "女", "跳高", "0302"),
         ("七年级2班", "孙尚香", "女", "800米", "0201"),
         ("初三(5)班", "周瑜", "男", "200米", "0501"),
         ("九年级4班", "郑成功", "男", "跳远", "0401"),
         ("初二3班", "冯程程", "女", "实心球", "0303")]
for c, n, g, e, num in clean:
    add(c, n, g, e, num)

add("初一(1)班", "张三", "男", "100米,跳远", num="0101")
add("初一(1)班", "王小明", "男", "100m", num="0103")
add("初一1班", "赵子龙", "男", "一百米", num="0104")
add("七年级2班", "钱多多", "女", "女子200米决赛", grp="女子组", t="09:00")
add("初三·2", "吴用", "男", "4乘100接力", t="11:00")
add("初一(1)班", "陈梦", "", "女子100米", num="0105")
add("初二(3)班", "朱重八", "", "跳远", t="15:00", v="沙坑")
add("3班", "吕小布", "男", "100米")
add("高中部", "施雨", "女", "跳高", t="14:00", v="沙坑")
add("初一(1)班", "孔", "男", "100米")
add("初一(1)班", "王1", "男", "200米", t="09:00")
add("初一(1)班", "李雷", "男", "瞎写项目", t="09:00")
add("初一(1)班", "", "男", "100米")
add("", "孔明", "男", "100米")
add("初一(1)班", "李雷", "男", "", "", "", "")

# 项目时间重叠场景（其中一个故意用全角冒号 8：40）
add("初一(1)班", "赵子龙", "男", "100米", t="8:40")
add("初一(1)班", "陈梦", "", "女子100米", num="0105", t="8：40")

# 运动员时间冲突场景
add("初一(1)班", "钱多多", "女", "跳高", t="14:00", v="沙坑")
add("初一(1)班", "钱多多", "女", "铅球", t="14:10", v="投掷区")

df = pd.DataFrame(rows)
path1 = os.path.join(OUT_DIR, "测试报名表.xlsx")
df.to_excel(path1, index=False)
print(f"已生成：{path1}（{len(df)} 行）")

df2 = pd.DataFrame({
    "班别": ["七年级1班", "八年级2班"],
    "学生": ["刘备", "关羽"],
    "sex": ["男", "男"],
    "参赛项目": ["60m", "垒球"],
    "分组": ["甲组", "乙组"],
    "比赛时间": ["08:00", "14:00"],
    "地点": ["田径场", "投掷区"],
})
path2 = os.path.join(OUT_DIR, "测试报名表2.csv")
df2.to_csv(path2, index=False, encoding="utf-8-sig")
print(f"已生成：{path2}（{len(df2)} 行）")
'''


def main():
    print("运动会秩序册生成工具 第二轮更新 脚本B（ui 层）")
    print("=" * 50)
    open(os.path.join(BASE, "ui", "__init__.py"), "a").close()
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

    # 删除已废弃的 schedule_page.py
    old = os.path.join(BASE, "ui", "schedule_page.py")
    if os.path.exists(old):
        os.remove(old)
        print("  [OK] 已删除 ui/schedule_page.py")
    else:
        print("  [跳过] ui/schedule_page.py 不存在（可能已删除）")

    print("=" * 50)
    if fail:
        print(f"完成 {ok} 个，失败 {len(fail)} 个：{fail}")
        print("请把上方错误信息发回给助手。")
        sys.exit(1)
    print(f"全部 {ok} 个文件写入并检查通过。")
    print("现在可以运行 python main.py 启动程序。")
    print("首次启动会自动完成旧数据迁移（竞赛->径赛、清空预置文本、保留勾选）。")


if __name__ == "__main__":
    main()
