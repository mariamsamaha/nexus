import time
import os
import shutil

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_STREAM_DIR = os.path.join(CURRENT_DIR, "input_stream")
IMAGE_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "../../data/dog_edges.png"))

def feed_stream():
    if os.path.exists(INPUT_STREAM_DIR):
        shutil.rmtree(INPUT_STREAM_DIR)
    os.makedirs(INPUT_STREAM_DIR)

    print(f"Streaming data to: {INPUT_STREAM_DIR}")
    print(f"Using image: {IMAGE_PATH}")
    print("Press Ctrl+C to stop.")

    batch_id = 0
    try:
        while True:
            batch_id += 1
            filename = f"batch_{batch_id}.txt"
            filepath = os.path.join(INPUT_STREAM_DIR, filename)
            
            with open(filepath, "w") as f:
                f.write(IMAGE_PATH)
            
            print(f"[Feeder] Generated {filename}")
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nStopping feeder...")

if __name__ == "__main__":
    feed_stream()