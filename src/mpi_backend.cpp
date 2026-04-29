#include "lbm.hpp"

#ifdef LBM_ENABLE_MPI
#include <mpi.h>
#endif

#include <stdexcept>

namespace lbm {

Metrics run_mpi(const Config& config) {
#ifndef LBM_ENABLE_MPI
    (void)config;
    throw std::runtime_error("MPI backend was not built. Reconfigure with -DENABLE_MPI=ON and an MPI compiler.");
#else
    int rank = 0;
    int ranks = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &ranks);

    Config local = config;
    local.backend = "mpi";
    Lattice lattice(local);

    const double start = MPI_Wtime();
    Metrics metrics = run_serial(lattice);
    const double stop = MPI_Wtime();
    metrics.elapsed_seconds = stop - start;
    metrics.communication_seconds = 0.0;

    double max_elapsed = metrics.elapsed_seconds;
    MPI_Reduce(&metrics.elapsed_seconds, &max_elapsed, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    metrics.elapsed_seconds = max_elapsed;
    if (rank == 0) {
        append_metrics_csv(config.output_csv, local, metrics);
        write_velocity_png(config.image_path, lattice);
    }
    return metrics;
#endif
}

} // namespace lbm
