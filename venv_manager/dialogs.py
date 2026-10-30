#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""All modal dialogs of the application."""

import sys
import os
import json
import platform

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QDialog, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFormLayout, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QTabWidget, QPlainTextEdit, QListWidget, QFileDialog, QMessageBox,
    QFrame, QDialogButtonBox, QApplication
)

from .config import (
    APP_NAME, APP_VERSION, APP_BUILD, APP_AUTHOR, APP_COMPANY, APP_EMAIL,
    APP_GITHUB, APP_COPY, THEMES, DEFAULT_THEME, TEMPLATES_FILE,
    DEFAULT_SETTINGS, tr, merge_settings,
)
from .widgets import mono_font


# ==============================================================================
#  DIALOG:  CREATE ENVIRONMENT
# ==============================================================================
class CreateVenvDialog(QDialog):
    def __init__(self, settings, backend, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.backend = backend
        self.cfg = settings
        self.setWindowTitle(tr("create_venv"))
        self.setMinimumWidth(560)
        self.result_data = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_edit = QLineEdit("myenv")
        form.addRow(tr("venv_name"), self.name_edit)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit(self.cfg.get("default_venv_dir", ""))
        browse_dir = QPushButton(tr("browse"))
        browse_dir.clicked.connect(self._browse_dir)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_dir)
        form.addRow(tr("venv_location"), path_row)

        py_row = QHBoxLayout()
        self.py_combo = QComboBox()
        self.py_combo.setEditable(True)
        self.py_combo.addItems(self.backend.find_all_pythons())
        self.py_combo.setCurrentText(self.cfg.get("python_path", sys.executable))
        browse_py = QPushButton(tr("browse"))
        browse_py.clicked.connect(self._browse_python)
        py_row.addWidget(self.py_combo, 1)
        py_row.addWidget(browse_py)
        form.addRow(tr("python_interpreter"), py_row)

        layout.addLayout(form)

        self.upgrade_pip_cb = QCheckBox(tr("upgrade_pip"))
        self.upgrade_pip_cb.setChecked(True)
        self.system_site_cb = QCheckBox(tr("system_site"))
        layout.addWidget(self.upgrade_pip_cb)
        layout.addWidget(self.system_site_cb)

        hint = QLabel(
            "New environments are created with "
            "<code>python -m venv &lt;path&gt;</code> and are immediately "
            "usable by the rest of the application.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid);")
        layout.addWidget(hint)

        buttons = QDialogButtonBox()
        ok_btn = buttons.addButton(tr("create"), QDialogButtonBox.ButtonRole.AcceptRole)
        ok_btn.setObjectName("accentButton")
        buttons.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, tr("venv_location"),
                                             self.path_edit.text())
        if d:
            self.path_edit.setText(d)

    def _browse_python(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("python_interpreter"),
                                           "", "Python (*.exe);;All files (*)")
        if f:
            self.py_combo.setCurrentText(f)

    def _accept(self):
        name = self.name_edit.text().strip()
        base = self.path_edit.text().strip()
        python_exe = self.py_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, APP_NAME, "Please enter an environment name.")
            return
        if not base:
            QMessageBox.warning(self, APP_NAME, "Please choose a location.")
            return
        full = os.path.join(base, name)
        if os.path.exists(full):
            QMessageBox.warning(self, APP_NAME, tr("venv_exists"))
            return
        self.result_data = {
            "name": name,
            "base": base,
            "full_path": full,
            "python": python_exe,
            "upgrade_pip": self.upgrade_pip_cb.isChecked(),
            "system_site": self.system_site_cb.isChecked(),
        }
        self.accept()


