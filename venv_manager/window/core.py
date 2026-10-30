#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MainWindow mixin: theme handling, menus, central layout, status bar, threads.

The other ``window/*_mixin.py`` modules are mixed in next to :class:`WindowCore`
and contribute the tab pages and the environment / package / device actions.
"""

import sys
import time
import inspect
import platform
import subprocess
import datetime

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QMenuBar, QSplitter, QFrame, QTabWidget,
    QStatusBar, QProgressBar, QTableWidget, QHeaderView, QAbstractItemView,
)

from ..config import (
    APP_NAME, APP_VERSION, APP_COMPANY, APP_DATA_DIR, THEMES, DEFAULT_THEME,
    load_settings, save_settings, theme, build_stylesheet, tr,
)
from ..backend import Backend, Worker, StreamWorker
from ..widgets import mono_font, PageBook


class WindowCore(QMainWindow):
    """Window shell: builds the frame, connects signals and manages threads."""

    sig_vd_log = pyqtSignal(str)
    sig_vd_progress = pyqtSignal(int)
    sig_log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.backend = Backend(self.settings)
        self.T = tr
        self.pages = PageBook()

        self.sig_vd_log.connect(self.vd_log_msg)
        self.sig_vd_progress.connect(self.vd_set_progress)
        self.sig_log.connect(self.log)

        self._threads = []
        self._workers = []
        self._stream_workers = []
        self._scan_worker = None
        self._closing = False
        self._venv_rows = []
        self.chart_text = ""
        self._active_venv = None
        self._recent_action = None

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - {APP_COMPANY}")
        self.setMinimumSize(1120, 700)

        self._build_menu()
        self._build_central()
        self._build_statusbar()
        self._bind_shortcuts()

        self.apply_theme()
        self._restore_geometry()
        self.reload_venvs()
        self.refresh_dashboard()

        if self.settings.get("auto_refresh", True):
            self._auto_timer = QTimer(self)
            self._auto_timer.timeout.connect(self.reload_venvs)
            self._auto_timer.start(60_000)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

        self.log(f"{APP_NAME} {APP_VERSION} started.")
        self.log(f"Python {sys.version.split()[0]} on {platform.system()} "
                 f"{platform.release()}")
        self.log(f"Configuration directory: {APP_DATA_DIR}")
        self.log(f"Workspace directory: {self.settings.get('default_venv_dir')}")

    # ------------------------------------------------------------------ theme
    @property
    def _scan_cancelled(self):
        """True when the window is closing or the active scan was cancelled."""
        worker = getattr(self, "_scan_worker", None)
        return bool(worker is not None and worker.is_cancelled()) or self._closing

    def theme_colors(self):
        c = dict(theme(self.settings.get("theme", DEFAULT_THEME)))
        c["_font_family"] = self.settings.get("font_family", "Consolas")
        c["_font_size"] = self.settings.get("font_size", 10)
        return c

    def C(self, key):
        return self.theme_colors().get(key, "#000")

    def apply_theme(self):
        c = self.theme_colors()
        self._col = c
        app = QApplication.instance()
        app.setStyleSheet(build_stylesheet(c))

        font = mono_font(c["_font_family"], c["_font_size"])
        app.setFont(font)

        console_font = mono_font(c["_font_family"], max(8, c["_font_size"] - 1))
        for widget in (self.console, self.script_stdout, self.script_stderr,
                       self.git_output, self.vd_log):
            widget.setFont(console_font)

        for view in (self.venv_table, self.pkg_table, self.vd_table):
            view.setFont(mono_font(c["_font_family"], max(8, c["_font_size"] - 1)))

        self._repaint_table_headers()
        self._apply_console_tags()

    def _repaint_table_headers(self):
        # Colour-coded status text inside the environment table.
        c = self._col
        for row in range(self.venv_table.rowCount()):
            item = self.venv_table.item(row, 2)
            if item is None:
                continue
            active = item.text() == "Active"
            item.setForeground(QBrush(QColor(c["green"] if active else c["bg3"])))

    def _apply_console_tags(self):
        # Re-apply palette colours to the progress and status widgets.
        c = self._col
        self.progress.setStyleSheet(
            f"QProgressBar::chunk {{ background: {c['accent']}; "
            f"border-radius: 3px; }}")
        self.script_exit_label.setStyleSheet("font-weight: bold;")

    def _log_colour(self, message):
        # Pick a foreground colour for a console line based on its content.
        c = self._col
        lowered = message.lower()
        if "[ok]" in lowered or "success" in lowered or "finished" in lowered:
            return c["green"]
        if "[failed]" in lowered or "error" in lowered or "traceback" in lowered:
            return c["red"]
        if "warning" in lowered or "missing" in lowered or "warn" in lowered:
            return c["yellow"]
        if message.lstrip().startswith("$"):
            return c["accent"]
        return None

    def change_theme(self, name):
        self.settings["theme"] = name
        save_settings(self.settings)
        self.apply_theme()
        self.refresh_dashboard()
        self.set_status(f"Theme changed to {name}")

    # ------------------------------------------------------------------ menu
    def _build_menu(self):
        bar: QMenuBar = self.menuBar()

        # -- File
        m_file = bar.addMenu(tr("menu_file"))
        self._act(m_file, tr("new_project"), self.action_new_project, "Ctrl+Shift+N")
        self._act(m_file, tr("open_project"), self.action_new_project, "Ctrl+O")
        m_file.addSeparator()
        self._act(m_file, tr("save_config"), self.action_save_config, "Ctrl+S")
        m_file.addSeparator()
        self._act(m_file, tr("export_requirements"), self.action_export_requirements, "Ctrl+E")
        self._act(m_file, tr("export_pyproject"), self.action_export_pyproject)
        self._act(m_file, tr("export_conda"), self.action_export_conda)
        m_file.addSeparator()
        self._act(m_file, tr("import_requirements"), self.action_import_requirements)
        m_file.addSeparator()
        self.recent_menu = m_file.addMenu(tr("recent_projects"))
        self._rebuild_recent_menu()
        m_file.addSeparator()
        self._act(m_file, tr("exit"), self.close, "Ctrl+Q")

        # -- Environment
        m_env = bar.addMenu(tr("menu_venv"))
        self._act(m_env, tr("create_venv"), self.action_create_venv, "Ctrl+N")
        self._act(m_env, tr("activate_venv"), self.action_activate_venv)
        self._act(m_env, tr("deactivate_venv"), self.action_deactivate_venv)
        m_env.addSeparator()
        self._act(m_env, tr("clone_venv"), self.action_clone_venv)
        self._act(m_env, tr("rename_venv"), self.action_rename_venv)
        self._act(m_env, tr("delete_venv"), self.action_delete_venv, "Ctrl+D")
        m_env.addSeparator()
        self._act(m_env, tr("compare_venvs"), self.action_compare_venvs)
        self._act(m_env, tr("health_check"), self.action_health_check)
        m_env.addSeparator()
        self._act(m_env, tr("refresh_list"), self.reload_venvs, "F5")
        self._act(m_env, tr("open_in_explorer"), self.action_open_in_explorer)
        self._act(m_env, tr("open_in_editor"), self.action_open_in_editor)

        # -- Packages
        m_pkg = bar.addMenu(tr("menu_packages"))
        self._act(m_pkg, tr("install_package"), self.action_install_package, "Ctrl+I")
        self._act(m_pkg, tr("install_from_file"), self.action_install_from_file)
        self._act(m_pkg, tr("bulk_install"), self.action_bulk_install)
        m_pkg.addSeparator()
        self._act(m_pkg, tr("uninstall_package"), self.action_uninstall_package)
        self._act(m_pkg, tr("upgrade_package"), self.action_upgrade_package)
        self._act(m_pkg, tr("upgrade_all"), self.action_upgrade_all, "Ctrl+U")
        m_pkg.addSeparator()
        self._act(m_pkg, tr("freeze_packages"), self.action_freeze_packages)
        self._act(m_pkg, tr("check_outdated"), self.action_check_outdated)
        self._act(m_pkg, tr("show_package_info"), self.action_package_info)
        self._act(m_pkg, tr("search_pypi"), self.action_search_pypi)
        m_pkg.addSeparator()
        self._act(m_pkg, tr("pip_compile"), self.action_pip_compile)
        self._act(m_pkg, tr("pip_sync"), self.action_pip_sync)

        # -- Tools
        m_tools = bar.addMenu(tr("menu_tools"))
        self._act(m_tools, tr("open_terminal"), self.action_open_terminal, "Ctrl+T")
        self._act(m_tools, tr("run_script"), lambda: self._goto_tab("script"))
        m_tools.addSeparator()
        self._act(m_tools, tr("pip_audit"), self.action_pip_audit)
        self._act(m_tools, tr("check_python"), self.action_check_python)
        self._act(m_tools, tr("detect_tools"), self.action_detect_tools)
        self._act(m_tools, tr("detect_pythons"), self.action_detect_pythons)
        self._act(m_tools, tr("clear_cache"), self.action_clear_pip_cache)
        m_tools.addSeparator()
        self._act(m_tools, tr("git_status"), self.action_git_status)
        self._act(m_tools, tr("task_queue"), self.action_thread_activity)

        # -- View
        m_view = bar.addMenu(tr("menu_view"))
        self.theme_menu = m_view.addMenu(tr("theme"))
        for name in THEMES:
            act = QAction(name, self)
            act.setCheckable(True)
            act.setChecked(name == self.settings.get("theme", DEFAULT_THEME))
            act.triggered.connect(lambda _=False, n=name: self.change_theme(n))
            self.theme_menu.addAction(act)
        m_view.addSeparator()
        self._act(m_view, tr("refresh_list"), self.reload_venvs, "F5")
        self._act(m_view, tr("settings"), self.action_settings)
        m_view.addSeparator()
        self._act(m_view, tr("keyboard_shortcuts"), self.action_shortcuts, "F1")
        self._act(m_view, tr("about"), self.action_about)
        self._act(m_view, "Documentation", self.action_docs)

    def _act(self, menu, text, slot, shortcut=None):
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(lambda _=False: slot())
        menu.addAction(act)
        return act

    def _rebuild_recent_menu(self):
        self.recent_menu.clear()
        recents = self.settings.get("recent_projects", [])
        if not recents:
            act = QAction("(empty)", self)
            act.setEnabled(False)
            self.recent_menu.addAction(act)
            return
        for path in recents:
            act = QAction(path, self)
            act.triggered.connect(lambda _=False, p=path: self.open_recent(p))
            self.recent_menu.addAction(act)

    # ------------------------------------------------------------------ layout
    def _build_central(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_toolbar())
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self._build_env_panel())
        self.splitter.addWidget(self._build_tabs())
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        sizes = self.settings.get("splitter_sizes", [380, 1000])
        try:
            left, right = int(sizes[0]), int(sizes[1])
        except (TypeError, ValueError, IndexError):
            left, right = 380, 1000
        self.splitter.setSizes([max(left, 340), max(right, 600)])
        root.addWidget(self.splitter, 1)
        self.setCentralWidget(central)

    def _build_header(self):
        bar = QFrame()
        bar.setObjectName("headerBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 8, 12, 8)
        title = QLabel(APP_NAME)
        title.setObjectName("headerTitle")
        lay.addWidget(title)
        sub = QLabel(f"v{APP_VERSION}  |  Python environment manager")
        sub.setObjectName("headerSub")
        lay.addWidget(sub)
        lay.addStretch(1)
        self.header_path = QLabel(self.settings.get("default_venv_dir", ""))
        self.header_path.setObjectName("headerSub")
        lay.addWidget(self.header_path)
        self.active_badge = QLabel("")
        self.active_badge.setObjectName("activeBadge")
        lay.addSpacing(12)
        lay.addWidget(self.active_badge)
        return bar

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("toolBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(6)
        for text, slot, obj in (
            (f"+  {tr('create_venv')}", self.action_create_venv, "accentButton"),
            (f"Install package", self.action_install_package, None),
            (f"Refresh", self.reload_venvs, None),
            (f"Health check", self.action_health_check, None),
            (f"Settings", self.action_settings, None),
        ):
            btn = QPushButton(text)
            if obj:
                btn.setObjectName(obj)
            btn.clicked.connect(lambda _=False, s=slot: s())
            row.addWidget(btn)
        row.addStretch(1)
        return bar

    def _build_env_panel(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        heading = QLabel(tr("tab_environments"))
        heading.setStyleSheet("font-weight: bold; color: palette(highlight);")
        lay.addWidget(heading)

        self.env_filter = QLineEdit()
        self.env_filter.setPlaceholderText(tr("search_envs"))
        self.env_filter.textChanged.connect(self.apply_env_filter)
        lay.addWidget(self.env_filter)

        self.venv_table = QTableWidget(0, 5)
        self.venv_table.setHorizontalHeaderLabels(
            [tr("col_name"), tr("col_python"), tr("col_status"),
             tr("col_size"), tr("col_packages")])
        self.venv_table.verticalHeader().setVisible(False)
        self.venv_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.venv_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.venv_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.venv_table.setAlternatingRowColors(True)
        self.venv_table.setShowGrid(False)
        self.venv_table.setSortingEnabled(True)
        self.venv_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.venv_table.customContextMenuRequested.connect(self.env_context_menu)
        self.venv_table.itemSelectionChanged.connect(self.on_env_selected)
        header = self.venv_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(48)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.venv_table.setColumnWidth(0, 190)
        for col in (1, 2, 3, 4):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.venv_table, 1)

        row = QHBoxLayout()
        for text, slot in (("Activate", self.action_activate_venv),
                           ("Deactivate", self.action_deactivate_venv),
                           ("Delete", self.action_delete_venv)):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, s=slot: s())
            row.addWidget(btn)
        lay.addLayout(row)
        return panel

    # ------------------------------------------------------------------ tabs
    def _build_tabs(self):
        self.tabs = QTabWidget()
        for page, title in self.pages.pages():
            self.tabs.addTab(page, title)
        return self.tabs

    def _goto_tab(self, key):
        self.pages.goto(self.tabs, key)

    def _show_tab(self, key):
        self._goto_tab(key)

    # ------------------------------------------------------------------ status
    def _build_statusbar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        self.status_label = QLabel(tr("status_ready"))
        bar.addWidget(self.status_label, 1)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(180)
        self.progress.setVisible(False)
        bar.addPermanentWidget(self.progress)
        self.clock_label = QLabel("")
        bar.addPermanentWidget(self.clock_label)
        self.platform_label = QLabel(f"{platform.system()} {platform.release()}"
                                     f"  |  Python {sys.version.split()[0]}"
                                     f"  |  pip {self.backend.pip_version()}")
        bar.addPermanentWidget(self.platform_label)

    def _tick_clock(self):
        if self.settings.get("show_clock", True):
            self.clock_label.setText(datetime.datetime.now().strftime("%H:%M:%S"))
        else:
            self.clock_label.setText("")

    def set_status(self, text, progress=None):
        self.status_label.setText(text)
        if progress is None:
            self.progress.setVisible(False)
        else:
            self.progress.setVisible(True)
            self.progress.setValue(int(progress))

    # ------------------------------------------------------------------ threads
    def run_task(self, fn, on_done=None, on_error=None):
        """Run fn() in a worker thread; call on_done(result) on the GUI thread.

        If ``fn`` declares at least one positional parameter it receives its own
        Worker instance, so long jobs can poll ``worker.is_cancelled()``.
        """
        takes_worker = False
        try:
            takes_worker = inspect.signature(fn).parameters != {}
        except (TypeError, ValueError):
            takes_worker = False

        thread = QThread()
        worker = Worker(fn, takes_worker=takes_worker)
        worker.moveToThread(thread)

        def _done(result):
            if on_done:
                on_done(result)
            thread.quit()

        def _fail(message):
            self.log(f"ERROR: {message}")
            if on_error:
                on_error(message)
            else:
                self.set_status(f"Error: {message}")
            thread.quit()

        worker.finished.connect(_done)
        worker.failed.connect(_fail)
        thread.started.connect(worker.run)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._cleanup_thread(thread, worker))
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()
        return thread

    def stream_command(self, cmd, on_line=None, on_done=None, cwd=None, shell=False):
        """Run a subprocess streaming output lines back to the GUI."""
        thread = QThread()
        worker = StreamWorker(cmd, cwd=cwd, shell=shell)
        worker.moveToThread(thread)

        def _line(stream, text):
            if on_line:
                on_line(stream, text)

        def _done(code):
            if on_done:
                on_done(code)
            thread.quit()

        worker.line.connect(_line)
        worker.done.connect(_done)
        worker.failed.connect(lambda msg: self.log(f"ERROR: {msg}"))
        thread.started.connect(worker.run)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._cleanup_thread(thread, worker))
        self._threads.append(thread)
        self._workers.append(worker)
        self._stream_workers.append(worker)
        thread.start()
        return worker

    def _cleanup_thread(self, thread, worker):
        for lst, obj in ((self._threads, thread), (self._workers, worker),
                         (self._stream_workers, worker)):
            try:
                lst.remove(obj)
            except ValueError:
                pass

    def shutdown_workers(self, timeout_ms=1500):
        """Stop every background worker and wait for its thread to finish.

        Subprocess workers are killed together with their whole process group;
        plain task workers are cancelled. Returns the list of workers whose
        thread had still not finished (normally empty).
        """
        self._closing = True
        stuck = []
        pairs = list(self._worker_threads().items())

        # 0) Cap and then kill pip probes a scan may already be running.
        try:
            self.backend.start_shutdown_probe(max(1.0, timeout_ms / 2000.0))
            self.backend.kill_probes()
        except AttributeError:
            pass

        # 1) Stop subprocess workers first: that also unblocks their threads.
        for worker, _thread in pairs:
            try:
                if not worker.stop(timeout_ms=timeout_ms):
                    stuck.append(worker)
            except Exception as exc:                    # noqa: BLE001
                self.log(f"Worker stop failed: {exc}")
                stuck.append(worker)

        # 2) Ask every thread to quit, then poll - killing any probe that a
        #    scan starts late - instead of one blind wait.
        deadline = time.monotonic() + max(timeout_ms, 0) / 1000.0
        for _worker, thread in pairs:
            try:
                if thread is not None and thread.isRunning():
                    thread.quit()
            except RuntimeError:
                pass                                    # thread already deleted
        while time.monotonic() < deadline:
            if not any(t is not None and t.isRunning() for _w, t in pairs):
                break
            try:
                self.backend.kill_probes()
            except AttributeError:
                pass
            time.sleep(0.02)
        for worker, thread in pairs:
            try:
                if thread is not None and thread.isRunning():
                    stuck.append(worker)
            except RuntimeError:
                pass
        try:
            self.backend.end_shutdown_probe()
        except AttributeError:
            pass
        return stuck

    def _worker_threads(self):
        """Map each tracked worker to the QThread it was started on."""
        threads = {}
        for worker in list(self._workers):
            if worker is None:
                continue
            try:
                threads[worker] = worker.thread()
            except RuntimeError:
                continue
        return threads

    # --------------------------------------------------------------- shortcuts
    def _bind_shortcuts(self):
        for keys, slot in (
            ("Ctrl+N", self.action_create_venv),
            ("Ctrl+Shift+N", self.action_new_project),
            ("Ctrl+R", self.reload_venvs),
            ("F5", self.reload_venvs),
            ("Ctrl+I", self.action_install_package),
            ("Ctrl+T", self.action_open_terminal),
            ("Ctrl+S", self.action_save_config),
            ("Ctrl+E", self.action_export_requirements),
            ("Ctrl+D", self.action_delete_venv),
            ("Ctrl+U", self.action_upgrade_all),
            ("Ctrl+L", self.clear_console),
            ("Ctrl+Q", self.close),
            ("F1", self.action_shortcuts),
        ):
            act = QAction(self)
            act.setShortcut(QKeySequence(keys))
            act.triggered.connect(lambda _=False, s=slot: s())
            self.addAction(act)
