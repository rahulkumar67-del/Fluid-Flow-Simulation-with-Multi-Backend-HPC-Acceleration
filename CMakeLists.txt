cmake_minimum_required(VERSION 3.16)
project(lbm_hpc LANGUAGES CXX)

option(ENABLE_OPENMP "Build OpenMP backend when OpenMP is available" ON)
option(ENABLE_MPI "Build MPI backend" OFF)
option(ENABLE_CUDA "Build CUDA backend" OFF)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(lbm_core
    src/lbm.cpp
    src/serial_backend.cpp
    src/stb_image_write_impl.cpp
)
target_include_directories(lbm_core PUBLIC include)
target_compile_options(lbm_core PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall -Wextra -Wpedantic>
)

if(ENABLE_OPENMP)
    find_package(OpenMP)
    if(OpenMP_CXX_FOUND)
        target_sources(lbm_core PRIVATE src/openmp_backend.cpp)
        target_link_libraries(lbm_core PUBLIC OpenMP::OpenMP_CXX)
        target_compile_definitions(lbm_core PUBLIC LBM_ENABLE_OPENMP=1)
    endif()
endif()

if(ENABLE_MPI)
    find_package(MPI REQUIRED)
    target_sources(lbm_core PRIVATE src/mpi_backend.cpp)
    target_link_libraries(lbm_core PUBLIC MPI::MPI_CXX)
    target_compile_definitions(lbm_core PUBLIC LBM_ENABLE_MPI=1)
endif()

add_executable(lbm_sim src/main.cpp)
target_link_libraries(lbm_sim PRIVATE lbm_core)

if(ENABLE_CUDA)
    enable_language(CUDA)
    add_executable(lbm_cuda src/cuda_backend.cu)
    target_include_directories(lbm_cuda PRIVATE include)
    set_target_properties(lbm_cuda PROPERTIES CUDA_STANDARD 17 CUDA_STANDARD_REQUIRED ON)
endif()
