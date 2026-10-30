#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings, theming and localisation helpers ("config" layer).

Holds the platform constants, the English translation table, the colour
themes, the stylesheet builder and the load/save logic for the JSON config
file kept in the user application-data directory.
"""

import sys
import os
import json
import logging
import logging.handlers
import shutil
import platform

APP_NAME    = "VEnv Manager"
APP_VERSION = "3.0.0"
APP_BUILD   = "2026.03.05"
APP_AUTHOR  = "Sebastian Januchowski"
APP_COMPANY = "polsoft.ITS(TM) Group"
APP_EMAIL   = "polsoft.its@mail.com"
APP_GITHUB  = "https://github.com/polsoft-it"
APP_COPY    = "(c) 2026 Sebastian Januchowski & polsoft.ITS(TM). All rights reserved."

# Default window size, used when no saved geometry can be restored.
DEFAULT_WINDOW_SIZE = (1360, 820)

# ==============================================================================
#  PLATFORM FLAGS AND HELPER PATHS
# ==============================================================================
IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

BIN_DIR = "Scripts" if IS_WIN else "bin"
PY_EXE  = "python.exe" if IS_WIN else "python"
PIP_EXE = "pip.exe" if IS_WIN else "pip"


# ==============================================================================
#  APPLICATION LOGGER  (console mirror + rotating file next to the config)
# ==============================================================================
def get_logger():
    """Return the shared application logger, configured on first use.

    Messages go to ``venv_manager.log`` in the application-data directory so a
    failure during shutdown (when the GUI console may already be gone) still
    leaves a trace. Setup failures are ignored - logging must never crash.
    """
    logger = logging.getLogger("venv_manager")
    if getattr(logger, "_venv_configured", False):
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s",
                            "%Y-%m-%d %H:%M:%S")
    try:
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(APP_DATA_DIR, "venv_manager.log"),
            maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    except (OSError, ValueError):
        logger.addHandler(logging.NullHandler())
    logger._venv_configured = True
    return logger


def fmt_size(b):
    """Human readable file size."""
    b = float(b)
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def dir_size(path, should_stop=None):
    """Total size of a tree; ``should_stop()`` aborts early during shutdown."""
    total = 0
    try:
        for dirpath, _dirs, filenames in os.walk(path):
            if should_stop is not None and should_stop():
                break
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
    "dash_dash": "Disk usage",
    "dash_chart": "Package distribution",
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


def merge_settings(values=None):
    """Return a settings dict that always contains every required key.

    ``values`` (a loaded file or a value returned by a dialog) is layered over
    :data:`DEFAULT_SETTINGS`; unknown or broken entries fall back to defaults so
    callers may index keys such as ``settings["theme"]`` safely.
    """
    merged = dict(DEFAULT_SETTINGS)
    merged["recent_projects"] = []
    merged["splitter_sizes"] = list(DEFAULT_SETTINGS["splitter_sizes"])
    if not isinstance(values, dict):
        return _normalise_settings(merged)

    for key, default in DEFAULT_SETTINGS.items():
        if key not in values:
            continue
        value = values[key]
        if value is None:
            continue
        if isinstance(default, bool):
            merged[key] = bool(value)
        elif isinstance(default, int) and not isinstance(value, bool):
            try:
                merged[key] = int(value)
            except (TypeError, ValueError):
                pass
        elif isinstance(default, list):
            if isinstance(value, (list, tuple)):
                merged[key] = list(value)
        elif isinstance(default, str):
            if isinstance(value, str):
                merged[key] = value
        else:
            merged[key] = value

    # Keep any extra keys the config file carries (forward compatibility).
    for key, value in values.items():
        merged.setdefault(key, value)

    if merged.get("theme") not in THEMES:
        merged["theme"] = DEFAULT_THEME
    return _normalise_settings(merged)


def _normalise_settings(s):
    for key in ("python_path", "pip_path", "default_venv_dir",
                "editor_path", "terminal_path", "shell_path"):
        if s.get(key):
            s[key] = os.path.normpath(s[key])
    s["recent_projects"] = [os.path.normpath(p)
                            for p in s.get("recent_projects", [])
                            if isinstance(p, str)]
    try:
        sizes = [int(v) for v in s.get("splitter_sizes", [])]
        if len(sizes) != 2:
            raise ValueError
        s["splitter_sizes"] = sizes
    except (TypeError, ValueError):
        s["splitter_sizes"] = list(DEFAULT_SETTINGS["splitter_sizes"])
    return s


def load_settings():
    raw = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                raw = loaded
        except Exception as exc:                       # noqa: BLE001
            print(f"[VEnv Manager] Could not read config: {exc}")
    return merge_settings(raw)


def save_settings(settings):
    """Persist a complete settings dict, filling any missing key with defaults."""
    merged = merge_settings(settings)
    try:
        temp_file = CONFIG_FILE + f".tmp.{os.getpid()}"
        with open(temp_file, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, indent=2, ensure_ascii=False)
        os.replace(temp_file, CONFIG_FILE)
        # Keep the caller's dict in sync with what was written.
        if isinstance(settings, dict):
            settings.clear()
            settings.update(merged)
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
