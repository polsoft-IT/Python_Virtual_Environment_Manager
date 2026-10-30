#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dashboard card refresh, recent projects, settings and window lifecycle."""

import sys
import os
import json
import shutil
import threading
import subprocess
import webbrowser
import datetime

import platform

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLineEdit, QComboBox, QCheckBox, QTreeWidget, QTreeWidgetItem,
    QPlainTextEdit, QListWidget, QListWidgetItem, QProgressBar, QFileDialog,
    QMenu, QGroupBox, QInputDialog, QFrame,
)

from ..config import (
    APP_NAME, IS_WIN, IS_MAC, BIN_DIR, PY_EXE, BASE_DIR, save_settings,
    DEFAULT_SETTINGS, DEFAULT_THEME, DEFAULT_WINDOW_SIZE, tr, THEMES,
    fmt_size, dir_size, merge_settings, get_logger,
)
from ..backend import (
    Backend, write_floppy_image, write_vhd_footer_image,
    write_sparse_raw_image, write_iso_stub, detect_image_format,
)
from ..dialogs import (
    CreateVenvDialog, BulkInstallDialog, TemplatesDialog, AboutDialog,
    ShortcutsDialog, PackageInfoDialog,
)
from ..data import DEVICE_TYPES, IMAGE_FILE_FILTER
from ..uikit import confirm, warn, info, trl, write, progress, done
from ..widgets import status_item, mono_font, make_dot, StatCard, _table_item_data
from .interactive_tabs import InteractiveTabsMixin


