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
  This file is the launcher. The application itself lives in the
  ``venv_manager`` package:

     venv_manager/config.py        flags, translations, themes, QSS, settings
     venv_manager/backend.py       workers, pip/git helpers, disk-image writers
     venv_manager/dialogs.py       create venv, settings, templates, about, ...
     venv_manager/widgets.py       small widgets, drawing helpers, PageBook
     venv_manager/data.py          terminal guide text and device types
     venv_manager/uikit.py         dialog façade (works with or without a GUI)
     venv_manager/window/          MainWindow shell + tab builders + action mixins

  Every public name of the old monolithic module is re-exported below, so
  ``from VEnv_Manager import MainWindow, Backend, load_settings, ...`` keeps
  working for existing scripts.
================================================================================
"""

import sys

try:
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
    )
except ImportError:
    sys.stderr.write(
        "PyQt6 is required.\n"
        "Install it with:  pip install PyQt6\n")
    raise

from venv_manager.config import (                     # noqa: F401
    APP_NAME, APP_VERSION, APP_BUILD, APP_AUTHOR, APP_COMPANY, APP_EMAIL,
    APP_GITHUB, APP_COPY, IS_WIN, IS_MAC, BIN_DIR, PY_EXE, PIP_EXE,
    BASE_DIR, APP_DATA_DIR, CONFIG_FILE, TEMPLATES_FILE,
    TRANSLATIONS, T, tr, THEMES, DEFAULT_THEME, theme, DEFAULT_SETTINGS,
    get_app_data_dir, load_settings, save_settings, build_stylesheet,
    merge_settings, fmt_size, dir_size, get_logger,
)
from venv_manager.backend import (                    # noqa: F401
    Worker, StreamWorker, Backend,
    write_floppy_image, write_vhd_footer_image, write_sparse_raw_image,
    write_iso_stub, detect_image_format,
)
from venv_manager.data import (                       # noqa: F401
    TERMINAL_GUIDE, DEVICE_TYPES, IMAGE_FILE_FILTER,
)
from venv_manager.widgets import (                    # noqa: F401
    make_dot, StatCard, status_item, mono_font, PageBook,
)
from venv_manager.dialogs import (                    # noqa: F401
    CreateVenvDialog, BulkInstallDialog, SettingsDialog, TemplatesDialog,
    AboutDialog, ShortcutsDialog, PackageInfoDialog,
)
from venv_manager.window import MainWindow            # noqa: F401


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
