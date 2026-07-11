#!/usr/bin/env python3
"""
EbookAlchemist-Portable
=======================
A fully offline, privacy-first desktop application for converting ebooks
between many formats (HTML, EPUB, MOBI, AZW3, PDF, FB2, TXT, DOCX, RTF, LIT,
PDB, and more).

Design goals
------------
* All-in-one: the released Windows executable bundles calibre's headless
  ebook-convert engine, so the end user does not need to install anything.
* Privacy: the application performs NO network access whatsoever. Files never
  leave the user machine. See SECURITY.md.
* Convenience: add individual files, whole folders (recursively including
  sub-folders), or drag-and-drop them onto the window.

The conversion engine
---------------------
Conversion is delegated to calibre ebook-convert command line tool, which is
the strongest open-source ebook conversion engine available and supports a
very wide range of input and output formats. The build workflow bundles this
engine next to the executable so no separate download is required at runtime.

This module locates ebook-convert using the following search order:
1. The EBOOK_CONVERT environment variable, if set.
2. A bundled copy shipped next to the frozen executable
   (calibre/ebook-convert.exe relative to the app), which is how the
   released build is packaged.
3. A copy found on the system PATH (useful for developers who already have
   calibre installed).
"""

from __future__ import annotations

import os
import sys
import queue
import shutil
import threading
import subprocess
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Optional drag-and-drop support. tkinterdnd2 provides real OS drag-and-drop.
# The app degrades gracefully to the file/folder pickers if it is unavailable.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    _DND_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _DND_AVAILABLE = False


APP_NAME = "EbookAlchemist"

# Recognised ebook input extensions (lower-case, without the leading dot).
INPUT_EXTENSIONS = {
    "azw", "azw3", "azw4", "cbz", "cbr", "cbc", "chm", "djvu", "docx",
    "epub", "fb2", "fbz", "html", "htmlz", "htm", "lit", "lrf", "mobi",
    "odt", "pdb", "pdf", "pml", "prc", "rb", "rtf", "snb", "tcr", "txt",
    "txtz",
}

# Output formats offered in the UI (calibre determines format from extension).
OUTPUT_FORMATS = [
    "epub", "mobi", "azw3", "pdf", "docx", "fb2", "htmlz", "lit",
    "lrf", "pdb", "rtf", "snb", "txt", "txtz", "oeb", "pml", "rb", "tcr",
]


def find_ebook_convert():
    """Locate the calibre ebook-convert executable.

    Returns the path as a string, or None if it cannot be found.
    """
    # 1. Explicit override.
    env = os.environ.get("EBOOK_CONVERT")
    if env and Path(env).exists():
        return env

    # 2. Bundled next to the (frozen) application.
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent

    exe_name = "ebook-convert.exe" if os.name == "nt" else "ebook-convert"
    for candidate in (
        base / "calibre" / exe_name,
        base / exe_name,
        base / "_internal" / "calibre" / exe_name,
    ):
        if candidate.exists():
            return str(candidate)

    # 3. On PATH.
    found = shutil.which("ebook-convert")
    if found:
        return found
    return None


def gather_ebooks(paths):
    """Expand a list of files/folders into a de-duplicated list of ebook files.

    Folders are walked recursively so that files in sub-folders are included.
    """
    collected = []
    seen = set()

    def add(p):
        rp = p.resolve()
        if rp in seen:
            return
        if rp.suffix.lower().lstrip(".") in INPUT_EXTENSIONS:
            seen.add(rp)
            collected.append(rp)

    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for child in p.rglob("*"):
                if child.is_file():
                    add(child)
        elif p.is_file():
            add(p)

    collected.sort(key=lambda x: str(x).lower())
    return collected


def convert_one(convert_exe, src, out_format, out_dir):
    """Convert a single ebook. Returns (success, message)."""
    target_dir = out_dir if out_dir is not None else src.parent
    target = target_dir / (src.stem + "." + out_format)

    # Never overwrite a file that would be identical to the source.
    if target.resolve() == src.resolve():
        return False, "Output would overwrite the source; skipped."

    cmd = [convert_exe, str(src), str(target)]
    try:
        # No shell; no network; strictly a local subprocess.
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
    except FileNotFoundError:
        return False, "ebook-convert engine not found."
    except Exception as exc:  # pragma: no cover - defensive
        return False, "Error: " + str(exc)

    if result.returncode == 0 and target.exists():
        return True, "-> " + target.name
    tail = (result.stdout or "").strip().splitlines()[-1:] or [""]
    return False, "Failed (" + str(result.returncode) + "): " + tail[0]


