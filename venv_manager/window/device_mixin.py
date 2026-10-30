#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Virtual device (disk image) tab actions."""

import sys
import os
import json
import shutil
import threading
import subprocess
import webbrowser
import datetime
import importlib

import stat

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtCore import QTimer, Qt, QByteArray
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
    DEFAULT_SETTINGS, tr, THEMES, fmt_size, dir_size,
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


class DeviceMixin:
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
                self, trl("vd_image_path"), "", IMAGE_FILE_FILTER)
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, trl("vd_image_path"), "", IMAGE_FILE_FILTER)
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
            self.vd_deps_label.setText(trl("vd_deps_ok"))
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
            warn("Choose an image file path first.")
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
            info(f"Could not create the image:\n{message}")

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
            warn(trl("vd_select_image"))
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
            warn(trl("vd_select_image"))
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
            warn(trl("vd_select_image"))
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
            warn(trl("vd_select_image"))
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
                                 info(m)))

    def vd_make_iso(self):
        source = QFileDialog.getExistingDirectory(self, "Choose the folder to pack")
        if not source:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, trl("vd_make_iso"), "image.iso", "ISO images (*.iso)")
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
                                 info(m)))

    def vd_convert(self):
        source = self.vd_convert_src.text().strip()
        target = self.vd_convert_dst.text().strip()
        output_format = self.vd_convert_fmt.currentText()
        if not source or not os.path.exists(source):
            warn("Choose a valid source image.")
            return
        if not target:
            warn("Choose a target file name.")
            return
        qemu = shutil.which("qemu-img")
        if not qemu:
            warn("qemu-img is required to convert between image formats.\n" "Install QEMU and make sure qemu-img is on your PATH.")
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
            warn(trl("vd_select_image"))
            return
        filesystem = self.vd_format_fs.currentText()
        answer = warn(f"Format the image as {filesystem}?\n\n" "Every file inside the image will be destroyed.\n\n" f"Image: {path}")
        if answer != True:
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
            warn(trl("vd_select_image"))
            return
        if os.path.getsize(path) < 512:
            warn("The image is too small to hold a boot sector.")
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
            warn(trl("vd_select_image"))
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
            warn("Select a device row first.")
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
        menu.addAction(trl("vd_info"), self.vd_image_info)
        menu.addAction(trl("vd_verify"), self.vd_verify_image)
        menu.exec(self.vd_table.viewport().mapToGlobal(pos))
    # ================================================================ DASHBOARD

