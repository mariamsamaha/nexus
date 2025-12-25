# 🌌 Nexus: Parallel Image Processing - Edge Detection

## Project Overview

**Nexus** is a scalable parallel and distributed system engineered for **high-performance edge detection** in images. The core goal of this project is to explore and implement various parallelism and distribution strategies to achieve measurable **speedup**, robust **scalability**, and effective **fault tolerance** in image processing tasks.

---

## 🎯 Key Features and Goals

- **High-Performance Edge Detection:** Implementing established algorithms (e.g., Canny, Sobel) with a focus on speed.
- **Parallel Computing:** Utilizing multi-core architectures to process image data concurrently.
- **Distributed Scalability:** Spreading the workload across multiple machines/nodes for handling large datasets.
- **Fault Tolerance:** Designing the system to continue operation even if individual nodes or processes fail.
- **Performance Benchmarking:** Rigorous measurement and comparison of speedup across the different implementation phases.

---

## 🗺️ Project Phases

The development of Nexus is structured into three progressive phases, each building upon the previous one to introduce increasingly complex and powerful computing paradigms:

### Phase 1: Shared-Memory Parallelism (Single-Node Optimization) ⚡

- **Focus:** Implementing **threads** and/or **processes** (e.g., using OpenMP, pthreads, or language-native features) to leverage multi-core CPUs.
- **Goal:** Demonstrate initial, significant speedup compared to a sequential implementation on a single machine.
- **Implementation:** Parallelization of core image filtering and gradient computation steps.

### Phase 2: Distributed Computing (Multi-Node Scaling) 🌐

- **Focus:** Moving to a multi-node environment using a message-passing interface (e.g., **MPI** or similar RPC framework).
- **Goal:** Achieve horizontal scalability by partitioning image data and processing it across a cluster of machines.
- **Implementation:** Development of communication protocols for data distribution, synchronization, and result aggregation.

### Phase 3: Big Data Processing & Fault Tolerance 🛡️

- **Focus:** Integrating a **big-data framework** (e.g., Apache Spark, Hadoop MapReduce) to manage large-scale data and inherent fault tolerance.
- **Goal:** Process massive datasets (e.g., video streams, large image archives) efficiently while ensuring the system can recover from node failures without losing data.
- **Implementation:** Adapt the edge detection logic to run as a distributed job within the chosen framework, utilizing its built-in mechanisms for resilience and scheduling.

---

## 🛠️ Technologies

---

## 🚀 Getting Started

Below is the minimal end-to-end flow: convert inputs as needed, run the Sobel edge detector, and (optionally) convert the result to PNG.

### 1) Dependencies

- C build tools (clang/gcc)
- Python 3
- Python: Pillow (for conversions)

Install Pillow:

```bash
python3 -m pip install --user Pillow
```

### 2) Build the sequential Sobel tool

The `sequential` binary reads any common image via `stb_image.h` (e.g., JPEG/PNG) and outputs a PGM edge map.

```bash
# Example (adjust if you have a different build setup)
clang -O2 -o sequential src/sequential.c -lm
```

### 3) Convert input (optional)

If you prefer/need to work with PGM explicitly, you can convert images first:

```bash
python3 convert_to_pgm.py data/dog.jpg data/dog.pgm
```

### 4) Run edge detection

Usage:

```bash
./sequential <input_image> <output_edges.pgm> [threshold]
```

- `input_image`: JPEG/PNG/PGM supported
- `output_edges.pgm`: binary PGM edge map
- `threshold` (optional): 0–255, default 100

Example:

```bash
./sequential data/dog.jpg data/dog_edges.pgm 100
```

### 5) Convert PGM edges to PNG (optional)

```bash
python3 convert_to_png.py data/dog_edges.pgm data/dog_edges.png
```

If you do not have Pillow, you can install it as above. Alternatively, install ImageMagick and use `convert` directly:

```bash
brew install imagemagick
convert data/dog_edges.pgm data/dog_edges.png
```

### Notes

- `stb_image.h` is a single-header loader included in `src/` that lets the C program read common formats without extra libraries. If you want to remove it, restrict inputs to PGM and run conversions beforehand.

---

# 🧪 test.c — Memory Benchmark (Stride / Block Access)

This benchmark tests how memory access patterns affect performance, useful for analyzing cache locality and bandwidth during Phase 1 optimization.

---

## *Build*

```bash
# Linux / macOS
gcc -O3 -march=native -std=c11 -o memtest src/test.c -lm
# or
clang -O3 -march=native -std=c11 -o memtest src/test.c -lm
```
---

## *Usage*

```bash
./memtest <mode> <param> [iters=5] [array_MB=512]
```
Modes:
* stride <stride_in_elements> walks memory with a fixed stride (tests spatial locality).
Example:
```bash
./memtest stride 1 5 512
```
* block <block_size_in_elems> processes memory in 2D tiles (models tiling/local reuse).
Example:
```bash
./memtest block 64 5 512
```
Output: per-iteration time, accesses, bytes read, average access time (ns), checksum, and bandwidth (MB/s).

---

## *Collecting Hardware Counters (Linux)*
```bash
sudo perf stat -e cycles,instructions,cache-references,cache-misses,L1-dcache-loads,L1-dcache-load-misses \
-o perf_stride_1.txt ./memtest stride 1 5 512
```
Run a sweep for multiple strides:
```bash
for s in 1 2 4 8 16 32 64 128 256 512 1024; do
  echo "stride=$s"
  sudo perf stat -e cycles,instructions,cache-references,cache-misses,L1-dcache-loads,L1-dcache-load-misses \
    -o perf_stride_${s}.txt ./memtest stride $s 5 512
done
```
Tip: Pin to one core for reproducibility:
```bash
taskset -c 0 sudo perf stat -e ... ./memtest stride 1 5 512
```

