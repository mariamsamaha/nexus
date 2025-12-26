import sys
import os
import time
import grpc
import argparse
import random
import csv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))
import sobel_pb2
import sobel_pb2_grpc

SERVERS = ["localhost:50051", "localhost:50052"]
DURATION = 60 # seconds
LOG_FILE = "metrics.csv"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "../../data/dog_edges.png"))

def run_load(rate):
    with open(LOG_FILE, 'w', newline='') as csvfile:
        fieldnames = ['timestamp', 'latency', 'status', 'server']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        if not os.path.exists(IMAGE_PATH):
            print(f"ERROR: Image not found at {IMAGE_PATH}")
            return

        threshold = 100
        end_time_global = time.time() + DURATION
        
        print(f"Starting load test on {SERVERS} for {DURATION} seconds...")
        print(f"Sending requests (Rate: {rate} req/sec)...")

        while time.time() < end_time_global:
            loop_start = time.time()

            target = random.choice(SERVERS)
            
            req_start = time.time()
            status = "SUCCESS"
            
            try:
                channel = grpc.insecure_channel(target)
                stub = sobel_pb2_grpc.SobelServiceStub(channel)
                
                response = stub.ProcessImage(
                    sobel_pb2.SobelRequest(input_path=IMAGE_PATH, threshold=threshold),
                    timeout=5
                )
                print(f"[OK] {target} -> Processed")

            except grpc.RpcError: #retry on the other server
                status = "FAILED"
                print(f"[FAIL] {target} crashed. Retrying on backup...")
                
                for backup_target in SERVERS:
                    if backup_target == target: continue 
                    
                    try:
                        print(f"   -> Retrying on {backup_target}...")
                        channel_backup = grpc.insecure_channel(backup_target)
                        stub_backup = sobel_pb2_grpc.SobelServiceStub(channel_backup)
                        
                        response = stub_backup.ProcessImage(
                            sobel_pb2.SobelRequest(input_path=IMAGE_PATH, threshold=threshold),
                            timeout=5
                        )
                        print(f"   -> [RECOVERED] Served by {backup_target}")
                        status = "RECOVERED"
                        target = backup_target 
                        break
                    except:
                        print(f"   -> [FAIL] Backup {backup_target} also failed.")
            
            req_end = time.time()
            latency = req_end - req_start

            writer.writerow({
                'timestamp': req_end,
                'latency': latency,
                'status': status,
                'server': target
            })
            
            elapsed = time.time() - loop_start
            sleep_time = (1.0 / rate) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=int, default=5, help="Requests per second")
    args = parser.parse_args()
    
    run_load(args.rate)