#!/usr/bin/env python3
"""
Insert net labels into a KiCad schematic from a CSV.
"""

import csv
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog


def ensure_skip():
    try:
        from skip import Schematic
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "kicad-skip>=0.2.5"])
        from skip import Schematic
    return Schematic


class ConfigDialog(simpledialog.Dialog):
    def body(self, master):
        # Defaults note
        tk.Label(master, text="Defaults: imperial units (mil) and local net labels").grid(row=0, column=0, columnspan=3, sticky='w')
        # Metric checkbox
        self.metric = tk.BooleanVar(value=False)
        tk.Checkbutton(master, text="Use metric units (mm)", variable=self.metric).grid(row=1, column=0, columnspan=3, sticky='w')
        # Global labels checkbox
        self.global_lbl = tk.BooleanVar(value=False)
        tk.Checkbutton(master, text="Use global labels", variable=self.global_lbl).grid(row=2, column=0, columnspan=3, sticky='w')
        # Schematic file selection
        tk.Label(master, text="Schematic file:").grid(row=3, column=0, sticky='e')
        self.schem_path = tk.StringVar()
        tk.Entry(master, textvariable=self.schem_path, width=40).grid(row=3, column=1)
        tk.Button(master, text="Browse...", command=self.browse_schem).grid(row=3, column=2)
        # CSV file selection
        tk.Label(master, text="CSV file:").grid(row=4, column=0, sticky='e')
        self.csv_path = tk.StringVar()
        tk.Entry(master, textvariable=self.csv_path, width=40).grid(row=4, column=1)
        tk.Button(master, text="Browse...", command=self.browse_csv).grid(row=4, column=2)
        return None

    def browse_schem(self):
        path = filedialog.askopenfilename(title="Select schematic", filetypes=[("KiCad schematic", "*.kicad_sch")])
        if path:
            self.schem_path.set(path)

    def browse_csv(self):
        path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV file", "*.csv")])
        if path:
            self.csv_path.set(path)

    def validate(self):
        if not self.schem_path.get() or not Path(self.schem_path.get()).exists():
            messagebox.showerror("Error", "Please select a valid schematic file.")
            return False
        if not self.csv_path.get() or not Path(self.csv_path.get()).exists():
            messagebox.showerror("Error", "Please select a valid CSV file.")
            return False
        return True

    def apply(self):
        self.unit = 'mm' if self.metric.get() else 'mil'
        self.use_global = self.global_lbl.get()
        self.schematic = Path(self.schem_path.get())
        self.csvfile = Path(self.csv_path.get())


def main():
    root = tk.Tk(); root.withdraw()
    consent = messagebox.askyesno(
        "Disclaimer",
        "This tool modifies the native KiCad schematic file (.kicad_sch) directly.\n"
        "A backup (.bak) will be saved alongside the original.\n"
        "Run this tool outside your project root to minimize corruption risk.\n"
        "Labels are placed outside the titleblock at the top-left center of the sheet.\n\n"
        "Click Yes to proceed or No/Close to cancel."
    )
    if not consent:
        print("Operation cancelled by user.")
        sys.exit(0)

    dialog = ConfigDialog(root, title="Settings and Files")
    root.destroy()
    if not hasattr(dialog, 'schematic'):
        sys.exit(0)

    factor = 1.0 if dialog.unit == 'mm' else 0.0254
    start_x = -10 * factor
    start_y = -10 * factor
    pitch = 2.54 * factor

    bak = dialog.schematic.with_suffix(dialog.schematic.suffix + ".bak")
    bak.write_bytes(dialog.schematic.read_bytes())

    Schematic = ensure_skip()
    sch = Schematic(str(dialog.schematic))  # type: ignore
    maker = sch.global_label if dialog.use_global else sch.label  # type: ignore

    count = 0
    with dialog.csvfile.open(newline='') as f:
        reader = csv.DictReader(f)
        lblcol = next((c for c in reader.fieldnames or [] if c.strip().lower() == 'label'), None)
        if not lblcol:
            messagebox.showerror("Error", "CSV missing 'Label' column.")
            sys.exit(1)
        for i, row in enumerate(reader):
            text = row.get(lblcol, '').strip().upper()
            if text:
                lbl = maker.new()
                lbl.value = text
                lbl.move(start_x, start_y - i * pitch)
                count += 1

    sch.write(str(dialog.schematic))  # type: ignore
    messagebox.showinfo("Done", f"Inserted {count} labels into {dialog.schematic.name}.")
    print(f"Inserted {count} labels into {dialog.schematic.name}.")

if __name__ == '__main__':
    main()

# MIT License
#
# Copyright (c) 2025 Kai Wyborny, Prism Enterprises LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
