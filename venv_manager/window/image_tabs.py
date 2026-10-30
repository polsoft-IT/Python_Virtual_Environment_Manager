#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Virtual device tab (disk images) and the terminal guide tab (builders only)."""

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit,
    QComboBox, QSpinBox, QCheckBox, QTableWidget, QPlainTextEdit,
    QGroupBox, QScrollArea, QHeaderView, QAbstractItemView, QFileDialog,
    QSplitter, QProgressBar, QTabWidget, QGridLayout, QFormLayout,
)

from ..config import tr, IS_WIN, theme, DEFAULT_THEME
from ..data import DEVICE_TYPES, TERMINAL_GUIDE
from ..widgets import mono_font



class ImageTabsMixin:
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
