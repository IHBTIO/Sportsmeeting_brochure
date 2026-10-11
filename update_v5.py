# -*- coding: utf-8 -*-
"""运动会秩序册生成工具 v2.5.0 更新。

- 新增 app/version.py：版本号、作者、GitHub 链接（链接只从 data/about.json 读取）
- 主窗口标题栏显示版本号和作者
- 设置页新增「关于」分组：版本/作者/链接（只读，应用内不提供修改入口）
- 生成 data/about.json 空模板（作者、链接由你自行填写）
"""
import os
import py_compile
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

FILES = {}

# ============================================================
# app/version.py（新增）
# ============================================================
FILES["app/version.py"] = r'''# -*- coding: utf-8 -*-
"""版本与作者信息。

GitHub 链接、作者名只能通过 data/about.json 修改，应用内只读展示。
"""
import os

from . import config

APP_VERSION = "2.5.0"
ABOUT_FILE = os.path.join(config.DATA_DIR, "about.json")


def get_about():
    data = config.load_json(ABOUT_FILE, {}) or {}
    if not isinstance(data, dict):
        data = {}
    return {
        "version": APP_VERSION,
        "author": str(data.get("author", "") or ""),
        "github": str(data.get("github", "") or ""),
        "description": str(data.get("description", "") or ""),
    }
'''

# ============================================================
# ui/main_window.py（标题栏加版本号和作者）
# ============================================================
FILES["ui/main_window.py"] = r'''# -*- coding: utf-8 -*-
"""主窗口：左侧导航 + 右侧内容区。"""
import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QHBoxLayout, QListWidget, QMainWindow,
                               QStackedWidget, QWidget)

from app.config import APP_NAME
from app.data_models import AppState
from app.version import APP_VERSION, get_about
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
        about = get_about()
        title = f"{APP_NAME} v{APP_VERSION}"
        if about["author"]:
            title += f"  作者：{about['author']}"
        self.setWindowTitle(title)
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
            f"v{APP_VERSION}  当前共 {len(self.state.records)} 条报名记录")

    def goto(self, page_name):
        if page_name in NAV:
            self.nav.setCurrentRow(NAV.index(page_name))

    def refresh_all(self):
        for p in self.pages.values():
            if hasattr(p, "refresh"):
                p.refresh()
        self.statusBar().showMessage(
            f"v{APP_VERSION}  当前共 {len(self.state.records)} 条报名记录")

    def closeEvent(self, event):
        self.state.save()
        super().closeEvent(event)
'''

# ============================================================
# ui/settings_page.py（新增「关于」分组）
# ============================================================
FILES["ui/settings_page.py"] = r'''# -*- coding: utf-8 -*-
"""设置页：智能识别（子分组）+ 常规设置 + 关于。"""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
                               QWidget)

from app import config, module_flags
from app.version import APP_VERSION, get_about


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
        about = get_about()
        box3 = QGroupBox("关于")
        form3 = QFormLayout(box3)
        form3.addRow("版本：", QLabel(f"v{APP_VERSION}"))
        form3.addRow("作者：", QLabel(about["author"] or "（未设置）"))
        if about["description"]:
            form3.addRow("简介：", QLabel(about["description"]))
        link_row = QHBoxLayout()
        self.ed_link = QLineEdit(about["github"])
        self.ed_link.setReadOnly(True)          # 只读：应用内不提供修改入口
        self.ed_link.setPlaceholderText("（未设置，见下方说明）")
        link_row.addWidget(self.ed_link, 1)
        if about["github"]:
            b_open = QPushButton("打开链接")
            b_open.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(about["github"])))
            link_row.addWidget(b_open)
        form3.addRow("开源地址：", link_row)
        form3.addRow(QLabel(
            "开源链接、作者名只能在配置文件 data/about.json 中修改：\n"
            '  {"author": "你的名字", "github": "https://github.com/你/仓库",\n'
            '   "description": "项目简介"}\n'
            "修改后重启程序生效。"))
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
'''


def main():
    print("运动会秩序册生成工具 v2.5.0 更新")
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

    # about.json 模板（字段全空，由用户自行填写；已存在则不覆盖）
    data_dir = os.path.join(BASE, "data")
    os.makedirs(data_dir, exist_ok=True)
    about_path = os.path.join(data_dir, "about.json")
    if not os.path.exists(about_path):
        with open(about_path, "w", encoding="utf-8") as f:
            f.write('{\n  "author": "",\n  "github": "",\n'
                    '  "description": ""\n}\n')
        print("  [OK] 已生成 data/about.json 模板（请自行填写）")
    else:
        print("  [跳过] data/about.json 已存在，不覆盖")

    print("=" * 50)
    if fail:
        print(f"完成 {ok} 个，失败 {len(fail)} 个：{fail}")
        sys.exit(1)
    print(f"全部 {ok} 个文件写入并检查通过。")
    print("运行 python main.py 启动，标题栏应显示版本号和作者。")


if __name__ == "__main__":
    main()
