# -*- coding: utf-8 -*-
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