class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME + " - Portable Ebook Converter")
        self.root.geometry("760x560")
        self.root.minsize(640, 480)

        self.files = []
        self.log_queue = queue.Queue()
        self.convert_exe = find_ebook_convert()
        self.out_dir = None

        self._build_ui()
        self._poll_log()

        if self.convert_exe is None:
            self._log(
                "WARNING: conversion engine (ebook-convert) not found. "
                "The released build bundles it automatically."
            )
        else:
            self._log("Engine: " + self.convert_exe)

    # ----- UI -----------------------------------------------------------
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="Add Files...", command=self.add_files).pack(side="left")
        ttk.Button(top, text="Add Folder...", command=self.add_folder).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Clear", command=self.clear_files).pack(side="left", padx=(6, 0))

        ttk.Label(top, text="Convert to:").pack(side="left", padx=(18, 4))
        self.format_var = tk.StringVar(value="epub")
        fmt = ttk.Combobox(
            top,
            textvariable=self.format_var,
            values=OUTPUT_FORMATS,
            width=8,
            state="readonly",
        )
        fmt.pack(side="left")

        ttk.Button(top, text="Output Folder...", command=self.pick_out_dir).pack(side="left", padx=(12, 0))

        mid = ttk.Frame(self.root, padding=(10, 0))
        mid.pack(fill="both", expand=True)

        hint = (
            "Drag & drop files or folders here"
            if _DND_AVAILABLE
            else "Use the buttons above to add files or folders"
        )
        ttk.Label(mid, text=hint, foreground="#666").pack(anchor="w")

        self.listbox = tk.Listbox(mid, selectmode="extended")
        self.listbox.pack(fill="both", expand=True, pady=(4, 0))

        if _DND_AVAILABLE:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self._on_drop)

        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill="x")

        self.convert_btn = ttk.Button(bottom, text="Convert", command=self.start_conversion)
        self.convert_btn.pack(side="left")
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(10, 0))

        logframe = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        logframe.pack(fill="both")
        self.logbox = tk.Text(logframe, height=8, state="disabled", wrap="word")
        self.logbox.pack(fill="both", expand=True)

    # ----- File management ----------------------------------------------
    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select ebook files")
        if paths:
            self._add_paths(list(paths))

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select a folder (searched recursively)")
        if folder:
            self._add_paths([folder])

    def pick_out_dir(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.out_dir = Path(folder)
            self._log("Output folder: " + folder)

    def clear_files(self):
        self.files = []
        self.listbox.delete(0, "end")

    def _on_drop(self, event):  # pragma: no cover - GUI callback
        raw = self.root.tk.splitlist(event.data)
        self._add_paths(list(raw))

    def _add_paths(self, paths):
        found = gather_ebooks(paths)
        existing = set(self.files)
        added = 0
        for f in found:
            if f not in existing:
                self.files.append(f)
                self.listbox.insert("end", str(f))
                existing.add(f)
                added += 1
        self._log("Added " + str(added) + " file(s). Total: " + str(len(self.files)) + ".")

    # ----- Conversion ---------------------------------------------------
    def start_conversion(self):
        if self.convert_exe is None:
            messagebox.showerror(APP_NAME, "Conversion engine not found. The released build bundles it.")
            return
        if not self.files:
            messagebox.showinfo(APP_NAME, "Add some files or folders first.")
            return
        self.convert_btn.config(state="disabled")
        self.progress.config(maximum=len(self.files), value=0)
        out_format = self.format_var.get()
        worker = threading.Thread(
            target=self._run_conversions,
            args=(list(self.files), out_format, self.out_dir),
            daemon=True,
        )
        worker.start()

    def _run_conversions(self, files, out_format, out_dir):
        ok = 0
        fail = 0
        for i, src in enumerate(files, 1):
            self._log("[" + str(i) + "/" + str(len(files)) + "] " + src.name)
            success, msg = convert_one(self.convert_exe, src, out_format, out_dir)
            self._log("    " + msg)
            if success:
                ok += 1
            else:
                fail += 1
            self.log_queue.put("__PROGRESS__" + str(i))
        self._log("Done. " + str(ok) + " converted, " + str(fail) + " failed.")
        self.log_queue.put("__DONE__")

    # ----- Logging / polling --------------------------------------------
    def _log(self, message):
        self.log_queue.put(message)

    def _poll_log(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if item.startswith("__PROGRESS__"):
                    self.progress.config(value=int(item.split("__PROGRESS__")[1]))
                elif item == "__DONE__":
                    self.convert_btn.config(state="normal")
                else:
                    self.logbox.config(state="normal")
                    self.logbox.insert("end", item + "\n")
                    self.logbox.see("end")
                    self.logbox.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(120, self._poll_log)


def main():
    if _DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
