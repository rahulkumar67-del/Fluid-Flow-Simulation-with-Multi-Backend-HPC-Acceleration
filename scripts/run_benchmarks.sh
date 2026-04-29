#!/usr/bin/env bash
# =============================================================================
# Benchmark Script: Runs serial, OpenMP, and (optionally) MPI backends
# across multiple grid sizes and saves results to a single CSV.
#
# Usage (from project root, inside WSL):
#   chmod +x scripts/run_benchmarks.sh
#   bash scripts/run_benchmarks.sh
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${PROJECT_DIR}/build"
RESULTS_DIR="${PROJECT_DIR}/results"
CSV_FILE="${RESULTS_DIR}/benchmarks.csv"
EXE="${BUILD_DIR}/lbm_sim"

# ---------- Configuration ----------
GRID_SIZES=("128 128" "256 256" "512 512")
CASES=("cavity" "cylinder")
REYNOLDS=100
STEPS=1000
OMP_THREADS=(1 2 4 8)

# Check for MPI
HAS_MPI=false
if command -v mpirun &>/dev/null; then
    HAS_MPI=true
    echo "[INFO] MPI detected. Will run MPI benchmarks."
else
    echo "[INFO] MPI not found. Skipping MPI benchmarks."
    echo "       Install with: sudo apt install -y openmpi-bin libopenmpi-dev"
fi

# ---------- Build ----------
echo ""
echo "=============================="
echo "  BUILDING PROJECT"
echo "=============================="

cd "$PROJECT_DIR"

CMAKE_OPTS="-DENABLE_OPENMP=ON -DENABLE_CUDA=OFF"
if $HAS_MPI; then
    CMAKE_OPTS="$CMAKE_OPTS -DENABLE_MPI=ON"
fi

cmake -S . -B build $CMAKE_OPTS
cmake --build build --config Release -j "$(nproc)"

if [ ! -f "$EXE" ]; then
    # Try Release subdirectory (multi-config generators)
    if [ -f "${BUILD_DIR}/Release/lbm_sim" ]; then
        EXE="${BUILD_DIR}/Release/lbm_sim"
    else
        echo "[ERROR] Cannot find lbm_sim executable!"
        exit 1
    fi
fi

echo "[OK] Executable: $EXE"

# ---------- Prepare results ----------
mkdir -p "$RESULTS_DIR"
# Remove old benchmark CSV to start fresh
rm -f "$CSV_FILE"

echo ""
echo "=============================="
echo "  RUNNING BENCHMARKS"
echo "=============================="

run_count=0

for case_name in "${CASES[@]}"; do
    for grid in "${GRID_SIZES[@]}"; do
        read -r nx ny <<< "$grid"
        img_base="${RESULTS_DIR}/${case_name}_${nx}x${ny}"

        # --- Serial ---
        echo ""
        echo ">> Serial | ${case_name} | ${nx}x${ny} | Re=${REYNOLDS}"
        "$EXE" --backend serial --case "$case_name" --nx "$nx" --ny "$ny" \
               --steps "$STEPS" --re "$REYNOLDS" \
               --output "$CSV_FILE" --image "${img_base}_serial.png"
        run_count=$((run_count + 1))

        # --- OpenMP with different thread counts ---
        for threads in "${OMP_THREADS[@]}"; do
            echo ">> OpenMP (${threads}T) | ${case_name} | ${nx}x${ny} | Re=${REYNOLDS}"
            OMP_NUM_THREADS=$threads "$EXE" \
                --backend openmp --case "$case_name" --nx "$nx" --ny "$ny" \
                --steps "$STEPS" --re "$REYNOLDS" \
                --output "$CSV_FILE" --image "${img_base}_openmp_${threads}t.png"
            run_count=$((run_count + 1))
        done

        # --- MPI (if available) ---
        if $HAS_MPI; then
            for np in 1 2 4; do
                echo ">> MPI (${np} ranks) | ${case_name} | ${nx}x${ny} | Re=${REYNOLDS}"
                mpirun --oversubscribe -np "$np" "$EXE" \
                    --backend mpi --case "$case_name" --nx "$nx" --ny "$ny" \
                    --steps "$STEPS" --re "$REYNOLDS" \
                    --output "$CSV_FILE" --image "${img_base}_mpi_${np}p.png"
                run_count=$((run_count + 1))
            done
        fi
    done
done

echo ""
echo "=============================="
echo "  BENCHMARKS COMPLETE"
echo "=============================="
echo "  Runs completed: $run_count"
echo "  Results CSV:    $CSV_FILE"
echo ""
echo "  Next step: Generate charts with:"
echo "    python3 scripts/plot_comparison.py results/benchmarks.csv results"
echo ""
echo "  Verify accuracy with:"
echo "    python3 scripts/verify_results.py results/benchmarks.csv"
