# -*- coding: utf-8 -*-
"""运动会秩序册生成工具 v2.6.0 开源准备更新。

- 删除 about.json 配置文件机制（含删除已生成的 data/about.json）
- 作者、GitHub 链接直接写在代码 app/version.py 里（修改即改代码）
- 设置-关于：展示只读信息 + 打开链接按钮
- 创建开源所需文件：README.md / .gitignore / requirements.txt / LICENSE
"""
import os
import py_compile
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

FILES = {}

# ============================================================
# app/version.py（重写：作者和链接写死在代码里）
# ============================================================
FILES["app/version.py"] = r'''# -*- coding: utf-8 -*-
"""版本与作者信息。

开源仓库地址在这里修改（应用内不提供修改入口）：
    本文件中 GITHUB 常量。
修改后重启程序生效。
"""

APP_VERSION = "2.6.0"
AUTHOR = "hbhbhbhbhvb"
GITHUB = ""   # 开源后填你的仓库地址，如 "https://github.com/hbhbhbhbhvb/sport-meet"
DESCRIPTION = "学校运动会秩序册自动生成工具（报名表导入 -> 智能识别 -> 冲突检查 -> Word 秩序册）"


def get_about():
    return {
        "version": APP_VERSION,
        "author": AUTHOR,
        "github": GITHUB,
        "description": DESCRIPTION,
    }
'''

# ============================================================
# ui/settings_page.py（关于区改为展示代码常量）
# ============================================================
FILES["ui/settings_page.py"] = r'''# -*- coding: utf-8 -*-
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
'''

# ============================================================
# ui/main_window.py（标题栏版本+作者，去掉配置读取）
# ============================================================
FILES["ui/main_window.py"] = r'''# -*- coding: utf-8 -*-
"""主窗口：左侧导航 + 右侧内容区。"""
import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QHBoxLayout, QListWidget, QMainWindow,
                               QStackedWidget, QWidget)

from app.config import APP_NAME
from app.data_models import AppState
from app.version import APP_VERSION, AUTHOR
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
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}  作者：{AUTHOR}")
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
# README.md
# ============================================================
FILES["README.md"] = r'''# 运动会秩序册生成工具

学校运动会秩序册自动生成工具：从报名表（Excel/CSV）导入数据，
经智能识别、人工审查、冲突检测，一键排版生成 Word 格式秩序册。

- **版本**：v2.6.0
- **作者**：hbhbhbhbhvb
- **开源地址**：见 `app/version.py` 中的 GITHUB 常量

## 功能特性

- 多类型数据导入：报名信息 / 校纪录 / 体质健康标准 / 其他表格，
  均带字段映射，额外列自动忽略，支持覆盖/追加
- 智能识别：项目名、班级名、人名、性别自动规范化，
  置信分分级（自动通过/建议核对/需人工审查），开关与阈值可调
- 人工审查：按问题分组查看、批量忽略、逐条修改、手动增删
- 项目管理：内置 40+ 常见项目，可自定义/禁用/删除，
  时间轴预览，一键冲突检测（项目时间重叠=黄色，运动员冲突=红色）
- 班级管理：号码范围自动计算（全校累计 / 班内独立）
- 秩序册模块：13 个模块自由勾选，长文本支持 txt/docx 导入与拖拽，
  条款支持预设快速填写
- Word 输出：目录自动生成，黑体标题 / 宋体正文 / 表格线框

## 环境要求

Python 3.9+，Windows / macOS / Linux

## 安装

bash
git clone <你的仓库地址>
cd sport-meet
pip install -r requirements.txt


## 使用

bash
python main.py


流程：数据导入 → 人工审查 → 项目/赛程管理 → 班级管理 →
秩序册模块 → 生成秩序册。测试数据可运行 `python make_test_data.py`。

## 二次开发

- 修改作者名/开源地址：`app/version.py` 顶部常量
- 扩充识别词库：`app/recognizer.py`
- 新增预设条款：`app/presets.py`
- 调整 Word 排版：`app/docgen.py`

## 许可证

MIT License，详见 LICENSE。
'''

FILES[".gitignore"] = r'''__pycache__/
*.py[cod]
.venv/
venv/
data/
*.docx
!templates/*.docx
.idea/
.vscode/
'''

FILES["requirements.txt"] = r'''PySide6>=6.5
pandas>=2.0
openpyxl>=3.1
python-docx>=1.1
'''

FILES["LICENSE"] = r'''MIT License

Copyright (c) 2026 hbhbhbhbhvb

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


def main():
    print("运动会秩序册生成工具 v2.6.0 开源准备更新")
    print("=" * 50)
    ok = 0
    fail = []
    for rel, content in FILES.items():
        path = os.path.join(BASE, rel)
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        if rel.endswith(".py"):
            try:
                py_compile.compile(path, doraise=True)
                print(f"  [OK] {rel}")
                ok += 1
            except py_compile.PyCompileError as e:
                print(f"  [失败] {rel}")
                print(str(e))
                fail.append(rel)
        else:
            print(f"  [OK] {rel}")
            ok += 1

    old = os.path.join(BASE, "data", "about.json")
    if os.path.exists(old):
        os.remove(old)
        print("  [OK] 已删除 data/about.json（改为代码常量）")

    print("=" * 50)
    if fail:
        print(f"完成 {ok} 个，失败 {len(fail)} 个：{fail}")
        sys.exit(1)
    print(f"全部 {ok} 个文件写入完成。")
    print("开源地址当前为空，请在 app/version.py 的 GITHUB 常量中填写。")


if __name__ == "__main__":
    main()
