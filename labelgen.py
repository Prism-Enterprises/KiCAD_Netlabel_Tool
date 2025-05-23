#!/usr/bin/env python3
"""
labelgen.py – insert local **or** global net‑labels into a KiCad schematic
using a simple CSV file that contains a `Label` column.

Tested with **kicad‑skip 0.2.5**.
"""

from __future__ import annotations

import csv
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# -----------------------------------------------------------------------------
# Utility: ensure kicad‑skip is available
# -----------------------------------------------------------------------------

def ensure_skip():
    """Import `skip.Schematic`, installing kicad‑skip if needed."""

    try:
        from skip import Schematic  # type: ignore  # noqa: E402
    except ImportError:  # pragma: no cover – one‑shot install path
        subprocess.check_call([sys.executable, "-m", "pip", "install", "kicad-skip>=0.2.5"])
        from skip import Schematic  # type: ignore  # noqa: E402
    return Schematic

# -----------------------------------------------------------------------------
# Settings dialog
# -----------------------------------------------------------------------------

class ConfigDialog(simpledialog.Dialog):
    """Modal dialog to collect options and file paths from the user."""

    def body(self, master: tk.Misc):  # type: ignore[override]
        # Header / disclaimer
        tk.Label(master, text="Settings & Disclaimer", justify="left").grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Label(
            master,
            text=(
                "Modifies your KiCad schematic (.kicad_sch) in place.\n"
                "A backup (.bak) is saved alongside the original.\n"
                "Run outside your project root to reduce corruption risk.\n"
                "Labels are placed just outside the title‑block at the top‑left."
            ),
            justify="left",
            wraplength=420,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Defaults note
        tk.Label(master, text="Defaults: mil units · local labels · 100 mil pitch").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Units
        self.metric = tk.BooleanVar(value=False)
        tk.Checkbutton(master, text="Use metric units (2 mm pitch)", variable=self.metric).grid(row=3, column=0, columnspan=3, sticky="w")

        # Global / local
        self.global_lbl = tk.BooleanVar(value=False)
        tk.Checkbutton(master, text="Use global labels", variable=self.global_lbl).grid(row=4, column=0, columnspan=3, sticky="w")

        # Pitch (user may override)
        tk.Label(master, text="Pitch:").grid(row=5, column=0, sticky="e")
        default_pitch = 2.0 if self.metric.get() else 100.0
        self.pitch_var = tk.DoubleVar(value=default_pitch)
        tk.Entry(master, textvariable=self.pitch_var, width=10).grid(row=5, column=1, sticky="w")
        tk.Label(master, text="units").grid(row=5, column=2, sticky="w")

        # Schematic file path
        tk.Label(master, text="Schematic file:").grid(row=6, column=0, sticky="e")
        self.schem_var = tk.StringVar()
        tk.Entry(master, textvariable=self.schem_var, width=52).grid(row=6, column=1)
        tk.Button(master, text="Browse…", command=self._browse_schem).grid(row=6, column=2)

        # CSV file path
        tk.Label(master, text="CSV file:").grid(row=7, column=0, sticky="e")
        self.csv_var = tk.StringVar()
        tk.Entry(master, textvariable=self.csv_var, width=52).grid(row=7, column=1)
        tk.Button(master, text="Browse…", command=self._browse_csv).grid(row=7, column=2)

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _browse_schem(self) -> None:
        path = filedialog.askopenfilename(title="Select schematic", filetypes=[("KiCad schematic", "*.kicad_sch")])
        if path:
            self.schem_var.set(path)

    def _browse_csv(self) -> None:
        path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV", "*.csv")])
        if path:
            self.csv_var.set(path)

    # ------------------------------------------------------------------
    # Validation / results
    # ------------------------------------------------------------------

    def validate(self) -> bool:  # type: ignore[override]
        if not Path(self.schem_var.get()).exists():
            messagebox.showerror("Error", "Please select a valid schematic file.")
            return False
        if not Path(self.csv_var.get()).exists():
            messagebox.showerror("Error", "Please select a valid CSV file.")
            return False
        return True

    def apply(self) -> None:  # type: ignore[override]
        self.unit: str = "mm" if self.metric.get() else "mil"
        self.use_global: bool = self.global_lbl.get()
        self.pitch: float = self.pitch_var.get()
        self.schematic: Path = Path(self.schem_var.get())
        self.csvfile: Path = Path(self.csv_var.get())

# -----------------------------------------------------------------------------
# Main routine
# -----------------------------------------------------------------------------

def main() -> None:  # noqa: C901 – simple script entry
    # One‑time disclaimer
    root = tk.Tk(); root.withdraw()
    if not messagebox.askyesno(
        "Disclaimer",
        "This tool edits your schematic directly (backup *.bak is created).\nProceed?",
    ):
        sys.exit(0)

    # Settings dialog
    dialog = ConfigDialog(root, title="labelgen – settings & files")
    if not hasattr(dialog, "schematic"):
        sys.exit(0)

    # Constants: start position (mm)
    START_X_MM, START_Y_MM = -10.0, -10.0

    # Pitch in mm
    pitch_mm = dialog.pitch if dialog.unit == "mm" else dialog.pitch * 0.0254

    # Backup original schematic
    bak_path = dialog.schematic.with_suffix(dialog.schematic.suffix + ".bak")
    bak_path.write_bytes(dialog.schematic.read_bytes())

    # Load schematic
    Schematic = ensure_skip()
    sch = Schematic(str(dialog.schematic))  # type: ignore[arg-type]

    # Choose correct collection for new labels
    if dialog.use_global and hasattr(sch, "global_label") and hasattr(sch.global_label, "new"):
        collection = sch.global_label  # GlobalLabelCollection
    else:
        collection = sch.label  # Local LabelCollection

    # Insert labels
    count = 0
    with dialog.csvfile.open(newline="") as csv_f:
        reader = csv.DictReader(csv_f)
        label_col = next((c for c in (reader.fieldnames or []) if c.strip().lower() == "label"), None)
        if not label_col:
            messagebox.showerror("Error", "CSV lacks a 'Label' column.")
            sys.exit(1)
        for idx, row in enumerate(reader):
            raw = row.get(label_col, "").strip()
            if not raw:
                continue
            lbl = collection.new()  # type: ignore[attr-defined]
            lbl.value = raw.upper()
            lbl.move(START_X_MM, START_Y_MM - idx * pitch_mm)
            count += 1

    sch.write(str(dialog.schematic))  # type: ignore[arg-type]
    messagebox.showinfo("Done", f"Inserted {count} labels into {dialog.schematic.name}")
    print(f"Inserted {count} labels → {dialog.schematic}")


if __name__ == "__main__":
    main()

# MIT License – Kai Wyborny / Prism Enterprise LLC
