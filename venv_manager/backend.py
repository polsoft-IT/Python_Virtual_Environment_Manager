#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Non-GUI backend: background workers, pip/git helpers and disk images.

Everything in this module talks to the operating system only; it never
imports widgets, so it can be exercised headlessly.
"""

import sys
import os
import json
import struct
import shutil
import signal
import uuid
import threading
import subprocess
import glob as _glob

from PyQt6.QtCore import QObject, pyqtSignal

from .config import IS_WIN, BIN_DIR, PY_EXE


def _new_group_args():
    """Popen kwargs that put the child in a killable group (Windows only)."""
    if not IS_WIN:
        return {}
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return {"creationflags": flags} if flags else {}


# ==============================================================================
#  BACKGROUND TASKS  (QThread so the GUI never blocks)
# ==============================================================================
class Worker(QObject):
    """Runs a callable in a worker thread and emits its result."""
    finished = pyqtSignal(object)
    failed   = pyqtSignal(str)

    def __init__(self, fn, *args, takes_worker=False, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._takes_worker = takes_worker
        self._cancelled = threading.Event()

    def cancel(self):
        """Ask the task to stop; long jobs can poll ``is_cancelled()``."""
        self._cancelled.set()

    def is_cancelled(self):
        return self._cancelled.is_set()

    def stop(self, timeout_ms=1500):
        """Cancel the task and suppress its result signal."""
        self.cancel()
        return True

    def run(self):
        try:
            if self._takes_worker:
                result = self._fn(self, *self._args, **self._kwargs)
            else:
                result = self._fn(*self._args, **self._kwargs)
            if not self._cancelled.is_set():
                self.finished.emit(result)
        except Exception as exc:                        # noqa: BLE001
            if not self._cancelled.is_set():
                self.failed.emit(str(exc))


class StreamWorker(QObject):
    """Runs a subprocess and streams its output lines as they arrive.

    The child is started in its own process group/session so ``stop()`` can
    tear down the whole tree - pip and pytest routinely spawn grandchildren
    that would otherwise keep running after the window closes.
    """
    line     = pyqtSignal(str, str)   # (stream_name, text_line)
    done     = pyqtSignal(int)        # return code
    failed   = pyqtSignal(str)

    def __init__(self, cmd, cwd=None, shell=False, env=None):
        super().__init__()
        self._cmd = cmd
        self._cwd = cwd
        self._shell = shell
        self._env = env
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self.proc = None

    def run(self):
        try:
            self.proc = subprocess.Popen(
                self._cmd, cwd=self._cwd, shell=self._shell, env=self._env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                start_new_session=True, **_new_group_args())
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
        if not self._stopped.is_set():
            self.done.emit(code)

    # ------------------------------------------------------------- shutdown
    def _signal_group(self, sig):
        """Send ``sig`` to the child's whole process group when possible."""
        with self._lock:
            proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        if IS_WIN:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except OSError:
            try:
                proc.send_signal(sig)
            except OSError:
                pass

    def terminate(self):
        """Backwards-compatible alias for :meth:`stop`."""
        return self.stop()

    def stop(self, timeout_ms=1500):
        """Kill the child tree and return True once it has really exited."""
        self._stopped.set()
        with self._lock:
            proc = self.proc
        if proc is None or proc.poll() is not None:
            return True

        self._signal_group(getattr(signal, "SIGTERM", None))
        try:
            proc.wait(timeout=max(timeout_ms, 0) / 1000.0)
            return True
        except subprocess.TimeoutExpired:
            pass

        self._signal_group(getattr(signal, "SIGKILL", None))
        try:
            proc.wait(timeout=1.0)
            return True
        except subprocess.TimeoutExpired:
            return proc.poll() is not None


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
        self._cancel = None
        self._probe_cap = None
        self._probes = set()
        self._probes_lock = threading.Lock()

    # ---------------- interpreters ----------------
    def find_all_pythons(self):
        found = []

        def add(path):
            path = os.path.normpath(path)
            if path not in found and os.path.isfile(path):
                found.append(path)

        if self.cancelled:
            return [sys.executable]

        # One PATH walk instead of ~28 ``shutil.which`` scans, so startup and
        # cancellation stay fast even with a long PATH.
        dirs = {os.getcwd()}
        dirs.update(os.environ.get("PATH", "").split(os.pathsep))
        for folder in dirs:
            if self.cancelled:
                return [sys.executable]
            if not folder or not os.path.isdir(folder):
                continue
            try:
                entries = os.listdir(folder)
            except OSError:
                continue
            for entry in entries:
                low = entry.lower()
                if not low.startswith("python3") and low not in (
                        "python", "python.exe", "py", "py.exe"):
                    continue
                if "." in low and not low.endswith(".exe"):
                    continue                        # skip shim targets / ._pth
                if low.endswith("-config"):
                    continue
                add(os.path.join(folder, entry))

        pyenv_root = os.environ.get("PYENV_ROOT", os.path.expanduser("~/.pyenv"))
        for py in _glob.glob(os.path.join(pyenv_root, "versions", "*", "bin", "python*")):
            if not py.endswith(("-config", "m")):
                add(py)

        if self.cancelled:
            add(sys.executable)
            return found[:16]

        conda_exe = shutil.which("conda") or shutil.which("conda.exe")
        if conda_exe and not self.cancelled:
            try:
                out = subprocess.run([conda_exe, "info", "--envs", "--json"],
                                     capture_output=True, text=True,
                                     timeout=self._bounded_timeout(10))
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
            for base in (r"C:\Python3*", r"C:\Program Files\Python3*",
                         os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                      "Programs", "Python", "Python3*")):
                for d in _glob.glob(base):
                    cand = os.path.join(d, "python.exe")
                    if os.path.isfile(cand):
                        add(cand)

        add(sys.executable)
        return found[:16]

    def python_version(self, python_exe):
        try:
            r = self._probe([python_exe, "--version"], 5)
            if r is None:
                return "?"
            return (r.stdout + r.stderr).strip().split()[-1]
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

    def venv_python_version(self, venv):
        return self.python_version(Backend.venv_python(venv))

    def pip_version(self):
        """pip version via a killable probe (falls back to '?' on shutdown)."""
        try:
            r = self._probe([sys.executable, "-m", "pip", "--version"], 8)
            if r is None or r.returncode != 0:
                return "?"
            parts = r.stdout.split()
            return parts[1] if len(parts) > 1 else "?"
        except Exception:                               # noqa: BLE001
            return "?"

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

    def set_cancel_event(self, event):
        """Attach a ``threading.Event`` that aborts long pip probes."""
        self._cancel = event

    @property
    def cancelled(self):
        event = getattr(self, "_cancel", None)
        return bool(event is not None and event.is_set())

    def start_shutdown_probe(self, timeout=1.5):
        """Cap the timeout of subsequent probes so closing cannot block long."""
        self._probe_cap = timeout

    def end_shutdown_probe(self):
        self._probe_cap = None

    def _bounded_timeout(self, timeout):
        """Keep a probe short while the window is shutting down."""
        cap = getattr(self, "_probe_cap", None)
        if cap is not None:
            return min(timeout, cap)
        return min(timeout, 8) if self.cancelled else timeout

    def _probe(self, cmd, timeout):
        """Run a short read-only command that shutdown can kill immediately.

        Tracks live probes so ``kill_probes()`` can terminate them; returns the
        completed process or None when the probe had to be abandoned.
        """
        if self.cancelled:
            return None
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace")
        with self._probes_lock:
            self._probes.add(proc)
        try:
            out, err = proc.communicate(timeout=self._bounded_timeout(timeout))
            return subprocess.CompletedProcess(cmd, proc.returncode, out, err)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.communicate(timeout=1)
            except Exception:                           # noqa: BLE001
                pass
            return None
        finally:
            with self._probes_lock:
                self._probes.discard(proc)

    def kill_probes(self):
        """Kill every pip probe still running (used by the shutdown path)."""
        with self._probes_lock:
            live = list(self._probes)
        for proc in live:
            try:
                proc.kill()
            except OSError:
                pass
        return len(live)

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
        if self.cancelled:
            return -1
        try:
            r = self._probe(self.pip_cmd(venv) + ["list", "--format=freeze"], 30)
            if r is None:
                return -1
            return sum(1 for line in r.stdout.splitlines() if "==" in line)
        except Exception:                               # noqa: BLE001
            return -1

    def list_packages(self, venv):
        """Return [(name, version), ...] for a venv."""
        out = []
        try:
            r = self._probe(self.pip_cmd(venv) + ["list", "--format=freeze"], 60)
            if r is None:
                return out
            for line in r.stdout.splitlines():
                if "==" in line:
                    name, _, ver = line.partition("==")
                    out.append((name.strip(), ver.strip()))
        except Exception:                               # noqa: BLE001
            pass
        return out

    def freeze(self, venv):
        try:
            r = self._probe(self.pip_cmd(venv) + ["freeze"], 60)
            return r.stdout if r is not None else ""
        except Exception:                               # noqa: BLE001
            return ""

    def outdated(self, venv):
        """Return {package_lower: latest_version}."""
        result = {}
        try:
            r = self._probe(self.pip_cmd(venv)
                            + ["list", "--outdated", "--format=columns"], 120)
            if r is None:
                return result
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
            ok.append(f"Python executable: {self.python_version(py)}")
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
