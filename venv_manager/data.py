#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static text shown by the terminal guide and the virtual device tab."""

import os

from .config import IS_WIN


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