# ==============================================================================
#  DIALOG:  BULK INSTALL
# ==============================================================================
class BulkInstallDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("bulk_install"))
        self.resize(460, 340)
        self.packages = []
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter one package per line. Version pins are allowed "
                                "(for example <code>requests==2.31.0</code>)."))
        self.text = QPlainTextEdit()
        self.text.setFont(mono_font("Consolas", 10))
        layout.addWidget(self.text, 1)
        buttons = QDialogButtonBox()
        ok = buttons.addButton(tr("install"), QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setObjectName("accentButton")
        buttons.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        self.packages = [line.strip() for line in
                         self.text.toPlainText().splitlines() if line.strip()]
        self.accept()


# ==============================================================================
#  DIALOG: TINGS
# ==============================================================================
class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = dict(settings)
        self.setWindowTitle(tr("settings"))
        self.resize(720, 620)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._tab_general(), tr("set_general"))
        tabs.addTab(self._tab_paths(), tr("set_paths"))
        tabs.addTab(self._tab_advanced(), tr("set_advanced"))
        tabs.addTab(self._tab_interface(), tr("set_interface"))
        layout.addWidget(tabs, 1)

        buttons = QDialogButtonBox()
        save = buttons.addButton(tr("save"), QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("accentButton")
        buttons.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        reset = buttons.addButton(tr("reset_defaults"),
                                  QDialogButtonBox.ButtonRole.ResetRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        reset.clicked.connect(self._reset)
        layout.addWidget(buttons)

    # ---- tab 1
    def _tab_general(self):
        w = QWidget()
        form = QFormLayout(w)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(self.settings.get("theme", DEFAULT_THEME))
        form.addRow(tr("theme"), self.theme_combo)

        lang = QLineEdit("English")
        lang.setReadOnly(True)
        form.addRow(tr("language"), lang)
        form.addRow("", QLabel(tr("language_hint")))

        self.auto_refresh_cb = QCheckBox()
        self.auto_refresh_cb.setChecked(bool(self.settings.get("auto_refresh", True)))
        form.addRow(tr("auto_refresh"), self.auto_refresh_cb)

        self.confirm_cb = QCheckBox()
        self.confirm_cb.setChecked(bool(self.settings.get("confirm_destructive", True)))
        form.addRow(tr("confirm_destructive"), self.confirm_cb)

        self.save_geom_cb = QCheckBox()
        self.save_geom_cb.setChecked(bool(self.settings.get("save_window_pos", True)))
        form.addRow(tr("save_window_pos"), self.save_geom_cb)

        self.max_recent_spin = QSpinBox()
        self.max_recent_spin.setRange(0, 30)
        self.max_recent_spin.setValue(int(self.settings.get("max_recent", 10)))
        form.addRow(tr("max_recent"), self.max_recent_spin)
        return w

    # ---- tab 2
    def _tab_paths(self):
        w = QWidget()
        form = QFormLayout(w)
        self.path_edits = {}
        for key, label, is_dir in (
            ("python_path", tr("python_path"), False),
            ("pip_path", tr("pip_path"), False),
            ("default_venv_dir", tr("default_venv_dir"), True),
            ("editor_path", tr("editor_path"), False),
            ("terminal_path", tr("terminal_path"), False),
            ("shell_path", tr("shell_path"), False),
        ):
            row = QHBoxLayout()
            edit = QLineEdit(self.settings.get(key, ""))
            self.path_edits[key] = edit
            btn = QPushButton(tr("browse"))
            btn.clicked.connect(lambda _=False, k=key, d=is_dir: self._browse(k, d))
            row.addWidget(edit, 1)
            row.addWidget(btn)
            form.addRow(label, row)
        return w

    def _browse(self, key, is_dir):
        if is_dir:
            path = QFileDialog.getExistingDirectory(self, tr(key))
        else:
            path, _ = QFileDialog.getOpenFileName(self, tr(key), "",
                                                  "Executables (*.exe);;All files (*)")
        if path:
            self.path_edits[key].setText(path)

    # ---- tab 3
    def _tab_advanced(self):
        w = QWidget()
        form = QFormLayout(w)
        self.adv_edits = {}
        for key in ("pip_extra_index", "pip_trusted_host", "proxy_url"):
            edit = QLineEdit(self.settings.get(key, ""))
            self.adv_edits[key] = edit
            form.addRow(tr(key), edit)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 3600)
        self.timeout_spin.setValue(int(self.settings.get("timeout", 120)))
        form.addRow(tr("timeout"), self.timeout_spin)
        return w

    # ---- tab 4
    def _tab_interface(self):
        w = QWidget()
        form = QFormLayout(w)

        self.font_combo = QComboBox()
        families = sorted(set(QFontDatabase.families()))
        self.font_combo.addItems(families)
        current = self.settings.get("font_family", "Consolas")
        if current in families:
            self.font_combo.setCurrentText(current)
        form.addRow(tr("font_family"), self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(7, 24)
        self.font_size_spin.setValue(int(self.settings.get("font_size", 10)))
        form.addRow(tr("font_size"), self.font_size_spin)

        self.clock_cb = QCheckBox()
        self.clock_cb.setChecked(bool(self.settings.get("show_clock", True)))
        form.addRow(tr("show_clock"), self.clock_cb)

        self.notify_cb = QCheckBox()
        self.notify_cb.setChecked(bool(self.settings.get("notify_on_done", False)))
        form.addRow(tr("notify_on_done"), self.notify_cb)
        return w

    # ---- actions
    def _reset(self):
        if QMessageBox.question(self, APP_NAME,
                                "Reset every setting to its default value?") \
                == QMessageBox.StandardButton.Yes:
            self.settings = merge_settings(DEFAULT_SETTINGS)
            self.accept()

    def _save(self):
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["auto_refresh"] = self.auto_refresh_cb.isChecked()
        self.settings["confirm_destructive"] = self.confirm_cb.isChecked()
        self.settings["save_window_pos"] = self.save_geom_cb.isChecked()
        self.settings["max_recent"] = self.max_recent_spin.value()
        for key, edit in self.path_edits.items():
            self.settings[key] = edit.text().strip()
        for key, edit in self.adv_edits.items():
            self.settings[key] = edit.text().strip()
        self.settings["timeout"] = self.timeout_spin.value()
        self.settings["font_family"] = self.font_combo.currentText()
        self.settings["font_size"] = self.font_size_spin.value()
        self.settings["show_clock"] = self.clock_cb.isChecked()
        self.settings["notify_on_done"] = self.notify_cb.isChecked()
        self.accept()


# ==============================================================================
#  DIALOG:  TEMPLATES
# ==============================================================================
class TemplatesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Environment templates")
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        self.listw = QListWidget()
        self.info = QLabel("")
        self.info.setWordWrap(True)
        layout.addWidget(QLabel("Saved environment templates:"))
        layout.addWidget(self.listw, 1)
        layout.addWidget(self.info)

        row = QHBoxLayout()
        use_btn = QPushButton("Apply to selected environment")
        use_btn.setObjectName("accentButton")
        del_btn = QPushButton("Delete")
        close_btn = QPushButton(tr("close"))
        row.addWidget(use_btn)
        row.addWidget(del_btn)
        row.addStretch(1)
        row.addWidget(close_btn)
        layout.addLayout(row)

        self._templates = {}
        self.apply_request = None
        use_btn.clicked.connect(self._apply)
        del_btn.clicked.connect(self._delete)
        close_btn.clicked.connect(self.reject)
        self.listw.currentRowChanged.connect(self._show_info)
        self.reload()

    def reload(self):
        self._templates = {}
        self.listw.clear()
        if os.path.exists(TEMPLATES_FILE):
            try:
                with open(TEMPLATES_FILE, "r", encoding="utf-8") as fh:
                    self._templates = json.load(fh)
            except Exception as exc:                    # noqa: BLE001
                print(f"[Templates] {exc}")
        for name, data in self._templates.items():
            count = len(data.get("packages", []))
            self.listw.addItem(f"{name}    [Python {data.get('python_version','?')}]"
                               f"    [{count} packages]")

    def _current_name(self):
        row = self.listw.currentRow()
        if row < 0:
            return None
        return list(self._templates.keys())[row]

    def _show_info(self, _row):
        name = self._current_name()
        if not name:
            self.info.setText("")
            return
        data = self._templates[name]
        pkgs = data.get("packages", [])
        self.info.setText("Packages: " + (", ".join(pkgs[:10]) or "(none)")
                          + ("..." if len(pkgs) > 10 else ""))

    def _apply(self):
        name = self._current_name()
        if not name:
            QMessageBox.warning(self, APP_NAME, "Select a template first.")
            return
        self.apply_request = self._templates[name]
        self.accept()

    def _delete(self):
        name = self._current_name()
        if not name:
            return
        if QMessageBox.question(self, APP_NAME,
                                f"Delete template '{name}'?") \
                == QMessageBox.StandardButton.Yes:
            self._templates.pop(name, None)
            with open(TEMPLATES_FILE, "w", encoding="utf-8") as fh:
                json.dump(self._templates, fh, indent=2, ensure_ascii=False)
            self.reload()


# ==============================================================================
#  DIALOG:  ABOUT
# ==============================================================================
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("about_title"))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)

        title = QLabel(f"VEnv Manager {APP_VERSION}")
        title.setObjectName("headerTitle")
        layout.addWidget(title)

        subtitle = QLabel("Professional Python virtual environment manager "
                          "with a PyQt6 interface.")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addWidget(self._line())

        info = {
            "Version":  APP_VERSION,
            "Build":    APP_BUILD,
            "Author":   APP_AUTHOR,
            "Company":  APP_COMPANY,
            "Email":    APP_EMAIL,
            "GitHub":   APP_GITHUB,
            "Platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "Python":   sys.version.split()[0],
            "Qt":       getattr(QApplication, "__version__", "") or "-",
            "Themes":   str(len(THEMES)),
        }
        grid = QFormLayout()
        for key, value in info.items():
            lbl = QLabel(value)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addRow(f"<b>{key}</b>", lbl)
        layout.addLayout(grid)
        layout.addWidget(self._line())

        copy = QLabel(APP_COPY)
        copy.setStyleSheet("color: palette(mid);")
        copy.setWordWrap(True)
        layout.addWidget(copy)

        buttons = QDialogButtonBox()
        buttons.addButton(tr("close"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _line():
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line


# ==============================================================================
#  DIALOG:  KEYBOARD SHORTCUTS
# ==============================================================================
class ShortcutsDialog(QDialog):
    SHORTCUTS = [
        ("Ctrl+N", "Create a new environment"),
        ("Ctrl+Shift+N", "New project directory"),
        ("Ctrl+R / F5", "Refresh the environment list"),
        ("Ctrl+I", "Install a package"),
        ("Ctrl+T", "Open a system terminal"),
        ("Ctrl+S", "Save the configuration file"),
        ("Ctrl+E", "Export requirements.txt"),
        ("Ctrl+D / Del", "Delete the selected environment"),
        ("Ctrl+U", "Upgrade all packages"),
        ("Ctrl+F", "Focus the package filter box"),
        ("Ctrl+L", "Clear the console"),
        ("Ctrl+Q", "Quit the application"),
        ("Double-click", "Activate the environment"),
        ("Right-click", "Open the context menu"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("shortcuts_title"))
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        for row, (keys, desc) in enumerate(self.SHORTCUTS):
            key_lbl = QLabel(keys)
            key_lbl.setFont(mono_font("Consolas", 10, bold=True))
            key_lbl.setStyleSheet("color: palette(highlight);")
            grid.addWidget(key_lbl, row, 0)
            grid.addWidget(QLabel(desc), row, 1)
        layout.addLayout(grid)
        buttons = QDialogButtonBox()
        buttons.addButton(tr("close"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


# ==============================================================================
#  DIALOG:  PACKAGE INFO
# ==============================================================================
class PackageInfoDialog(QDialog):
    def __init__(self, package, info_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{tr('show_package_info')} - {package}")
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        view = QPlainTextEdit()
        view.setPlainText(info_text)
        view.setReadOnly(True)
        view.setFont(mono_font("Consolas", 10))
        layout.addWidget(view, 1)
        buttons = QDialogButtonBox()
        buttons.addButton(tr("close"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
