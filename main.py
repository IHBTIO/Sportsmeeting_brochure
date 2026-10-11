# -*- coding: utf-8 -*-
"""程序入口。"""
import sys

from PySide6.QtWidgets import QApplication

from app.config import APP_NAME
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
