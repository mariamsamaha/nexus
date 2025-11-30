#!/usr/bin/env bash
set -e

# Resolve absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

OUTDIR="$REPO_ROOT/phase2/results/strong_scaling"
mkdir -p "$OUTDIR"

BIN="$REPO_ROOT/phase2/src/sobel_mbi"
IMG="$REPO_ROOT/data/dog.jpg"
OUTPREFIX="$OUTDIR/output"
RANKS=(1 2 4 8 16)

echo "ranks,walltime_s" > "$OUTDIR/strong_scaling.csv"

for p in "${RANKS[@]}"; do
  echo "Running with $p ranks..."
  LOG="$OUTDIR/run_${p}.log"
  
  # Check if binary exists
  if [ ! -f "$BIN" ]; then
      echo "Error: Binary $BIN not found!"
      exit 1
  fi

  mpirun --oversubscribe -np $p "$BIN" "$IMG" "${OUTPREFIX}_${p}.pgm" > "$LOG" 2>&1 || { 
      echo "run failed, check $LOG"; 
      cat "$LOG"; # Print log to stdout on failure for debugging
      exit 1; 
  }
  
  # extract Max total runtime line
  WT=$(grep "Max total runtime" "$LOG" | awk '{print $4}')
  if [ -z "$WT" ]; then
    echo "Warning: couldn't find timing in $LOG. Dumping log:"
    tail -n 20 "$LOG"
    WT=0
  fi
  echo "${p},${WT}" >> "$OUTDIR/strong_scaling.csv"
done
echo "Saved: $OUTDIR/strong_scaling.csv"
