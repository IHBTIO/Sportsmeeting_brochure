# -*- coding: utf-8 -*-
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
