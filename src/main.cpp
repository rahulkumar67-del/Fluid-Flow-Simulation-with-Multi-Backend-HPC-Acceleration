#include "lbm.hpp"

#include <exception>
#include <iostream>
#include <string>

namespace {

void print_usage() {
    std::cout << "Usage: lbm_sim [--backend serial|openmp|mpi] [--case cavity|cylinder] "
                 "[--nx N] [--ny N] [--steps N] [--re Re] [--output file.csv] [--image file.ppm]\n";
}

lbm::Config parse_args(int argc, char** argv) {
    lbm::Config config;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        auto next = [&]() -> std::string {
            if (i + 1 >= argc) {
                throw std::invalid_argument("Missing value for " + arg);
            }
            return argv[++i];
        };
        if (arg == "--backend") config.backend = next();
        else if (arg == "--case") config.case_name = next();
        else if (arg == "--nx") config.nx = std::stoi(next());
        else if (arg == "--ny") config.ny = std::stoi(next());
        else if (arg == "--steps") config.steps = std::stoi(next());
        else if (arg == "--output-every") config.output_every = std::stoi(next());
        else if (arg == "--re") config.reynolds = std::stod(next());
        else if (arg == "--output") config.output_csv = next();
        else if (arg == "--image") config.image_path = next();
        else if (arg == "--help") {
            print_usage();
            std::exit(0);
        } else {
            throw std::invalid_argument("Unknown argument: " + arg);
        }
    }
    return config;
}

} // namespace

int main(int argc, char** argv) {
    try {
        lbm::Config config = parse_args(argc, argv);
        lbm::Metrics metrics;

        if (config.backend == "mpi") {
#ifdef LBM_ENABLE_MPI
            metrics = lbm::run_mpi(config);
            return 0;
#else
            throw std::invalid_argument("MPI backend was not enabled at build time");
#endif
        }

        lbm::Lattice lattice(config);
        if (config.backend == "serial") {
            metrics = lbm::run_serial(lattice);
        } else if (config.backend == "openmp") {
            metrics = lbm::run_openmp(lattice);
        } else {
            throw std::invalid_argument("Unsupported backend: " + config.backend);
        }

        lbm::append_metrics_csv(config.output_csv, config, metrics);
        lbm::write_velocity_png(config.image_path, lattice);

        std::cout << "Backend: " << config.backend << "\nCase: " << config.case_name
                  << "\nGrid: " << config.nx << "x" << config.ny
                  << "\nSteps: " << metrics.steps_executed
                  << "\nElapsed seconds: " << metrics.elapsed_seconds
                  << "\nMLUPS: " << metrics.mlups
                  << "\nFinal L2: " << metrics.final_l2
                  << "\nCSV: " << config.output_csv
                  << "\nImage: " << config.image_path << '\n';
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        print_usage();
        return 1;
    }
    return 0;
}
