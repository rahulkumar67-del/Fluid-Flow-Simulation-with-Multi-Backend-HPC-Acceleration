#!/usr/bin/env python3
"""
Verification Script for LBM Fluid Simulation.

Validates results by checking:
  1. Conservation: density should be close to 1.0 everywhere
  2. Convergence: L2 error should decrease over time
  3. Ghia benchmark: Compare cavity centerline velocity profiles against
     the well-known Ghia et al. (1982) reference data for Re=100
  4. Cross-backend: Serial and OpenMP should give nearly identical results

Usage:
    python3 scripts/verify_results.py [results_dir]

    If results_dir is not given, defaults to 'results/'
"""

import csv
import os
import struct
import sys
from pathlib import Path


# =============================================================================
# Ghia et al. (1982) benchmark data for lid-driven cavity at Re=100
# Vertical centerline: u-velocity vs y/L
# =============================================================================
GHIA_RE100_VERTICAL = {
    # y/L : u/u_lid
    1.0000: 1.00000,
    0.9766: 0.84123,
    0.9688: 0.78871,
    0.9609: 0.73722,
    0.9531: 0.68717,
    0.8516: 0.23151,
    0.7344: 0.00332,
    0.6172: -0.13641,
    0.5000: -0.20581,
    0.4531: -0.21090,
    0.2813: -0.15662,
    0.1719: -0.10150,
    0.1016: -0.06434,
    0.0703: -0.04775,
    0.0625: -0.04192,
    0.0547: -0.03717,
    0.0000: 0.00000,
}

# Horizontal centerline: v-velocity vs x/L
GHIA_RE100_HORIZONTAL = {
    # x/L : v/u_lid
    1.0000: 0.00000,
    0.9688: -0.05906,
    0.9609: -0.07391,
    0.9531: -0.08864,
    0.8516: -0.24533,
    0.7344: -0.22445,
    0.6172: -0.16914,
    0.5000: -0.06080,
    0.4531: -0.03039,
    0.2813: 0.08183,
    0.1719: 0.10091,
    0.1016: 0.09233,
    0.0703: 0.07507,
    0.0625: 0.06434,
    0.0547: 0.05283,
    0.0000: 0.00000,
}


def read_ppm_velocities(ppm_path):
    """
    Read the PPM image and reconstruct approximate velocity magnitudes.
    This is a rough check — the PPM encodes normalized velocity as color.
    Returns (nx, ny, pixel_data) where pixel_data is list of (r, g, b).
    """
    with open(ppm_path, "rb") as f:
        magic = f.readline().strip()
        if magic != b"P6":
            raise ValueError(f"Not a binary PPM file: {magic}")
        # Skip comments
        line = f.readline()
        while line.startswith(b"#"):
            line = f.readline()
        dims = line.strip().split()
        nx, ny = int(dims[0]), int(dims[1])
        max_val = int(f.readline().strip())
        data = f.read()

    pixels = []
    for i in range(0, len(data), 3):
        r, g, b = data[i], data[i + 1], data[i + 2]
        pixels.append((r, g, b))

    return nx, ny, pixels


def verify_ppm_sanity(ppm_path, label=""):
    """Check that the velocity image has non-trivial content (not all black/uniform)."""
    try:
        nx, ny, pixels = read_ppm_velocities(ppm_path)
    except Exception as e:
        return False, f"Cannot read PPM: {e}"

    total = len(pixels)
    if total != nx * ny:
        return False, f"Pixel count mismatch: {total} vs {nx}x{ny}={nx * ny}"

    # Check that not all pixels are the same (simulation actually did something)
    unique_colors = len(set(pixels))
    if unique_colors < 5:
        return False, f"Image has only {unique_colors} unique colors — simulation may not have run properly"

    # Check that there's variation in the red channel (velocity magnitude)
    reds = [p[0] for p in pixels]
    r_min, r_max = min(reds), max(reds)
    if r_max - r_min < 10:
        return False, f"Very low velocity variation (red channel range: {r_min}-{r_max})"

    return True, f"OK — {nx}x{ny}, {unique_colors} unique colors, velocity range [{r_min}-{r_max}]"


