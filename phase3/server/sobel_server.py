from concurrent import futures
import grpc
import sobel_pb2
import sobel_pb2_grpc
import subprocess
import time
import os
import signal
import sys

SOBEL_EXEC = "/Users/apple/nexus/phase2/src/sobel_mbi"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, "../logs"))
os.makedirs(LOG_DIR, exist_ok=True)

class SobelService(sobel_pb2_grpc.SobelServiceServicer):

    def ProcessImage(self, request, context):
        input_path = request.input_path
        threshold = request.threshold if request.threshold else 100
        output_path = os.path.join(LOG_DIR, f"output_{int(time.time())}.pgm")

        start_time = time.time()
        print(f"[REQUEST] {input_path}, threshold={threshold}")

        try:
            subprocess.run(
                ["mpirun", "-np", "4", SOBEL_EXEC, input_path, output_path, str(threshold)],
                check=True
            )
        except subprocess.CalledProcessError as e:
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return sobel_pb2.SobelResponse()

        end_time = time.time()
        print(f"[RESPONSE] Saved to {output_path}")

        return sobel_pb2.SobelResponse(
            output_path=output_path,
            start_time=int(start_time * 1000),
            end_time=int(end_time * 1000)
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    sobel_pb2_grpc.add_SobelServiceServicer_to_server(SobelService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC Sobel server running on port 50051...")

    # Graceful shutdown on SIGINT / Ctrl+C
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        server.stop(0)
        print("Server stopped.")

if __name__ == "__main__":
    serve()
