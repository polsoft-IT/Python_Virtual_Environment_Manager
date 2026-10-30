#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
  Virtual Environment Manager  -  v3.0  (PyQt6 Edition)
  English user interface, modern Qt graphics
================================================================================
  Author / Autor:     Sebastian Januchowski
  Company / Firma:    polsoft.ITS(TM) Group
  Email:              polsoft.its@mail.com
  GitHub:             https://github.com/polsoft-it
  Based on:           VEnv_Manager v2.5.2 (Tkinter edition)
  License:            (c) 2026 Sebastian Januchowski & polsoft.ITS(TM)
================================================================================
  Rewrite of the original Tkinter application using PyQt6 with a full English
  interface. Every working feature from v2.5.2 is preserved:

   * Dashboard with live statistics, quick actions and system information
   * Virtual environment list with filter, sorting, size and package counts
   * Create / activate / deactivate / clone / rename / delete / compare venvs
   * Health check of an environment
   * Installed packages tree with search, outdated and vulnerability tags
   * Install / uninstall / upgrade / bulk install / freeze / package info
   * PyPI search, pip-tools (pip-compile, pip-sync)
   * Console with ANSI colour coding, command history and search
   * Script runner with arguments, stdout/stderr tabs and exit code
   * Git tab: status, pull, log, branch, stash
   * Virtual device tab: FDD/CD/DVD/BD/HDD images (VHD/VMDK/QCOW2/RAW/ISO)
   * Export to requirements.txt / pyproject.toml / environment.yml
   * Import from requirements.txt
   * Tools: terminal, pip-audit, tool detection, interpreter detection, cache
   * Settings dialog, 7 colour themes, live theme switching
   * Status bar with clock, progress and platform information
   * Recent projects, keyboard shortcuts, About / Shortcuts dialogs
