# -*- coding: utf-8 -*-
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