---

# 🌐 Phase 2: Distributed Computing (MPI)

This phase implements the Sobel Edge Detector using **MPI (Message Passing Interface)** for distributed memory systems. It includes domain decomposition, halo exchange, and performance benchmarking.

## 📂 Directory Structure

```
phase2/
├── src/
│   ├── sobel_mbi.c            # Main MPI implementation
│   ├── mpi_latency_bandwidth.c # Network microbenchmark
│   └── stb_image.h            # Image loading library
├── run_scripts/
│   ├── run_strong_scaling.sh  # Script for strong scaling test
│   ├── run_weak_scaling.sh    # Script for weak scaling test
│   └── run_latency_bandwidth.sh # Script for latency/bandwidth test
├── plots/
│   ├── scaling_plot.py        # Generates scaling graphs
│   └── bandwidth_plot.py      # Generates latency/bandwidth graphs
└── results/                   # Output CSVs and PNG plots
```

## 🛠️ Compilation

You need an MPI implementation (e.g., OpenMPI, MPICH) installed.

### 1. Compile the Sobel Application
```bash
mpicc -O3 -std=c99 -o phase2/src/sobel_mbi phase2/src/sobel_mbi.c -lm
```

### 2. Compile the Microbenchmark
```bash
mpicc -O3 -std=c99 -o phase2/src/mpi_latency_bandwidth phase2/src/mpi_latency_bandwidth.c
```

## 🚀 Running Experiments

We provide automated scripts to run the benchmarks. Ensure you are in the project root directory.

### 1. Latency & Bandwidth
Measures point-to-point communication performance (ping-pong and streaming).
```bash
./phase2/run_scripts/run_latency_bandwidth.sh
```
*   **Output**: `phase2/results/latency_bandwidth/latency_bandwidth.csv`

### 2. Strong Scaling
Measures speedup with a fixed problem size (`dog.jpg`) as ranks increase (1, 2, 4, 8, 16).
```bash
./phase2/run_scripts/run_strong_scaling.sh
```
*   **Output**: `phase2/results/strong_scaling/strong_scaling.csv`

### 3. Weak Scaling
Measures efficiency with a fixed workload per rank (image size increases with ranks).
```bash
./phase2/run_scripts/run_weak_scaling.sh
```
*   **Output**: `phase2/results/weak_scaling/weak_scaling.csv`

## 📊 Generating Plots

Python scripts are provided to visualize the results. Requires `pandas` and `matplotlib`.

```bash
# Install dependencies (if needed)
pip install pandas matplotlib

# Generate Latency/Bandwidth Plot
python3 phase2/plots/bandwidth_plot.py

# Generate Scaling Plots (Speedup & Efficiency)
python3 phase2/plots/scaling_plot.py
```

Plots will be saved in the respective `phase2/results/` subdirectories.

---

# 🔌 Phase 3: gRPC-Based Distributed Edge Detection

Phase 3 builds on Phase 2 by introducing a remote procedure call (RPC) interface using gRPC, enabling distributed and modular execution of the Sobel edge detector while tracking request/response times.

## 📂 Directory Structure

```
phase3/
├── proto/                  # Protobuf definitions
│   └── sobel.proto
├── server/                 # gRPC server
│   ├── sobel_server.py
│   ├── sobel_pb2.py
│   └── sobel_pb2_grpc.py
├── client/                 # gRPC client
│   └── sobel_client.py
├── logs/                   # Output edge maps
└── README.md
```

## 🛠️ Setup

### 1. Create Python 3.12 Virtual Environment

```bash
python3.12 -m venv .venv312
source .venv312/bin/activate
```

### 2. Install Dependencies

```bash
pip install grpcio grpcio-tools
```

### 3. Generate gRPC Python Code

From the `phase3/` directory:

```bash
python -m grpc_tools.protoc -I proto --python_out=server --grpc_python_out=server proto/sobel.proto
```

This generates `sobel_pb2.py` and `sobel_pb2_grpc.py` in the `server/` directory.

### 4. Build the Sobel Executable (from Phase 2)

Ensure the MPI Sobel executable is built and executable:

```bash
cd phase2/src
mpicc -O3 -std=c99 -o sobel_mbi sobel_mbi.c -lm
chmod +x sobel_mbi
```

## 🚀 Running the gRPC Server

**Open a terminal** and navigate to the `phase3/` directory:

```bash
cd phase3
python server/sobel_server.py
```

**Server Details:**
- Listens on port `50051`
- Logs request timestamps and processing durations
- Outputs PGM edge maps in `phase3/logs/`
- Uses MPI with 4 processes by default
- **Keep this terminal running** - the server will continue listening for requests

## 🚀 Running the gRPC Client

**Open a separate terminal** and navigate to the `phase3/client/` directory:

```bash
cd phase3/client
python sobel_client.py
```

**Client Behavior:**
- Sends a Sobel edge detection request to the server
- Processes the image specified in the client code (default: `data/dog_edges.png`)
- Prints:
  - `output_path`: Path to the generated edge map
  - `start_time`: Request start time (milliseconds since epoch)
  - `end_time`: Request completion time (milliseconds since epoch)
  - `processing_time`: Total processing duration (ms)

**Important:** 
- The server must be running (in the first terminal) before starting the client
- You can run the client multiple times while the server is running
- Modify `sobel_client.py` to change the input image path or threshold value
