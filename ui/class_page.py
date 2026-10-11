# -*- coding: utf-8 -*-
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
