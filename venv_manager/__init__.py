#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Virtual Environment Manager - PyQt6 edition, split into layers.

Layout
------
``config``    platform flags, translations, themes, QSS and settings storage
``backend``   Worker/StreamWorker, Backend (pip/git/venv) and disk-image writers
``dialogs``   modal dialogs (create venv, settings, templates, about, ...)
``widgets``   small reusable widgets, drawing helpers and the tab PageBook
``data``      static terminal guide text and device-type lists
``uikit``     dialog façade so actions work with or without a window attached
``window``    MainWindow assembled from :class:`WindowCore` plus smaller mixins
"""

__version__ = "3.0.0"
