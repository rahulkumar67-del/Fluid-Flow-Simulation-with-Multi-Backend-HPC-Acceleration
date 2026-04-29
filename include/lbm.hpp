#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace lbm {

constexpr int Q = 9;

struct Config {
    int nx = 128;
    int ny = 128;
    int steps = 1000;
    int output_every = 100;
    double reynolds = 100.0;
    double u_lid = 0.08;
    double u_inlet = 0.06;
    double convergence = 1.0e-6;
    std::string case_name = "cavity";
    std::string backend = "serial";
    std::string output_csv = "results/run.csv";
    std::string image_path = "results/velocity.png";
};

struct Metrics {
    int steps_executed = 0;
    double elapsed_seconds = 0.0;
    double mlups = 0.0;
    double final_l2 = 0.0;
    double communication_seconds = 0.0;
};

class Lattice {
public:
    explicit Lattice(Config config);

    const Config& config() const { return config_; }
    int nx() const { return config_.nx; }
    int ny() const { return config_.ny; }
    double omega() const { return omega_; }
    std::size_t cell_count() const { return static_cast<std::size_t>(config_.nx) * config_.ny; }

    std::size_t idx(int x, int y) const;
    std::size_t fidx(int x, int y, int q) const;
    void initialise();
    void swap_distributions();

    std::vector<double> f;
    std::vector<double> next;
    std::vector<double> rho;
    std::vector<double> ux;
    std::vector<double> uy;
    std::vector<unsigned char> solid;

private:
    Config config_;
    double omega_ = 1.0;
};

extern const std::array<int, Q> CX;
extern const std::array<int, Q> CY;
extern const std::array<int, Q> OPPOSITE;
extern const std::array<double, Q> W;

double equilibrium(int q, double density, double vx, double vy);
double collide_stream_cell(const Lattice& lattice, Lattice& out, int x, int y);
void apply_boundaries(Lattice& lattice);
double compute_l2_error(const Lattice& current, const std::vector<double>& prev_ux, const std::vector<double>& prev_uy);
void write_csv_header_if_needed(const std::string& path);
void append_metrics_csv(const std::string& path, const Config& config, const Metrics& metrics);
void write_velocity_png(const std::string& path, const Lattice& lattice);

Metrics run_serial(Lattice& lattice);
Metrics run_openmp(Lattice& lattice);
Metrics run_mpi(const Config& config);

} // namespace lbm


