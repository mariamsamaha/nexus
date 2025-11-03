#!/usr/bin/env python3
"""
Simple script to convert images to PGM format.
Requires: pip install Pillow
"""
import sys
from PIL import Image


def convert_to_pgm(input_path, output_path):
    try:
        # convert pic to grayscale
        img = Image.open(input_path).convert('L')

        # save as ppm --binary format
        img.save(output_path, 'PPM')

        with open(output_path, 'wb') as f:
            # write pgm header
            f.write(f'P5\n{img.width} {img.height}\n255\n'.encode())
            # pixel data
            img_bytes = img.tobytes()
            f.write(img_bytes)

        print(f"Successfully converted {input_path} to {output_path}")
        return True
    except Exception as e:
        print(f"Error converting image: {e}")
        print("Trying alternative method...")

        try:
            import subprocess
            result = subprocess.run(['which', 'convert'], capture_output=True)
            if result.returncode == 0:
                subprocess.run(
                    ['convert', input_path, '-colorspace', 'Gray', output_path])
                return True
        except:
            raise

        return False


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 convert_to_pgm.py <input_image> <output.pgm>")
        sys.exit(1)

    convert_to_pgm(sys.argv[1], sys.argv[2])
