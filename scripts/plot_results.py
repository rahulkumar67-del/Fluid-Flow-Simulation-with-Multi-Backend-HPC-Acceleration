import csv
import sys
from pathlib import Path


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/plot_results.py results/benchmarks.csv results")
        return 1

    csv_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(csv_path)
    if not rows:
        print("No rows found.")
        return 1

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is required for plotting. Install it or use the CSV directly.")
        return 1

    labels = [f"{r['backend']}-{r['case']}-{r['nx']}x{r['ny']}" for r in rows]
    elapsed = [float(r["elapsed_seconds"]) for r in rows]
    mlups = [float(r["mlups"]) for r in rows]

    for values, ylabel, filename in [
        (elapsed, "Elapsed seconds", "elapsed_seconds.png"),
        (mlups, "MLUPS", "mlups.png"),
    ]:
        plt.figure(figsize=(max(8, len(labels) * 0.8), 5))
        plt.bar(labels, values)
        plt.ylabel(ylabel)
        plt.xticks(rotation=35, ha="right")
        plt.tight_layout()
        plt.savefig(out_dir / filename, dpi=180)
        plt.close()

    print(f"Wrote plots to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
