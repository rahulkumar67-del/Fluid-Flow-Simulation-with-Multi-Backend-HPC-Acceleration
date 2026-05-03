#!/usr/bin/env python3
"""
Paper Plots Generator for LBM IEEE Report.

Reads benchmark CSV data and generates all figures for the paper.
Output goes to report/plots/.

Usage:
    python3 scripts/paper_plots.py
"""

import csv
import sys
import os
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
except ImportError:
    print("ERROR: matplotlib is required. Install: pip install matplotlib numpy")
    sys.exit(1)


# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
RESULTS_DIR = PROJECT_DIR / "results"
PLOT_DIR = PROJECT_DIR / "report" / "plots"
CSV_PATH = RESULTS_DIR / "paper_benchmarks.csv"
CONV_CSV = RESULTS_DIR / "convergence.csv"


# ── Style ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "serif"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "figure.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "lines.linewidth": 1.8,
    "lines.markersize": 6,
})

COLORS = {
    "serial": "#1565C0",
    "openmp": "#2E7D32",
    "mpi": "#E65100",
}
OMP_COLORS = ["#66BB6A", "#43A047", "#2E7D32", "#1B5E20"]


def read_csv(path):
    if not path.exists():
        print(f"WARNING: {path} not found. Skipping dependent plots.")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT_DIR / name, dpi=250, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {name}")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Elapsed time grouped bar chart (cavity, all backends)
