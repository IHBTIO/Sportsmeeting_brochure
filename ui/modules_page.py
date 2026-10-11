# -*- coding: utf-8 -*-
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