class DashboardMixin:
    def refresh_dashboard(self):
        self.card_envs.set_value("...")
        self.card_pkgs.set_value("...")
        self.card_outdated.set_value("...")
        self.card_disk.set_value("...")

        def work(self_worker):
            self._scan_worker = self_worker
            try:
                return _collect()
            finally:
                self._scan_worker = None

        def _collect():
            directory = self.settings.get("default_venv_dir", "")
            venvs = Backend.dashboard_venvs(directory)
            total_packages = 0
            disk = 0
            per_venv = []
            for venv in venvs:
                if self._scan_cancelled:
                    break
                disk += dir_size(venv, lambda: self.backend.cancelled)
                count = self.backend.count_packages(venv)
                if count > 0:
                    total_packages += count
                per_venv.append((os.path.basename(venv), max(count, 0),
                                 self.backend.venv_python_version(venv)))
            info_lines = [
                f"Operating system : {platform.system()} {platform.release()}",
                f"Machine          : {platform.machine()}",
                f"Python           : {sys.version.split()[0]}",
                f"Executable       : {sys.executable}",
                f"pip              : {self.backend.pip_version()}",
                f"Environments dir : {directory}",
                f"Environments     : {len(venvs)}",
                f"Disk usage       : {fmt_size(disk)}",
                "",
                "Interpreters detected on this system:",
            ]
            for path in self.backend.find_all_pythons():
                info_lines.append(f"  Python {self.backend.python_version(path):<8} {path}")
            return total_packages, disk, per_venv, info_lines

        def done(result):
            total_packages, disk, per_venv, info_lines = result
            self.card_envs.set_value(len(per_venv))
            self.card_pkgs.set_value(total_packages if total_packages else "-")
            self.card_outdated.set_value("-")
            self.card_disk.set_value(fmt_size(disk))
            self.dash_info.setPlainText("\n".join(info_lines))
            self._draw_env_chart(per_venv)

        self.run_task(work, done)

    def _draw_env_chart(self, per_venv):
        """Render a small bar chart of package counts per environment."""
        self._update_outdated_card()
        if not per_venv:
            self.chart_text = "No environments were found in the workspace directory yet."
            if hasattr(self, "chart_label"):
                self.chart_label.setPlainText(self.chart_text)
            return
        top = sorted(per_venv, key=lambda item: item[1], reverse=True)[:8]
        maximum = max((item[1] for item in top), default=1) or 1
        lines = ["Package distribution per environment:", ""]
        for name, count, _python_version in top:
            bar = "\u2588" * max(1, int(count / maximum * 30)) if count else ""
            lines.append(f"  {name[:22]:<22} {count:>5}  {bar}")
        self.chart_text = "\n".join(lines)
        if hasattr(self, "chart_label"):
            self.chart_label.setPlainText(self.chart_text)

    def _update_outdated_card(self):
        directory = self.settings.get("default_venv_dir", "")
        venvs = Backend.dashboard_venvs(directory)
        if not venvs:
            self.card_outdated.set_value(0)
            return

        def work():
            total = 0
            for venv in venvs:
                total += len(self.backend.outdated(venv))
            return total

        self.run_task(work, lambda n: self.card_outdated.set_value(n))

    def update_recent_buttons(self):
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        recents = self.settings.get("recent_projects", [])[:6]
        if not recents:
            self.recent_layout.addWidget(QLabel(trl("dash_no_recent")))
            return
        for path in recents:
            button = QPushButton(os.path.basename(path) or path)
            button.setToolTip(path)
            button.clicked.connect(lambda _=False, p=path: self.open_recent(p))
            self.recent_layout.addWidget(button)
        self.recent_layout.addStretch(1)

    def add_recent(self, path):
        if not path:
            return
        path = os.path.normpath(path)
        recents = self.settings.get("recent_projects", [])
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        limit = int(self.settings.get("max_recent", 10))
        self.settings["recent_projects"] = recents[:limit] if limit else []
        save_settings(self.settings)
        self._rebuild_recent_menu()
        self.update_recent_buttons()

    def set_working_directory(self, path, remember=True):
        """Make ``path`` the active workspace and refresh everything that uses it.

        Used by the File-menu project actions and by the recent-project buttons
        and menu. Returns True when the directory was adopted.
        """
        if not path:
            return False
        path = os.path.normpath(path)
        if not os.path.isdir(path):
            warn(f"That directory no longer exists:\n{path}")
            return False

        self.settings["default_venv_dir"] = path
        save_settings(self.settings)
        if remember:
            self.add_recent(path)       # also refreshes menu and recent buttons
        else:
            self._rebuild_recent_menu()
            self.update_recent_buttons()
        if hasattr(self, "header_path"):
            self.header_path.setText(path)
        self.reload_venvs()
        self.refresh_dashboard()
        self.log(f"Working directory changed to {path}")
        return True

    def open_recent(self, path):
        return self.set_working_directory(path, remember=False)

    # ================================================ FILE MENU / SETTINGS ACTS

    def action_new_project(self):
        """Pick a workspace folder (also backs File > Open project, Ctrl+O)."""
        path = QFileDialog.getExistingDirectory(self, "Choose a project directory")
        if path:
            self.set_working_directory(path)

    def action_save_config(self):
        save_settings(self.settings)
        self.log(f"Configuration saved to {CONFIG_FILE}")
        self.set_status("Configuration saved")

    def action_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # The dialog (or a stale config file) may hand back a partial dict, so
        # layer it over the defaults before anything indexes a key directly.
        updated = merge_settings(getattr(dialog, "settings", None))
        updated["window_geometry"] = self.settings.get("window_geometry", "")
        updated["splitter_sizes"] = self.settings.get(
            "splitter_sizes", DEFAULT_SETTINGS["splitter_sizes"])
        theme_changed = updated.get("theme") != self.settings.get("theme")

        self.settings = updated
        self.backend.settings = self.settings
        save_settings(self.settings)
        self.apply_theme()
        if theme_changed:
            current = self.settings.get("theme", DEFAULT_THEME)
            for action in self.theme_menu.actions():
                action.setChecked(action.text() == current)
        self.reload_venvs()
        self.refresh_dashboard()
        self.log("Settings applied.")

    def action_docs(self):
        webbrowser.open("https://docs.python.org/3/library/venv.html")

    def action_project_page(self):
        webbrowser.open(APP_GITHUB)

    def action_about(self):
        AboutDialog(self).exec()

    def action_shortcuts(self):
        ShortcutsDialog(self).exec()

    # =============================================================== GEOMETRY

    def _restore_geometry(self):
        """Restore the saved window geometry, or fall back to the default size."""
        geometry = self.settings.get("window_geometry", "")
        saved = None
        if isinstance(geometry, str) and geometry and \
                self.settings.get("save_window_pos", True):
            try:
                # fromHex() never raises - it silently drops invalid input - so
                # the value is validated first and only accepted when it decodes
                # to the same number of bytes it was asked to.
                raw = bytes.fromhex(geometry)
                candidate = QByteArray(raw)
                if len(candidate) == len(raw) and len(raw) % 2 == 0:
                    saved = candidate
            except (ValueError, AttributeError) as exc:
                get_logger().warning(
                    "Ignoring unreadable window geometry (%s): %s",
                    type(exc).__name__, exc)
                saved = None

        restored = saved is not None and self.restoreGeometry(saved)
        if not restored:
            if saved is not None:
                get_logger().warning(
                    "Saved window geometry was rejected; using the default size")
            self.resize(*DEFAULT_WINDOW_SIZE)

    def closeEvent(self, event):
        try:
            if self.settings.get("save_window_pos", True):
                self.settings["window_geometry"] = bytes(
                    self.saveGeometry().toHex()).decode("ascii")
            self.settings["splitter_sizes"] = self.splitter.sizes()
            save_settings(self.settings)
        except (AttributeError, RuntimeError, TypeError) as exc:
            # RuntimeError: the underlying C++ widget is already gone.
            get_logger().warning("Could not save window geometry: %s", exc)

        # Stop timers
        if hasattr(self, "_auto_timer") and self._auto_timer.isActive():
            self._auto_timer.stop()
        if hasattr(self, "_clock_timer") and self._clock_timer.isActive():
            self._clock_timer.stop()

        # Stop every tracked worker (kills subprocess trees) and wait on threads
        try:
            stuck = self.shutdown_workers()
            if stuck:
                get_logger().warning(
                    "%d worker(s) did not stop cleanly: %s",
                    len(stuck), ", ".join(
                        type(w).__name__ for w in stuck))
        except (AttributeError, RuntimeError) as exc:
            get_logger().error("Worker shutdown failed: %s", exc)

        super().closeEvent(event)