# ═════════════════════════════════════════════════════════════════════════════
def plot_elapsed_comparison(rows):
    cavity = [r for r in rows if r["case"] == "cavity"
              and r["reynolds"] == "100"]
    if not cavity:
        return

    grids = sorted(set(f"{r['nx']}x{r['ny']}" for r in cavity),
                   key=lambda g: int(g.split("x")[0]))

    # Collect serial and best-OpenMP (highest thread count) for each grid
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bar_w = 0.15
    x = np.arange(len(grids))

    # Find all unique backend labels
    labels_data = {}  # label -> {grid: elapsed}
    for grid in grids:
        grid_rows = [r for r in cavity if f"{r['nx']}x{r['ny']}" == grid]
        serial_rows = [r for r in grid_rows if r["backend"] == "serial"]
        omp_rows = [r for r in grid_rows if r["backend"] == "openmp"]
        mpi_rows = [r for r in grid_rows if r["backend"] == "mpi"]

        if serial_rows:
            labels_data.setdefault("Serial", {})[grid] = float(serial_rows[0]["elapsed_seconds"])

        for i, r in enumerate(omp_rows):
            t = [1, 2, 4, 8][i] if i < 4 else i + 1
            lbl = f"OpenMP-{t}T"
            labels_data.setdefault(lbl, {})[grid] = float(r["elapsed_seconds"])

        if mpi_rows:
            labels_data.setdefault("MPI-1p", {})[grid] = float(mpi_rows[0]["elapsed_seconds"])

    n_bars = len(labels_data)
    color_map = {
        "Serial": COLORS["serial"],
        "OpenMP-1T": "#A5D6A7", "OpenMP-2T": "#66BB6A",
        "OpenMP-4T": "#43A047", "OpenMP-8T": "#1B5E20",
        "MPI-1p": COLORS["mpi"],
    }

    for i, (label, gdata) in enumerate(labels_data.items()):
        vals = [gdata.get(g, 0) for g in grids]
        c = color_map.get(label, "#999")
        ax.bar(x + i * bar_w, vals, bar_w, label=label, color=c,
               edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Grid Size")
    ax.set_ylabel("Elapsed Time (s)")
    ax.set_title("Lid-Driven Cavity — Elapsed Time by Backend (Re = 100)")
    ax.set_xticks(x + bar_w * (n_bars - 1) / 2)
    ax.set_xticklabels(grids)
    ax.set_yscale("log")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    save(fig, "fig_elapsed_comparison.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: MLUPS performance bar chart
# ═════════════════════════════════════════════════════════════════════════════
def plot_mlups_comparison(rows):
    cavity = [r for r in rows if r["case"] == "cavity"
              and r["reynolds"] == "100"]
    if not cavity:
        return

    grids = sorted(set(f"{r['nx']}x{r['ny']}" for r in cavity),
                   key=lambda g: int(g.split("x")[0]))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bar_w = 0.15
    x = np.arange(len(grids))

    labels_data = {}
    for grid in grids:
        grid_rows = [r for r in cavity if f"{r['nx']}x{r['ny']}" == grid]
        serial_rows = [r for r in grid_rows if r["backend"] == "serial"]
        omp_rows = [r for r in grid_rows if r["backend"] == "openmp"]
        mpi_rows = [r for r in grid_rows if r["backend"] == "mpi"]

        if serial_rows:
            labels_data.setdefault("Serial", {})[grid] = float(serial_rows[0]["mlups"])
        for i, r in enumerate(omp_rows):
            t = [1, 2, 4, 8][i] if i < 4 else i + 1
            labels_data.setdefault(f"OpenMP-{t}T", {})[grid] = float(r["mlups"])
        if mpi_rows:
            labels_data.setdefault("MPI-1p", {})[grid] = float(mpi_rows[0]["mlups"])

    color_map = {
        "Serial": COLORS["serial"], "OpenMP-1T": "#A5D6A7",
        "OpenMP-2T": "#66BB6A", "OpenMP-4T": "#43A047",
        "OpenMP-8T": "#1B5E20", "MPI-1p": COLORS["mpi"],
    }
    n_bars = len(labels_data)
    for i, (label, gdata) in enumerate(labels_data.items()):
        vals = [gdata.get(g, 0) for g in grids]
        ax.bar(x + i * bar_w, vals, bar_w, label=label,
               color=color_map.get(label, "#999"), edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Grid Size")
    ax.set_ylabel("MLUPS (Million Lattice Updates / s)")
    ax.set_title("Lid-Driven Cavity — Throughput by Backend (Re = 100)")
    ax.set_xticks(x + bar_w * (n_bars - 1) / 2)
    ax.set_xticklabels(grids)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    save(fig, "fig_mlups_comparison.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: OpenMP Speedup
# ═════════════════════════════════════════════════════════════════════════════
def plot_speedup(rows):
    cavity = [r for r in rows if r["case"] == "cavity"
              and r["reynolds"] == "100"]
    if not cavity:
        return

    grids = sorted(set(f"{r['nx']}x{r['ny']}" for r in cavity),
                   key=lambda g: int(g.split("x")[0]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    markers = ["o", "s", "D", "^"]
    colors = ["#42A5F5", "#66BB6A", "#FFA726", "#EF5350"]

    max_t = 1
    for gi, grid in enumerate(grids):
        grid_rows = [r for r in cavity if f"{r['nx']}x{r['ny']}" == grid]
        serial_rows = [r for r in grid_rows if r["backend"] == "serial"]
        omp_rows = [r for r in grid_rows if r["backend"] == "openmp"]

        if not serial_rows or not omp_rows:
            continue

        t_serial = float(serial_rows[0]["elapsed_seconds"])
        threads = []
        speedups = []
        for i, r in enumerate(omp_rows):
            t = [1, 2, 4, 8][i] if i < 4 else i + 1
            threads.append(t)
            speedups.append(t_serial / float(r["elapsed_seconds"]))
        max_t = max(max_t, max(threads))

        efficiencies = [s / t for s, t in zip(speedups, threads)]

        ax1.plot(threads, speedups, f"-{markers[gi % 4]}", color=colors[gi % 4],
                 label=grid, linewidth=2, markersize=7)
        ax2.plot(threads, efficiencies, f"-{markers[gi % 4]}", color=colors[gi % 4],
                 label=grid, linewidth=2, markersize=7)

    # Ideal line
    ideal = list(range(1, max_t + 1))
    ax1.plot(ideal, ideal, "k--", alpha=0.3, label="Ideal")
    ax2.axhline(y=1.0, color="k", linestyle="--", alpha=0.3, label="Ideal")

    ax1.set_xlabel("OpenMP Threads ($p$)")
    ax1.set_ylabel("Speedup $S(p) = T_1 / T_p$")
    ax1.set_title("(a) OpenMP Speedup")
    ax1.legend(fontsize=8)
    ax1.set_xticks(range(1, max_t + 1))

    ax2.set_xlabel("OpenMP Threads ($p$)")
    ax2.set_ylabel("Efficiency $E(p) = S(p) / p$")
    ax2.set_title("(b) OpenMP Efficiency")
    ax2.legend(fontsize=8)
    ax2.set_xticks(range(1, max_t + 1))
    ax2.set_ylim(0, 1.15)

    fig.suptitle("Cavity Flow — OpenMP Scaling (Re = 100)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    save(fig, "fig_speedup_efficiency.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Grid convergence (L2 error vs grid size)
# ═════════════════════════════════════════════════════════════════════════════
def plot_convergence(conv_rows):
    if not conv_rows:
        return

    grids = []
    l2_errors = []
    for r in conv_rows:
        n = int(r["nx"])
        l2 = float(r["final_l2"])
        if l2 > 0:
            grids.append(n)
            l2_errors.append(l2)

    if len(grids) < 2:
        return

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.loglog(grids, l2_errors, "o-", color="#1565C0", linewidth=2, markersize=8, label="Measured L2")

    # Reference slope lines
    g_arr = np.array(grids, dtype=float)
    ref1 = l2_errors[0] * (g_arr / g_arr[0]) ** (-1)
    ref2 = l2_errors[0] * (g_arr / g_arr[0]) ** (-2)
    ax.loglog(g_arr, ref1, "k--", alpha=0.35, label="O($h$) reference")
    ax.loglog(g_arr, ref2, "k:", alpha=0.35, label="O($h^2$) reference")

    ax.set_xlabel("Grid Size $N$")
    ax.set_ylabel("Final L2 Error")
    ax.set_title("Grid Convergence Study (Cavity, Re = 100)")
    ax.legend()
    save(fig, "fig_convergence.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Grid scaling (elapsed time vs grid size)
# ═════════════════════════════════════════════════════════════════════════════
def plot_grid_scaling(rows):
    cavity = [r for r in rows if r["case"] == "cavity"
              and r["backend"] == "serial" and r["reynolds"] == "100"]
    if not cavity:
        return

    grids = []
    times = []
    for r in sorted(cavity, key=lambda r: int(r["nx"])):
        n = int(r["nx"])
        if n not in grids:
            grids.append(n)
            times.append(float(r["elapsed_seconds"]))

    if len(grids) < 2:
        return

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.loglog(grids, times, "s-", color="#1565C0", linewidth=2, markersize=8, label="Measured")

    g_arr = np.array(grids, dtype=float)
    ref = times[0] * (g_arr / g_arr[0]) ** 2
    ax.loglog(g_arr, ref, "k--", alpha=0.35, label="O($N^2$) reference")

    ax.set_xlabel("Grid Size $N$")
    ax.set_ylabel("Elapsed Time (s)")
    ax.set_title("Serial Runtime Scaling — Cavity (Re = 100)")
    ax.legend()
    save(fig, "fig_grid_scaling.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Cylinder flow elapsed time comparison
# ═════════════════════════════════════════════════════════════════════════════
def plot_cylinder_comparison(rows):
    cyl = [r for r in rows if r["case"] == "cylinder" and r["reynolds"] == "100"]
    if not cyl:
        return

    grids = sorted(set(f"{r['nx']}x{r['ny']}" for r in cyl),
                   key=lambda g: int(g.split("x")[0]))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bar_w = 0.15
    x = np.arange(len(grids))

    labels_data = {}
    for grid in grids:
        grid_rows = [r for r in cyl if f"{r['nx']}x{r['ny']}" == grid]
        serial_rows = [r for r in grid_rows if r["backend"] == "serial"]
        omp_rows = [r for r in grid_rows if r["backend"] == "openmp"]

        if serial_rows:
            labels_data.setdefault("Serial", {})[grid] = float(serial_rows[0]["elapsed_seconds"])
        for i, r in enumerate(omp_rows):
            t = [1, 2, 4, 8][i] if i < 4 else i + 1
            labels_data.setdefault(f"OpenMP-{t}T", {})[grid] = float(r["elapsed_seconds"])

    color_map = {
        "Serial": COLORS["serial"], "OpenMP-1T": "#A5D6A7",
        "OpenMP-2T": "#66BB6A", "OpenMP-4T": "#43A047",
        "OpenMP-8T": "#1B5E20",
    }
    n_bars = len(labels_data)
    for i, (label, gdata) in enumerate(labels_data.items()):
        vals = [gdata.get(g, 0) for g in grids]
        ax.bar(x + i * bar_w, vals, bar_w, label=label,
               color=color_map.get(label, "#999"), edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Grid Size")
    ax.set_ylabel("Elapsed Time (s)")
    ax.set_title("Flow Past Cylinder — Elapsed Time by Backend (Re = 100)")
    ax.set_xticks(x + bar_w * (n_bars - 1) / 2)
    ax.set_xticklabels(grids)
    ax.set_yscale("log")
    ax.legend(fontsize=8)
    save(fig, "fig_cylinder_comparison.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Peak MLUPS by backend
# ═════════════════════════════════════════════════════════════════════════════
def plot_peak_mlups(rows):
    if not rows:
        return

    best = defaultdict(float)
    for r in rows:
        b = r["backend"]
        m = float(r["mlups"])
        best[b] = max(best[b], m)

    fig, ax = plt.subplots(figsize=(6, 4))
    backends = list(best.keys())
    vals = [best[b] for b in backends]
    colors = [COLORS.get(b, "#999") for b in backends]
    bars = ax.bar(backends, vals, color=colors, edgecolor="white",
                  linewidth=1.5, width=0.45)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{v:.2f}", ha="center", va="bottom", fontweight="bold", fontsize=10)
    ax.set_ylabel("Peak MLUPS")
    ax.set_title("Peak Throughput by Backend")
    save(fig, "fig_peak_mlups.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Reynolds number comparison (velocity images side by side)
# ═════════════════════════════════════════════════════════════════════════════
def plot_reynolds_gallery():
    """Copy velocity field PNGs and create a gallery figure."""
    re_images = {}
    for re in [100, 400]:
        for case in ["cavity", "cylinder"]:
            if case == "cavity":
                path = RESULTS_DIR / f"paper_cavity_256_re{re}.png"
            else:
                path = RESULTS_DIR / f"paper_cylinder_256_re{re}.png"
            if path.exists():
                re_images[(case, re)] = path

    if not re_images:
        return

    # Create a gallery with available images
    cases = sorted(set(k[0] for k in re_images))
    reynolds = sorted(set(k[1] for k in re_images))

    n_cols = len(reynolds)
    n_rows = len(cases)

    if n_cols == 0 or n_rows == 0:
        return

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
    if n_rows == 1 and n_cols == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes[np.newaxis, :]
    elif n_cols == 1:
        axes = axes[:, np.newaxis]

    for ri, case in enumerate(cases):
        for ci, re in enumerate(reynolds):
            ax = axes[ri, ci]
            key = (case, re)
            if key in re_images:
                img = plt.imread(str(re_images[key]))
                ax.imshow(img)
                ax.set_title(f"{case.title()} — Re = {re}", fontsize=10)
            ax.axis("off")

    fig.suptitle("Velocity Field Comparison Across Reynolds Numbers",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    save(fig, "fig_reynolds_comparison.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE: Copy best velocity field images for the paper
# ═════════════════════════════════════════════════════════════════════════════
def copy_velocity_images():
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    copies = {
        "paper_cavity_256x256_serial.png": "fig_cavity_velocity.png",
        "paper_cylinder_256x128_serial.png": "fig_cylinder_velocity.png",
    }
    for src_name, dst_name in copies.items():
        src = RESULTS_DIR / src_name
        dst = PLOT_DIR / dst_name
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  [OK] {dst_name} (copied from {src_name})")


# ═════════════════════════════════════════════════════════════════════════════
# TABLE DATA: Generate scaling table for LaTeX
# ═════════════════════════════════════════════════════════════════════════════
def print_scaling_table(rows):
    cavity = [r for r in rows if r["case"] == "cavity"
              and r["reynolds"] == "100"]
    if not cavity:
        return

    grids = sorted(set(f"{r['nx']}x{r['ny']}" for r in cavity),
                   key=lambda g: int(g.split("x")[0]))

    print("\n  ── SCALING TABLE DATA (for LaTeX) ──")
    print(f"  {'Grid':>10} {'Backend':>10} {'Time(s)':>10} {'Speedup':>10} {'Efficiency':>10} {'MLUPS':>10}")
    print("  " + "-" * 65)

    for grid in grids:
        grid_rows = [r for r in cavity if f"{r['nx']}x{r['ny']}" == grid]
        serial_rows = [r for r in grid_rows if r["backend"] == "serial"]
        omp_rows = [r for r in grid_rows if r["backend"] == "openmp"]

        if not serial_rows:
            continue

        t_serial = float(serial_rows[0]["elapsed_seconds"])
        print(f"  {grid:>10} {'serial':>10} {t_serial:>10.3f} {'1.000':>10} {'1.000':>10} {float(serial_rows[0]['mlups']):>10.3f}")

        for i, r in enumerate(omp_rows):
            t = [1, 2, 4, 8][i] if i < 4 else i + 1
            tp = float(r["elapsed_seconds"])
            sp = t_serial / tp
            eff = sp / t
            print(f"  {'':>10} {f'omp-{t}T':>10} {tp:>10.3f} {sp:>10.3f} {eff:>10.3f} {float(r['mlups']):>10.3f}")

    # Save as CSV for easy LaTeX import
    table_path = PLOT_DIR / "scaling_table.csv"
    with open(table_path, "w") as f:
        f.write("grid,backend,threads,elapsed_s,speedup,efficiency,mlups\n")
        for grid in grids:
            grid_rows = [r for r in cavity if f"{r['nx']}x{r['ny']}" == grid]
            serial_rows = [r for r in grid_rows if r["backend"] == "serial"]
            omp_rows = [r for r in grid_rows if r["backend"] == "openmp"]
            if not serial_rows:
                continue
            t_serial = float(serial_rows[0]["elapsed_seconds"])
            f.write(f"{grid},serial,1,{t_serial:.4f},1.000,1.000,{float(serial_rows[0]['mlups']):.3f}\n")
            for i, r in enumerate(omp_rows):
                t = [1, 2, 4, 8][i] if i < 4 else i + 1
                tp = float(r["elapsed_seconds"])
                sp = t_serial / tp
                eff = sp / t
                f.write(f"{grid},openmp,{t},{tp:.4f},{sp:.3f},{eff:.3f},{float(r['mlups']):.3f}\n")
    print(f"\n  [OK] scaling_table.csv")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 55)
    print("  GENERATING PAPER FIGURES")
    print("=" * 55)

    rows = read_csv(CSV_PATH)
    conv_rows = read_csv(CONV_CSV)

    if rows:
        plot_elapsed_comparison(rows)
        plot_mlups_comparison(rows)
        plot_speedup(rows)
        plot_cylinder_comparison(rows)
        plot_peak_mlups(rows)
        plot_grid_scaling(rows)
        plot_reynolds_gallery()
        copy_velocity_images()
        print_scaling_table(rows)

    if conv_rows:
        plot_convergence(conv_rows)

    print()
    print(f"  All figures saved to: {PLOT_DIR}/")
    print("  Compile report with: cd report && pdflatex lbm_paper.tex")


if __name__ == "__main__":
    main()
