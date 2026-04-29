# How Things Work in This Folder

## Top-Level Files

| File | Purpose |
| --- | --- |
| `README.md` | Main setup, build, run, and benchmark instructions |
| `IMPLEMENTATION_PLAN.md` | Project roadmap based on the requirement document |
| `HOW_THINGS_WORK.md` | File-by-file explanation of the folder |
| `CMakeLists.txt` | Primary cross-platform build configuration |
| `Makefile` | Convenience wrapper around CMake commands |

## Source Code

| File | Purpose |
| --- | --- |
| `include/lbm.hpp` | Shared declarations for configuration, metrics, lattice storage, solver functions, and backend entry points |
| `src/main.cpp` | Command-line interface; parses arguments, selects backend, writes CSV and image outputs |
| `src/lbm.cpp` | Core D2Q9 constants, lattice initialization, equilibrium function, collision/streaming helper, boundaries, CSV writer, and PPM image writer |
| `src/serial_backend.cpp` | Serial baseline simulation loop |
| `src/openmp_backend.cpp` | OpenMP simulation loop using `#pragma omp parallel for` when OpenMP is enabled |
| `src/mpi_backend.cpp` | MPI-gated backend file; currently reports that MPI must be built/enabled before use |
| `src/cuda_backend.cu` | CUDA-gated backend scaffold for future GPU kernels |

## Scripts

| File | Purpose |
| --- | --- |
| `scripts/plot_results.py` | Reads benchmark CSV files and creates elapsed-time and MLUPS plots |

## Runtime Output

| Path | Purpose |
| --- | --- |
| `results/*.csv` | Benchmark rows appended by the executable |
| `results/*.ppm` | Velocity magnitude visualization images |

## Execution Flow

1. `src/main.cpp` reads command-line arguments into `lbm::Config`.
2. It creates a `lbm::Lattice`, which allocates all distribution and velocity arrays.
3. The selected backend runs the time-stepping loop.
4. Each time step performs collision, streaming, boundary updates, and distribution swapping.
5. Every `--output-every` steps, the solver checks relative L2 velocity change.
6. At the end, `src/main.cpp` appends a benchmark row to CSV and writes a velocity image.

## Important Concepts

| Concept | Meaning in This Project |
| --- | --- |
| `f` | Current D2Q9 particle distribution values |
| `next` | Next-step D2Q9 particle distribution values |
| `rho` | Fluid density per cell |
| `ux`, `uy` | Fluid velocity components |
| `solid` | Marks obstacle cells for bounce-back behavior |
| `omega` | BGK relaxation parameter derived from Reynolds number |
| `MLUPS` | Million lattice updates per second, used for performance comparison |
