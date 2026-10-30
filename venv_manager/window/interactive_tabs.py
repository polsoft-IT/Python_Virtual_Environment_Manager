#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tab pages whose widgets the user interacts with (builders only)."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit,
    QComboBox, QCheckBox, QTableWidget, QPlainTextEdit, QTreeWidget,
    QGroupBox, QHeaderView, QAbstractItemView, QTabWidget, QSpinBox,
)

from ..config import tr
from ..widgets import StatCard, mono_font


class InteractiveTabsMixin:
    def _tab_dashboard(self):
        """Dashboard page; registered in _build_tabs()."""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_envs = StatCard("\U0001F4C1", tr("dash_total_venvs"), self.C("accent"))
        self.card_pkgs = StatCard("\U0001F4E6", tr("dash_total_pkgs"), self.C("green"))
        self.card_outdated = StatCard("\u2B06", tr("dash_outdated"), self.C("yellow"))
        self.card_disk = StatCard("\U0001F4BE", tr("dash_disk"),
                                  self.C("accent2"))
        for card in (self.card_envs, self.card_pkgs, self.card_outdated, self.card_disk):
            cards.addWidget(card)
        lay.addLayout(cards)

        mid = QHBoxLayout()
        mid.setSpacing(10)

        quick_box = QGroupBox(tr("dash_quick_actions"))
        quick_lay = QVBoxLayout(quick_box)
        quick = [
            (f"+  {tr('create_venv')}", self.action_create_venv),
            (f"Install package", self.action_install_package),
            (f"Search PyPI", self.action_search_pypi),
            (f"Upgrade all", self.action_upgrade_all),
            (f"pip-audit", self.action_pip_audit),
            (f"Compare environments", self.action_compare_venvs),
            (f"Export requirements.txt", self.action_export_requirements),
            (f"Refresh statistics", self.refresh_dashboard),
        ]
        for text, slot in quick:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, s=slot: s())
            quick_lay.addWidget(btn)
        quick_lay.addStretch(1)
        mid.addWidget(quick_box, 1)

        chart_box = QGroupBox(tr("dash_chart"))
        chart_lay = QVBoxLayout(chart_box)
        self.chart_label = QPlainTextEdit()
        self.chart_label.setReadOnly(True)
        self.chart_label.setFont(mono_font(self.settings.get("font_family"),
                                           max(8, self.settings.get("font_size", 10) - 1)))
        chart_lay.addWidget(self.chart_label)
        mid.addWidget(chart_box, 1)

        info_box = QGroupBox(tr("dash_system_info"))
        info_lay = QVBoxLayout(info_box)
        self.dash_info = QPlainTextEdit()
        self.dash_info.setReadOnly(True)
        self.dash_info.setFont(mono_font(self.settings.get("font_family"), 10))
        info_lay.addWidget(self.dash_info)
        mid.addWidget(info_box, 2)
        lay.addLayout(mid, 1)

        recent_box = QGroupBox(tr("dash_recent"))
        recent_lay = QHBoxLayout(recent_box)
        self.recent_widget = QWidget()
        self.recent_layout = QHBoxLayout(self.recent_widget)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_lay.addWidget(self.recent_widget, 1)
        lay.addWidget(recent_box)
        return page

    # ============================================================== PACKAGES TAB
    def _tab_packages(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        top = QHBoxLayout()
        self.pkg_filter = QLineEdit()
        self.pkg_filter.setPlaceholderText(tr("search_packages"))
        self.pkg_filter.textChanged.connect(self.apply_pkg_filter)
        top.addWidget(self.pkg_filter, 1)

        buttons = [
            (f"+  {tr('install')}", self.action_install_package, "accentButton"),
            (f"-  {tr('uninstall')}", self.action_uninstall_package, "dangerButton"),
            (f"Upgrade", self.action_upgrade_package, None),
            (f"Upgrade all", self.action_upgrade_all, None),
            (f"Check outdated", self.action_check_outdated, None),
            (f"Info", self.action_package_info, None),
        ]
        for text, slot, obj in buttons:
            btn = QPushButton(text)
            if obj:
                btn.setObjectName(obj)
            btn.clicked.connect(lambda _=False, s=slot: s())
            top.addWidget(btn)
        lay.addLayout(top)

        self.pkg_table = QTableWidget(0, 4)
        self.pkg_table.setHorizontalHeaderLabels(
            [tr("col_package"), tr("col_version"), tr("col_latest"), tr("col_location")])
        self.pkg_table.verticalHeader().setVisible(False)
        self.pkg_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.pkg_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.pkg_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pkg_table.setAlternatingRowColors(True)
        self.pkg_table.setShowGrid(False)
        self.pkg_table.setSortingEnabled(True)
        self.pkg_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pkg_table.customContextMenuRequested.connect(self.pkg_context_menu)
        self.pkg_table.itemDoubleClicked.connect(lambda _i: self.action_package_info())
        header = self.pkg_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.pkg_table, 1)

        bottom = QHBoxLayout()
        self.pkg_count_label = QLabel(tr("no_environment"))
        bottom.addWidget(self.pkg_count_label, 1)
        for text, slot in (("Select all", self.pkg_select_all),
                           ("Export requirements.txt", self.action_export_requirements),
                           ("pip-audit", self.action_pip_audit),
                           ("Freeze", self.action_freeze_packages)):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, s=slot: s())
            bottom.addWidget(btn)
        lay.addLayout(bottom)
        return page

    # =============================================================== CONSOLE TAB
    def _tab_console(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        top = QHBoxLayout()
        for text, slot in ((tr("clear"), self.clear_console),
                           (tr("save_log"), self.save_console_log),
                           (tr("search"), self.search_console)):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, s=slot: s())
            top.addWidget(btn)

        self.wrap_cb = QCheckBox(tr("wrap"))
        self.wrap_cb.setChecked(True)
        self.wrap_cb.toggled.connect(self.toggle_wrap)
        top.addWidget(self.wrap_cb)

        self.autoscroll_cb = QCheckBox(tr("autoscroll"))
        self.autoscroll_cb.setChecked(True)
        top.addWidget(self.autoscroll_cb)
        top.addStretch(1)
        lay.addLayout(top)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.console.setMaximumBlockCount(20000)
        self.console.setFont(mono_font(self.settings.get("font_family"), 10))
        lay.addWidget(self.console, 1)

        row = QHBoxLayout()
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText(tr("cmd_placeholder"))
        self.cmd_edit.returnPressed.connect(self.run_console_command)
        self._cmd_history = []
        self._cmd_index = 0
        self.cmd_edit.installEventFilter(self)
        row.addWidget(self.cmd_edit, 1)

        run_btn = QPushButton(tr("run"))
        run_btn.setObjectName("accentButton")
        run_btn.clicked.connect(self.run_console_command)
        row.addWidget(run_btn)
        lay.addLayout(row)
        return page

    # ========================================================= SCRIPT RUNNER TAB
    def _tab_script(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.addWidget(QLabel(tr("script_path")))
        self.script_path = QLineEdit()
        top.addWidget(self.script_path, 1)
        browse = QPushButton(tr("browse"))
        browse.clicked.connect(self.browse_script)
        top.addWidget(browse)

        top.addWidget(QLabel(tr("script_args")))
        self.script_args = QLineEdit()
        self.script_args.setMaximumWidth(220)
        top.addWidget(self.script_args)

        run_btn = QPushButton(tr("run"))
        run_btn.setObjectName("accentButton")
        run_btn.clicked.connect(self.run_script)
        top.addWidget(run_btn)

        self.script_stop_btn = QPushButton(tr("stop"))
        self.script_stop_btn.setObjectName("dangerButton")
        self.script_stop_btn.setEnabled(False)
        self.script_stop_btn.clicked.connect(self.stop_script)
        top.addWidget(self.script_stop_btn)
        lay.addLayout(top)

        self.script_out_tabs = QTabWidget()
        self.script_stdout = QPlainTextEdit()
        self.script_stdout.setReadOnly(True)
        self.script_stdout.setFont(mono_font(self.settings.get("font_family"), 10))
        self.script_stderr = QPlainTextEdit()
        self.script_stderr.setReadOnly(True)
        self.script_stderr.setFont(mono_font(self.settings.get("font_family"), 10))
        self.script_out_tabs.addTab(self.script_stdout, tr("tab_stdout"))
        self.script_out_tabs.addTab(self.script_stderr, tr("tab_stderr"))
        lay.addWidget(self.script_out_tabs, 1)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel(tr("exit_code")))
        self.script_exit_label = QLabel("--")
        self.script_exit_label.setStyleSheet("font-weight: bold;")
        bottom.addWidget(self.script_exit_label)
        self.script_time_label = QLabel("")
        bottom.addWidget(self.script_time_label)
        bottom.addStretch(1)
        lay.addLayout(bottom)
        self._script_worker = None
        return page

    # ================================================================ GIT TAB
    def _tab_git(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.addWidget(QLabel(tr("repo_path")))
        self.git_path = QLineEdit()
        top.addWidget(self.git_path, 1)
        browse = QPushButton(tr("browse"))
        browse.clicked.connect(self.browse_git_repo)
        top.addWidget(browse)
        for text, args in ((tr("git_status"), ["status", "-sb"]),
                           (tr("pull"), ["pull", "--rebase"]),
                           (tr("log"), ["log", "--oneline", "--graph", "--decorate", "-20"]),
                           (tr("branches"), ["branch", "-vv"]),
                           (tr("stash"), ["stash", "list"])):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, a=args: self.git_command(a))
            top.addWidget(btn)
        lay.addLayout(top)

        info = QHBoxLayout()
        info.addWidget(QLabel(f"{tr('git_branch')}:"))
        self.git_branch_label = QLabel("--")
        self.git_branch_label.setStyleSheet("font-weight: bold; color: palette(highlight);")
        info.addWidget(self.git_branch_label)
        info.addSpacing(20)
        self.git_status_label = QLabel("")
        info.addWidget(self.git_status_label)
        info.addStretch(1)
        lay.addLayout(info)

        self.git_output = QPlainTextEdit()
        self.git_output.setReadOnly(True)
        self.git_output.setFont(mono_font(self.settings.get("font_family"), 10))
        lay.addWidget(self.git_output, 1)
        return page
