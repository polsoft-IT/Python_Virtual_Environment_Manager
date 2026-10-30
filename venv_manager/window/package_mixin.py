#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Packages tab actions, console, script runner and git helpers."""

import sys
import os
import json
import shutil
import threading
import subprocess
import webbrowser
import datetime

import platform
import shlex
import time

from PyQt6.QtGui import QBrush, QColor, QTextCursor
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication, QTableWidgetItem,
    QWidget, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLineEdit, QComboBox, QCheckBox, QTreeWidget, QTreeWidgetItem,
    QPlainTextEdit, QListWidget, QListWidgetItem, QProgressBar, QFileDialog,
    QMenu, QGroupBox, QInputDialog, QFrame,
)

from ..config import (
    APP_NAME, IS_WIN, IS_MAC, BIN_DIR, PY_EXE, BASE_DIR, save_settings,
    DEFAULT_SETTINGS, tr, THEMES, fmt_size, dir_size, get_logger,
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


class PackageMixin:
    def pkg_context_menu(self, pos):
        if not self.pkg_table.selectionModel().selectedRows():
            return
        menu = QMenu(self)
        menu.addAction(f"\u2B06 {trl('upgrade_package')}", self.action_upgrade_package)
        menu.addAction(f"\u2139 {trl('show_package_info')}", self.action_package_info)
        menu.addAction(f"\U0001F50D {trl('search_pypi')}", self.action_search_pypi)
        menu.addSeparator()
        menu.addAction(f"\u2716 {trl('uninstall_package')}", self.action_uninstall_package)
        menu.addAction("Copy package name", self._copy_package_name)
        menu.exec(self.pkg_table.viewport().mapToGlobal(pos))

    def _copy_package_name(self):
        names = self.selected_packages()
        if names:
            QApplication.clipboard().setText("\n".join(names))

    # ============================================================ PACKAGE LOGIC

    def load_packages(self, venv):
        self.pkg_table.setRowCount(0)
        self.pkg_count_label.setText("Loading packages...")
        self._goto_tab("packages")

        def work():
            pip_cmd = self.backend.pip_cmd(venv)
            proc = subprocess.run(pip_cmd + ["list", "--format=columns"],
                                  capture_output=True, text=True, timeout=120, check=False)
            rows = []
            for line in proc.stdout.splitlines()[2:]:
                parts = line.split()
                if len(parts) >= 2:
                    rows.append((parts[0], parts[1],
                                 parts[2] if len(parts) > 2 else ""))
            return rows

        def done(rows):
            c = self._col
            self.pkg_table.setSortingEnabled(False)
            self.pkg_table.setRowCount(0)
            for name, version, location in rows:
                row = self.pkg_table.rowCount()
                self.pkg_table.insertRow(row)
                self.pkg_table.setItem(row, 0, QTableWidgetItem(name))
                self.pkg_table.setItem(row, 1, QTableWidgetItem(version))
                self.pkg_table.setItem(row, 2, QTableWidgetItem("-"))
                self.pkg_table.setItem(row, 3, QTableWidgetItem(location))
            self.pkg_table.setSortingEnabled(True)
            self.pkg_count_label.setText(
                f"{len(rows)} package(s) installed in {os.path.basename(venv)}")
            self._mark_outdated_async(venv)

        self.run_task(work, done, lambda m: self.log(f"ERROR: {m}"))

    def _mark_outdated_async(self, venv):
        def work():
            return self.backend.outdated(venv)

        def done(outdated):
            c = self._col
            self.pkg_table.setSortingEnabled(False)
            count = 0
            for row in range(self.pkg_table.rowCount()):
                name_item = self.pkg_table.item(row, 0)
                if name_item is None:
                    continue
                name = name_item.text().lower()
                if name in outdated:
                    latest = QTableWidgetItem(outdated[name])
                    latest.setForeground(QBrush(QColor(c["yellow"])))
                    self.pkg_table.setItem(row, 2, latest)
                    name_item.setForeground(QBrush(QColor(c["yellow"])))
                    count += 1
            self.pkg_table.setSortingEnabled(True)
            if count:
                self.set_status(f"{count} package(s) can be updated")

        self.run_task(work, done)

    def apply_pkg_filter(self, text):
        term = text.strip().lower()
        for row in range(self.pkg_table.rowCount()):
            item = self.pkg_table.item(row, 0)
            if item is None:
                continue
            self.pkg_table.setRowHidden(row, bool(term) and term not in item.text().lower())

    def pkg_select_all(self):
        self.pkg_table.selectAll()

    def selected_packages(self):
        names = []
        for index in self.pkg_table.selectionModel().selectedRows():
            item = self.pkg_table.item(index.row(), 0)
            if item:
                names.append(item.text())
        return names

    # ---------------------------------------------------------------- pip calls

    def pip_action(self, args, venv, description):
        self.log(f"$ pip {' '.join(args)}")
        self.set_status(description)
        self._goto_tab("console")

        cmd = self.backend.pip_cmd(venv) + args + self.backend.pip_args()

        def on_line(_stream, text):
            if text.strip():
                self.log(text)

        def on_done(code):
            if code == 0:
                self.log(f"[OK] {description} finished.")
                self.set_status(trl("status_done"))
            else:
                self.log(f"[FAILED] {description} exited with code {code}.")
                self.set_status(f"{description} failed (code {code})")
            self.load_packages(venv)
            self.refresh_dashboard()

        self.stream_command(cmd, on_line=on_line, on_done=on_done)

    def action_install_package(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        text, ok = QInputDialog.getText(
            self, APP_NAME,
            "Package name(s) (multiple allowed, e.g. requests pytest or requests>=2.31.0):")
        if not ok or not text.strip():
            return
        try:
            pkgs = shlex.split(text.strip(), posix=not IS_WIN)
        except ValueError as exc:
            warn(f"Invalid package specification:\n{exc}")
            return
        self.pip_action(["install"] + pkgs, venv,
                        f"Installing {len(pkgs)} package(s)")

    def action_install_from_file(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        path, _ = QFileDialog.getOpenFileName(
            self, trl("install_from_file"), "",
            "Distributions (*.whl *.tar.gz *.zip);;All files (*)")
        if path:
            self.pip_action(["install", path], venv,
                            f"Installing {os.path.basename(path)}")

    def action_bulk_install(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        dlg = BulkInstallDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.packages:
            self.pip_action(["install"] + dlg.packages, venv,
                            f"Installing {len(dlg.packages)} package(s)")

    def action_uninstall_package(self):
        venv = self.selected_env_path()
        names = self.selected_packages()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        if not names:
            warn(trl("no_pkg_selected"))
            return
        if self.settings.get("confirm_destructive", True):
            answer = confirm("Uninstall the following package(s)?\n\n" + ", ".join(names))
            if answer != True:
                return
        self.pip_action(["uninstall", "-y"] + names, venv,
                        f"Uninstalling {len(names)} package(s)")

    def action_upgrade_package(self):
        venv = self.selected_env_path()
        names = self.selected_packages()
        if not venv or not names:
            warn(trl("no_pkg_selected"))
            return
        self.pip_action(["install", "--upgrade"] + names, venv,
                        f"Upgrading {len(names)} package(s)")

    def action_upgrade_all(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        self.log("Collecting the list of outdated packages...")
        self.set_status("Upgrading all packages...")

        def work():
            outdated = self.backend.outdated(venv)
            return sorted(outdated.keys())

        def done(names):
            if not names:
                self.log("All packages are already up to date.")
                self.set_status(trl("status_done"))
                return
            self.log(f"Upgrading {len(names)} package(s): {', '.join(names)}")
            self.pip_action(["install", "--upgrade"] + names, venv,
                            f"Upgrading {len(names)} package(s)")

        self.run_task(work, done)

    def action_freeze_packages(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        self._goto_tab("console")
        self.log("pip freeze output:")

        def work():
            return self.backend.freeze(venv)

        def done(text):
            for line in text.splitlines():
                self.log(line)
            self.set_status(trl("status_done"))

        self.run_task(work, done)

    def action_check_outdated(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        self._goto_tab("console")
        self.log("Checking for outdated packages...")

        def work():
            return self.backend.outdated(venv)

        def done(outdated):
            if not outdated:
                self.log("Every installed package is up to date.")
            else:
                self.log(f"{len(outdated)} package(s) can be updated:")
                for name, version in sorted(outdated.items()):
                    self.log(f"  {name}  ->  {version}")
            self._mark_outdated_async(venv)
            self.set_status(trl("status_done"))

        self.run_task(work, done)

    def action_package_info(self):
        venv = self.selected_env_path()
        names = self.selected_packages()
        if not venv or not names:
            warn(trl("no_pkg_selected"))
            return
        package = names[0]

        def work():
            proc = subprocess.run(
                self.backend.pip_cmd(venv) + ["show", package],
                capture_output=True, text=True, timeout=60, check=False)
            text = proc.stdout.strip()
            if not text:
                text = proc.stderr.strip() or "No information available."
            try:
                import urllib.request
                with urllib.request.urlopen(
                        f"https://pypi.org/pypi/{package}/json", timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                info = data.get("info", {})
                text += ("\n\n--- PyPI ---\n"
                         f"Latest version : {info.get('version', '?')}\n"
                         f"Summary        : {info.get('summary', '')}\n"
                         f"Home page      : {info.get('home_page', '')}\n"
                         f"Author         : {info.get('author', '')}\n"
                         f"License        : {info.get('license', '')}")
            except Exception:                           # noqa: BLE001
                text += "\n\n--- PyPI ---\n(latest metadata could not be fetched)"
            return text

        self.run_task(work,
                      lambda text: PackageInfoDialog(package, text, self).exec())

    def action_search_pypi(self):
        query, ok = QInputDialog.getText(self, APP_NAME, "Search PyPI for:")
        if ok and query.strip():
            url = f"https://pypi.org/search/?q={query.strip()}"
            self.log(f"Opening PyPI search: {url}")
            webbrowser.open(url)

    # ---------------------------------------------------------------- pip-tools

    def action_pip_compile(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        source, _ = QFileDialog.getOpenFileName(
            self, "Select the input file", "",
            "Requirements (*.in *.txt);;pyproject (*.toml);;All files (*)")
        if not source:
            return
        self._goto_tab("console")
        self.log("Installing pip-tools and running pip-compile...")

        def work():
            pip_cmd = self.backend.pip_cmd(venv)
            subprocess.run(pip_cmd + ["install", "pip-tools"],
                           capture_output=True, text=True, timeout=600, check=False)
            compiler = self.backend.find_venv_tool(venv, "pip-compile")
            if not compiler:
                raise RuntimeError("pip-compile was not found after installing pip-tools")
            proc = subprocess.run([compiler, source], capture_output=True,
                                  text=True, timeout=900)
            return proc.stdout + proc.stderr

        def done(text):
            for line in text.splitlines():
                self.log(line)
            self.log("pip-compile finished.")
            self.set_status(trl("status_done"))

        self.run_task(work, done, lambda m: self.log(f"ERROR: {m}"))

    def action_pip_sync(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        source, _ = QFileDialog.getOpenFileName(
            self, "Select requirements.txt", "", "Requirements (*.txt);;All files (*)")
        if not source:
            return
        self._goto_tab("console")
        self.log("Installing pip-tools and running pip-sync...")

        def work():
            pip_cmd = self.backend.pip_cmd(venv)
            subprocess.run(pip_cmd + ["install", "pip-tools"],
                           capture_output=True, text=True, timeout=600, check=False)
            sync = self.backend.find_venv_tool(venv, "pip-sync")
            if not sync:
                raise RuntimeError("pip-sync was not found after installing pip-tools")
            proc = subprocess.run([sync, source], capture_output=True,
                                  text=True, timeout=900)
            return proc.stdout + proc.stderr

        def run_done(text):
            for line in text.splitlines():
                self.log(line)
            self.log("pip-sync finished.")
            self.set_status(trl("status_done"))
            self.load_packages(venv)

        self.run_task(work, run_done, lambda m: self.log(f"ERROR: {m}"))
    # ======================================================= EXPORT / IMPORT

    def action_export_requirements(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, trl("export_requirements"), "requirements.txt",
            "Text files (*.txt);;All files (*)")
        if not path:
            return

        def work():
            text = self.backend.freeze(venv)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            return len([l for l in text.splitlines() if l.strip()])

        def done(count):
            self.log(f"Exported {count} requirement(s) to {path}")
            self.set_status(f"Exported to {os.path.basename(path)}")

        self.run_task(work, done)

    def action_export_pyproject(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, trl("export_pyproject"), "pyproject.toml",
            "TOML files (*.toml);;All files (*)")
        if not path:
            return

        def work():
            packages = self.backend.list_packages(venv)
            dependencies = ",\n".join(
                f'    "{name}>={version}"' for name, version in packages)
            content = (
                "[build-system]\n"
                'requires = ["setuptools>=68", "wheel"]\n'
                'build-backend = "setuptools.build_meta"\n\n'
                "[project]\n"
                'name = "my-project"\n'
                'version = "0.1.0"\n'
                'description = ""\n'
                'requires-python = ">=3.8"\n'
                "dependencies = [\n" + dependencies + "\n]\n"
            )
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            return len(packages)

        self.run_task(work, lambda n: self.log(
            f"Exported pyproject.toml with {n} dependencies to {path}"))

    def action_export_conda(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, trl("export_conda"), "environment.yml",
            "YAML files (*.yml *.yaml);;All files (*)")
        if not path:
            return

        def work():
            name = os.path.basename(venv)
            python_version = self.backend.venv_python_version(venv)
            packages = self.backend.freeze(venv).splitlines()
            lines = [f"name: {name}", "channels:", "  - defaults",
                     "  - conda-forge", "dependencies:",
                     f"  - python={python_version}", "  - pip", "  - pip:"]
            lines += [f"      - {p}" for p in packages if p.strip()]
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            return len(packages)

        self.run_task(work, lambda n: self.log(
            f"Exported environment.yml with {n} pip packages to {path}"))

    def action_import_requirements(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        path, _ = QFileDialog.getOpenFileName(
            self, trl("import_requirements"), "",
            "Text files (*.txt);;All files (*)")
        if not path:
            return
        self.pip_action(["install", "-r", path], venv,
                        f"Importing {os.path.basename(path)}")

    # ==================================================================== TOOLS

    def action_open_terminal(self):
        venv = self.selected_env_path()
        configured = self.settings.get("terminal_path", "")
        try:
            if configured and os.path.exists(configured):
                subprocess.Popen([configured], cwd=venv or os.getcwd())
                return
            if IS_WIN:
                if shutil.which("wt"):
                    args = ["wt"]
                    if venv:
                        args += ["-d", venv]
                    subprocess.Popen(args)
                    return
                activate = os.path.join(venv, "Scripts", "activate.bat") if venv else ""
                if activate and os.path.exists(activate):
                    subprocess.Popen(f'cmd /k "{activate}"', shell=True,
                                     cwd=venv)
                else:
                    subprocess.Popen("cmd", shell=True, cwd=venv or os.getcwd())
            elif IS_MAC:
                subprocess.Popen(["open", "-a", "Terminal",
                                  venv or os.getcwd()])
            else:
                for term in ("x-terminal-emulator", "gnome-terminal", "konsole",
                             "xfce4-terminal", "xterm"):
                    exe = shutil.which(term)
                    if exe:
                        subprocess.Popen([exe], cwd=venv or os.getcwd())
                        return
                self.log("No terminal emulator was found on PATH.")
        except Exception as exc:                        # noqa: BLE001
            self.log(f"Could not open a terminal: {exc}")

    def action_pip_audit(self):
        venv = self.selected_env_path()
        if not venv:
            warn(trl("no_venv_selected"))
            return
        self._goto_tab("console")
        self.log("Installing pip-audit and scanning for vulnerabilities...")
        self.set_status("Running pip-audit...")

        def work():
            pip_cmd = self.backend.pip_cmd(venv)
            subprocess.run(pip_cmd + ["install", "pip-audit"],
                           capture_output=True, text=True, timeout=600, check=False)
            py = Backend.venv_python(venv)
            cmd = pip_cmd + ["run", "pip-audit"]  # noqa: F841 (kept for reference)
            audit = self.backend.find_venv_tool(venv, "pip-audit")
            if audit:
                cmd = [audit, "--format=columns"]
            else:
                cmd = [Backend.venv_python(venv), "-m", "pip_audit", "--format=columns"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900,
                                  check=False)
            return proc.returncode, proc.stdout + proc.stderr

        def done(result):
            code, text = result
            for line in text.splitlines():
                self.log(line)
            if code == 0:
                self.log("No known vulnerabilities were reported.")
                self.set_status("pip-audit: no vulnerabilities")
            else:
                self.log("Vulnerabilities were reported - see the output above.")
                self.set_status("pip-audit finished with findings")

        self.run_task(work, done, lambda m: self.log(f"ERROR: {m}"))

    def action_check_python(self):
        self._goto_tab("console")
        self.log("=" * 60)
        self.log("Current Python interpreter")
        self.log("=" * 60)
        self.log(f"Version      : {sys.version.split()[0]}")
        self.log(f"Full version : {sys.version}")
        self.log(f"Executable   : {sys.executable}")
        self.log(f"Platform     : {platform.platform()}")
        self.log(f"pip          : {self.backend.pip_version()}")
        self.log(f"Architecture : {platform.machine()}")
        self.log(f"Timezone     : {time.tzname[0]}")

    def action_detect_tools(self):
        self._goto_tab("console")
        self.log("Scanning the system PATH for relevant tools:")
        for name, path in Backend.tools():
            marker = "[OK] " if path else "[--] "
            self.log(f"  {marker} {name:<14} {path or 'not found'}")
        self.set_status(trl("status_done"))

    def action_detect_pythons(self):
        self._goto_tab("console")
        self.log("Detected Python interpreters:")

        def work():
            found = []
            for path in self.backend.find_all_pythons():
                found.append((path, self.backend.python_version(path)))
            return found

        def done(found):
            if not found:
                self.log("  No interpreters were detected.")
            for path, version in found:
                self.log(f"  Python {version:<8} {path}")
            self.set_status(f"{len(found)} interpreter(s) detected")

        self.run_task(work, done)

    def action_clear_pip_cache(self):
        self._goto_tab("console")
        self.log("Purging the pip download cache...")

        def work():
            proc = subprocess.run([sys.executable, "-m", "pip", "cache", "purge"],
                                  capture_output=True, text=True, timeout=300)
            return proc.stdout + proc.stderr

        def done(text):
            for line in text.splitlines():
                self.log(line)
            self.log("pip cache purge finished.")
            self.set_status(trl("status_done"))

        self.run_task(work, done)

    def action_thread_activity(self):
        alive = [t for t in threading.enumerate() if t.is_alive()]
        info(
            self, trl("task_queue"),
            f"Active Python threads: {len(alive)}\n"
            f"Managed worker threads: {len(self._threads)}\n\n"
            + "\n".join(f"  - {t.name}" for t in alive[:15]))

    # ================================================================== CONSOLE

    def log(self, message):
        get_logger().info(message)
        if getattr(self, "console", None) is None:
            return                              # logging without the console tab
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        colour = self._log_colour(message)
        if colour:
            self.console.appendHtml(
                f'<span style="color:{colour};">[{stamp}] '
                f'{message.replace("<", "&lt;").replace(">", "&gt;")}</span>')
        else:
            self.console.appendPlainText(f"[{stamp}] {message}")
        if self.autoscroll_cb.isChecked():
            self.console.verticalScrollBar().setValue(
                self.console.verticalScrollBar().maximum())

    def save_console_log(self):
        default_log = os.path.join(APP_DATA_DIR, "venv_manager.log")
        path, _ = QFileDialog.getSaveFileName(
            self, trl("save_log"), default_log,
            "Log files (*.log *.txt);;All files (*)")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.console.toPlainText())
            self.log(f"Console log saved to {path}")

    def clear_console(self):
        self.console.clear()

    def search_console(self):
        text, ok = QInputDialog.getText(self, APP_NAME, "Search the console for:")
        if not ok or not text:
            return
        found = self.console.find(text)
        if not found:
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.console.setTextCursor(cursor)
            found = self.console.find(text)
        if found:
            self.set_status(f"Found '{text}' in the console")
        else:
            self.set_status(f"'{text}' was not found in the console")

    def toggle_wrap(self, checked):
        mode = (QPlainTextEdit.LineWrapMode.WidgetWidth if checked
                else QPlainTextEdit.LineWrapMode.NoWrap)
        self.console.setLineWrapMode(mode)

    def run_console_command(self):
        command = self.cmd_edit.text().strip()
        if not command:
            return
        self._cmd_history.append(command)
        self._cmd_index = len(self._cmd_history)
        self.cmd_edit.clear()
        self.log(f"$ {command}")
        self.set_status(trl("status_working"))

        def on_done(code):
            self.set_status(f"Command finished with exit code {code}")

        self.stream_command(command, shell=True, on_done=on_done)

    def eventFilter(self, obj, event):
        """Provide Up/Down history navigation in the console command box."""
        if obj is getattr(self, "cmd_edit", None) and event.type() == event.Type.KeyPress:
            key = event.key()
            if key == Qt.Key_Up and self._cmd_history:
                self._cmd_index = max(0, self._cmd_index - 1)
                self.cmd_edit.setText(self._cmd_history[self._cmd_index])
                return True
            if key == Qt.Key_Down:
                if self._cmd_index < len(self._cmd_history) - 1:
                    self._cmd_index += 1
                    self.cmd_edit.setText(self._cmd_history[self._cmd_index])
                else:
                    self._cmd_index = len(self._cmd_history)
                    self.cmd_edit.clear()
                return True
        return super().eventFilter(obj, event)

    # =========================================================== SCRIPT RUNNER

    def browse_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self, trl("script_path"), "", "Python scripts (*.py);;All files (*)")
        if path:
            self.script_path.setText(path)

    def run_script(self):
        script = self.script_path.text().strip()
        if not script:
            warn("Choose a script to run first.")
            return
        if not os.path.exists(script):
            warn("That script does not exist.")
            return

        venv = self.selected_env_path()
        python_exe = Backend.venv_python(venv) if venv else sys.executable
        try:
            args = shlex.split(self.script_args.text().strip(), posix=not IS_WIN)
        except ValueError as exc:
            warn(f"Invalid arguments:\n{exc}")
            return
        cmd = [python_exe, script] + args
        cwd = os.path.dirname(os.path.abspath(script))

        self.script_stdout.clear()
        self.script_stderr.clear()
        self.script_exit_label.setText("running...")
        self.script_time_label.setText("")
        self.script_stop_btn.setEnabled(True)
        self.log(f"$ {' '.join(cmd)}")
        started = time.time()

        def on_line(stream, text):
            target = self.script_stdout if stream == "stdout" else self.script_stderr
            target.appendPlainText(text)

        def on_done(code):
            elapsed = time.time() - started
            self._script_worker = None
            self.script_exit_label.setText(str(code))
            colour = self._col["green"] if code == 0 else self._col["red"]
            self.script_exit_label.setStyleSheet(f"font-weight: bold; color: {colour};")
            self.script_time_label.setText(f"finished in {elapsed:.2f}s")
            self.script_stop_btn.setEnabled(False)
            self.log(f"Script finished with exit code {code} after {elapsed:.2f}s")
            self.set_status(f"Script exit code {code}")

        self._script_worker = self.stream_command(cmd, on_line=on_line,
                                                  on_done=on_done, cwd=cwd)

    def stop_script(self):
        worker = self._script_worker
        if not worker:
            return
        if worker.stop(timeout_ms=1500):
            self.log("Script and its child processes terminated by the user.")
            self.script_exit_label.setText("terminated")
            self.script_stop_btn.setEnabled(False)
        else:
            warn("The script process tree did not exit and may still be running.")
        self._script_worker = None

    # ====================================================================== GIT

    def browse_git_repo(self):
        path = QFileDialog.getExistingDirectory(self, trl("repo_path"))
        if path:
            self.git_path.setText(path)
            self.refresh_git_info(path)

    def _auto_detect_repo(self, venv_path):
        repo = Backend.find_repo_for(venv_path)
        if repo and repo != self.git_path.text().strip():
            self.git_path.setText(repo)
            self.refresh_git_info(repo)

    def refresh_git_info(self, repo):
        if not repo or not os.path.isdir(repo):
            return
        if not Backend.git_available():
            self.git_branch_label.setText("-")
            self.git_status_label.setText(trl("git_not_installed"))
            return

        def work():
            branch = Backend.git_branch(repo)
            _code, out, _err = Backend.git_run(repo, ["status", "--porcelain"])
            dirty = bool(out.strip())
            _c2, out2, _e2 = Backend.git_run(repo, ["log", "-1", "--pretty=%h %s"])
            return branch, dirty, out2.strip()

        def done(result):
            branch, dirty, last_commit = result
            self.git_branch_label.setText(branch)
            self.git_status_label.setText(
                trl("git_dirty") if dirty else trl("git_clean"))
            colour = self._col["yellow"] if dirty else self._col["green"]
            self.git_status_label.setStyleSheet(f"color: {colour};")
            if last_commit:
                self.set_status(f"Git: {branch} - {last_commit}")

        self.run_task(work, done)

    def action_git_status(self):
        self._goto_tab("git")
        repo = self.selected_env_path()
        if repo:
            self._auto_detect_repo(repo)
        target = self.git_path.text().strip()
        if target:
            self.git_command(["status", "-sb"])

    def git_command(self, args):
        repo = self.git_path.text().strip()
        if not repo:
            warn("Choose a git repository first.")
            return
        self.git_output.appendPlainText(f"$ git {' '.join(args)}")
        git = Backend.git_available()
        if not git:
            self.git_output.appendPlainText(trl("git_not_installed"))
            return

        def on_line(_stream, text):
            self.git_output.appendPlainText(text)

        def on_done(code):
            self.git_output.appendPlainText(f"(git exited with code {code})")
            self.refresh_git_info(repo)

        self.stream_command([git] + args, cwd=repo, on_line=on_line, on_done=on_done)
    # ========================================================= VIRTUAL DEVICES