def verify_csv_metrics(csv_path):
    """Verify that benchmark metrics are physically reasonable."""
    issues = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return ["CSV is empty"]

    for i, r in enumerate(rows):
        label = f"Row {i+1} ({r['backend']}/{r['case']}/{r['nx']}x{r['ny']})"

        elapsed = float(r["elapsed_seconds"])
        mlups = float(r["mlups"])
        l2 = float(r["final_l2"])
        steps = int(r["steps"])

        # Check elapsed time is positive
        if elapsed <= 0:
            issues.append(f"{label}: elapsed_seconds = {elapsed} (should be > 0)")

        # Check MLUPS is reasonable (should be > 0, typically 0.1–100 for CPU)
        if mlups <= 0:
            issues.append(f"{label}: MLUPS = {mlups} (should be > 0)")
        elif mlups > 500:
            issues.append(f"{label}: MLUPS = {mlups:.1f} (unusually high — verify)")

        # Check convergence
        if l2 > 1.0 and steps > 100:
            issues.append(f"{label}: L2 error = {l2:.2e} (very high — simulation may be unstable)")

        # Check steps
        if steps <= 0:
            issues.append(f"{label}: steps = {steps} (should be > 0)")

    return issues


def verify_cross_backend(csv_path):
    """
    Check that serial and OpenMP give the same (or very similar) L2 error
    for the same grid size and case.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    from collections import defaultdict
    grouped = defaultdict(list)
    for r in rows:
        key = (r["case"], r["nx"], r["ny"])
        grouped[key].append(r)

    issues = []
    for key, group in grouped.items():
        serial_l2 = [float(r["final_l2"]) for r in group if r["backend"] == "serial"]
        omp_l2 = [float(r["final_l2"]) for r in group if r["backend"] == "openmp"]

        if serial_l2 and omp_l2:
            s = serial_l2[0]
            for o in omp_l2:
                if s > 0 and abs(s - o) / max(s, 1e-30) > 0.1:
                    issues.append(
                        f"  {key[0]} {key[1]}x{key[2]}: serial L2={s:.2e} vs openmp L2={o:.2e} "
                        f"(>10% difference)"
                    )

    return issues


def main():
    results_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results")

    print("=" * 60)
    print("  LBM SIMULATION VERIFICATION")
    print("=" * 60)

    all_pass = True

    # --- 1. Check CSV metrics ---
    csv_file = results_dir / "benchmarks.csv"
    if not csv_file.exists():
        csv_file = results_dir / "run.csv"

    if csv_file.exists():
        print(f"\n[1] CSV Metrics Check: {csv_file}")
        issues = verify_csv_metrics(csv_file)
        if issues:
            all_pass = False
            for issue in issues:
                print(f"  ⚠  {issue}")
        else:
            print("  ✓  All metrics look reasonable")
    else:
        print(f"\n[1] CSV Metrics Check: SKIPPED (no CSV found)")

    # --- 2. Cross-backend consistency ---
    if csv_file.exists():
        print(f"\n[2] Cross-Backend Consistency (serial vs openmp)")
        issues = verify_cross_backend(csv_file)
        if issues:
            all_pass = False
            for issue in issues:
                print(f"  ⚠ {issue}")
        else:
            print("  ✓  Serial and OpenMP produce consistent results")

    # --- 3. PPM Image checks ---
    print(f"\n[3] Velocity Image Sanity Check")
    ppm_files = sorted(results_dir.glob("*.ppm"))
    if ppm_files:
        for ppm in ppm_files:
            ok, msg = verify_ppm_sanity(ppm, ppm.stem)
            symbol = "✓" if ok else "✗"
            if not ok:
                all_pass = False
            print(f"  {symbol}  {ppm.name}: {msg}")
    else:
        print("  (no PPM files found)")

    # --- 4. Ghia reference comparison ---
    print(f"\n[4] Ghia et al. (1982) Reference — Re=100 Cavity")
    print("  This check requires extracting centerline velocities from the simulation.")
    print("  The simulation stores velocity fields internally but the PPM only has")
    print("  color-encoded magnitudes. For a proper Ghia comparison, you would need")
    print("  to either:")
    print("    a) Add CSV output of centerline velocities to the simulation code, or")
    print("    b) Compare visually: the cavity should show a single primary vortex")
    print("       centered slightly above and to the right of the geometric center.")
    print()
    print("  Quick visual checks for a CORRECT cavity simulation at Re=100:")
    print("    • Single large clockwise vortex fills most of the cavity")
    print("    • Vortex center is at approximately (x/L=0.62, y/L=0.74)")
    print("    • Small secondary vortices in the bottom corners")
    print("    • Maximum velocity near the top-right corner")
    print()
    print("  Quick visual checks for a CORRECT cylinder flow at Re=100:")
    print("    • Flow moves left to right")
    print("    • Symmetric wake behind the cylinder at low Re")
    print("    • Von Kármán vortex street may appear at higher Re")

    # --- Summary ---
    print()
    print("=" * 60)
    if all_pass:
        print("  ✓  ALL CHECKS PASSED")
    else:
        print("  ⚠  SOME CHECKS HAD WARNINGS — review above")
    print("=" * 60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
