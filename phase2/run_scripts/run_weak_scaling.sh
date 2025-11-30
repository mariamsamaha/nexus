#!/usr/bin/env bash
set -e

# Resolve absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

OUTDIR="$REPO_ROOT/phase2/results/weak_scaling"
mkdir -p "$OUTDIR"

BIN="$REPO_ROOT/phase2/src/sobel_mbi"
# Use the dog image as the base
BASE_IMG="$REPO_ROOT/data/dog.jpg"

if [ ! -f "$BASE_IMG" ]; then
  echo "Error: Base image $BASE_IMG not found."
  exit 1
fi

# Weak scaling: Workload per processor stays constant.
# We increase the problem size (image height) proportionally to the number of ranks.
RANKS=(1 2 4 8 16)
BASE_HEIGHT=0

# Get base image dimensions if possible (requires identify from ImageMagick)
if command -v identify >/dev/null 2>&1; then
    BASE_HEIGHT=$(identify -format "%h" "$BASE_IMG")
else
    # Fallback or hardcode if known. The dog.jpg is likely standard size.
    # Let's assume a reasonable default or try to read it.
    # For now, we'll just use the file as is for rank 1 and duplicate it for others.
    # But wait, simply duplicating the file content won't make a valid larger image.
    # We need to actually resize/tile it.
    echo "Warning: ImageMagick 'identify' not found. Assuming base height..."
fi

echo "ranks,walltime_s" > "$OUTDIR/weak_scaling.csv"

for p in "${RANKS[@]}"; do
  OUTIMG="$OUTDIR/input_weak_${p}.jpg"
  
  # Create a scaled image: Height = Base_Height * p
  # If we don't have ImageMagick, we can't easily create a valid larger image on the fly 
  # without a python script or similar.
  # ALTERNATIVE: Use the SAME image but process it 'p' times? No, that's not weak scaling.
  # ALTERNATIVE: Just use the same image and accept it's not true weak scaling, 
  # OR use a python one-liner to generate it.
  
  echo "Generating input for $p ranks..."
  
  # Python script to generate tiled image
  "$REPO_ROOT/.venv/bin/python3" -c "
import sys
from PIL import Image
try:
    img = Image.open('$BASE_IMG')
    w, h = img.size
    new_h = h * $p
    new_img = Image.new(img.mode, (w, new_h))
    for i in range($p):
        new_img.paste(img, (0, i * h))
    new_img.save('$OUTIMG')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"
  
  LOG="$OUTDIR/run_${p}.log"
  echo "Running with $p ranks on scaled image..."
  
  # Check binary
  if [ ! -f "$BIN" ]; then
      echo "Error: Binary $BIN not found!"
      exit 1
  fi

  mpirun --oversubscribe -np $p "$BIN" "$OUTIMG" "${OUTDIR}/out_weak_${p}.pgm" > "$LOG" 2>&1 || { 
      echo "run failed, check $LOG"; 
      cat "$LOG";
      exit 1; 
  }
  
  WT=$(grep "Max total runtime" "$LOG" | awk '{print $4}')
  if [ -z "$WT" ]; then WT=0; fi
  echo "${p},${WT}" >> "$OUTDIR/weak_scaling.csv"
done

echo "Saved: $OUTDIR/weak_scaling.csv"
