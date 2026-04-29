# Implementation Plan

This plan translates `LBM_HPC_Project_Requirements.docx` into a practical 4-day project schedule.

## Day 1: Core Solver and Baseline

- Create the D2Q9 lattice data model.
- Implement BGK collision and streaming.
- Add lid-driven cavity and cylinder-flow setup.
- Add boundary handling for walls, inlet, and outlet.
- Write serial benchmark timing and CSV output.
- Generate basic velocity magnitude images.

Deliverable: serial solver with measurable output.

## Day 2: OpenMP Parallel Backend

- Parallelize the main collision/streaming loop.
- Run thread counts `1`, `2`, `4`, `8`, and `16`.
- Record wall time, MLUPS, speedup, and efficiency.
- Compare OpenMP output against serial results for sanity.

Deliverable: OpenMP backend with benchmark table.

## Day 3: MPI and CUDA Extension

- Replace MPI scaffold with 1D horizontal slab decomposition.
- Add halo rows and non-blocking `MPI_Isend` / `MPI_Irecv` exchanges.
- Measure communication time separately from compute time.
- Replace CUDA scaffold with three kernels: collision, streaming, boundary update.
- Profile CUDA kernel time, bandwidth, and occupancy with NVIDIA tools.

Deliverable: distributed and GPU backend evidence.

## Day 4: Results, Report, and Presentation

- Run final benchmark matrix across grid sizes and backends.
- Produce charts for elapsed time, speedup, efficiency, and MLUPS.
- Capture velocity images for cavity and cylinder cases.
- Write IEEE-style paper and technical report.
- Prepare 10-12 slide presentation.

Deliverable: complete submission package.

## Acceptance Checklist

- Project builds cleanly with CMake.
- Serial and OpenMP simulations run from the command line.
- CSV metrics are produced for every benchmark run.
- Velocity image output is generated.
- README explains setup, build, run, and outputs.
- File guide explains the role of each project file.
- MPI and CUDA paths are documented and ready for extension.
