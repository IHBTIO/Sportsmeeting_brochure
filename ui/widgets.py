# -*- coding: utf-8 -*-
"""界面通用工具：置信度配色、表格构造、单元格创建。"""
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QHeaderView, QTableWidgetItem

# 置信分 -> 颜色（90-100 通过，60-89 黄，0-59 红）
CONF_COLORS = {
    "green": QColor(200, 240, 200),
    "yellow": QColor(255, 244, 189),
    "red": QColor(255, 205, 205),
}


def conf_level(score: int) -> str:
    if score >= 90:
        return "green"
    if score >= 60:
        return "yellow"
    return "red"


def plain_item(text):
    """普通（无底色）表格单元格。"""
    return QTableWidgetItem("" if text is None else str(text))


def conf_item(text, score=None, conflict=False):
    """带置信度/冲突背景色的表格单元格。"""
    it = plain_item(text)
    if conflict:
        it.setBackground(QBrush(CONF_COLORS["red"]))
    elif score is not None:
        it.setBackground(QBrush(CONF_COLORS[conf_level(score)]))
    return it


def setup_table(table, headers, stretch_last=True):
    """初始化 QTableWidget 表头。"""
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(type(table).NoEditTriggers)
    table.setSelectionBehavior(type(table).SelectRows)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeToContents)
    if stretch_last:
        header.setStretchLastSection(True)
