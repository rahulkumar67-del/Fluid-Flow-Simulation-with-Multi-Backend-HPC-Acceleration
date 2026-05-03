#!/usr/bin/env bash
# =============================================================================
# Paper Benchmark Script
# Generates ALL data needed for the IEEE paper figures and tables.
#
# Usage:  bash scripts/paper_benchmarks.sh
# Output: results/paper_benchmarks.csv  +  results/paper_*.png (velocity images)
#         results/convergence.csv        (grid convergence study)
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${PROJECT_DIR}/build"
RESULTS_DIR="${PROJECT_DIR}/results"
CSV="${RESULTS_DIR}/paper_benchmarks.csv"
CONV_CSV="${RESULTS_DIR}/convergence.csv"
EXE="${BUILD_DIR}/lbm_sim"

# ---------- Configuration ----------
GRIDS_CAVITY=("64 64" "128 128" "256 256" "512 512")
GRIDS_CYLINDER=("128 64" "256 128" "512 256")
REYNOLDS_VALUES=(100 400)
STEPS=2000
OMP_THREADS=(1 2 4 8)

# Check for MPI
HAS_MPI=false
if command -v mpirun &>/dev/null; then
    HAS_MPI=true
    echo "[INFO] MPI detected."
else
    echo "[INFO] MPI not found. Skipping MPI benchmarks."
    echo "       Install with: sudo apt install -y openmpi-bin libopenmpi-dev"
fi

# ---------- Build ----------
echo ""
echo "============================================"
echo "  BUILDING PROJECT (Serial + OpenMP + MPI)"
echo "============================================"

cd "$PROJECT_DIR"

CMAKE_OPTS="-DENABLE_OPENMP=ON -DENABLE_CUDA=OFF"
if $HAS_MPI; then
    CMAKE_OPTS="$CMAKE_OPTS -DENABLE_MPI=ON"
fi

cmake -S . -B build $CMAKE_OPTS 2>&1 | tail -5
cmake --build build --config Release -j "$(nproc)" 2>&1 | tail -3

if [ ! -f "$EXE" ]; then
    if [ -f "${BUILD_DIR}/Release/lbm_sim" ]; then
        EXE="${BUILD_DIR}/Release/lbm_sim"
    else
        echo "[ERROR] Cannot find lbm_sim executable!"
        exit 1
    fi
fi
echo "[OK] Executable: $EXE"

# ---------- Prepare ----------
mkdir -p "$RESULTS_DIR"
rm -f "$CSV" "$CONV_CSV"

run_count=0
total_start=$(date +%s)

# ==========================================================================
# PART 1: Performance benchmarks (cavity, Re=100)
# ==========================================================================
echo ""
echo "============================================"
echo "  PART 1: PERFORMANCE BENCHMARKS (CAVITY)"
echo "============================================"

RE=100
for grid in "${GRIDS_CAVITY[@]}"; do
    read -r nx ny <<< "$grid"
    tag="cavity_${nx}x${ny}"

    # --- Serial ---
    echo "  >> Serial | cavity | ${nx}x${ny}"
    "$EXE" --backend serial --case cavity --nx "$nx" --ny "$ny" \
           --steps $STEPS --re $RE \
           --output "$CSV" --image "${RESULTS_DIR}/paper_${tag}_serial.png"
    run_count=$((run_count + 1))

    # --- OpenMP ---
    for t in "${OMP_THREADS[@]}"; do
        echo "  >> OpenMP ${t}T | cavity | ${nx}x${ny}"
        OMP_NUM_THREADS=$t "$EXE" \
            --backend openmp --case cavity --nx "$nx" --ny "$ny" \
            --steps $STEPS --re $RE \
            --output "$CSV" --image "${RESULTS_DIR}/paper_${tag}_omp${t}.png"
        run_count=$((run_count + 1))
    done

    # --- MPI ---
    if $HAS_MPI; then
        for np in 1 2 4; do
            echo "  >> MPI ${np}p | cavity | ${nx}x${ny}"
            mpirun --oversubscribe -np "$np" "$EXE" \
                --backend mpi --case cavity --nx "$nx" --ny "$ny" \
                --steps $STEPS --re $RE \
                --output "$CSV" --image "${RESULTS_DIR}/paper_${tag}_mpi${np}.png"
            run_count=$((run_count + 1))
        done
    fi
done

# ==========================================================================
# PART 2: Cylinder flow benchmarks
# ==========================================================================
echo ""
echo "============================================"
echo "  PART 2: CYLINDER FLOW BENCHMARKS"
echo "============================================"

for grid in "${GRIDS_CYLINDER[@]}"; do
    read -r nx ny <<< "$grid"
    tag="cylinder_${nx}x${ny}"

    echo "  >> Serial | cylinder | ${nx}x${ny}"
    "$EXE" --backend serial --case cylinder --nx "$nx" --ny "$ny" \
           --steps $STEPS --re $RE \
           --output "$CSV" --image "${RESULTS_DIR}/paper_${tag}_serial.png"
    run_count=$((run_count + 1))

    for t in "${OMP_THREADS[@]}"; do
        echo "  >> OpenMP ${t}T | cylinder | ${nx}x${ny}"
        OMP_NUM_THREADS=$t "$EXE" \
            --backend openmp --case cylinder --nx "$nx" --ny "$ny" \
            --steps $STEPS --re $RE \
            --output "$CSV" --image "${RESULTS_DIR}/paper_${tag}_omp${t}.png"
        run_count=$((run_count + 1))
    done
done

# ==========================================================================
# PART 3: Grid convergence study (cavity, Re=100, serial)
# ==========================================================================
echo ""
echo "============================================"
echo "  PART 3: GRID CONVERGENCE STUDY"
echo "============================================"

CONV_GRIDS=("32 32" "64 64" "128 128" "256 256" "512 512")
for grid in "${CONV_GRIDS[@]}"; do
    read -r nx ny <<< "$grid"
    echo "  >> Convergence | cavity | ${nx}x${ny}"
    "$EXE" --backend serial --case cavity --nx "$nx" --ny "$ny" \
           --steps 5000 --re 100 \
           --output "$CONV_CSV" --image "${RESULTS_DIR}/paper_conv_${nx}.png"
    run_count=$((run_count + 1))
done

# ==========================================================================
# PART 4: Reynolds number comparison
# ==========================================================================
echo ""
echo "============================================"
echo "  PART 4: REYNOLDS NUMBER COMPARISON"
echo "============================================"

for re in "${REYNOLDS_VALUES[@]}"; do
    echo "  >> Serial | cavity | 256x256 | Re=${re}"
    "$EXE" --backend serial --case cavity --nx 256 --ny 256 \
           --steps 3000 --re "$re" \
           --output "$CSV" --image "${RESULTS_DIR}/paper_cavity_256_re${re}.png"
    run_count=$((run_count + 1))

    echo "  >> Serial | cylinder | 256x128 | Re=${re}"
    "$EXE" --backend serial --case cylinder --nx 256 --ny 128 \
           --steps 3000 --re "$re" \
           --output "$CSV" --image "${RESULTS_DIR}/paper_cylinder_256_re${re}.png"
    run_count=$((run_count + 1))
done

# ---------- Done ----------
total_end=$(date +%s)
elapsed=$((total_end - total_start))

echo ""
echo "============================================"
echo "  ALL BENCHMARKS COMPLETE"
echo "============================================"
echo "  Runs:     $run_count"
echo "  Time:     ${elapsed}s"
echo "  CSV:      $CSV"
echo "  Conv CSV: $CONV_CSV"
echo ""
echo "  Next: python3 scripts/paper_plots.py"
