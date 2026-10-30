#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Environment list refresh plus create/activate/clone/rename/delete actions."""

import sys
import os
import json
import shutil
import threading
import subprocess
import webbrowser
import datetime

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QHeaderView,
    QTableWidgetItem,
    QWidget, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLineEdit, QComboBox, QCheckBox, QTreeWidget, QTreeWidgetItem,
    QPlainTextEdit, QListWidget, QListWidgetItem, QProgressBar, QFileDialog,
    QMenu, QGroupBox, QInputDialog, QFrame,
)

from ..config import (
    APP_NAME, IS_WIN, IS_MAC, BIN_DIR, PY_EXE, BASE_DIR, save_settings,
    DEFAULT_SETTINGS, tr, THEMES, fmt_size, dir_size,
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

from .interactive_tabs import InteractiveTabsMixin


class EnvironmentMixin:
    def reload_venvs(self):
        directory = self.settings.get("default_venv_dir", "")
        self.set_status(f"Scanning {directory} ...")

        def work(worker):
            self.backend.set_cancel_event(getattr(worker, "_cancelled", None))
            try:
                return _scan(directory)
            finally:
                self.backend.set_cancel_event(None)

        def _scan(directory):
            venvs = []
            if directory and os.path.isdir(directory):
                for item in sorted(os.listdir(directory)):
                    if self.backend.cancelled:
                        break
                    full = os.path.join(directory, item)
                    if Backend.is_venv(full):
                        venvs.append({
                            "name": item,
                            "path": full,
                            "python": self.backend.venv_python_version(full),
                            "size": dir_size(full, lambda: self.backend.cancelled),
                            "created": self._created_date(full),
                            "packages": self.backend.count_packages(full),
                        })
            return venvs

        self.run_task(work, self._populate_env_table, self.set_status)

    @staticmethod
    def _created_date(path):
        try:
            return datetime.datetime.fromtimestamp(os.path.getctime(path))
        except OSError:
            return None

    def _populate_env_table(self, venvs):
        self._venv_rows = venvs
        self.venv_table.setSortingEnabled(False)
        self.venv_table.setRowCount(0)
        c = self._col
        for data in venvs:
            row = self.venv_table.rowCount()
            self.venv_table.insertRow(row)

            name_item = QTableWidgetItem("\U0001F4C1  " + data["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, data)
            self.venv_table.setItem(row, 0, name_item)

            self.venv_table.setItem(row, 1, QTableWidgetItem(data["python"]))

            is_active = data["path"] == self._active_venv
            status_text = "Active" if is_active else "-"
            status = QTableWidgetItem(status_text)
            status.setForeground(QBrush(QColor(c["green"] if is_active else c["bg3"])))
            status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.venv_table.setItem(row, 2, status)

            self.venv_table.setItem(row, 3, QTableWidgetItem(fmt_size(data["size"])))
            count = data["packages"]
            self.venv_table.setItem(row, 4, QTableWidgetItem(
                str(count) if count >= 0 else "?"))

        self.venv_table.setSortingEnabled(False)
        self.set_status(f"{len(venvs)} environment(s) found in "
                        f"{self.settings.get('default_venv_dir')}")
        self.venv_table.setColumnWidth(0, 190)
        self.apply_env_filter(self.env_filter.text())
        self._rebuild_recent_menu()
        self.update_recent_buttons()

    def apply_env_filter(self, text):
        term = (text or "").strip().lower()
        for row in range(self.venv_table.rowCount()):
            if not term:
                self.venv_table.setRowHidden(row, False)
                continue
            item = self.venv_table.item(row, 0)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            haystack = " ".join(str(v) for v in (
                data.get("name", ""), data.get("python", ""),
                data.get("path", ""))).lower()
            self.venv_table.setRowHidden(row, term not in haystack)

    def _sort_env_table(self, column):
        order = self.venv_table.horizontalHeader().sortIndicatorOrder()
        self.venv_table.sortItems(column, order)

    def selected_env_path(self):
        rows = self.venv_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.venv_table.item(rows[0].row(), 0)
        data = item.data(Qt.ItemDataRole.UserRole) if item else None
        return data.get("path") if data else None

    def on_env_selected(self):
        path = self.selected_env_path()
        if not path:
            return
        self.set_status(path)
        self.load_packages(path)
        self._auto_detect_repo(path)

    # ---------------------------------------------------------------- creation

    def action_create_venv(self):
        dlg = CreateVenvDialog(self.settings, self.backend, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.result_data:
            return
        data = dlg.result_data
        self.log(f"Creating environment: {data['full_path']}")
        self.set_status(trl("status_working"), 5)

        def work():
            cmd = [data["python"], "-m", "venv", data["full_path"]]
            if data["system_site"]:
                cmd.append("--system-site-packages")
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=self.settings.get("timeout", 120))
            if proc.returncode != 0:
                raise RuntimeError((proc.stdout + proc.stderr).strip()
                                   or "python -m venv failed")
            if data["upgrade_pip"]:
                cmd_upgrade = self.backend.pip_cmd(data["full_path"]) + ["install", "--upgrade", "pip"]
                subprocess.run(cmd_upgrade, capture_output=True, text=True, timeout=300, check=False)
            return data["full_path"]

        def done(path):
            self.log(f"{trl('venv_created')}: {path}")
            self.set_status(f"{trl('venv_created')}: {os.path.basename(path)}", 100)
            self.add_recent(os.path.dirname(path))
            self.reload_venvs()
            self.refresh_dashboard()

        self.run_task(work, done, lambda msg: info(msg))

    def action_activate_venv(self):
        path = self.selected_env_path()
        if not path:
            warn(trl("no_venv_selected"))
            return
        self._active_venv = path
        name = os.path.basename(path)
        self.active_badge.setText(f"\u26A1 Active: {name}")
        self.log(f"Activated environment: {path}")
        self.set_status(f"{name} is now the active environment")
        self.reload_venvs()

    def action_deactivate_venv(self):
        self._active_venv = None
        self.active_badge.setText("")
        self.log("Deactivated the active environment.")
        self.reload_venvs()

    def action_delete_venv(self):
        path = self.selected_env_path()
        if not path:
            warn(trl("no_venv_selected"))
            return
        if self.settings.get("confirm_destructive", True):
            size_str = ""
            rows = self.venv_table.selectionModel().selectedRows()
            if rows:
                size_item = self.venv_table.item(rows[0].row(), 3)
                if size_item and size_item.text():
                    size_str = f"Size: {size_item.text()}\n"
            answer = confirm(f"{trl('confirm_delete')}\n\n{path}\n\n" f"{size_str}" f"{trl('confirm_delete_hint')}")
            if answer != True:
                return

        self.set_status(f"Deleting {os.path.basename(path)}...")
        self.log(f"Deleting environment: {path}")

        def work():
            import stat

            def _handle_readonly(func, subpath, _exc_info=None):
                try:
                    os.chmod(subpath, stat.S_IWRITE)
                    func(subpath)
                except Exception:
                    pass

            if sys.version_info >= (3, 12):
                shutil.rmtree(path, onexc=lambda fn, p, err: _handle_readonly(fn, p, err))
            else:
                shutil.rmtree(path, onerror=_handle_readonly)
            return path

        def done(deleted_path):
            self.log(f"{trl('venv_deleted')}: {deleted_path}")
            self.set_status(trl("venv_deleted"))
            if self._active_venv == deleted_path:
                self.action_deactivate_venv()
            self.reload_venvs()
            self.refresh_dashboard()

        def failed(err):
            self.log(f"ERROR: Delete failed: {err}")
            info(f"Delete failed:\n{err}")

        self.run_task(work, done, failed)

    def action_clone_venv(self):
        path = self.selected_env_path()
        if not path:
            warn(trl("no_venv_selected"))
            return
        default = os.path.basename(path) + "_clone"
        name, ok = QInputDialog.getText(self, APP_NAME, "Name for the clone:", text=default)
        if not ok or not name.strip():
            return
        dest = os.path.join(os.path.dirname(path), name.strip())
        self.log(f"Cloning {path} to {dest}")
        self.set_status("Cloning environment...")

        def work():
            requirements = self.backend.freeze(path)
            python_exe = Backend.venv_python(path)
            proc = subprocess.run([python_exe, "-m", "venv", dest],
                                  capture_output=True, text=True, timeout=180)
            if proc.returncode != 0:
                raise RuntimeError((proc.stdout + proc.stderr).strip())
            if requirements.strip():
                import tempfile
                with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                                 delete=False) as fh:
                    fh.write(requirements)
                    req_path = fh.name
                try:
                    cmd_install = self.backend.pip_cmd(dest) + ["install", "-r", req_path]
                    subprocess.run(cmd_install, capture_output=True, text=True, timeout=900, check=False)
                finally:
                    try:
                        os.unlink(req_path)
                    except OSError:
                        pass
            return dest

        self.run_task(work,
                      lambda d: (self.log(f"Clone created: {d}"),
                                 self.reload_venvs()),
                      lambda m: info(m))

    def action_rename_venv(self):
        path = self.selected_env_path()
        if not path:
            warn(trl("no_venv_selected"))
            return
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, APP_NAME, "New name:", text=old_name)
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return
        new_path = os.path.join(os.path.dirname(path), new_name.strip())
        if os.path.exists(new_path):
            warn(f"A file or directory named '{new_name.strip()}' already exists.")
            return

        answer = confirm(
            "Renaming a virtual environment folder will invalidate absolute paths "
            "inside pre-installed executable scripts (e.g. pip.exe, pytest.exe).\n\n"
            "Recommended: clone the environment under the new name and delete the "
            "original (this rebuilds all launcher scripts).\n\n"
            "Continue with the clone-and-delete approach?")
        if answer:
            self.log(f"Clone & rename: cloning {old_name} -> {new_name.strip()}")
            self.set_status("Cloning environment...")

            def clone_work():
                requirements = self.backend.freeze(path)
                python_exe = Backend.venv_python(path)
                proc = subprocess.run([python_exe, "-m", "venv", new_path],
                                      capture_output=True, text=True, timeout=180,
                                      check=False)
                if proc.returncode != 0:
                    raise RuntimeError((proc.stdout + proc.stderr).strip())
                if requirements.strip():
                    import tempfile
                    with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                                     delete=False) as fh:
                        fh.write(requirements)
                        req_path = fh.name
                    try:
                        cmd_install = (self.backend.pip_cmd(new_path)
                                       + ["install", "-r", req_path])
                        subprocess.run(cmd_install, capture_output=True, text=True,
                                       timeout=900, check=False)
                    finally:
                        try:
                            os.unlink(req_path)
                        except OSError:
                            pass
                return new_path

            def clone_done(dest):
                self.log(f"Clone created: {dest}")
                self._remove_old_venv_after_clone(path)

            self.run_task(clone_work, clone_done,
                          lambda m: info(m))
            return

        # Hard rename path
        try:
            os.rename(path, new_path)
            self._fix_pyvenv_home(new_path)
            self.log(f"Renamed: {old_name} -> {new_name.strip()}")
            if self._active_venv == path:
                self._active_venv = new_path
                self.active_badge.setText(f"\u26A1 Active: {new_name.strip()}")
            recents = self.settings.get("recent_projects", [])
            if path in recents:
                idx = recents.index(path)
                recents[idx] = new_path
                save_settings(self.settings)
        except Exception as exc:                        # noqa: BLE001
            info(f"Rename failed:\n{exc}")
            return
        self.reload_venvs()
        self.refresh_dashboard()

    def _fix_pyvenv_home(self, venv_path):
        """Refresh the 'home' line in pyvenv.cfg after a directory rename."""
        cfg = os.path.join(venv_path, "pyvenv.cfg")
        if not os.path.isfile(cfg):
            return
        try:
            with open(cfg, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
            for i, line in enumerate(lines):
                if line.strip().lower().startswith("home") and "=" in line:
                    key, _, old_val = line.partition("=")
                    old_dir = old_val.strip()
                    parent = os.path.dirname(old_dir.rstrip("\\/").rstrip("/"))
                    if parent and os.path.isdir(parent):
                        lines[i] = f"{key}= {parent}{os.linesep}"
            with open(cfg, "w", encoding="utf-8") as fh:
                fh.writelines(lines)
            self.log("Updated pyvenv.cfg after rename.")
        except OSError as exc:                          # noqa: BLE001
            self.log(f"Could not update pyvenv.cfg: {exc}")

    def _remove_old_venv_after_clone(self, old_path):
        """Ask whether to delete the original venv after a successful clone."""
        answer = confirm(f"Clone created successfully.\nDelete the original environment\n{old_path}?")
        if answer != True:
            self.reload_venvs()
            self.refresh_dashboard()
            return

        def work():
            import stat

            def on_error(func, p, _exc):
                try:
                    os.chmod(p, stat.S_IWRITE)
                    func(p)
                except OSError:
                    pass

            try:
                shutil.rmtree(old_path, onexc=on_error)
            except TypeError:                           # Python < 3.12
                shutil.rmtree(old_path, onerror=on_error)
            return not os.path.exists(old_path)

        def done(removed):
            if removed:
                self.log(f"Original environment removed: {old_path}")
            else:
                self.log(f"Could not fully remove: {old_path}")
            self.reload_venvs()
            self.refresh_dashboard()

        self.run_task(work, done,
                      lambda m: (info(m),
                                 self.reload_venvs()))

    def action_compare_venvs(self):
        path = self.selected_env_path()
        if not path:
            warn(trl("no_venv_selected"))
            return
        other = QFileDialog.getExistingDirectory(self, "Select the second environment")
        if not other:
            return
        self._goto_tab("console")
        self.log(f"Comparing:\n  A: {path}\n  B: {other}")

        def work():
            a = dict((n.lower(), v) for n, v in self.backend.list_packages(path))
            b = dict((n.lower(), v) for n, v in self.backend.list_packages(other))
            lines = []
            for key in sorted(set(a) | set(b)):
                va, vb = a.get(key, "-"), b.get(key, "-")
                marker = "  " if va == vb else "! "
                lines.append(f"{marker}{key:<32}{va:>16}{vb:>16}")
            return lines

        def done(lines):
            self.log(f"{'Package':<32}{'A':>16}{'B':>16}")
            self.log("-" * 64)
            for line in lines:
                self.log(line)
            self.log("Comparison finished.")
            self.set_status(trl("status_done"))

        self.run_task(work, done)

    def action_health_check(self):
        path = self.selected_env_path()
        if not path:
            warn(trl("no_venv_selected"))
            return
        self._goto_tab("console")
        self.log("=" * 60)
        self.log(f"Health check: {os.path.basename(path)}")
        self.log("=" * 60)

        def work():
            return self.backend.health_check(path)

        def done(result):
            ok_lines, issue_lines = result
            for line in ok_lines:
                self.log(f"  [OK]   {line}")
            for line in issue_lines:
                self.log(f"  [FAIL] {line}")
            self.log("-" * 60)
            if issue_lines:
                self.log(f"{len(issue_lines)} issue(s), {len(ok_lines)} check(s) passed.")
                self.set_status(f"Health check: {len(issue_lines)} issue(s) found")
            else:
                self.log(f"All {len(ok_lines)} checks passed - the environment is healthy.")
                self.set_status("Environment is healthy")

        self.run_task(work, done)

    def action_open_in_explorer(self):
        path = self.selected_env_path() or self.settings.get("default_venv_dir", "")
        if path and os.path.isdir(path):
            self.open_path(path)

    def action_open_in_editor(self):
        path = self.selected_env_path() or self.settings.get("default_venv_dir", "")
        if not path:
            return
        editor = self.settings.get("editor_path", "")
        if editor and os.path.exists(editor):
            subprocess.Popen([editor, path])
            return
        for candidate in ("code", "code-insiders", "subl", "atom", "notepad"):
            exe = shutil.which(candidate)
            if exe:
                subprocess.Popen([exe, path])
                return
        info("No editor configured. Set one in Settings > Paths & tools.")

    @staticmethod
    def open_path(path):
        try:
            if IS_WIN:
                os.startfile(path)                       # noqa: S606
            elif IS_MAC:
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:                        # noqa: BLE001
            print(f"[VEnv Manager] open_path: {exc}")

    # ----------------------------------------------------------- context menus

    def env_context_menu(self, pos):
        if not self.selected_env_path():
            return
        menu = QMenu(self)
        menu.addAction(f"\u26A1 {trl('activate_venv')}", self.action_activate_venv)
        menu.addAction(f"\u23F9 {trl('deactivate_venv')}", self.action_deactivate_venv)
        menu.addSeparator()
        menu.addAction(f"\u2398 {trl('clone_venv')}", self.action_clone_venv)
        menu.addAction(f"\u270E {trl('rename_venv')}", self.action_rename_venv)
        menu.addAction(f"\U0001FA7A {trl('health_check')}", self.action_health_check)
        menu.addSeparator()
        menu.addAction(f"+ {trl('install_package')}", self.action_install_package)
        menu.addAction(f"\u2B06 {trl('upgrade_all')}", self.action_upgrade_all)
        menu.addAction(f"\u2913 {trl('export_requirements')}", self.action_export_requirements)
        menu.addSeparator()
        menu.addAction(f"\U0001F4C2 {trl('open_in_explorer')}", self.action_open_in_explorer)
        menu.addAction(f"\u2716 {trl('delete_venv')}", self.action_delete_venv)
        menu.exec(self.venv_table.viewport().mapToGlobal(pos))

