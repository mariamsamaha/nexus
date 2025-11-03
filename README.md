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
