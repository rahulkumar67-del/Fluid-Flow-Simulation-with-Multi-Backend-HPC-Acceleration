# Performance Analysis of LBM Fluid Simulation Across HPC Backends

This project implements a D2Q9 Lattice Boltzmann Method (LBM) fluid simulation for the HPSC requirement document. It supports lid-driven cavity and flow-past-cylinder cases, records benchmark metrics, and is structured for serial, OpenMP, MPI, and CUDA experimentation.

## Current Implementation Status

| Backend | Status | Notes |
| --- | --- | --- |
| Serial | Implemented | Baseline D2Q9 BGK solver |
| OpenMP | Implemented | Parallel collision/streaming loop when OpenMP is available |
| MPI | Build-gated scaffold | Source file and CMake option are present; domain decomposition is the next extension |
| CUDA | Build-gated scaffold | CUDA target is present for kernel implementation |

## Requirements Covered

- D2Q9 LBM with BGK collision operator
- Lid-driven cavity test case
- Flow past a cylinder test case with circular obstacle
- No-slip bounce-back style wall handling
- Velocity inlet and pressure-like outlet for cylinder flow
- Reynolds number, grid size, step count, backend, and output path options
- CSV benchmark output with elapsed time, MLUPS, final L2 error, and communication time field
- Velocity magnitude visualization as a `.ppm` image
- CMake and Makefile build entry points

## Build

### CMake

```powershell
cmake -S . -B build -DENABLE_OPENMP=ON
cmake --build build --config Release
```

### Make

```powershell
make build
```

If `make` is not installed on Windows, use the CMake commands above.

## Run

Serial cavity simulation:

```powershell
.\build\Release\lbm_sim.exe --backend serial --case cavity --nx 128 --ny 128 --steps 1000 --output results\serial.csv --image results\serial.ppm
```

OpenMP cavity simulation:

```powershell
.\build\Release\lbm_sim.exe --backend openmp --case cavity --nx 256 --ny 256 --steps 1000 --output results\openmp.csv --image results\openmp.ppm
```

Cylinder flow:

```powershell
.\build\Release\lbm_sim.exe --backend serial --case cylinder --nx 256 --ny 128 --steps 1500 --re 100 --output results\cylinder.csv --image results\cylinder.ppm
```

On single-config generators, the executable may be at:

```powershell
.\build\lbm_sim.exe
```

## Command Line Options

| Option | Default | Description |
| --- | --- | --- |
| `--backend` | `serial` | `serial`, `openmp`, or `mpi` |
| `--case` | `cavity` | `cavity` or `cylinder` |
| `--nx` | `128` | Grid width |
| `--ny` | `128` | Grid height |
| `--steps` | `1000` | Maximum time steps |
| `--output-every` | `100` | Convergence check interval |
| `--re` | `100` | Reynolds number |
| `--output` | `results/run.csv` | CSV metrics path |
| `--image` | `results/velocity.ppm` | Velocity image path |

## Benchmark Plan

Run all combinations required by the document:

- Grid sizes: `128x128`, `256x256`, `512x512`, `1024x1024`
- Reynolds numbers: `100`, `400`, `1000`
- Backends: `serial`, `openmp`, later `mpi`, later `cuda`
- OpenMP thread counts: `1`, `2`, `4`, `8`, `16`

Example OpenMP thread run:

```powershell
$env:OMP_NUM_THREADS=4
.\build\Release\lbm_sim.exe --backend openmp --case cavity --nx 512 --ny 512 --steps 1000 --output results\benchmarks.csv
```

## Outputs

- CSV metrics are appended to the selected output file.
- Velocity images are written as binary PPM files. They can be opened by image tools such as GIMP, ImageMagick, or many online PPM viewers.

## Plot Results

After running benchmarks:

```powershell
python scripts\plot_results.py results\benchmarks.csv results
```

This creates elapsed-time and MLUPS bar charts when `matplotlib` is available.
