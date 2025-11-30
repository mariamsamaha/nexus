#!/usr/bin/env bash
set -e

# Resolve absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

OUTDIR="$REPO_ROOT/phase2/results/latency_bandwidth"
mkdir -p "$OUTDIR"

BIN="$REPO_ROOT/phase2/src/mpi_latency_bandwidth"
SRC="$REPO_ROOT/phase2/src/mpi_latency_bandwidth.c"

if [ ! -x "$BIN" ]; then
  echo "Building mpi_latency_bandwidth..."
  mpicc -O3 -std=c99 -o "$BIN" "$SRC"
fi

echo "Running latency/bandwidth microbench (2 ranks)..."
mpirun -np 2 "$BIN" 0 22 > "$OUTDIR/latency_bandwidth.csv"
echo "Saved: $OUTDIR/latency_bandwidth.csv"
