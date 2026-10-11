# -*- coding: utf-8 -*-
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