================================================================================
"""

import sys
import os
import subprocess
import shutil
import json
import platform
import datetime
import time
import uuid
import struct
import threading
import shlex
import webbrowser
import importlib
import glob as _glob
from concurrent.futures import ThreadPoolExecutor

try:
    from PyQt6.QtCore import (
        Qt, QSize, QTimer, QThread, QObject, pyqtSignal, QPoint
    )
    from PyQt6.QtGui import (
        QAction, QKeySequence, QFont, QColor, QIcon, QPixmap, QPainter,
        QBrush, QPen, QFontDatabase, QTextCursor
    )
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QDialog, QLabel, QPushButton,
        QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QLineEdit,
        QComboBox, QSpinBox, QCheckBox, QTabWidget, QTableWidget,
        QTableWidgetItem, QHeaderView, QTreeWidget, QTreeWidgetItem,
        QPlainTextEdit, QTextEdit, QSplitter, QListWidget, QListWidgetItem,
        QProgressBar, QStatusBar, QFileDialog, QMessageBox, QMenu,
        QMenuBar, QToolBar, QGroupBox, QFrame, QAbstractItemView,
        QSizePolicy, QScrollArea, QDialogButtonBox, QInputDialog, QStyle,
        QStackedWidget, QToolButton, QSlider, QSpacerItem, QRadioButton,
        QPlainTextEdit as _QPTE
    )
except ImportError:
    sys.stderr.write(
        "PyQt6 is required.\n"
        "Install it with:  pip install PyQt6\n")
    raise

APP_NAME    = "VEnv Manager"
APP_VERSION = "3.0.0"
APP_BUILD   = "2026.03.05"
APP_AUTHOR  = "Sebastian Januchowski"
APP_COMPANY = "polsoft.ITS(TM) Group"
APP_EMAIL   = "polsoft.its@mail.com"
APP_GITHUB  = "https://github.com/polsoft-it"
APP_COPY    = "(c) 2026 Sebastian Januchowski & polsoft.ITS(TM). All rights reserved."
# ==============================================================================
#  HELPERS
# ==============================================================================
IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

BIN_DIR = "Scripts" if IS_WIN else "bin"
PY_EXE  = "python.exe" if IS_WIN else "python"
PIP_EXE = "pip.exe" if IS_WIN else "pip"


def fmt_size(b):
    """Human readable file size."""
    b = float(b)
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def dir_size(path):
    total = 0
    try:
        for dirpath, _dirs, filenames in os.walk(path):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


# ==============================================================================
#  INTERNATIONALISATION  (English only, kept as a dict so text is centralised)
# ==============================================================================
TRANSLATIONS = {
    # ---- menus
    "menu_file": "File",
    "menu_venv": "Environment",
    "menu_packages": "Packages",
    "menu_tools": "Tools",
    "menu_view": "View",
    "menu_help": "Help",
    "new_project": "New project...",
    "open_project": "Open project...",
    "save_config": "Save configuration",
    "export_requirements": "Export requirements.txt",
    "export_pyproject": "Export pyproject.toml",
    "export_conda": "Export environment.yml",
    "import_requirements": "Import requirements.txt",
    "recent_projects": "Recent projects",
    "exit": "Exit",
    # ---- environment
    "create_venv": "Create environment",
    "activate_venv": "Activate environment",
    "deactivate_venv": "Deactivate environment",
    "delete_venv": "Delete environment",
    "clone_venv": "Clone environment",
    "rename_venv": "Rename environment",
    "compare_venvs": "Compare environments",
    "health_check": "Health check",
    "refresh_list": "Refresh list",
    "open_in_explorer": "Open in file manager",
    "open_in_editor": "Open in editor",
    # ---- packages
    "install_package": "Install package",
    "install_from_file": "Install from file",
    "uninstall_package": "Uninstall package",
    "upgrade_package": "Upgrade package",
    "upgrade_all": "Upgrade all",
    "freeze_packages": "Freeze packages",
    "check_outdated": "Check outdated",
    "show_package_info": "Package information",
    "search_pypi": "Search PyPI",
    "bulk_install": "Bulk install",
    "pip_compile": "pip-compile (pip-tools)",
    "pip_sync": "pip-sync (pip-tools)",
    "select_all_pkgs": "Select all",
    # ---- tools
    "open_terminal": "Open terminal",
    "run_script": "Run script",
    "pip_audit": "Pip audit (pip-audit)",
    "check_python": "Check Python",
    "detect_tools": "Detect tools",
    "clear_cache": "Clear pip cache",
    "git_status": "Git status",
    "detect_pythons": "Detect Python interpreters",
    "task_queue": "Thread activity",
    "run_in_terminal": "Run in terminal",
    # ---- view / appearance
    "theme": "Theme",
    "settings": "Settings",
    # ---- help
    "documentation": "Python venv documentation",
    "about": "About",
    "check_updates": "Project page",
    "keyboard_shortcuts": "Keyboard shortcuts",
    # ---- tabs
    "tab_dashboard": "Dashboard",
    "tab_environments": "Environments",
    "tab_packages": "Packages",
    "tab_console": "Console",
    "tab_script": "Script Runner",
    "tab_git": "Git",
    "tab_device": "Virtual Devices",
    "tab_guide": "Guide",
    # ---- dashboard
    "dash_total_venvs": "Environments",
    "dash_total_pkgs": "Installed packages",
    "dash_outdated": "Updates available",
    "dash_disk": "Disk usage",
    "dash_quick_actions": "Quick actions",
    "dash_system_info": "System information",
    "dash_recent": "Recently used",
    "dash_no_recent": "No recent projects yet.",
    # ---- settings dialog
    "set_general": "General",
    "set_paths": "Paths & tools",
    "set_advanced": "Advanced",
    "set_interface": "Interface",
    "language": "Language",
    "language_hint": "(English only in this build)",
    "font_family": "Font family",
    "font_size": "Font size",
    "python_path": "Python interpreter",
    "pip_path": "pip executable",
    "default_venv_dir": "Default environments directory",
    "editor_path": "Code editor",
    "terminal_path": "Terminal",
    "shell_path": "Shell",
    "browse": "Browse...",
    "pip_extra_index": "Extra pip index URL",
    "pip_trusted_host": "Trusted pip host",
    "proxy_url": "Proxy URL",
    "timeout": "Command timeout (s)",
    "max_recent": "Maximum recent projects",
    "auto_refresh": "Automatically refresh every 60 seconds",
    "confirm_destructive": "Confirm destructive operations",
    "save_window_pos": "Remember window geometry",
    "show_clock": "Show clock in status bar",
    "notify_on_done": "Show notification when long tasks finish",
    "save": "Save",
    "cancel": "Cancel",
    "reset_defaults": "Reset to defaults",
    # ---- common
    "ok": "OK",
    "close": "Close",
    "create": "Create",
    "install": "Install",
    "uninstall": "Uninstall",
    "refresh": "Refresh",
    "clear": "Clear",
    "save_log": "Save log",
    "search": "Search",
    "status_ready": "Ready",
    "status_working": "Working...",
    "status_done": "Done",
    "status_error": "Error",
    "warning": "Warning",
    # ---- messages
    "no_venv_selected": "No environment selected.",
    "no_pkg_selected": "No package selected.",
    "confirm_delete": "Delete this environment?",
    "confirm_delete_hint": "This cannot be undone.",
    "venv_created": "Environment created",
    "venv_deleted": "Environment deleted",
    "restart_needed": "The application needs to restart for this change to take effect.",
    # ---- create dialog
    "venv_name": "Environment name",
    "venv_location": "Location",
    "python_interpreter": "Python interpreter",
    "upgrade_pip": "Upgrade pip after creation",
    "system_site": "Use --system-site-packages",
    "venv_exists": "A directory with that name already exists.",
    # ---- packages tab
    "col_package": "Package",
    "col_version": "Version",
    "col_latest": "Latest",
    "col_location": "Location",
    "col_name": "Name",
    "col_python": "Python",
    "col_status": "Status",
    "col_size": "Size",
    "col_packages": "Pkgs",
    "col_created": "Created",
    "search_packages": "Filter packages...",
    "search_envs": "Filter environments...",
    "no_environment": "No environment selected",
    # ---- console tab
    "cmd_placeholder": "Type a shell command and press Enter...",
    "run": "Run",
    "wrap": "Wrap",
    "autoscroll": "Auto-scroll",
    # ---- script runner
    "script_path": "Script",
    "script_args": "Arguments",
    "stop": "Stop",
    "exit_code": "Exit code",
    "tab_stdout": "stdout",
    "tab_stderr": "stderr",
    # ---- git tab
    "repo_path": "Repository",
    "git_branch": "Branch",
    "git_clean": "Clean",
    "git_dirty": "Uncommitted changes",
    "git_not_repo": "Not a git repository",
    "git_not_installed": "git was not found on PATH",
    "pull": "Pull (--rebase)",
    "log": "Log (20)",
    "branches": "Branches",
    "stash": "Stash list",
    # ---- virtual device
    "vd_device_type": "Device type",
    "vd_image_path": "Image file",
    "vd_size": "Size (MB)",
    "vd_filesystem": "Filesystem",
    "vd_label": "Volume label",
    "vd_sector": "Sector size",
    "vd_read_only": "Read only",
    "vd_bootable": "Boot flag",
    "vd_create_image": "Create image",
    "vd_new_image": "New image",
    "vd_mount": "Mount",
    "vd_mount_point": "Mount point",
    "vd_unmount": "Unmount",
    "vd_extract_iso": "Extract ISO",
    "vd_make_iso": "Create ISO from folder",
    "vd_convert": "Convert",
    "vd_source": "Source image",
    "vd_target": "Target image",
    "vd_output_format": "Output format",
    "vd_format_tab": "Format & repair",
    "vd_format_dev": "Format image",
    "vd_repair_mbr": "Write MBR",
    "vd_check_fs": "Check filesystem",
    "vd_verify": "Verify image",
    "vd_info": "Image information",
    "vd_log": "Operation log",
    "vd_install_deps": "Install Python dependencies",
    "vd_deps_ok": "All Python dependencies present",
    "vd_select_image": "Select a disk image first.",
    "vd_threads": "Emulation targets",
    # ---- about / shortcuts
    "about_title": "About VEnv Manager",
    "shortcuts_title": "Keyboard shortcuts",
}

T = TRANSLATIONS.get  # shorthand


def tr(key):
    return TRANSLATIONS.get(key, key)


# ==============================================================================
#  COLOR THEMES
# ==============================================================================
THEMES = {
    "Dark (Catppuccin)": {
        "bg": "#1e1e2e", "fg": "#cdd6f4", "bg2": "#313244", "bg3": "#45475a",
        "accent": "#89b4fa", "accent2": "#cba6f7", "green": "#a6e3a1",
        "red": "#f38ba8", "yellow": "#f9e2af", "console_bg": "#11111b",
        "console_fg": "#cdd6f4", "header_bg": "#181825", "select": "#585b70",
        "border": "#585b70", "is_dark": True,
    },
    "Light (Catppuccin)": {
        "bg": "#eff1f5", "fg": "#4c4f69", "bg2": "#dce0e8", "bg3": "#ccd0da",
        "accent": "#1e66f5", "accent2": "#8839ef", "green": "#40a02b",
        "red": "#d20f39", "yellow": "#df8e1d", "console_bg": "#e6e9ef",
        "console_fg": "#4c4f69", "header_bg": "#dce0e8", "select": "#bcc0cc",
        "border": "#bcc0cc", "is_dark": False,
    },
    "Dracula": {
        "bg": "#282a36", "fg": "#f8f8f2", "bg2": "#44475a", "bg3": "#6272a4",
        "accent": "#bd93f9", "accent2": "#ff79c6", "green": "#50fa7b",
        "red": "#ff5555", "yellow": "#f1fa8c", "console_bg": "#1e1f29",
        "console_fg": "#f8f8f2", "header_bg": "#1e1f29", "select": "#44475a",
        "border": "#6272a4", "is_dark": True,
    },
    "Nord": {
        "bg": "#2e3440", "fg": "#d8dee9", "bg2": "#3b4252", "bg3": "#434c5e",
        "accent": "#88c0d0", "accent2": "#81a1c1", "green": "#a3be8c",
        "red": "#bf616a", "yellow": "#ebcb8b", "console_bg": "#242933",
        "console_fg": "#d8dee9", "header_bg": "#242933", "select": "#4c566a",
        "border": "#4c566a", "is_dark": True,
    },
    "Solarized Dark": {
        "bg": "#002b36", "fg": "#93a1a1", "bg2": "#073642", "bg3": "#586e75",
        "accent": "#268bd2", "accent2": "#2aa198", "green": "#859900",
        "red": "#dc322f", "yellow": "#b58900", "console_bg": "#001e26",
        "console_fg": "#93a1a1", "header_bg": "#001e26", "select": "#073642",
        "border": "#586e75", "is_dark": True,
    },
    "Monokai": {
        "bg": "#272822", "fg": "#f8f8f2", "bg2": "#3e3d32", "bg3": "#49483e",
        "accent": "#a6e22e", "accent2": "#66d9e8", "green": "#a6e22e",
        "red": "#f92672", "yellow": "#e6db74", "console_bg": "#1e1f1c",
        "console_fg": "#f8f8f2", "header_bg": "#1e1f1c", "select": "#49483e",
        "border": "#75715e", "is_dark": True,
    },
    "Cyberpunk": {
        "bg": "#0d0d1a", "fg": "#e0e0ff", "bg2": "#1a1a2e", "bg3": "#2d2d44",
        "accent": "#00ffcc", "accent2": "#ff00aa", "green": "#00ff88",
        "red": "#ff3366", "yellow": "#ffcc00", "console_bg": "#080810",
        "console_fg": "#c8c8ff", "header_bg": "#0a0a18", "select": "#2d2d44",
        "border": "#3a3a5c", "is_dark": True,
    },
}

DEFAULT_THEME = "Dark (Catppuccin)"


def theme(name):
    return THEMES.get(name, THEMES[DEFAULT_THEME])


# ==============================================================================
#  PATHS AND DEFAULT SETTINGS
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_app_data_dir():
    """Return user application data directory; created automatically."""
    if IS_WIN:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        d = os.path.join(appdata, ".polsoft", "VEnvManager")
    elif IS_MAC:
        d = os.path.join(os.path.expanduser("~"), "Library", "Application Support", ".polsoft", "VEnvManager")
    else:
        d = os.path.join(os.path.expanduser("~"), ".config", ".polsoft", "VEnvManager")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        d = BASE_DIR
    return d


APP_DATA_DIR    = get_app_data_dir()
CONFIG_FILE     = os.path.join(APP_DATA_DIR, "venv_manager_qt_config.json")
TEMPLATES_FILE  = os.path.join(APP_DATA_DIR, "venv_manager_qt_templates.json")

# Automatically migrate legacy config/templates from BASE_DIR if present
_legacy_cfg = os.path.join(BASE_DIR, "venv_manager_qt_config.json")
if _legacy_cfg != CONFIG_FILE and os.path.isfile(_legacy_cfg) and not os.path.exists(CONFIG_FILE):
    try:
        shutil.copy2(_legacy_cfg, CONFIG_FILE)
    except Exception:
        pass

_legacy_tmpl = os.path.join(BASE_DIR, "venv_manager_qt_templates.json")
if _legacy_tmpl != TEMPLATES_FILE and os.path.isfile(_legacy_tmpl) and not os.path.exists(TEMPLATES_FILE):
    try:
        shutil.copy2(_legacy_tmpl, TEMPLATES_FILE)
    except Exception:
        pass

DEFAULT_SETTINGS = {
    "theme":               DEFAULT_THEME,
    "font_family":         "Consolas" if IS_WIN else "Monospace",
    "font_size":           10,
    "python_path":         sys.executable,
    "pip_path":            "",
    "default_venv_dir":    os.path.join(os.path.expanduser("~"), "venvs"),
    "editor_path":         "",
    "terminal_path":       "",
    "shell_path":          "",
    "auto_refresh":        True,
    "confirm_destructive": True,
    "save_window_pos":     True,
    "pip_extra_index":     "",
    "pip_trusted_host":    "",
    "proxy_url":           "",
    "timeout":             120,
    "window_geometry":     "",
    "splitter_sizes":      [320, 1000],
    "show_clock":          True,
    "notify_on_done":      False,
    "max_recent":          10,
    "recent_projects":     [],
}


def load_settings():
    s = dict(DEFAULT_SETTINGS)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
                s.update(json.load(fh))
        except Exception as exc:                       # noqa: BLE001
            print(f"[VEnv Manager] Could not read config: {exc}")
    for key in ("python_path", "pip_path", "default_venv_dir",
                "editor_path", "terminal_path", "shell_path"):
        if s.get(key):
            s[key] = os.path.normpath(s[key])
    s["recent_projects"] = [os.path.normpath(p)
                            for p in s.get("recent_projects", [])]
    return s


def save_settings(settings):
    try:
        temp_file = CONFIG_FILE + f".tmp.{os.getpid()}"
        with open(temp_file, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2, ensure_ascii=False)
        os.replace(temp_file, CONFIG_FILE)
    except Exception as exc:                           # noqa: BLE001
        print(f"[VEnv Manager] Could not write config: {exc}")
# ==============================================================================
#  STYLESHEET BUILDER  (graphics: one QSS string generated from a theme)
# ==============================================================================
def build_stylesheet(c):
    """Return a Qt style sheet string for the given colour dictionary."""
    text_sel = "#000" if not c["is_dark"] else c["bg"]
    return f"""
    QWidget {{
        background-color: {c['bg']};
        color: {c['fg']};
        font-family: "{c['_font_family']}";
        font-size: {c['_font_size']}pt;
    }}
    QMainWindow::separator {{ background: {c['border']}; width: 3px; height: 3px; }}

    /* ---------- tabs ---------- */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        background: {c['bg']};
        top: -1px;
    }}
    QTabBar::tab {{
        background: {c['bg2']};
        color: {c['bg3'] if not c['is_dark'] else c['fg']};
        padding: 7px 16px;
        margin-right: 2px;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        border: 1px solid {c['border']};
        border-bottom: none;
    }}
    QTabBar::tab:selected {{
        background: {c['accent']};
        color: {text_sel};
        font-weight: bold;
    }}
    QTabBar::tab:hover:!selected {{ background: {c['bg3']}; }}

    /* ---------- buttons ---------- */
    QPushButton {{
        background: {c['bg2']};
        color: {c['fg']};
        border: 1px solid {c['border']};
        border-radius: 5px;
        padding: 5px 12px;
        min-height: 18px;
    }}
    QPushButton:hover  {{ background: {c['bg3']}; border-color: {c['accent']}; }}
    QPushButton:pressed{{ background: {c['accent2']}; color: {text_sel}; }}
    QPushButton:disabled {{ color: {c['bg3']}; border-color: {c['bg2']}; }}
    QPushButton#accentButton {{
        background: {c['accent']};
        color: {text_sel};
        font-weight: bold;
        border: none;
    }}
    QPushButton#accentButton:hover {{ background: {c['accent2']}; }}
    QPushButton#dangerButton {{
        background: {c['red']};
        color: {text_sel};
        border: none;
    }}
    QPushButton#successButton {{
        background: {c['green']};
        color: {text_sel};
        border: none;
    }}
    QToolButton {{ background: transparent; border: none; padding: 4px; }}
    QToolButton:hover {{ background: {c['bg3']}; border-radius: 4px; }}

    /* ---------- text inputs ---------- */
    QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {{
        background: {c['bg2']};
        color: {c['fg']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 4px 6px;
        selection-background-color: {c['accent']};
        selection-color: {text_sel};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {c['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background: {c['bg2']};
        color: {c['fg']};
        selection-background-color: {c['accent']};
        selection-color: {text_sel};
        border: 1px solid {c['border']};
    }}

    /* ---------- text / console areas ---------- */
    QPlainTextEdit, QTextEdit {{
        background: {c['console_bg']};
        color: {c['console_fg']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        selection-background-color: {c['accent']};
        selection-color: {text_sel};
    }}

    /* ---------- lists / tables / trees ---------- */
    QListWidget, QTableWidget, QTreeWidget, QTreeView {{
        background: {c['bg2']};
        alternate-background-color: {c['bg']};
        color: {c['fg']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        gridline-color: {c['border']};
        selection-background-color: {c['accent']};
        selection-color: {text_sel};
        outline: none;
    }}
    QTreeWidget::item, QTableWidget::item, QListWidget::item {{
        padding: 4px 2px;
    }}
    QTreeWidget::item:selected, QTableWidget::item:selected, QListWidget::item:selected {{
        background: {c['accent']};
        color: {text_sel};
    }}
    QTreeWidget::item:hover, QTableWidget::item:hover {{ background: {c['bg3']}; }}
    QHeaderView::section {{
        background: {c['header_bg']};
        color: {c['accent']};
        padding: 6px 6px;
        border: none;
        border-right: 1px solid {c['border']};
        border-bottom: 1px solid {c['border']};
        font-weight: bold;
    }}
    QTableView QTableCornerButton::section {{ background: {c['header_bg']}; border: none; }}

    /* ---------- group boxes ---------- */
    QGroupBox {{
        border: 1px solid {c['border']};
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 10px;
        font-weight: bold;
        color: {c['accent']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 5px;
    }}

    /* ---------- misc ---------- */
    QProgressBar {{
        background: {c['bg2']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        text-align: center;
        color: {c['fg']};
        height: 16px;
    }}
    QProgressBar::chunk {{ background: {c['accent']}; border-radius: 3px; }}
    QScrollBar:vertical {{
        background: {c['bg2']}; width: 12px; margin: 0; border-radius: 6px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['bg3']}; min-height: 26px; border-radius: 6px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
    QScrollBar:horizontal {{
        background: {c['bg2']}; height: 12px; margin: 0; border-radius: 6px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['bg3']}; min-width: 26px; border-radius: 6px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {c['accent']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

    QMenuBar {{ background: {c['header_bg']}; color: {c['fg']}; padding: 2px; }}
    QMenuBar::item {{ background: transparent; padding: 5px 10px; border-radius: 4px; }}
    QMenuBar::item:selected {{ background: {c['accent']}; color: {text_sel}; }}
    QMenu {{
        background: {c['bg2']}; color: {c['fg']};
        border: 1px solid {c['border']};
    }}
    QMenu::item {{ padding: 5px 24px 5px 22px; }}
    QMenu::item:selected {{ background: {c['accent']}; color: {text_sel}; }}
    QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 8px; }}

    QStatusBar {{ background: {c['header_bg']}; color: {c['fg']}; }}
    QStatusBar::item {{ border: none; }}
    QToolTip {{
        background: {c['bg2']}; color: {c['fg']};
        border: 1px solid {c['accent']}; padding: 3px;
    }}
    QSplitter::handle {{ background: {c['border']}; }}
    QSplitter::handle:hover {{ background: {c['accent']}; }}
    QCheckBox, QRadioButton {{ spacing: 6px; }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {c['border']};
        background: {c['bg2']};
    }}
    QCheckBox::indicator {{ border-radius: 3px; }}
    QRadioButton::indicator {{ border-radius: 7px; }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent']};
    }}
    QLabel#headerTitle {{
        color: {c['accent']};
        font-size: {max(13, int(c['_font_size']) + 6)}pt;
        font-weight: bold;
    }}
    QLabel#headerSub {{ color: {c['fg']}; font-size: {c['_font_size']}pt; }}
    QLabel#activeBadge {{ color: {c['green']}; font-weight: bold; }}
    QLabel#cardValue {{
        color: {c['accent']};
        font-size: {max(14, int(c['_font_size']) + 8)}pt;
        font-weight: bold;
    }}
    QLabel#cardIcon {{ color: {c['accent']}; font-size: {max(16, int(c['_font_size']) + 12)}pt; }}
    QLabel#cardCaption {{ color: {c['fg']}; font-size: {max(7, int(c['_font_size']) - 2)}pt; }}
    QFrame#card {{
        background: {c['bg2']};
        border: 1px solid {c['border']};
        border-radius: 8px;
    }}
    QFrame#headerBar {{ background: {c['header_bg']}; border: none; }}
    QFrame#toolBar {{ background: {c['bg2']}; border: none; }}
    """


# ==============================================================================
#  BACKGROUND TASKS  (QThread so the GUI never blocks)
# ==============================================================================
class Worker(QObject):
    """Runs a callable in a worker thread and emits its result."""
    finished = pyqtSignal(object)
    failed   = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as exc:                        # noqa: BLE001
            self.failed.emit(str(exc))


class StreamWorker(QObject):
    """Runs a subprocess and streams its output lines as they arrive."""
    line     = pyqtSignal(str, str)   # (stream_name, text_line)
    done     = pyqtSignal(int)        # return code
    failed   = pyqtSignal(str)

    def __init__(self, cmd, cwd=None, shell=False, env=None):
        super().__init__()
        self._cmd = cmd
        self._cwd = cwd
        self._shell = shell
        self._env = env
        self.proc = None

    def run(self):
        try:
            self.proc = subprocess.Popen(
                self._cmd, cwd=self._cwd, shell=self._shell, env=self._env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", bufsize=1)
        except Exception as exc:                        # noqa: BLE001
            self.failed.emit(str(exc))
            return

        def pump(stream, name):
            try:
                for raw in iter(stream.readline, ""):
                    self.line.emit(name, raw.rstrip("\n"))
            except Exception:                           # noqa: BLE001
                pass
            finally:
                try:
                    stream.close()
                except Exception:                       # noqa: BLE001
                    pass

        t_out = threading.Thread(target=pump, args=(self.proc.stdout, "stdout"), daemon=True)
        t_err = threading.Thread(target=pump, args=(self.proc.stderr, "stderr"), daemon=True)
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()
        code = self.proc.wait()
        self.done.emit(code)

    def terminate(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:                           # noqa: BLE001
                pass
            try:
                if self.proc.poll() is None and hasattr(self.proc, "kill"):
                    self.proc.kill()
            except Exception:                           # noqa: BLE001
                pass


# ==============================================================================
#  TERMINAL / TOOLING GUIDE DATA
# ==============================================================================
TERMINAL_GUIDE = [
    ("Basics", [
        "Readable, configurable interface - fonts, colours, themes, DPI scaling",
        "Multi-tab and split-pane support (split view)",
        "Command history - scrolling, searching, filtering",
        "Keyboard shortcuts - quick switching, copy, clear screen",
        "Full Unicode support - international characters, emoji, box symbols",
        "Fullscreen mode and per-monitor DPI handling",
    ]),
    ("Technical features", [
        "Multi-shell support: Bash, PowerShell, CMD, Python REPL, SSH, WSL",
        "Configuration profiles - different settings per environment",
        "Split panes - vertical and horizontal window splits",
        "GPU rendering - smooth scrolling without lag",
        "Fast buffer search - find log lines and errors instantly",
        "256+ colours and TrueColor support",
    ]),
    ("Security and stability", [
        "Isolated sessions - no data leaking between tabs",
        "Secure credential storage - Keyring / Windows Credential Manager",
        "Stability with very large logs - no freezing",
        "Warnings before destructive commands (for example rm -rf /)",
    ]),
    ("Integrations and extensibility", [
        "Plugins and extensions: oh-my-posh, starship, zsh plugins",
        "Git integration - repository status, branches, conflicts",
        "SSH integration - profiles, keys, quick switching",
        "JSON / YAML configuration files - portable settings",
    ]),
    ("User experience and aesthetics", [
        "Colour schemes: Solarized, Dracula, Nord, Monokai",
        "Informative prompt - git branch, status, execution time",
        "Clear section separators - lines, spacers, minimalism",
        "Smooth animations and transitions",
    ]),
    ("Advanced features", [
        "Quake mode - drop-down terminal from the top of the screen",
        "Cloud synchronisation of settings",
        "Built-in plugin / package manager",
        "Built-in file explorer",
        "Inline image and file preview (Kitty, iTerm2)",
    ]),
    ("Good terminal examples", [
        "Windows Terminal - modern, fast, profiles, GPU, tabs",
        "iTerm2 (macOS) - one of the most advanced terminals available",
        "Kitty - GPU rendered, fast, highly configurable",
        "Alacritty - minimalism and raw performance",
        "WezTerm - very configurable, Lua scripting, GPU, split panes",
    ]),
]

DEVICE_TYPES = [
    "FDD 1.44 MB (floppy)",
    "FDD 720 KB (floppy)",
    "CD-ROM (ISO 9660)",
    "DVD-ROM (ISO 9660)",
    "BD-ROM (ISO 9660)",
    "HDD (VHD)",
    "HDD (VMDK)",
    "HDD (QCOW2)",
    "HDD (RAW)",
    "USB flash (RAW)",
    "SD card (RAW)",
    "ZIP drive (100 MB)",
    "MO disk (230 MB)",
    "Tape archive (TAR)",
]

IMAGE_FILE_FILTER = (
    "All disk images (*.iso *.img *.ima *.bin *.vhd *.vhdx *.vmdk *.qcow2 "
    "*.raw *.tar *.mdf);;"
    "ISO images (*.iso);;VHD/VHDX (*.vhd *.vhdx);;VMDK (*.vmdk);;"
    "QCOW2 (*.qcow2);;Floppy images (*.img *.ima);;Raw images (*.raw *.bin);;"
    "All files (*)"
)


# ==============================================================================
#  DISK IMAGE HELPERS  (real byte-level writers, no external tools required)
# ==============================================================================
def write_floppy_image(path, size_mb, label):
    """Create a bootable-format FAT12 floppy image (720 KB or 1.44 MB)."""
    if size_mb <= 720:
        total_sectors, heads, spt, media = 1440, 2, 9, 0xF0
    else:
        total_sectors, heads, spt, media = 2880, 2, 18, 0xF0
    total_bytes = total_sectors * 512
    img = bytearray(total_bytes)

    img[0:3]   = b"\xEB\x3C\x90"
    img[3:11]  = b"MSDOS5.0"
    img[11]    = 0x00          # bytes per sector low
    img[12]    = 0x02          # bytes per sector high  -> 512
    img[13]    = 0x01          # sectors per cluster
    img[14]    = 0x01          # reserved sectors
    img[15]    = 0x00
    img[16]    = 0x02          # number of FATs
    img[17]    = 0xE0          # root entries
    img[18]    = 0x00
    img[19]    = total_sectors & 0xFF
    img[20]    = (total_sectors >> 8) & 0xFF
    img[21]    = media
    img[22]    = 0x09          # sectors per FAT
    img[23]    = 0x00
    img[24]    = spt
    img[25]    = 0x00
    img[26]    = heads
    img[27]    = 0x00
    img[510]   = 0x55
    img[511]   = 0xAA

    fat_size = 9 * 512
    for fat_off in (512, 512 + fat_size):
        img[fat_off]     = media
        img[fat_off + 1] = 0xFF
        img[fat_off + 2] = 0xFF

    root_start = 512 + 2 * fat_size
    img[root_start:root_start + 11] = label[:11].ljust(11).encode("ascii", "replace")
    img[root_start + 11] = 0x08
    with open(path, "wb") as fh:
        fh.write(bytes(img))
    return total_bytes


def write_vhd_footer_image(path, size_mb):
    """Create a fixed-size VHD with a valid conectix footer."""
    total_bytes = max(1024 * 1024, int(size_mb) * 1024 * 1024)
    cookie      = b"conectix"
    features    = struct.pack(">I", 0x00002)
    version     = struct.pack(">I", 0x00010000)
    data_offset = struct.pack(">Q", 0xFFFFFFFF)
    timestamp   = struct.pack(">I", 0)
    creator_app = b"py  "
    creator_ver = struct.pack(">I", 0x00010000)
    creator_os  = b"Wi2k"
    orig_size   = struct.pack(">Q", total_bytes)
    curr_size   = struct.pack(">Q", total_bytes)
    cylinders   = max(1, total_bytes // (512 * 16 * 63))
    geometry    = struct.pack(">HBB", min(cylinders, 0xFFFF), 16, 63)
    disk_type   = struct.pack(">I", 2)
    disk_uuid   = uuid.uuid4().bytes

    body = (cookie + features + version + data_offset + timestamp +
            creator_app + creator_ver + creator_os + orig_size + curr_size +
            geometry + disk_type + b"\x00\x00\x00\x00" + disk_uuid +
            b"\x00" + b"\x00" * 427)
    body = body[:512].ljust(512, b"\x00")
    checksum = (~sum(body)) & 0xFFFFFFFF
    footer = body[:64] + struct.pack(">I", checksum) + body[68:512]

    with open(path, "wb") as fh:
        if total_bytes > 512:
            fh.seek(total_bytes - 512)
        fh.write(footer)
    return total_bytes


def write_sparse_raw_image(path, size_mb):
    """Create a sparse raw disk image."""
    total_bytes = max(1024 * 1024, int(size_mb) * 1024 * 1024)
    with open(path, "wb") as fh:
        fh.seek(total_bytes - 1)
        fh.write(b"\x00")
    return total_bytes


def write_iso_stub(path, label):
    """Minimal ISO 9660 primary volume descriptor when pycdlib is absent."""
    with open(path, "wb") as fh:
        fh.write(b"\x00" * 16 * 2048)
        pvd = bytearray(2048)
        pvd[0] = 0x01
        pvd[1:6] = b"CD001"
        pvd[6] = 0x01
        pvd[40:72] = label[:32].ljust(32).encode("ascii", "replace")
        fh.write(bytes(pvd))
        fh.write(b"\x00" * 2048)
    return 2048 * 18


def detect_image_format(path):
    """Sniff the container format of a disk image by its magic bytes."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(16)
            # ISO 9660 stores its primary volume descriptor at sector 16
            fh.seek(16 * 2048)
            pvd = fh.read(8)
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            if size >= 512:
                fh.seek(size - 512)
                tail = fh.read(8)
            else:
                tail = b""
    except OSError:
        return "unreadable"
    if head[1:6] == b"CD001" or pvd[1:6] == b"CD001":
        return "ISO 9660 image"
    if tail[:8] == b"conectix" or head[:8] == b"conectix":
        return "VHD (Microsoft Virtual Hard Disk)"
    if head[:4] == b"KDMV":
        return "VMDK (VMware)"
    if head[:4] == b"QFI\xfb":
        return "QCOW2 (QEMU)"
    if head[3:11] == b"MSDOS5.0" or head[54:62] == b"FAT16   ":
        return "FAT12/FAT16 floppy image"
    if head[82:90] == b"FAT32   ":
        return "FAT32 volume"
    if head[:4] == b"\x7fELF":
        return "ELF binary (not a disk image)"
    if head[510:512] == b"\x55\xAA":
        return "Raw image with MBR boot signature"
    return "Raw / unrecognised image"
