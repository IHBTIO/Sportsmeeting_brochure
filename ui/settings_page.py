# -*- coding: utf-8 -*-
"""设置页：智能识别（子分组）+ 常规设置 + 关于。"""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget)

from app import config, module_flags
from app.version import APP_VERSION, AUTHOR, GITHUB, DESCRIPTION


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

        # ---- 关于 ----
        box3 = QGroupBox("关于")
        form3 = QFormLayout(box3)
        form3.addRow("版本：", QLabel(f"v{APP_VERSION}"))
        form3.addRow("作者：", QLabel(AUTHOR))
        form3.addRow("简介：", QLabel(DESCRIPTION))
        link_row = QHBoxLayout()
        lbl_link = QLabel(GITHUB or "（待开源，见代码 app/version.py）")
        lbl_link.setTextInteractionFlags(
            __import__("PySide6.QtCore", fromlist=["Qt"]).TextSelectableByMouse)
        lbl_link.setWordWrap(True)
        link_row.addWidget(lbl_link, 1)
        if GITHUB:
            b_open = QPushButton("打开链接")
            b_open.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(GITHUB)))
            link_row.addWidget(b_open)
        form3.addRow("开源地址：", link_row)
        form3.addRow(QLabel(
            "开源地址、作者名写在代码 app/version.py 中，修改后重启生效。"))
        root.addWidget(box3)

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
