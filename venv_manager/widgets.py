#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small reusable widgets and drawing helpers shared by tabs and dialogs."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QBrush, QPen
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QTableWidgetItem


# ==============================================================================
#  SMALL REUSABLE WIDGETS  (graphics helpers)
# ==============================================================================
def make_dot(color, diameter=10):
    """Return a circular QIcon of the given colour (status indicators)."""
    pix = QPixmap(diameter, diameter)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(QPen(QColor(color).darker(140), 1))
    painter.drawEllipse(1, 1, diameter - 2, diameter - 2)
    painter.end()
    return QIcon(pix)


class StatCard(QFrame):
    """A dashboard statistic card: icon, big value and a caption."""

    def __init__(self, icon_text, caption, colour, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(96)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(0)

        self.icon_lbl = QLabel(icon_text)
        self.icon_lbl.setObjectName("cardIcon")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_lbl = QLabel("--")
        self.value_lbl.setObjectName("cardValue")
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_lbl.setStyleSheet(f"color: {colour};")

        self.caption_lbl = QLabel(caption)
        self.caption_lbl.setObjectName("cardCaption")
        self.caption_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(self.icon_lbl)
        lay.addWidget(self.value_lbl)
        lay.addWidget(self.caption_lbl)

    def set_value(self, text):
        self.value_lbl.setText(str(text))


def status_item(text, colour, align_center=False):
    """A QTableWidgetItem whose text is coloured."""
    item = QTableWidgetItem(text)
    item.setForeground(QBrush(QColor(colour)))
    if align_center:
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return item


def mono_font(family, size, bold=False):
    f = QFont(family, size)
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setBold(bold)
    return f


def _table_item_data(item):
    """Return the dict stored on a table item under Qt's UserRole."""
    return item.data(Qt.ItemDataRole.UserRole) if item is not None else None


# ==============================================================================
#  PAGE BOOK  (dashboard / packages / console / script / git / devices / guide)
# ==============================================================================
PAGE_KEYS = ("dashboard", "packages", "console", "script", "git", "devices", "guide")


class PageBook:
    """Ordered registry of the tab pages built by the MainWindow._build_* mixins.

    ``add()`` appends a page, ``goto()`` selects it by key and ``pages`` gives
    the ``(page, title)`` pairs used to populate the QTabWidget.
    """

    def __init__(self):
        self._titles = {}
        self._pages = []

    def add(self, key, page, title):
        self._titles[key] = title
        self._pages.append((key, page, title))

    def keys(self):
        return [key for key, _page, _title in self._pages]

    def index(self, key):
        keys = self.keys()
        return keys.index(key) if key in keys else 0

    def goto(self, tabs, key):
        tabs.setCurrentIndex(self.index(key))

    def pages(self):
        return [(page, title) for _key, page, title in self._pages]
