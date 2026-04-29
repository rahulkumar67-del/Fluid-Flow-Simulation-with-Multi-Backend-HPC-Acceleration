#include "lbm.hpp"
#include "stb_image_write.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <stdexcept>

namespace lbm {

const std::array<int, Q> CX = {0, 1, 0, -1, 0, 1, -1, -1, 1};
const std::array<int, Q> CY = {0, 0, 1, 0, -1, 1, 1, -1, -1};
const std::array<int, Q> OPPOSITE = {0, 3, 4, 1, 2, 7, 8, 5, 6};
const std::array<double, Q> W = {4.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0,
                                 1.0 / 36.0, 1.0 / 36.0, 1.0 / 36.0, 1.0 / 36.0};

Lattice::Lattice(Config config) : config_(std::move(config)) {
    if (config_.nx < 8 || config_.ny < 8) {
        throw std::invalid_argument("Grid must be at least 8x8.");
    }
    const double length = static_cast<double>(std::max(config_.nx, config_.ny));
    const double nu = config_.u_lid * length / config_.reynolds;
    omega_ = 1.0 / (3.0 * nu + 0.5);
    const std::size_t cells = cell_count();
    f.assign(cells * Q, 0.0);
    next.assign(cells * Q, 0.0);
    rho.assign(cells, 1.0);
    ux.assign(cells, 0.0);
    uy.assign(cells, 0.0);
    solid.assign(cells, 0);
}

std::size_t Lattice::idx(int x, int y) const {
    return static_cast<std::size_t>(y) * config_.nx + x;
}

std::size_t Lattice::fidx(int x, int y, int q) const {
    return idx(x, y) * Q + q;
}

void Lattice::initialise() {
    std::fill(rho.begin(), rho.end(), 1.0);
    std::fill(ux.begin(), ux.end(), 0.0);
    std::fill(uy.begin(), uy.end(), 0.0);
    std::fill(solid.begin(), solid.end(), 0);

    if (config_.case_name == "cylinder") {
        const int cx = config_.nx / 4;
        const int cy = config_.ny / 2;
        const int radius = std::max(3, std::min(config_.nx, config_.ny) / 12);
        for (int y = 0; y < config_.ny; ++y) {
            for (int x = 0; x < config_.nx; ++x) {
                const int dx = x - cx;
                const int dy = y - cy;
                if (dx * dx + dy * dy <= radius * radius) {
                    solid[idx(x, y)] = 1;
                }
            }
        }
    }

    for (int y = 0; y < config_.ny; ++y) {
        for (int x = 0; x < config_.nx; ++x) {
            const std::size_t i = idx(x, y);
            const double vx = (config_.case_name == "cylinder") ? config_.u_inlet : 0.0;
            ux[i] = solid[i] ? 0.0 : vx;
            for (int q = 0; q < Q; ++q) {
                f[fidx(x, y, q)] = equilibrium(q, rho[i], ux[i], uy[i]);
            }
        }
    }
    next = f;
}

void Lattice::swap_distributions() {
    f.swap(next);
}

double equilibrium(int q, double density, double vx, double vy) {
    const double cu = 3.0 * (CX[q] * vx + CY[q] * vy);
    const double uu = 1.5 * (vx * vx + vy * vy);
    return W[q] * density * (1.0 + cu + 0.5 * cu * cu - uu);
}

double collide_stream_cell(const Lattice& lattice, Lattice& out, int x, int y) {
    const std::size_t cell = lattice.idx(x, y);
    if (lattice.solid[cell]) {
        for (int q = 0; q < Q; ++q) {
            out.next[lattice.fidx(x, y, OPPOSITE[q])] = lattice.f[lattice.fidx(x, y, q)];
        }
        out.rho[cell] = 1.0;
        out.ux[cell] = 0.0;
        out.uy[cell] = 0.0;
        return 0.0;
    }

    double density = 0.0;
    double vx = 0.0;
    double vy = 0.0;
    for (int q = 0; q < Q; ++q) {
        const double value = lattice.f[lattice.fidx(x, y, q)];
        density += value;
        vx += value * CX[q];
        vy += value * CY[q];
    }
    vx /= density;
    vy /= density;

    out.rho[cell] = density;
    out.ux[cell] = vx;
    out.uy[cell] = vy;

    for (int q = 0; q < Q; ++q) {
        const double relaxed = lattice.f[lattice.fidx(x, y, q)] -
                               lattice.omega() * (lattice.f[lattice.fidx(x, y, q)] - equilibrium(q, density, vx, vy));
        const int tx = x + CX[q];
        const int ty = y + CY[q];
        if (tx > 0 && tx < lattice.nx() - 1 && ty > 0 && ty < lattice.ny() - 1 &&
            !lattice.solid[lattice.idx(tx, ty)]) {
            out.next[lattice.fidx(tx, ty, q)] = relaxed;
        } else {
            out.next[lattice.fidx(x, y, OPPOSITE[q])] = relaxed;
        }
    }
    return vx * vx + vy * vy;
}

void apply_boundaries(Lattice& lattice) {
    const Config& cfg = lattice.config();
    for (int x = 0; x < cfg.nx; ++x) {
        const double lid_u = (cfg.case_name == "cavity") ? cfg.u_lid : 0.0;
        const std::size_t top = lattice.idx(x, cfg.ny - 1);
        lattice.rho[top] = 1.0;
        lattice.ux[top] = lid_u;
        lattice.uy[top] = 0.0;
        for (int q = 0; q < Q; ++q) {
            lattice.next[lattice.fidx(x, cfg.ny - 1, q)] = equilibrium(q, 1.0, lid_u, 0.0);
            lattice.next[lattice.fidx(x, 0, q)] = equilibrium(q, 1.0, 0.0, 0.0);
        }
    }

    for (int y = 0; y < cfg.ny; ++y) {
        const double inlet_u = (cfg.case_name == "cylinder") ? cfg.u_inlet : 0.0;
        for (int q = 0; q < Q; ++q) {
            lattice.next[lattice.fidx(0, y, q)] = equilibrium(q, 1.0, inlet_u, 0.0);
            lattice.next[lattice.fidx(cfg.nx - 1, y, q)] = lattice.next[lattice.fidx(cfg.nx - 2, y, q)];
        }
        lattice.ux[lattice.idx(0, y)] = inlet_u;
        lattice.uy[lattice.idx(0, y)] = 0.0;
    }
}

double compute_l2_error(const Lattice& current, const std::vector<double>& prev_ux, const std::vector<double>& prev_uy) {
    double numerator = 0.0;
    double denominator = 0.0;
    for (std::size_t i = 0; i < current.cell_count(); ++i) {
        const double du = current.ux[i] - prev_ux[i];
        const double dv = current.uy[i] - prev_uy[i];
        numerator += du * du + dv * dv;
        denominator += current.ux[i] * current.ux[i] + current.uy[i] * current.uy[i];
    }
    return std::sqrt(numerator / std::max(denominator, 1.0e-30));
}

static void ensure_parent(const std::string& path) {
    const std::filesystem::path p(path);
    if (p.has_parent_path()) {
        std::filesystem::create_directories(p.parent_path());
    }
}

void write_csv_header_if_needed(const std::string& path) {
    ensure_parent(path);
    if (std::filesystem::exists(path) && std::filesystem::file_size(path) > 0) {
        return;
    }
    std::ofstream out(path);
    out << "backend,case,nx,ny,steps,reynolds,elapsed_seconds,mlups,final_l2,communication_seconds\n";
}

void append_metrics_csv(const std::string& path, const Config& config, const Metrics& metrics) {
    write_csv_header_if_needed(path);
    std::ofstream out(path, std::ios::app);
    out << config.backend << ',' << config.case_name << ',' << config.nx << ',' << config.ny << ','
        << metrics.steps_executed << ',' << config.reynolds << ',' << std::fixed << std::setprecision(6)
        << metrics.elapsed_seconds << ',' << metrics.mlups << ',' << std::scientific << metrics.final_l2 << ','
        << std::fixed << metrics.communication_seconds << '\n';
}

void write_velocity_png(const std::string& path, const Lattice& lattice) {
    ensure_parent(path);
    double max_speed = 1.0e-12;
    for (std::size_t i = 0; i < lattice.cell_count(); ++i) {
        max_speed = std::max(max_speed, std::hypot(lattice.ux[i], lattice.uy[i]));
    }

    const int w = lattice.nx();
    const int h = lattice.ny();
    std::vector<unsigned char> pixels(static_cast<std::size_t>(w) * h * 3);

    for (int y = h - 1; y >= 0; --y) {
        for (int x = 0; x < w; ++x) {
            const std::size_t i = lattice.idx(x, y);
            const double t = std::min(1.0, std::hypot(lattice.ux[i], lattice.uy[i]) / max_speed);
            const std::size_t pi = (static_cast<std::size_t>(h - 1 - y) * w + x) * 3;
            pixels[pi + 0] = static_cast<unsigned char>(255.0 * t);
            pixels[pi + 1] = static_cast<unsigned char>(255.0 * (1.0 - std::abs(t - 0.5) * 2.0));
            pixels[pi + 2] = static_cast<unsigned char>(255.0 * (1.0 - t));
        }
    }

    stbi_write_png(path.c_str(), w, h, 3, pixels.data(), w * 3);
}

} // namespace lbm
