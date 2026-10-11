# -*- coding: utf-8 -*-
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
        self.ed_time.setPlaceholderText("时:分")
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
