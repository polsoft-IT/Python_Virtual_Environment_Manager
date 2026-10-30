#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin UI façade used by the window mixins.

Dialogs are handled by :class:`Dialogs` when a main window is attached (real
GUI) and by :class:`HeadlessDialogs` otherwise (tests, CLI usage), so the whole
action layer can be exercised without a display server.
"""

import builtins

from PyQt6.QtWidgets import QInputDialog, QMessageBox

from .config import APP_NAME, tr


class Dialogs:
    """Real GUI prompts - every dialog knows its parent window."""

    _window = None

    @classmethod
    def attach(cls, window):
        cls._window = window

    @classmethod
    def detach(cls):
        cls._window = None

    @classmethod
    def info(cls, title, text):
        print(text)
        if cls._window is not None:
            QMessageBox.information(cls._window, title, text)

    @classmethod
    def warn(cls, title, text):
        print(text)
        if cls._window is not None:
            QMessageBox.warning(cls._window, title, text)

    @classmethod
    def ask(cls, title, text):
        return cls._window is None or QMessageBox.question(
            cls._window, title, text) == QMessageBox.StandardButton.Yes

    @classmethod
    def ask_text(cls, title, label):
        if cls._window is None:
            return "", False
        return QInputDialog.getText(cls._window, title, label)


class HeadlessDialogs(Dialogs):
    """Non-interactive answers used when no window is attached."""

    @classmethod
    def ask(cls, title, text):
        return True


def trl(text):
    """Translate a key, falling back to the key itself when it is unknown."""
    return tr(text)


def show_(name, window, *args):
    """Console line routed to the window log when one is attached."""
    print(f"[{name}] " + " ".join(str(a) for a in args))
    signal = getattr(window, "sig_log", None)
    if signal is not None:
        signal.emit(" ".join(str(a) for a in args))


def confirm(text):
    return Dialogs.ask(APP_NAME, text)


def warn(text):
    Dialogs.warn(APP_NAME, text)


def info(text):
    Dialogs.info(APP_NAME, text)


def write(path, data):
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)


def progress(window, value):
    signal = getattr(window, "sig_vd_progress", None)
    if signal is not None:
        signal.emit(int(value))


def done(_path, text):
    print(text)
    return True


_builtin_print = builtins.print
