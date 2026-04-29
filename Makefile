.PHONY: configure build run clean

BUILD_DIR ?= build
BACKEND ?= serial
NX ?= 128
NY ?= 128
STEPS ?= 1000
CASE ?= cavity

configure:
	cmake -S . -B $(BUILD_DIR) -DENABLE_OPENMP=ON

build: configure
	cmake --build $(BUILD_DIR) --config Release

run: build
	./$(BUILD_DIR)/lbm_sim --backend $(BACKEND) --case $(CASE) --nx $(NX) --ny $(NY) --steps $(STEPS) --output results/run.csv --image results/velocity.png

clean:
	cmake -E rm -rf $(BUILD_DIR)