# ==============================================================================
#  BACKEND  -  all shell / pip / git / filesystem work lives here
# ==============================================================================
class Backend:
    """Stateless helpers that talk to pip, git and the filesystem."""

    def __init__(self, settings):
        self.settings = settings

    # ---------------- interpreters ----------------
    def find_all_pythons(self):
        found = []

        def add(path):
            path = os.path.normpath(path)
            if path not in found and os.path.isfile(path):
                found.append(path)

        for major in range(8, 21):
            for name in (f"python3.{major}", f"python3.{major}.exe"):
                p = shutil.which(name)
                if p:
                    add(p)
        for name in ("python3", "python", "python.exe", "py"):
            p = shutil.which(name)
            if p:
                add(p)

        pyenv_root = os.environ.get("PYENV_ROOT", os.path.expanduser("~/.pyenv"))
        for py in _glob.glob(os.path.join(pyenv_root, "versions", "*", "bin", "python*")):
            if not py.endswith(("-config", "m")):
                add(py)

        conda_exe = shutil.which("conda") or shutil.which("conda.exe")
        if conda_exe:
            try:
                out = subprocess.run([conda_exe, "info", "--envs", "--json"],
                                     capture_output=True, text=True, timeout=10)
                if out.returncode == 0:
                    for env_path in json.loads(out.stdout).get("envs", []):
                        for name in ("python.exe", "python3", "python"):
                            cand = os.path.join(env_path, BIN_DIR, name)
                            if os.path.isfile(cand):
                                add(cand)
                                break
            except Exception:                           # noqa: BLE001
                pass

        if IS_WIN:
            import glob as g
            for base in (r"C:\Python3*", r"C:\Program Files\Python3*",
                         os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                      "Programs", "Python", "Python3*")):
                for d in g.glob(base):
                    cand = os.path.join(d, "python.exe")
                    if os.path.isfile(cand):
                        add(cand)

        add(sys.executable)
        return found[:16]

    @staticmethod
    def python_version(python_exe):
        try:
            r = subprocess.run([python_exe, "--version"], capture_output=True,
                               text=True, timeout=5)
            return (r.stdout + r.stderr).strip().split()[-1]
        except Exception:                               # noqa: BLE001
            return "?"

    @staticmethod
    def pip_version():
        try:
            r = subprocess.run([sys.executable, "-m", "pip", "--version"],
                               capture_output=True, text=True, timeout=8)
            return r.stdout.split()[1] if r.returncode == 0 else "?"
        except Exception:                               # noqa: BLE001
            return "?"

    @staticmethod
    def tools():
        names = ["python", "python3", "pip", "pip3", "virtualenv", "poetry",
                 "pipenv", "conda", "pyenv", "uv", "git", "docker", "node",
                 "npm", "qemu-img", "mkfs.fat", "mkfs.ext4", "fsck"]
        return [(n, shutil.which(n)) for n in names]

    # ---------------- environments ----------------
    @staticmethod
    def is_venv(path):
        if not os.path.isdir(path):
            return False
        if not os.path.isdir(os.path.join(path, BIN_DIR)):
            return False
        return (os.path.exists(os.path.join(path, "pyvenv.cfg"))
                or os.path.isdir(os.path.join(path, "Lib"))
                or os.path.isdir(os.path.join(path, "lib")))

    def discover_venvs(self, directory):
        result = []
        if not directory or not os.path.isdir(directory):
            return result
        try:
            for item in sorted(os.listdir(directory)):
                full = os.path.join(directory, item)
                if self.is_venv(full):
                    result.append(full)
        except PermissionError:
            pass
        return result

    @staticmethod
    def venv_python(venv):
        cand = os.path.join(venv, BIN_DIR, PY_EXE)
        return cand if os.path.exists(cand) else sys.executable

    @staticmethod
    def venv_python_version(venv):
        return Backend.python_version(Backend.venv_python(venv))

    def pip_cmd(self, venv=None):
        """Return the command list to invoke pip for a venv: [python_exe, "-m", "pip"]."""
        custom = self.settings.get("pip_path", "")
        if custom and os.path.exists(custom):
            return [custom]
        py = Backend.venv_python(venv) if venv else sys.executable
        return [py, "-m", "pip"]

    @staticmethod
    def find_venv_tool(venv, tool_name):
        """Locate a console tool inside a venv, honouring the '.exe' suffix on Windows."""
        names = [tool_name, f"{tool_name}.exe"] if IS_WIN else [tool_name]
        for name in names:
            p = os.path.join(venv, BIN_DIR, name)
            if os.path.isfile(p):
                return p
        return shutil.which(tool_name)

    def pip_for(self, venv=None):
        """Backwards-compatible accessor returning the pip command list."""
        return self.pip_cmd(venv)

    def pip_args(self):
        """Extra pip options taken from the settings dialog."""
        extra = []
        if self.settings.get("pip_extra_index"):
            extra += ["--extra-index-url", self.settings["pip_extra_index"]]
        if self.settings.get("pip_trusted_host"):
            extra += ["--trusted-host", self.settings["pip_trusted_host"]]
        if self.settings.get("proxy_url"):
            extra += ["--proxy", self.settings["proxy_url"]]
        return extra

    def count_packages(self, venv):
        try:
            r = subprocess.run(self.pip_cmd(venv) + ["list", "--format=freeze"],
                               capture_output=True, text=True, timeout=30, check=False)
            return sum(1 for line in r.stdout.splitlines() if "==" in line)
        except Exception:                               # noqa: BLE001
            return -1

    def list_packages(self, venv):
        """Return [(name, version), ...] for a venv."""
        out = []
        try:
            r = subprocess.run(self.pip_cmd(venv) + ["list", "--format=freeze"],
                               capture_output=True, text=True, timeout=60, check=False)
            for line in r.stdout.splitlines():
                if "==" in line:
                    name, _, ver = line.partition("==")
                    out.append((name.strip(), ver.strip()))
        except Exception:                               # noqa: BLE001
            pass
        return out

    def freeze(self, venv):
        try:
            r = subprocess.run(self.pip_cmd(venv) + ["freeze"],
                               capture_output=True, text=True, timeout=60, check=False)
            return r.stdout
        except Exception:                               # noqa: BLE001
            return ""

    def outdated(self, venv):
        """Return {package_lower: latest_version}."""
        result = {}
        try:
            r = subprocess.run(self.pip_cmd(venv) + ["list", "--outdated", "--format=columns"],
                               capture_output=True, text=True, timeout=120, check=False)
            for line in r.stdout.splitlines()[2:]:
                parts = line.split()
                if len(parts) >= 3:
                    result[parts[0].lower()] = parts[2]
        except Exception:                               # noqa: BLE001
            pass
        return result

    def health_check(self, venv):
        """Return (ok_lines, issue_lines)."""
        ok, issues = [], []
        py = Backend.venv_python(venv)
        if os.path.exists(py):
            ok.append(f"Python executable: {Backend.python_version(py)}")
        else:
            issues.append(f"Python executable missing: {py}")

        pip_cmd = self.pip_cmd(venv)
        try:
            r = subprocess.run(pip_cmd + ["--version"], capture_output=True,
                               text=True, timeout=10, check=False)
            if r.returncode == 0:
                parts = r.stdout.split()
                ver = parts[1] if len(parts) > 1 else r.stdout.strip()
                ok.append(f"pip: {ver}")
            else:
                issues.append("pip returned a non-zero exit code")
        except Exception:                               # noqa: BLE001
            issues.append("pip is not responding")

        try:
            r = subprocess.run(pip_cmd + ["check"], capture_output=True,
                               text=True, timeout=60, check=False)
            if r.returncode == 0:
                ok.append("Dependencies: no conflicts reported")
            else:
                for line in r.stdout.strip().splitlines():
                    issues.append(f"Dependency conflict: {line}")
        except Exception:                               # noqa: BLE001
            issues.append("pip check could not be executed")

        cfg = os.path.join(venv, "pyvenv.cfg")
        if os.path.exists(cfg):
            ok.append("pyvenv.cfg present")
        else:
            issues.append("pyvenv.cfg missing - this may not be a valid venv")

        site_ok = any(os.path.isdir(os.path.join(venv, d))
                      for d in ("Lib", "lib", "site-packages"))
        if site_ok:
            ok.append("site-packages directory found")
        else:
            issues.append("no site-packages directory found")

        return ok, issues

    # ---------------- git ----------------
    @staticmethod
    def git_available():
        return shutil.which("git")

    @staticmethod
    def git_run(repo, args):
        git = shutil.which("git")
        if not git:
            return 1, "", "git was not found on PATH"
        try:
            r = subprocess.run([git] + args, cwd=repo, capture_output=True,
                               text=True, timeout=60)
            return r.returncode, r.stdout, r.stderr
        except Exception as exc:                        # noqa: BLE001
            return 1, "", str(exc)

    @staticmethod
    def git_branch(repo):
        code, out, _err = Backend.git_run(repo, ["branch", "--show-current"])
        return out.strip() or "detached" if code == 0 else "detached"

    @staticmethod
    def find_repo_for(path):
        """Walk up from a path looking for a .git directory."""
        cur = os.path.abspath(path)
        for _ in range(8):
            if os.path.isdir(os.path.join(cur, ".git")):
                return cur
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        return ""

    # ---------------- system info ----------------
    @staticmethod
    def dashboard_venvs(directory):
        """Discover environments and their natural keys for charting."""
        venvs = []
        if directory and os.path.isdir(directory):
            for item in sorted(os.listdir(directory)):
                full = os.path.join(directory, item)
                if Backend.is_venv(full):
                    venvs.append(full)
        return venvs


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
            self.settings = dict(DEFAULT_SETTINGS)
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
# ==============================================================================
#  MAIN WINDOW
# ==============================================================================
class MainWindow(QMainWindow):
    sig_vd_log = pyqtSignal(str)
    sig_vd_progress = pyqtSignal(int)
    sig_log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.backend = Backend(self.settings)
        self.T = tr

        self.sig_vd_log.connect(self.vd_log_msg)
        self.sig_vd_progress.connect(self.vd_set_progress)
        self.sig_log.connect(self.log)

        self._threads = []
        self._workers = []
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
        self._act(m_file, tr("open_project"), self.action_open_project, "Ctrl+O")
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
            act.setChecked(name == self.settings.get("theme"))
            act.triggered.connect(lambda _=False, n=name: self.change_theme(n))
            self.theme_menu.addAction(act)
        m_view.addSeparator()
        self._act(m_view, tr("settings"), self.action_settings, "Ctrl+,")

        # -- Help
        m_help = bar.addMenu(tr("menu_help"))
        self._act(m_help, tr("documentation"), self.action_docs)
        self._act(m_help, tr("keyboard_shortcuts"), self.action_shortcuts, "F1")
        self._act(m_help, tr("check_updates"), self.action_project_page)
        m_help.addSeparator()
        self._act(m_help, tr("about"), self.action_about)

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
        sizes = self.settings.get("splitter_sizes", [320, 1000])
        try:
            self.splitter.setSizes([int(sizes[0]), int(sizes[1])])
        except Exception:                               # noqa: BLE001
            self.splitter.setSizes([320, 1000])
        root.addWidget(self.splitter, 1)

        self.setCentralWidget(central)

    def _build_header(self):
        bar = QFrame()
        bar.setObjectName("headerBar")
        bar.setFixedHeight(56)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 6, 14, 6)

        icon_lbl = QLabel("\u25A3")
        icon_lbl.setObjectName("headerTitle")
        title = QLabel(APP_NAME)
        title.setObjectName("headerTitle")
        sub = QLabel(f"v{APP_VERSION}   \u00b7   {APP_COMPANY}   \u00b7   PyQt6 edition")
        sub.setObjectName("headerSub")

        lay.addWidget(icon_lbl)
        lay.addWidget(title)
        lay.addSpacing(10)
        lay.addWidget(sub)
        lay.addStretch(1)

        self.active_badge = QLabel("")
        self.active_badge.setObjectName("activeBadge")
        lay.addWidget(self.active_badge)
        return bar

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("toolBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        buttons = [
            (f"+  {tr('create_venv')}", self.action_create_venv, "accentButton"),
            (f"Install package", self.action_install_package, None),
            (f"Refresh", self.reload_venvs, None),
            (f"Terminal", self.action_open_terminal, None),
            (f"Search PyPI", self.action_search_pypi, None),
            (f"Upgrade all", self.action_upgrade_all, None),
            (f"pip-audit", self.action_pip_audit, None),
        ]
        for text, slot, obj_name in buttons:
            btn = QPushButton(text)
            if obj_name:
                btn.setObjectName(obj_name)
            btn.clicked.connect(lambda _=False, s=slot: s())
            lay.addWidget(btn)

        lay.addStretch(1)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.action_settings)
        lay.addWidget(settings_btn)
        return bar

    # -------------------------------------------------------- environments panel
    def _build_env_panel(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 8, 4, 8)
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
        self.venv_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.venv_table.customContextMenuRequested.connect(self.env_context_menu)
        self.venv_table.itemSelectionChanged.connect(self.on_env_selected)
        self.venv_table.itemDoubleClicked.connect(lambda _i: self.action_activate_venv())
        header = self.venv_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 5):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.sectionClicked.connect(self.sort_env_table)
        lay.addWidget(self.venv_table, 1)

        row = QHBoxLayout()
        row.setSpacing(4)
        for text, slot, tip, obj in (
            ("+", self.action_create_venv, tr("create_venv"), "accentButton"),
            ("\u2716", self.action_delete_venv, tr("delete_venv"), "dangerButton"),
            ("Clone", self.action_clone_venv, tr("clone_venv"), None),
            ("Folder", self.action_open_in_explorer, tr("open_in_explorer"), None),
            ("Folders", lambda: self._show_tab("dashboard"),
             tr("tab_dashboard"), None),
        ):
            btn = QPushButton(text)
            btn.setToolTip(tip)
            if obj:
                btn.setObjectName(obj)
            btn.clicked.connect(lambda _=False, s=slot: s())
            row.addWidget(btn)
        lay.addLayout(row)
        return panel

    # ------------------------------------------------------------------ tabs
    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_dashboard(), tr("tab_dashboard"))
        self.tabs.addTab(self._tab_packages(), tr("tab_packages"))
        self.tabs.addTab(self._tab_console(), tr("tab_console"))
        self.tabs.addTab(self._tab_script(), tr("tab_script"))
        self.tabs.addTab(self._tab_git(), tr("tab_git"))
        self.tabs.addTab(self._tab_devices(), tr("tab_device"))
        self.tabs.addTab(self._tab_guide(), tr("tab_guide"))
        return self.tabs

    def _goto_tab(self, key):
        index = {"dashboard": 0, "packages": 1, "console": 2, "script": 3,
                 "git": 4, "devices": 5, "guide": 6}.get(key, 0)
        self.tabs.setCurrentIndex(index)

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
                                     f"  |  pip {Backend.pip_version()}")
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
        """Run fn() in a worker thread; call on_done(result) on the GUI thread."""
        thread = QThread()
        worker = Worker(fn)
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
            target = on_line or (lambda s, t: self.log(t))
            target(stream, text)

        def _done(code):
            if on_done:
                on_done(code)
            thread.quit()

        worker.line.connect(_line)
        worker.done.connect(_done)
        worker.failed.connect(lambda msg: (self.log(f"ERROR: {msg}"), thread.quit()))
        thread.started.connect(worker.run)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._cleanup_thread(thread, worker))
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()
        return worker

    def _cleanup_thread(self, thread, worker):
        for collection in (self._threads, self._workers):
            for item in list(collection):
                if item is thread or item is worker:
                    try:
                        collection.remove(item)
                    except ValueError:
                        pass
        try:
            worker.deleteLater()
        except Exception:
            pass
        try:
            thread.deleteLater()
        except Exception:
            pass

    # ------------------------------------------------------------------ shortcuts
    def _bind_shortcuts(self):
        def add(seq, slot):
            act = QAction(self)
            act.setShortcut(QKeySequence(seq))
            act.triggered.connect(lambda _=False: slot())
            self.addAction(act)

        add("Ctrl+N", self.action_create_venv)
        add("Ctrl+Shift+N", self.action_new_project)
        add("Ctrl+R", self.reload_venvs)
        add("F5", self.reload_venvs)
        add("Ctrl+I", self.action_install_package)
        add("Ctrl+T", self.action_open_terminal)
        add("Ctrl+S", self.action_save_config)
        add("Ctrl+E", self.action_export_requirements)
        add("Ctrl+D", self.action_delete_venv)
        add("Ctrl+U", self.action_upgrade_all)
        add("Ctrl+L", self.clear_console)
        add("Ctrl+Q", self.close)
        add("F1", self.action_shortcuts)
    # ============================================================ DASHBOARD TAB
    def _tab_dashboard(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_envs = StatCard("\U0001F4C1", tr("dash_total_venvs"), self.C("accent"))
        self.card_pkgs = StatCard("\U0001F4E6", tr("dash_total_pkgs"), self.C("green"))
        self.card_outdated = StatCard("\u2B06", tr("dash_outdated"), self.C("yellow"))
        self.card_disk = StatCard("\U0001F4BE", tr("dash_dash") if False else tr("dash_disk"),
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

    # ======================================================= VIRTUAL DEVICE TAB
    def _tab_devices(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        # -- dependency bar
        dep_bar = QHBoxLayout()
        dep_bar.addWidget(QLabel("Python dependencies:"))
        self.vd_deps_label = QLabel("detecting...")
        dep_bar.addWidget(self.vd_deps_label, 1)
        check_btn = QPushButton("Check dependencies")
        check_btn.clicked.connect(self.vd_check_deps)
        dep_bar.addWidget(check_btn)
        install_btn = QPushButton(tr("vd_install_deps"))
        install_btn.clicked.connect(self.vd_install_deps)
        dep_bar.addWidget(install_btn)
        outer.addLayout(dep_bar)

        split = QSplitter(Qt.Orientation.Horizontal)

        # -- left: configuration notebook
        cfg = QTabWidget()

        # new image
        new_img = QWidget()
        form = QFormLayout(new_img)
        self.vd_type = QComboBox()
        self.vd_type.addItems(DEVICE_TYPES)
        self.vd_type.setCurrentText("HDD (VHD)")
        self.vd_type.currentTextChanged.connect(self.vd_on_type_change)
        form.addRow(tr("vd_device_type"), self.vd_type)

        path_row = QHBoxLayout()
        self.vd_image_path = QLineEdit(
            os.path.join(os.path.expanduser("~"), "disk.vhd"))
        path_row.addWidget(self.vd_image_path, 1)
        browse = QPushButton(tr("browse"))
        browse.clicked.connect(self.vd_browse_save)
        path_row.addWidget(browse)
        form.addRow(tr("vd_image_path"), path_row)

        self.vd_size = QSpinBox()
        self.vd_size.setRange(1, 2_097_152)
        self.vd_size.setValue(1024)
        self.vd_size.setSuffix(" MB")
        form.addRow(tr("vd_size"), self.vd_size)

        self.vd_fs = QComboBox()
        self.vd_fs.addItems(["FAT12", "FAT16", "FAT32", "exFAT", "NTFS",
                             "ext2", "ext3", "ext4", "ISO 9660", "UDF",
                             "HFS+", "None (raw)"])
        form.addRow(tr("vd_filesystem"), self.vd_fs)

        self.vd_label = QLineEdit("VDISK")
        form.addRow(tr("vd_label"), self.vd_label)

        self.vd_sector = QComboBox()
        self.vd_sector.addItems(["512", "1024", "2048", "4096"])
        form.addRow(tr("vd_sector"), self.vd_sector)

        self.vd_readonly_cb = QCheckBox(tr("vd_read_only"))
        self.vd_bootable_cb = QCheckBox(tr("vd_bootable"))
        form.addRow(self.vd_readonly_cb, self.vd_bootable_cb)

        create_btn = QPushButton(tr("vd_create_image"))
        create_btn.setObjectName("accentButton")
        create_btn.clicked.connect(self.vd_create_image)
        form.addRow(create_btn)
        cfg.addTab(new_img, tr("vd_new_image"))

        # mount
        mount = QWidget()
        mform = QFormLayout(mount)
        mrow = QHBoxLayout()
        self.vd_mount_image = QLineEdit()
        mrow.addWidget(self.vd_mount_image, 1)
        mbrowse = QPushButton(tr("browse"))
        mbrowse.clicked.connect(self.vd_browse_open)
        mrow.addWidget(mbrowse)
        mform.addRow(tr("vd_image_path"), mrow)

        self.vd_mount_point = QLineEdit("V:" if IS_WIN else "/mnt/vdisk")
        mform.addRow(tr("vd_mount_point"), self.vd_mount_point)

        self.vd_mount_fs = QComboBox()
        self.vd_mount_fs.addItems(["auto", "iso9660", "vfat", "ntfs", "ext4",
                                   "udf", "exfat"])
        mform.addRow(tr("vd_filesystem"), self.vd_mount_fs)

        mrow2 = QHBoxLayout()
        m_btn = QPushButton(tr("vd_mount"))
        m_btn.setObjectName("accentButton")
        m_btn.clicked.connect(self.vd_mount)
        u_btn = QPushButton(tr("vd_unmount"))
        u_btn.clicked.connect(self.vd_unmount)
        x_btn = QPushButton(tr("vd_extract_iso"))
        x_btn.clicked.connect(self.vd_extract_iso)
        i_btn = QPushButton(tr("vd_make_iso"))
        i_btn.clicked.connect(self.vd_make_iso)
        for b in (m_btn, u_btn, x_btn, i_btn):
            mrow2.addWidget(b)
        mform.addRow(mrow2)
        cfg.addTab(mount, tr("vd_mount"))

        # convert
        convert = QWidget()
        cform = QFormLayout(convert)
        crow = QHBoxLayout()
        self.vd_convert_src = QLineEdit()
        crow.addWidget(self.vd_convert_src, 1)
        sbrowse = QPushButton(tr("browse"))
        sbrowse.clicked.connect(lambda: self._vd_pick(self.vd_convert_src, False))
        crow.addWidget(sbrowse)
        cform.addRow(tr("vd_source"), crow)

        crow2 = QHBoxLayout()
        self.vd_convert_dst = QLineEdit()
        crow2.addWidget(self.vd_convert_dst, 1)
        dbrowse = QPushButton(tr("browse"))
        dbrowse.clicked.connect(lambda: self._vd_pick(self.vd_convert_dst, True))
        crow2.addWidget(dbrowse)
        cform.addRow(tr("vd_target"), crow2)

        self.vd_convert_fmt = QComboBox()
        self.vd_convert_fmt.addItems(["vhd", "vmdk", "qcow2", "raw", "vdi",
                                      "vpc", "parallels"])
        cform.addRow(tr("vd_output_format"), self.vd_convert_fmt)

        conv_btn = QPushButton(tr("vd_convert"))
        conv_btn.setObjectName("accentButton")
        conv_btn.clicked.connect(self.vd_convert)
        cform.addRow(conv_btn)
        cfg.addTab(convert, tr("vd_convert"))

        # format / repair
        repair = QWidget()
        rform = QFormLayout(repair)
        rrow = QHBoxLayout()
        self.vd_format_path = QLineEdit()
        rrow.addWidget(self.vd_format_path, 1)
        rbrowse = QPushButton(tr("browse"))
        rbrowse.clicked.connect(lambda: self._vd_pick(self.vd_format_path, False))
        rrow.addWidget(rbrowse)
        rform.addRow(tr("vd_image_path"), rrow)

        self.vd_format_fs = QComboBox()
        self.vd_format_fs.addItems(["FAT12", "FAT16", "FAT32", "exFAT", "NTFS", "ext4"])
        rform.addRow(tr("vd_filesystem"), self.vd_format_fs)

        self.vd_quick_format = QCheckBox("Quick format")
        self.vd_quick_format.setChecked(True)
        rform.addRow(self.vd_quick_format)

        rrow2 = QHBoxLayout()
        f_btn = QPushButton(tr("vd_format_dev"))
        f_btn.setObjectName("dangerButton")
        f_btn.clicked.connect(self.vd_format_image)
        mbr_btn = QPushButton(tr("vd_repair_mbr"))
        mbr_btn.clicked.connect(self.vd_write_mbr)
        fs_btn = QPushButton(tr("vd_check_fs"))
        fs_btn.clicked.connect(self.vd_check_filesystem)
        for b in (f_btn, mbr_btn, fs_btn):
            rrow2.addWidget(b)
        rform.addRow(rrow2)
        cfg.addTab(repair, tr("vd_format_tab"))

        split.addWidget(cfg)

        # -- right: device list and log
        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(4, 0, 0, 0)

        rlay.addWidget(QLabel(f"{tr('vd_threads')} / {tr('vd_log')}"))
        self.vd_table = QTableWidget(0, 5)
        self.vd_table.setHorizontalHeaderLabels(
            ["Type", "Image", "Mount point", "Status", "Size"])
        self.vd_table.verticalHeader().setVisible(False)
        self.vd_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.vd_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.vd_table.setAlternatingRowColors(True)
        self.vd_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.vd_table.customContextMenuRequested.connect(self.vd_context_menu)
        vh = self.vd_table.horizontalHeader()
        vh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        rlay.addWidget(self.vd_table, 1)

        vrow = QHBoxLayout()
        for text, slot in (("Eject / remove row", self.vd_eject_selected),
                           (tr("vd_info"), self.vd_image_info),
                           (tr("vd_verify"), self.vd_verify_image),
                           (tr("refresh"), self.vd_refresh_list),
                           ("Copy path", self.vd_copy_path)):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, s=slot: s())
            vrow.addWidget(btn)
        rlay.addLayout(vrow)

        self.vd_log = QPlainTextEdit()
        self.vd_log.setReadOnly(True)
        self.vd_log.setMaximumBlockCount(4000)
        self.vd_log.setFont(mono_font(self.settings.get("font_family"), 10))
        rlay.addWidget(self.vd_log, 2)

        split.addWidget(right)
        split.setSizes([520, 560])
        outer.addWidget(split, 1)

        # -- progress
        self.vd_progress = QProgressBar()
        self.vd_progress.setValue(0)
        outer.addWidget(self.vd_progress)

        QTimer.singleShot(400, self.vd_check_deps)
        return page

    # ================================================================= GUIDE TAB
    def _tab_guide(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        clay = QVBoxLayout(content)
        clay.setSpacing(4)

        for section, items in TERMINAL_GUIDE:
            head = QLabel(section)
            head.setStyleSheet("font-weight: bold; color: palette(highlight); "
                               "padding-top: 10px;")
            clay.addWidget(head)
            for item in items:
                bullet = QLabel(f"   \u25B8   {item}")
                bullet.setWordWrap(True)
                bullet.setStyleSheet("padding: 3px 10px;")
                clay.addWidget(bullet)
        clay.addStretch(1)
        scroll.setWidget(content)
        lay.addWidget(scroll)
        return page
    # ======================================================= ENVIRONMENT LOGIC
    def reload_venvs(self):
        directory = self.settings.get("default_venv_dir", "")
        self.set_status(f"Scanning {directory} ...")

        def work():
            venvs = []
            if directory and os.path.isdir(directory):
                for item in sorted(os.listdir(directory)):
                    full = os.path.join(directory, item)
                    if Backend.is_venv(full):
                        venvs.append({
                            "name": item,
                            "path": full,
                            "python": Backend.venv_python_version(full),
                            "size": dir_size(full),
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
        self.venv_table.resizeColumnsToContents()
        self._rebuild_recent_menu()
        self.update_recent_buttons()

    def apply_env_filter(self, text):
        term = text.strip().lower()
        for row in range(self.venv_table.rowCount()):
            item = self.venv_table.item(row, 0)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            haystack = " ".join(str(v) for v in (
                data.get("name", ""), data.get("python", ""),
                data.get("path", ""))).lower()
            self.venv_table.setRowHidden(row, bool(term) and term not in haystack)

    def sort_env_table(self, column):
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
        self.set_status(tr("status_working"), 5)

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
            self.log(f"{tr('venv_created')}: {path}")
            self.set_status(f"{tr('venv_created')}: {os.path.basename(path)}", 100)
            self.add_recent(os.path.dirname(path))
            self.reload_venvs()
            self.refresh_dashboard()

        self.run_task(work, done, lambda msg: QMessageBox.critical(self, APP_NAME, msg))

    def action_activate_venv(self):
        path = self.selected_env_path()
        if not path:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
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
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        if self.settings.get("confirm_destructive", True):
            size_str = ""
            rows = self.venv_table.selectionModel().selectedRows()
            if rows:
                size_item = self.venv_table.item(rows[0].row(), 3)
                if size_item and size_item.text():
                    size_str = f"Size: {size_item.text()}\n"
            answer = QMessageBox.question(
                self, APP_NAME,
                f"{tr('confirm_delete')}\n\n{path}\n\n"
                f"{size_str}"
                f"{tr('confirm_delete_hint')}")
            if answer != QMessageBox.StandardButton.Yes:
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
            self.log(f"{tr('venv_deleted')}: {deleted_path}")
            self.set_status(tr("venv_deleted"))
            if self._active_venv == deleted_path:
                self.action_deactivate_venv()
            self.reload_venvs()
            self.refresh_dashboard()

        def failed(err):
            self.log(f"ERROR: Delete failed: {err}")
            QMessageBox.critical(self, APP_NAME, f"Delete failed:\n{err}")

        self.run_task(work, done, failed)

    def action_clone_venv(self):
        path = self.selected_env_path()
        if not path:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
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
                      lambda m: QMessageBox.critical(self, APP_NAME, m))

    def action_rename_venv(self):
        path = self.selected_env_path()
        if not path:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, APP_NAME, "New name:", text=old_name)
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return
        new_path = os.path.join(os.path.dirname(path), new_name.strip())
        if os.path.exists(new_path):
            QMessageBox.warning(self, APP_NAME, f"A file or directory named '{new_name.strip()}' already exists.")
            return

        warn = QMessageBox.question(
            self, APP_NAME,
            f"Renaming a virtual environment folder will invalidate absolute paths inside "
            f"pre-installed executable scripts (e.g. pip.exe, pytest.exe).\n\n"
            f"Recommended: clone the environment under the new name and delete the "
            f"original (this rebuilds all launcher scripts).\n\n"
            f"Yes = Clone & Delete (recommended)\n"
            f"No = Hard rename anyway\n"
            f"Cancel = Abort",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes)
        if warn == QMessageBox.StandardButton.Cancel:
            return
        if warn == QMessageBox.StandardButton.Yes:
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
                          lambda m: QMessageBox.critical(self, APP_NAME, m))
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
            QMessageBox.critical(self, APP_NAME, f"Rename failed:\n{exc}")
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
        answer = QMessageBox.question(
            self, APP_NAME,
            f"Clone created successfully.\nDelete the original environment\n{old_path}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
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
                      lambda m: (QMessageBox.critical(self, APP_NAME, m),
                                 self.reload_venvs()))

    def action_compare_venvs(self):
        path = self.selected_env_path()
        if not path:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
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
            self.set_status(tr("status_done"))

        self.run_task(work, done)

    def action_health_check(self):
        path = self.selected_env_path()
        if not path:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
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
        QMessageBox.information(self, APP_NAME,
                                "No editor configured. Set one in Settings > Paths & tools.")

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
        menu.addAction(f"\u26A1 {tr('activate_venv')}", self.action_activate_venv)
        menu.addAction(f"\u23F9 {tr('deactivate_venv')}", self.action_deactivate_venv)
        menu.addSeparator()
        menu.addAction(f"\u2398 {tr('clone_venv')}", self.action_clone_venv)
        menu.addAction(f"\u270E {tr('rename_venv')}", self.action_rename_venv)
        menu.addAction(f"\U0001FA7A {tr('health_check')}", self.action_health_check)
        menu.addSeparator()
        menu.addAction(f"+ {tr('install_package')}", self.action_install_package)
        menu.addAction(f"\u2B06 {tr('upgrade_all')}", self.action_upgrade_all)
        menu.addAction(f"\u2913 {tr('export_requirements')}", self.action_export_requirements)
        menu.addSeparator()
        menu.addAction(f"\U0001F4C2 {tr('open_in_explorer')}", self.action_open_in_explorer)
        menu.addAction(f"\u2716 {tr('delete_venv')}", self.action_delete_venv)
        menu.exec(self.venv_table.viewport().mapToGlobal(pos))

    def pkg_context_menu(self, pos):
        if not self.pkg_table.selectionModel().selectedRows():
            return
        menu = QMenu(self)
        menu.addAction(f"\u2B06 {tr('upgrade_package')}", self.action_upgrade_package)
        menu.addAction(f"\u2139 {tr('show_package_info')}", self.action_package_info)
        menu.addAction(f"\U0001F50D {tr('search_pypi')}", self.action_search_pypi)
        menu.addSeparator()
        menu.addAction(f"\u2716 {tr('uninstall_package')}", self.action_uninstall_package)
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
                self.set_status(tr("status_done"))
            else:
                self.log(f"[FAILED] {description} exited with code {code}.")
                self.set_status(f"{description} failed (code {code})")
            self.load_packages(venv)
            self.refresh_dashboard()

        self.stream_command(cmd, on_line=on_line, on_done=on_done)

    def action_install_package(self):
        venv = self.selected_env_path()
        if not venv:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        text, ok = QInputDialog.getText(
            self, APP_NAME,
            "Package name(s) (multiple allowed, e.g. requests pytest or requests>=2.31.0):")
        if not ok or not text.strip():
            return
        try:
            pkgs = shlex.split(text.strip(), posix=not IS_WIN)
        except ValueError as exc:
            QMessageBox.warning(self, APP_NAME, f"Invalid package specification:\n{exc}")
            return
        self.pip_action(["install"] + pkgs, venv,
                        f"Installing {len(pkgs)} package(s)")

    def action_install_from_file(self):
        venv = self.selected_env_path()
        if not venv:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        path, _ = QFileDialog.getOpenFileName(
            self, tr("install_from_file"), "",
            "Distributions (*.whl *.tar.gz *.zip);;All files (*)")
        if path:
            self.pip_action(["install", path], venv,
                            f"Installing {os.path.basename(path)}")

    def action_bulk_install(self):
        venv = self.selected_env_path()
        if not venv:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        dlg = BulkInstallDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.packages:
            self.pip_action(["install"] + dlg.packages, venv,
                            f"Installing {len(dlg.packages)} package(s)")

    def action_uninstall_package(self):
        venv = self.selected_env_path()
        names = self.selected_packages()
        if not venv:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        if not names:
            QMessageBox.warning(self, APP_NAME, tr("no_pkg_selected"))
            return
        if self.settings.get("confirm_destructive", True):
            answer = QMessageBox.question(
                self, APP_NAME, "Uninstall the following package(s)?\n\n"
                + ", ".join(names))
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.pip_action(["uninstall", "-y"] + names, venv,
                        f"Uninstalling {len(names)} package(s)")

    def action_upgrade_package(self):
        venv = self.selected_env_path()
        names = self.selected_packages()
        if not venv or not names:
            QMessageBox.warning(self, APP_NAME, tr("no_pkg_selected"))
            return
        self.pip_action(["install", "--upgrade"] + names, venv,
                        f"Upgrading {len(names)} package(s)")

    def action_upgrade_all(self):
        venv = self.selected_env_path()
        if not venv:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        self.log("Collecting the list of outdated packages...")
        self.set_status("Upgrading all packages...")

        def work():
            outdated = self.backend.outdated(venv)
            return sorted(outdated.keys())

        def done(names):
            if not names:
                self.log("All packages are already up to date.")
                self.set_status(tr("status_done"))
                return
            self.log(f"Upgrading {len(names)} package(s): {', '.join(names)}")
            self.pip_action(["install", "--upgrade"] + names, venv,
                            f"Upgrading {len(names)} package(s)")

        self.run_task(work, done)

    def action_freeze_packages(self):
        venv = self.selected_env_path()
        if not venv:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        self._goto_tab("console")
        self.log("pip freeze output:")

        def work():
            return self.backend.freeze(venv)

        def done(text):
            for line in text.splitlines():
                self.log(line)
            self.set_status(tr("status_done"))

        self.run_task(work, done)

    def action_check_outdated(self):
        venv = self.selected_env_path()
        if not venv:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
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
            self.set_status(tr("status_done"))

        self.run_task(work, done)

    def action_package_info(self):
        venv = self.selected_env_path()
        names = self.selected_packages()
        if not venv or not names:
            QMessageBox.warning(self, APP_NAME, tr("no_pkg_selected"))
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
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
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
            self.set_status(tr("status_done"))

        self.run_task(work, done, lambda m: self.log(f"ERROR: {m}"))

    def action_pip_sync(self):
        venv = self.selected_env_path()
        if not venv:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
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
            self.set_status(tr("status_done"))
            self.load_packages(venv)

        self.run_task(work, run_done, lambda m: self.log(f"ERROR: {m}"))
    # ======================================================= EXPORT / IMPORT
    def action_export_requirements(self):
        venv = self.selected_env_path()
        if not venv:
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_requirements"), "requirements.txt",
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
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_pyproject"), "pyproject.toml",
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
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_conda"), "environment.yml",
            "YAML files (*.yml *.yaml);;All files (*)")
        if not path:
            return

        def work():
            name = os.path.basename(venv)
            python_version = Backend.venv_python_version(venv)
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
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
            return
        path, _ = QFileDialog.getOpenFileName(
            self, tr("import_requirements"), "",
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
            QMessageBox.warning(self, APP_NAME, tr("no_venv_selected"))
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
        self.log(f"pip          : {Backend.pip_version()}")
        self.log(f"Architecture : {platform.machine()}")
        self.log(f"Timezone     : {time.tzname[0]}")

    def action_detect_tools(self):
        self._goto_tab("console")
        self.log("Scanning the system PATH for relevant tools:")
        for name, path in Backend.tools():
            marker = "[OK] " if path else "[--] "
            self.log(f"  {marker} {name:<14} {path or 'not found'}")
        self.set_status(tr("status_done"))

    def action_detect_pythons(self):
        self._goto_tab("console")
        self.log("Detected Python interpreters:")

        def work():
            found = []
            for path in self.backend.find_all_pythons():
                found.append((path, Backend.python_version(path)))
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
            self.set_status(tr("status_done"))

        self.run_task(work, done)

    def action_thread_activity(self):
        alive = [t for t in threading.enumerate() if t.is_alive()]
        QMessageBox.information(
            self, tr("task_queue"),
            f"Active Python threads: {len(alive)}\n"
            f"Managed worker threads: {len(self._threads)}\n\n"
            + "\n".join(f"  - {t.name}" for t in alive[:15]))

    # ================================================================== CONSOLE
    def log(self, message):
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
            self, tr("save_log"), default_log,
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
        self.set_status(tr("status_working"))

        def on_done(code):
            self.set_status(f"Command finished with exit code {code}")

        self.stream_command(command, shell=True, on_done=on_done)

    def eventFilter(self, obj, event):
        """Provide Up/Down history navigation in the console command box."""
        if obj is self.cmd_edit and event.type() == event.Type.KeyPress:
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
            self, tr("script_path"), "", "Python scripts (*.py);;All files (*)")
        if path:
            self.script_path.setText(path)

    def run_script(self):
        script = self.script_path.text().strip()
        if not script:
            QMessageBox.warning(self, APP_NAME, "Choose a script to run first.")
            return
        if not os.path.exists(script):
            QMessageBox.warning(self, APP_NAME, "That script does not exist.")
            return

        venv = self.selected_env_path()
        python_exe = Backend.venv_python(venv) if venv else sys.executable
        try:
            args = shlex.split(self.script_args.text().strip(), posix=not IS_WIN)
        except ValueError as exc:
            QMessageBox.warning(self, APP_NAME, f"Invalid arguments:\n{exc}")
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
        if self._script_worker:
            self._script_worker.terminate()
            self.log("Script terminated by the user.")

    # ====================================================================== GIT
    def browse_git_repo(self):
        path = QFileDialog.getExistingDirectory(self, tr("repo_path"))
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
            self.git_status_label.setText(tr("git_not_installed"))
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
                tr("git_dirty") if dirty else tr("git_clean"))
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
            QMessageBox.warning(self, APP_NAME,
                                "Choose a git repository first.")
            return
        self.git_output.appendPlainText(f"$ git {' '.join(args)}")
        git = Backend.git_available()
        if not git:
            self.git_output.appendPlainText(tr("git_not_installed"))
            return

        def on_line(_stream, text):
            self.git_output.appendPlainText(text)

        def on_done(code):
            self.git_output.appendPlainText(f"(git exited with code {code})")
            self.refresh_git_info(repo)

        self.stream_command([git] + args, cwd=repo, on_line=on_line, on_done=on_done)
    # ========================================================= VIRTUAL DEVICES
    def vd_log_msg(self, message):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.vd_log.appendPlainText(f"[{stamp}] {message}")
        self.vd_log.verticalScrollBar().setValue(
            self.vd_log.verticalScrollBar().maximum())

    def vd_set_progress(self, value):
        self.vd_progress.setValue(int(value))

    def _vd_pick(self, line_edit, save):
        if save:
            path, _ = QFileDialog.getSaveFileName(
                self, tr("vd_image_path"), "", IMAGE_FILE_FILTER)
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, tr("vd_image_path"), "", IMAGE_FILE_FILTER)
        if path:
            line_edit.setText(path)

    def vd_browse_save(self):
        self._vd_pick(self.vd_image_path, True)

    def vd_browse_open(self):
        self._vd_pick(self.vd_mount_image, False)

    def vd_on_type_change(self, device_type):
        kind = device_type.lower()
        home = os.path.expanduser("~")
        if "720" in kind:
            self.vd_size.setValue(720)
            self.vd_fs.setCurrentText("FAT12")
            self.vd_image_path.setText(os.path.join(home, "floppy720.img"))
        elif "floppy" in kind:
            self.vd_size.setValue(1440)
            self.vd_fs.setCurrentText("FAT12")
            self.vd_image_path.setText(os.path.join(home, "floppy.img"))
        elif "bd" in kind or "blu" in kind:
            self.vd_size.setValue(25600)
            self.vd_fs.setCurrentText("UDF")
            self.vd_image_path.setText(os.path.join(home, "bluray.iso"))
        elif "dvd" in kind:
            self.vd_size.setValue(4480)
            self.vd_fs.setCurrentText("ISO 9660")
            self.vd_image_path.setText(os.path.join(home, "dvd.iso"))
        elif "cd" in kind:
            self.vd_size.setValue(700)
            self.vd_fs.setCurrentText("ISO 9660")
            self.vd_image_path.setText(os.path.join(home, "cdrom.iso"))
        elif "vmdk" in kind:
            self.vd_image_path.setText(os.path.join(home, "disk.vmdk"))
        elif "qcow2" in kind:
            self.vd_image_path.setText(os.path.join(home, "disk.qcow2"))
        elif "zip" in kind:
            self.vd_size.setValue(100)
            self.vd_fs.setCurrentText("FAT16")
        elif "mo disk" in kind:
            self.vd_size.setValue(230)
            self.vd_fs.setCurrentText("FAT16")
        elif "tape" in kind:
            self.vd_image_path.setText(os.path.join(home, "backup.tar"))
        elif "raw" in kind or "usb" in kind or "sd " in kind:
            self.vd_fs.setCurrentText("FAT32")
            self.vd_image_path.setText(os.path.join(home, "disk.img"))
        else:
            self.vd_image_path.setText(os.path.join(home, "disk.vhd"))

    def vd_check_deps(self):
        found, missing = [], []
        for module in ("pycdlib", "construct"):
            try:
                importlib.import_module(module)
                found.append(module)
            except ImportError:
                missing.append(module)
        if shutil.which("qemu-img"):
            found.append("qemu-img")
        else:
            missing.append("qemu-img")
        if missing:
            self.vd_deps_label.setText(
                f"missing: {', '.join(missing)}  |  found: "
                f"{', '.join(found) if found else 'none'}")
            self.vd_deps_label.setStyleSheet(f"color: {self._col['yellow']};")
        else:
            self.vd_deps_label.setText(tr("vd_deps_ok"))
            self.vd_deps_label.setStyleSheet(f"color: {self._col['green']};")
        return found, missing

    def vd_install_deps(self):
        self.vd_log_msg("Installing the optional Python dependencies "
                       "(pycdlib, construct, diskimage)...")

        def work():
            results = []
            for package in ("pycdlib", "construct", "diskimage"):
                proc = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True, text=True, timeout=600)
                results.append((package, proc.returncode))
            return results

        def done(results):
            for package, code in results:
                self.vd_log_msg(f"  {'installed' if code == 0 else 'failed'}: {package}")
            if not shutil.which("qemu-img"):
                self.vd_log_msg("qemu-img was not found. Install QEMU if you need "
                           "VMDK/QCOW2 conversion: https://www.qemu.org/download/")
            self.vd_check_deps()
            self.vd_log_msg("Dependency installation finished.")

        self.run_task(work, done)

    def vd_create_image(self):
        device = self.vd_type.currentText()
        path = self.vd_image_path.text().strip()
        size = self.vd_size.value()
        label = self.vd_label.text().strip() or "VDISK"
        if not path:
            QMessageBox.warning(self, APP_NAME, "Choose an image file path first.")
            return
        self.vd_log_msg(f"Creating {device} image: {path} ({size} MB)")
        self.vd_set_progress(5)

        def work():
            kind = device.lower()
            if any(token in kind for token in ("cd", "dvd", "bd", "iso")):
                return self._vd_write_iso(path, label, size)
            if "floppy" in kind or "fdd" in kind:
                return write_floppy_image(path, size, label)
            if "qcow2" in kind or "vmdk" in kind:
                return self._vd_qemu_create(path, "qcow2" if "qcow2" in kind else "vmdk", size)
            if "vhd" in kind:
                return write_vhd_footer_image(path, size)
            return write_sparse_raw_image(path, size)

        def done(_bytes_written):
            self.vd_set_progress(100)
            self.vd_log_msg(f"Image created: {path}")
            self.vd_refresh_list()
            QTimer.singleShot(1200, lambda: self.vd_set_progress(0))

        def failed(message):
            self.vd_set_progress(0)
            self.vd_log_msg(f"ERROR: {message}")
            QMessageBox.critical(self, APP_NAME, f"Could not create the image:\n{message}")

        self.run_task(work, done, failed)

    def _vd_write_iso(self, path, label, size_mb):
        """Create an ISO 9660 image, using pycdlib when it is available."""
        self.sig_vd_progress.emit(30)
        try:
            import pycdlib
            iso = pycdlib.PyCdlib()
            iso.new(interchange_level=1, joliet=3, rock_ridge="1.09",
                    vol_ident=label[:32])
            iso.write(path)
            iso.close()
            self.sig_vd_log.emit("  ISO structure written with pycdlib.")
            return os.path.getsize(path)
        except ImportError:
            self.sig_vd_log.emit("  pycdlib is not installed - writing a minimal "
                                 "ISO 9660 volume descriptor instead.")
            return write_iso_stub(path, label)

    def _vd_qemu_create(self, path, fmt, size_mb):
        qemu = shutil.which("qemu-img")
        if not qemu:
            self.sig_vd_log.emit("  qemu-img is not available - writing a raw image "
                                 "with the requested size instead.")
            return write_sparse_raw_image(path, size_mb)
        self.sig_vd_log.emit(f"  running: qemu-img create -f {fmt} {path} {size_mb}M")
        proc = subprocess.run([qemu, "create", "-f", fmt, path, f"{size_mb}M"],
                              capture_output=True, text=True, timeout=300, check=False)
        for line in (proc.stdout + proc.stderr).splitlines():
            self.sig_vd_log.emit(f"  {line}")
        if proc.returncode != 0:
            raise RuntimeError("qemu-img create failed")
        return os.path.getsize(path)

    def vd_verify_image(self):
        path = self.vd_image_path.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, APP_NAME, tr("vd_select_image"))
            return
        self.vd_log_msg(f"Verifying {path}")
        size = os.path.getsize(path)
        self.vd_log_msg(f"  size        : {size:,} bytes ({fmt_size(size)})")
        detected = detect_image_format(path)
        self.vd_log_msg(f"  format      : {detected}")

        def work():
            output = []
            qemu = shutil.which("qemu-img")
            if qemu:
                proc = subprocess.run([qemu, "check", path], capture_output=True,
                                      text=True, timeout=600)
                output = (proc.stdout + proc.stderr).splitlines()
                output.append(f"qemu-img check exit code: {proc.returncode}")
            return output

        def done(lines):
            for line in lines:
                self.vd_log_msg(f"  {line}")
            self.vd_log_msg("Verification finished.")

        self.run_task(work, done)

    def vd_image_info(self):
        path = self.vd_image_path.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, APP_NAME, tr("vd_select_image"))
            return
        stat = os.stat(path)
        self.vd_log_msg(f"Information for {path}")
        self.vd_log_msg(f"  size     : {stat.st_size:,} bytes ({fmt_size(stat.st_size)})")
        self.vd_log_msg(f"  modified : {datetime.datetime.fromtimestamp(stat.st_mtime)}")
        self.vd_log_msg(f"  created  : {datetime.datetime.fromtimestamp(stat.st_ctime)}")
        self.vd_log_msg(f"  format   : {detect_image_format(path)}")

        qemu = shutil.which("qemu-img")
        if qemu:
            def work():
                proc = subprocess.run([qemu, "info", "--output=human", path],
                                      capture_output=True, text=True, timeout=120)
                return (proc.stdout + proc.stderr).splitlines()

            def done(lines):
                for line in lines:
                    self.vd_log_msg(f"  {line}")

            self.run_task(work, done)

    def vd_refresh_list(self):
        self.vd_table.setRowCount(0)
        mounts = []

        if os.name == "posix" and os.path.exists("/proc/mounts"):
            try:
                with open("/proc/mounts", "r", encoding="utf-8",
                          errors="replace") as fh:
                    for line in fh:
                        parts = line.split()
                        if len(parts) >= 2 and "loop" in parts[0]:
                            mounts.append((parts[0], parts[1]))
            except OSError:
                pass

        for device, mount_point in mounts:
            row = self.vd_table.rowCount()
            self.vd_table.insertRow(row)
            self.vd_table.setItem(row, 0, QTableWidgetItem("loop"))
            self.vd_table.setItem(row, 1, QTableWidgetItem(device))
            self.vd_table.setItem(row, 2, QTableWidgetItem(mount_point))
            mounted = QTableWidgetItem("Mounted")
            mounted.setForeground(QBrush(QColor(self._col["green"])))
            self.vd_table.setItem(row, 3, mounted)
            self.vd_table.setItem(row, 4, QTableWidgetItem("-"))

        if not mounts:
            self.vd_log_msg("No loop-mounted images were found "
                           "(this list is populated when images are mounted "
                           "through this tab, or on Linux loop devices).")

    def vd_mount(self):
        path = self.vd_mount_image.text().strip()
        mount_point = self.vd_mount_point.text().strip()
        filesystem = self.vd_mount_fs.currentText()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, APP_NAME, tr("vd_select_image"))
            return
        self.vd_log_msg(f"Mounting {path} at {mount_point}")

        def work():
            if os.name == "posix":
                os.makedirs(mount_point, exist_ok=True)
                options = "loop,ro" if self.vd_readonly_cb.isChecked() else "loop"
                cmd = ["mount", "-o", options, path, mount_point]
                if filesystem != "auto":
                    cmd = ["mount", "-t", filesystem, "-o", options,
                           path, mount_point]
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      timeout=120)
                return proc.returncode == 0, (proc.stdout + proc.stderr).splitlines()
            return True, ["Windows and macOS require an elevated session. "
                          "Use the following command in an administrator shell:",
                          f'  Mount-DiskImage -ImagePath "{path}"']

        def done(result):
            ok, lines = result
            for line in lines:
                self.vd_log_msg(f"  {line}")
            if ok:
                row = self.vd_table.rowCount()
                self.vd_table.insertRow(row)
                self.vd_table.setItem(row, 0, QTableWidgetItem(filesystem))
                self.vd_table.setItem(row, 1, QTableWidgetItem(os.path.basename(path)))
                self.vd_table.setItem(row, 2, QTableWidgetItem(mount_point))
                mounted = QTableWidgetItem("Mounted")
                mounted.setForeground(QBrush(QColor(self._col["green"])))
                self.vd_table.setItem(row, 3, mounted)
                self.vd_table.setItem(row, 4,
                                      QTableWidgetItem(fmt_size(os.path.getsize(path))))
                self.vd_log_msg("Mount command completed.")
            else:
                self.vd_log_msg("Mounting failed. On Linux this needs root privileges.")

        self.run_task(work, done)

    def vd_unmount(self):
        path = self.vd_mount_image.text().strip()
        mount_point = self.vd_mount_point.text().strip()
        self.vd_log_msg(f"Unmounting {mount_point}")
        if os.name != "posix":
            self.vd_log_msg('  Run in an administrator shell: '
                           f'Dismount-DiskImage -ImagePath "{path}"')
            return

        def work():
            proc = subprocess.run(["umount", mount_point], capture_output=True,
                                  text=True, timeout=120)
            return (proc.stdout + proc.stderr).splitlines()

        def done(lines):
            for line in lines:
                self.vd_log_msg(f"  {line}")
            self.vd_refresh_list()

        self.run_task(work, done)

    def vd_extract_iso(self):
        path = self.vd_mount_image.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, APP_NAME, tr("vd_select_image"))
            return
        destination = QFileDialog.getExistingDirectory(self, "Extract to folder")
        if not destination:
            return
        self.vd_log_msg(f"Extracting {os.path.basename(path)} to {destination}")

        def work():
            try:
                import pycdlib
            except ImportError as exc:
                raise RuntimeError(
                    "pycdlib is required to extract an ISO image. "
                    "Use 'Install Python dependencies' first.") from exc
            iso = pycdlib.PyCdlib()
            iso.open(path)
            count = 0
            for dirpath, _dirs, files in iso.walk(joliet_path="/"):
                for filename in files:
                    out_dir = os.path.join(destination, dirpath.lstrip("/"))
                    os.makedirs(out_dir, exist_ok=True)
                    iso.get_file_from_iso(
                        joliet_path=f"{dirpath.rstrip('/')}/{filename}",
                        local_path=os.path.join(out_dir, filename))
                    count += 1
            iso.close()
            return count

        def done(count):
            self.vd_log_msg(f"Extracted {count} file(s) to {destination}")

        self.run_task(work, done,
                      lambda m: (self.vd_log_msg(f"ERROR: {m}"),
                                 QMessageBox.critical(self, APP_NAME, m)))

    def vd_make_iso(self):
        source = QFileDialog.getExistingDirectory(self, "Choose the folder to pack")
        if not source:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, tr("vd_make_iso"), "image.iso", "ISO images (*.iso)")
        if not destination:
            return
        label = self.vd_label.text().strip() or "CDROM"
        self.vd_log_msg(f"Building an ISO image from {source}")

        def work():
            try:
                import pycdlib
            except ImportError as exc:
                raise RuntimeError(
                    "pycdlib is required to build an ISO image. "
                    "Use 'Install Python dependencies' first.") from exc
            iso = pycdlib.PyCdlib()
            iso.new(interchange_level=4, joliet=3, rock_ridge="1.09",
                    vol_ident=label[:32])
            added = 0
            for root, _dirs, files in os.walk(source):
                relative = os.path.relpath(root, source)
                iso_dir = "/" if relative == "." else "/" + relative.replace("\\", "/")
                if iso_dir != "/":
                    try:
                        iso.add_directory(joliet_path=iso_dir, rr_name="dir")
                    except Exception:                   # noqa: BLE001
                        pass
                for filename in files:
                    iso_path = iso_dir.rstrip("/") + "/" + filename
                    try:
                        iso.add_file(os.path.join(root, filename),
                                     joliet_path=iso_path, rr_name=filename)
                        added += 1
                    except Exception as exc:            # noqa: BLE001
                        print(f"[ISO] {filename}: {exc}")
            iso.write(destination)
            iso.close()
            return added

        def done(added):
            self.vd_log_msg(f"ISO image written to {destination} "
                           f"with {added} file(s).")

        self.run_task(work, done,
                      lambda m: (self.vd_log_msg(f"ERROR: {m}"),
                                 QMessageBox.critical(self, APP_NAME, m)))

    def vd_convert(self):
        source = self.vd_convert_src.text().strip()
        target = self.vd_convert_dst.text().strip()
        output_format = self.vd_convert_fmt.currentText()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, APP_NAME, "Choose a valid source image.")
            return
        if not target:
            QMessageBox.warning(self, APP_NAME, "Choose a target file name.")
            return
        qemu = shutil.which("qemu-img")
        if not qemu:
            QMessageBox.warning(
                self, APP_NAME,
                "qemu-img is required to convert between image formats.\n"
                "Install QEMU and make sure qemu-img is on your PATH.")
            return
        self.vd_log_msg(f"Converting to {output_format.upper()}: {target}")

        def work():
            proc = subprocess.run(
                [qemu, "convert", "-O", output_format, source, target],
                capture_output=True, text=True, timeout=3600)
            return proc.returncode, (proc.stdout + proc.stderr).splitlines()

        def done(result):
            code, lines = result
            for line in lines:
                self.vd_log_msg(f"  {line}")
            if code == 0:
                self.vd_log_msg(f"Conversion finished: {target}")
                self.vd_refresh_list()
            else:
                self.vd_log_msg("Conversion failed.")

        self.run_task(work, done)

    def vd_format_image(self):
        path = self.vd_format_path.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, APP_NAME, tr("vd_select_image"))
            return
        filesystem = self.vd_format_fs.currentText()
        answer = QMessageBox.warning(
            self, APP_NAME,
            f"Format the image as {filesystem}?\n\n"
            "Every file inside the image will be destroyed.\n\n"
            f"Image: {path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.vd_log_msg(f"Formatting {os.path.basename(path)} as {filesystem}")

        def work():
            if os.name != "posix":
                return None
            commands = {
                "FAT12": ["mkfs.fat", "-F", "12", path],
                "FAT16": ["mkfs.fat", "-F", "16", path],
                "FAT32": ["mkfs.fat", "-F", "32", path],
                "exFAT": ["mkfs.exfat", path],
                "NTFS":  ["mkntfs", "-f", path],
                "ext4":  ["mkfs.ext4", "-F", path],
            }
            cmd = commands.get(filesystem)
            if not cmd or not shutil.which(cmd[0]):
                raise RuntimeError(f"{filesystem} formatting tools are not installed")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            return (proc.stdout + proc.stderr).splitlines()

        def done(lines):
            if lines is None:
                self.vd_log_msg("On Windows and macOS, format disk images with the "
                            "native disk management tools.")
                return
            for line in lines:
                self.vd_log_msg(f"  {line}")
            self.vd_log_msg("Formatting finished.")

        self.run_task(work, done, lambda m: self.vd_log_msg(f"ERROR: {m}"))

    def vd_write_mbr(self):
        path = self.vd_format_path.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, APP_NAME, tr("vd_select_image"))
            return
        if os.path.getsize(path) < 512:
            QMessageBox.warning(self, APP_NAME,
                                "The image is too small to hold a boot sector.")
            return
        try:
            mbr = bytearray(512)
            mbr[446] = 0x80                     # first partition is bootable
            mbr[450] = 0x0C                     # partition type: FAT32 LBA
            mbr[454] = 0x01                     # start LBA = 1
            mbr[510] = 0x55
            mbr[511] = 0xAA
            with open(path, "r+b") as fh:
                fh.write(bytes(mbr))
            self.vd_log_msg(f"A generic boot sector was written to "
                        f"{os.path.basename(path)}.")
        except Exception as exc:                        # noqa: BLE001
            self.vd_log_msg(f"ERROR: {exc}")

    def vd_check_filesystem(self):
        path = self.vd_format_path.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, APP_NAME, tr("vd_select_image"))
            return
        self.vd_log_msg(f"Checking the filesystem in {os.path.basename(path)}")
        if os.name != "posix":
            self.vd_log_msg("  On Windows use chkdsk against the mounted drive letter, "
                        "for example:  chkdsk V: /f")
            return

        def work():
            for candidate in (["fsck", "-n", path], ["e2fsck", "-n", path]):
                if shutil.which(candidate[0]):
                    proc = subprocess.run(candidate, capture_output=True,
                                          text=True, timeout=600)
                    return (proc.stdout + proc.stderr).splitlines()
            return ["No filesystem checking tool (fsck / e2fsck) was found."]

        def done(lines):
            for line in lines:
                self.vd_log_msg(f"  {line}")
            self.vd_log_msg("Filesystem check finished.")

        self.run_task(work, done)

    def vd_eject_selected(self):
        rows = self.vd_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, APP_NAME, "Select a device row first.")
            return
        row = rows[0].row()
        name = self.vd_table.item(row, 1).text() if self.vd_table.item(row, 1) else "?"
        self.vd_table.removeRow(row)
        self.vd_log_msg(f"Removed {name} from the device list.")

    def vd_copy_path(self):
        rows = self.vd_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        item = self.vd_table.item(row, 1)
        if item:
            QApplication.clipboard().setText(item.text())
            self.vd_log_msg(f"Copied '{item.text()}' to the clipboard.")

    def vd_context_menu(self, pos):
        rows = self.vd_table.selectionModel().selectedRows()
        if not rows:
            return
        menu = QMenu(self)
        menu.addAction("Eject / remove row", self.vd_eject_selected)
        menu.addAction("Copy image path", self.vd_copy_path)
        menu.addAction(tr("vd_info"), self.vd_image_info)
        menu.addAction(tr("vd_verify"), self.vd_verify_image)
        menu.exec(self.vd_table.viewport().mapToGlobal(pos))
    # ================================================================ DASHBOARD
    def refresh_dashboard(self):
        self.card_envs.set_value("...")
        self.card_pkgs.set_value("...")
        self.card_outdated.set_value("...")
        self.card_disk.set_value("...")

        def work():
            directory = self.settings.get("default_venv_dir", "")
            venvs = Backend.dashboard_venvs(directory)
            total_packages = 0
            disk = 0
            per_venv = []
            for venv in venvs:
                disk += dir_size(venv)
                count = self.backend.count_packages(venv)
                if count > 0:
                    total_packages += count
                per_venv.append((os.path.basename(venv), max(count, 0),
                                 Backend.venv_python_version(venv)))
            info_lines = [
                f"Operating system : {platform.system()} {platform.release()}",
                f"Machine          : {platform.machine()}",
                f"Python           : {sys.version.split()[0]}",
                f"Executable       : {sys.executable}",
                f"pip              : {Backend.pip_version()}",
                f"Environments dir : {directory}",
                f"Environments     : {len(venvs)}",
                f"Disk usage       : {fmt_size(disk)}",
                "",
                "Interpreters detected on this system:",
            ]
            for path in self.backend.find_all_pythons():
                info_lines.append(f"  Python {Backend.python_version(path):<8} {path}")
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
        if not hasattr(self, "chart_label"):
            if per_venv:
                top = sorted(per_venv, key=lambda item: item[1], reverse=True)[:8]
                maximum = max((item[1] for item in top), default=1) or 1
                lines = ["Package distribution per environment:", ""]
                for name, count, python_version in top:
                    bar = "\u2588" * max(1, int(count / maximum * 30)) if count else ""
                    lines.append(f"  {name[:22]:<22} {count:>5}  {bar}")
                self.card_outdated.set_value(
                    sum(1 for _n, c, _p in per_venv if c > 0))
                _ = python_version if False else None
                self._update_outdated_card()
                self.chart_text = "\n".join(lines)
            else:
                self.chart_text = ""
            return

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
            self.recent_layout.addWidget(QLabel(tr("dash_no_recent")))
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

    def open_recent(self, path):
        if not os.path.isdir(path):
            QMessageBox.warning(self, APP_NAME, f"That directory no longer exists:\n{path}")
            return
        self.settings["default_venv_dir"] = path
        save_settings(self.settings)
        self.reload_venvs()
        self.log(f"Working directory changed to {path}")

    # ================================================ FILE MENU / SETTINGS ACTS
    def action_new_project(self):
        path = QFileDialog.getExistingDirectory(self, "Choose a project directory")
        if path:
            self.settings["default_venv_dir"] = path
            save_settings(self.settings)
            self.add_recent(path)
            self.reload_venvs()
            self.refresh_dashboard()

    def action_open_project(self):
        self.action_new_project()

    def action_save_config(self):
        save_settings(self.settings)
        self.log(f"Configuration saved to {CONFIG_FILE}")
        self.set_status("Configuration saved")

    def action_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            theme_changed = dialog.settings.get("theme") != self.settings.get("theme")
            self.settings = dialog.settings
            self.backend.settings = self.settings
            save_settings(self.settings)
            self.apply_theme()
            if theme_changed:
                for action in self.theme_menu.actions():
                    action.setChecked(action.text() == self.settings["theme"])
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
        geometry = self.settings.get("window_geometry", "")
        if geometry and self.settings.get("save_window_pos", True):
            try:
                from PyQt6.QtCore import QByteArray
                if not self.restoreGeometry(QByteArray.fromHex(
                        geometry.encode("ascii"))):
                    self.resize(1360, 820)
            except Exception:                           # noqa: BLE001
                self.resize(1360, 820)
        else:
            self.resize(1360, 820)

    def closeEvent(self, event):
        try:
            if self.settings.get("save_window_pos", True):
                self.settings["window_geometry"] = bytes(
                    self.saveGeometry().toHex()).decode("ascii")
            self.settings["splitter_sizes"] = self.splitter.sizes()
            save_settings(self.settings)
        except Exception as exc:                        # noqa: BLE001
            print(f"[VEnv Manager] Could not save geometry: {exc}")

        # Stop timers
        if hasattr(self, "_auto_timer") and self._auto_timer.isActive():
            self._auto_timer.stop()
        if hasattr(self, "_clock_timer") and self._clock_timer.isActive():
            self._clock_timer.stop()

        # Terminate running subprocess workers
        for worker in list(self._workers):
            if hasattr(worker, "terminate"):
                try:
                    worker.terminate()
                except Exception:
                    pass

        # Request quit and wait for active QThreads
        for thread in list(self._threads):
            try:
                if thread.isRunning():
                    thread.quit()
                    thread.wait(600)
            except Exception:
                pass

        super().closeEvent(event)


# ==============================================================================
#  ENTRY POINT
# ==============================================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_COMPANY)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
