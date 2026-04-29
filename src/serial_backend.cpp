#include "lbm.hpp"

#include <algorithm>
#include <chrono>

namespace lbm {

Metrics run_serial(Lattice& lattice) {
    lattice.initialise();
    Metrics metrics;
    const auto start = std::chrono::steady_clock::now();
    double l2 = 1.0;

    for (int step = 1; step <= lattice.config().steps; ++step) {
        const std::vector<double> prev_ux = lattice.ux;
        const std::vector<double> prev_uy = lattice.uy;
        std::fill(lattice.next.begin(), lattice.next.end(), 0.0);

        for (int y = 1; y < lattice.ny() - 1; ++y) {
            for (int x = 1; x < lattice.nx() - 1; ++x) {
                collide_stream_cell(lattice, lattice, x, y);
            }
        }
        apply_boundaries(lattice);
        lattice.swap_distributions();

        if (step % lattice.config().output_every == 0) {
            l2 = compute_l2_error(lattice, prev_ux, prev_uy);
            if (l2 < lattice.config().convergence) {
                metrics.steps_executed = step;
                break;
            }
        }
        metrics.steps_executed = step;
    }

    const auto stop = std::chrono::steady_clock::now();
    metrics.elapsed_seconds = std::chrono::duration<double>(stop - start).count();
    metrics.final_l2 = l2;
    metrics.mlups = (static_cast<double>(lattice.cell_count()) * metrics.steps_executed) /
                    (metrics.elapsed_seconds * 1.0e6);
    return metrics;
}

} // namespace lbm
