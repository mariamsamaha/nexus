import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))

import grpc
import sobel_pb2
import sobel_pb2_grpc

def run():
    channel = grpc.insecure_channel("localhost:50051")
    stub = sobel_pb2_grpc.SobelServiceStub(channel)

    response = stub.ProcessImage(
        sobel_pb2.SobelRequest(
            input_path="/Users/apple/nexus/data/dog_edges.png",
            threshold=100
        )
    )

    print("Output path:", response.output_path)
    print("Start time:", response.start_time)
    print("End time:", response.end_time)
    print("Processing time (ms):", response.end_time - response.start_time)

if __name__ == "__main__":
    run()
