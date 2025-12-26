import sys
import os
import time
import grpc
import argparse

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "server")
    )
)

import sobel_pb2
import sobel_pb2_grpc

DURATION = 60  # seconds


def run_load(rate):
    channel = grpc.insecure_channel("localhost:50051")
    stub = sobel_pb2_grpc.SobelServiceStub(channel)

    input_path = "/Users/apple/nexus/data/dog_edges.png"
    threshold = 100

    interval = 1.0 / rate
    end_time = time.time() + DURATION  

    while time.time() < end_time:
        try:
            response = stub.ProcessImage(
                sobel_pb2.SobelRequest(
                    input_path=input_path,
                    threshold=threshold
                )
            )
            print(f"[OK] {response.output_path}")

        except grpc.RpcError as e:
            print(f"[ERROR] {e.code()} - {e.details()}")
            time.sleep(1)

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="gRPC Sobel load generator")
    parser.add_argument("--rate", type=int, default=5, help="Requests per second")
    args = parser.parse_args()

    run_load(args.rate)
