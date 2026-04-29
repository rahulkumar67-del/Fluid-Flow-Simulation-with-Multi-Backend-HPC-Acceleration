#!/usr/bin/env python3
"""
Comparison Plotting Script for LBM Benchmarks.

Generates publication-quality charts comparing Serial, OpenMP, and MPI backends.

Usage:
    python3 scripts/plot_comparison.py results/benchmarks.csv results
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/plot_comparison.py <csv_path> <output_dir>")
        return 1

    csv_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(csv_path)
    if not rows:
        print("No rows found in CSV.")
        return 1

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("matplotlib is required. Install: pip install matplotlib")
        return 1

    # ---- Style ----
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 12,
        "figure.facecolor": "white",
        "axes.grid": True,
        "grid.alpha": 0.3,
    })

    COLORS = {
        "serial": "#2196F3",
        "openmp": "#4CAF50",
        "mpi": "#FF9800",
    }

    # =========================================================================
    # CHART 1: Elapsed Time — Bar chart grouped by grid size (cavity only)
    # =========================================================================
    cavity_rows = [r for r in rows if r["case"] == "cavity"]
    if cavity_rows:
        # Group by grid size
        grids = sorted(set(f"{r['nx']}x{r['ny']}" for r in cavity_rows),
                       key=lambda g: int(g.split("x")[0]))

        fig, ax = plt.subplots(figsize=(12, 6))
        grid_data = defaultdict(list)
        for r in cavity_rows:
            grid = f"{r['nx']}x{r['ny']}"
            label = r["backend"]
            if label == "openmp":
                # Infer thread count — we'll just use elapsed time order
                pass
            grid_data[grid].append(r)

        # Create grouped bar chart
        import numpy as np
        bar_width = 0.12
        x_positions = np.arange(len(grids))

        # Collect all unique backend labels in order
        backend_labels = []
        seen = set()
        for r in cavity_rows:
            lbl = r["backend"]
            if lbl not in seen:
                backend_labels.append(lbl)
                seen.add(lbl)

        # Count occurrences per grid to handle multiple OpenMP entries
        all_labels = []
        for grid in grids:
            grid_rows = [r for r in cavity_rows if f"{r['nx']}x{r['ny']}" == grid]
            for i, r in enumerate(grid_rows):
                lbl = r["backend"]
                if lbl == "openmp":
                    count = sum(1 for rr in grid_rows[:i+1] if rr["backend"] == "openmp")
                    lbl = f"openmp-{count}T"
                elif lbl == "mpi":
                    count = sum(1 for rr in grid_rows[:i+1] if rr["backend"] == "mpi")
                    lbl = f"mpi-{count}p"
                if lbl not in all_labels:
                    all_labels.append(lbl)

        for i, label in enumerate(all_labels):
            times = []
            for grid in grids:
                grid_rows = [r for r in cavity_rows if f"{r['nx']}x{r['ny']}" == grid]
                # Find matching row
                base = label.split("-")[0]
                idx_in_type = 0
                if "-" in label:
                    idx_in_type = int(label.split("-")[1].replace("T","").replace("p","")) - 1
                matches = [r for r in grid_rows if r["backend"] == base]
                if idx_in_type < len(matches):
                    times.append(float(matches[idx_in_type]["elapsed_seconds"]))
                else:
                    times.append(0)

            color = COLORS.get(label.split("-")[0], "#9E9E9E")
            alpha = max(0.4, 1.0 - idx_in_type * 0.15)
            ax.bar(x_positions + i * bar_width, times, bar_width,
                   label=label, color=color, alpha=alpha, edgecolor="white", linewidth=0.5)

        ax.set_xlabel("Grid Size")
        ax.set_ylabel("Elapsed Time (seconds)")
        ax.set_title("Cavity Flow — Elapsed Time Comparison")
        ax.set_xticks(x_positions + bar_width * (len(all_labels) - 1) / 2)
        ax.set_xticklabels(grids)
        ax.legend(loc="upper left", fontsize=9)
        ax.set_yscale("log")
        plt.tight_layout()
        plt.savefig(out_dir / "comparison_elapsed_cavity.png", dpi=200)
        plt.close()
        print(f"[OK] comparison_elapsed_cavity.png")

    # =========================================================================
    # CHART 2: MLUPS (Performance) — Same grouped bar chart
    # =========================================================================
    if cavity_rows:
        fig, ax = plt.subplots(figsize=(12, 6))
        for i, label in enumerate(all_labels):
            mlups_vals = []
            for grid in grids:
                grid_rows = [r for r in cavity_rows if f"{r['nx']}x{r['ny']}" == grid]
                base = label.split("-")[0]
                idx_in_type = 0
                if "-" in label:
                    idx_in_type = int(label.split("-")[1].replace("T","").replace("p","")) - 1
                matches = [r for r in grid_rows if r["backend"] == base]
                if idx_in_type < len(matches):
                    mlups_vals.append(float(matches[idx_in_type]["mlups"]))
                else:
                    mlups_vals.append(0)

            color = COLORS.get(label.split("-")[0], "#9E9E9E")
            alpha = max(0.4, 1.0 - idx_in_type * 0.15)
            ax.bar(x_positions + i * bar_width, mlups_vals, bar_width,
                   label=label, color=color, alpha=alpha, edgecolor="white", linewidth=0.5)

        ax.set_xlabel("Grid Size")
        ax.set_ylabel("MLUPS (Million Lattice Updates/sec)")
        ax.set_title("Cavity Flow — Performance (MLUPS) Comparison")
        ax.set_xticks(x_positions + bar_width * (len(all_labels) - 1) / 2)
        ax.set_xticklabels(grids)
        ax.legend(loc="upper left", fontsize=9)
        plt.tight_layout()
        plt.savefig(out_dir / "comparison_mlups_cavity.png", dpi=200)
        plt.close()
        print(f"[OK] comparison_mlups_cavity.png")

    # =========================================================================
    # CHART 3: OpenMP Speedup curve (relative to serial baseline)
    # =========================================================================
    # Find serial baselines and OpenMP runs per grid
    if cavity_rows:
        fig, ax = plt.subplots(figsize=(10, 6))
        has_speedup_data = False

        for grid in grids:
            grid_rows = [r for r in cavity_rows if f"{r['nx']}x{r['ny']}" == grid]
            serial_rows = [r for r in grid_rows if r["backend"] == "serial"]
            omp_rows = [r for r in grid_rows if r["backend"] == "openmp"]

            if serial_rows and omp_rows:
                serial_time = float(serial_rows[0]["elapsed_seconds"])
                thread_counts = list(range(1, len(omp_rows) + 1))
                speedups = [serial_time / float(r["elapsed_seconds"]) for r in omp_rows]

                ax.plot(thread_counts, speedups, "o-", linewidth=2, markersize=8, label=f"{grid}")
                has_speedup_data = True

        if has_speedup_data:
            max_threads = max(len([r for r in cavity_rows if r["backend"] == "openmp"
                                   and f"{r['nx']}x{r['ny']}" == g]) for g in grids)
            ideal = list(range(1, max_threads + 1))
            ax.plot(ideal, ideal, "k--", alpha=0.4, label="Ideal (linear)")
            ax.set_xlabel("OpenMP Threads")
            ax.set_ylabel("Speedup (serial time / parallel time)")
            ax.set_title("OpenMP Speedup — Cavity Flow")
            ax.legend()
            ax.set_xticks(range(1, max_threads + 1))
            plt.tight_layout()
            plt.savefig(out_dir / "speedup_openmp.png", dpi=200)
            print(f"[OK] speedup_openmp.png")
        plt.close()

    # =========================================================================
    # CHART 4: Cylinder flow comparison (if present)
    # =========================================================================
    cyl_rows = [r for r in rows if r["case"] == "cylinder"]
    if cyl_rows:
        cyl_grids = sorted(set(f"{r['nx']}x{r['ny']}" for r in cyl_rows),
                           key=lambda g: int(g.split("x")[0]))
        import numpy as np

        cyl_labels = []
        for grid in cyl_grids:
            grid_rows_cyl = [r for r in cyl_rows if f"{r['nx']}x{r['ny']}" == grid]
            for j, r in enumerate(grid_rows_cyl):
                lbl = r["backend"]
                if lbl == "openmp":
                    count = sum(1 for rr in grid_rows_cyl[:j+1] if rr["backend"] == "openmp")
                    lbl = f"openmp-{count}T"
                elif lbl == "mpi":
                    count = sum(1 for rr in grid_rows_cyl[:j+1] if rr["backend"] == "mpi")
                    lbl = f"mpi-{count}p"
                if lbl not in cyl_labels:
                    cyl_labels.append(lbl)

        x_pos = np.arange(len(cyl_grids))
        bw = 0.12
        fig, ax = plt.subplots(figsize=(12, 6))

        for i, label in enumerate(cyl_labels):
            times = []
            for grid in cyl_grids:
                grid_rows_cyl = [r for r in cyl_rows if f"{r['nx']}x{r['ny']}" == grid]
                base = label.split("-")[0]
                idx_in_type = 0
                if "-" in label:
                    idx_in_type = int(label.split("-")[1].replace("T","").replace("p","")) - 1
                matches = [r for r in grid_rows_cyl if r["backend"] == base]
                if idx_in_type < len(matches):
                    times.append(float(matches[idx_in_type]["elapsed_seconds"]))
                else:
                    times.append(0)

            color = COLORS.get(label.split("-")[0], "#9E9E9E")
            ax.bar(x_pos + i * bw, times, bw, label=label, color=color,
                   edgecolor="white", linewidth=0.5)

        ax.set_xlabel("Grid Size")
        ax.set_ylabel("Elapsed Time (seconds)")
        ax.set_title("Cylinder Flow — Elapsed Time Comparison")
        ax.set_xticks(x_pos + bw * (len(cyl_labels) - 1) / 2)
        ax.set_xticklabels(cyl_grids)
        ax.legend(loc="upper left", fontsize=9)
        ax.set_yscale("log")
        plt.tight_layout()
        plt.savefig(out_dir / "comparison_elapsed_cylinder.png", dpi=200)
        plt.close()
        print(f"[OK] comparison_elapsed_cylinder.png")

    # =========================================================================
    # CHART 5: Backend summary — overall best MLUPS per backend
    # =========================================================================
    backend_best = defaultdict(float)
    for r in rows:
        b = r["backend"]
        m = float(r["mlups"])
        backend_best[b] = max(backend_best[b], m)

    if backend_best:
        fig, ax = plt.subplots(figsize=(8, 5))
        backends = list(backend_best.keys())
        mlups_best = [backend_best[b] for b in backends]
        colors = [COLORS.get(b, "#9E9E9E") for b in backends]
        bars = ax.bar(backends, mlups_best, color=colors, edgecolor="white", linewidth=1.5, width=0.5)
        for bar, val in zip(bars, mlups_best):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                    f"{val:.2f}", ha="center", va="bottom", fontweight="bold")
        ax.set_ylabel("Peak MLUPS")
        ax.set_title("Peak Performance by Backend")
        plt.tight_layout()
        plt.savefig(out_dir / "peak_mlups_by_backend.png", dpi=200)
        plt.close()
        print(f"[OK] peak_mlups_by_backend.png")

    print(f"\nAll charts saved to: {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
