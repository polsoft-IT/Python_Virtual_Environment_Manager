#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main window assembled from focused mixins.

``core``              window shell: menu, layout, status bar, threads, theme
``interactive_tabs``  dashboard / packages / console / script / git page builders
``image_tabs``        virtual device and guide page builders
``environment_mixin`` environment listing and venv actions
``package_mixin``     package, console, script-runner and git actions
``device_mixin``      disk image actions
``dashboard_mixin``   dashboard, recent projects, settings, window lifecycle
"""

from PyQt6.QtWidgets import QMainWindow

from ..config import tr
from ..dialogs import (
    CreateVenvDialog, BulkInstallDialog, TemplatesDialog, AboutDialog,
    ShortcutsDialog, PackageInfoDialog,
)

from .core import WindowCore
from .interactive_tabs import InteractiveTabsMixin
from .image_tabs import ImageTabsMixin
from .environment_mixin import EnvironmentMixin
from .package_mixin import PackageMixin
from .device_mixin import DeviceMixin
from .dashboard_mixin import DashboardMixin

__all__ = ["MainWindow"]


class MainWindow(WindowCore, InteractiveTabsMixin, ImageTabsMixin,
                 EnvironmentMixin, PackageMixin, DeviceMixin, DashboardMixin,
                 QMainWindow):
    """The application window: shell from WindowCore, behaviour from mixins."""

    TAB_TITLES = (
        ("dashboard", "tab_dashboard"),
        ("packages", "tab_packages"),
        ("console", "tab_console"),
        ("script", "tab_script"),
        ("git", "tab_git"),
        ("devices", "tab_device"),
        ("guide", "tab_guide"),
    )

    def _build_tabs(self):
        """Build every page once and register it with the PageBook."""
        from PyQt6.QtWidgets import QTabWidget

        builders = {
            "dashboard": self._tab_dashboard,
            "packages": self._tab_packages,
            "console": self._tab_console,
            "script": self._tab_script,
            "git": self._tab_git,
            "devices": self._tab_devices,
            "guide": self._tab_guide,
        }
        self.tabs = QTabWidget()
        for key, title_key in self.TAB_TITLES:
            page = builders[key]()
            self.pages.add(key, page, tr(title_key))
            self.tabs.addTab(page, tr(title_key))
        return self.tabs
