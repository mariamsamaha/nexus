#!/usr/bin/env python3
"""
Simple script to convert PGM images to PNG format.
Requires: pip install Pillow
"""
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


def convert_to_png(input_path: str, output_path: str) -> bool:
    # output should be "output.png"
    out = Path(output_path)
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")

    if Image is not None:
        try:
            with Image.open(input_path) as img:
                img = img.convert('L')  # must be grayscale
                img.save(out.as_posix(), format='PNG')
            print(f"Successfully converted {input_path} to {out}")
            return True
        except Exception as e:
            print(f"Pillow failed to convert: {e}")

    # ImageMagick `convert` if available
    try:
        import subprocess
        result = subprocess.run(['which', 'convert'], capture_output=True)
        if result.returncode == 0:
            subprocess.check_call(['convert', input_path, out.as_posix()])
            print(
                f"Successfully converted via ImageMagick: {input_path} -> {out}")
            return True
        else:
            print("ImageMagick 'convert' not found in PATH.")
    except Exception as e:
        print(f"Fallback conversion failed: {e}")

    return False


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 convert_to_png.py <input.pgm> <output.png>")
        sys.exit(1)

    ok = convert_to_png(sys.argv[1], sys.argv[2])
    sys.exit(0 if ok else 1)
