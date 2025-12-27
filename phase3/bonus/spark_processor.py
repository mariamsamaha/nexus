import sys
import os
import grpc
import random
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
import sobel_pb2
import sobel_pb2_grpc

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../server"))
sys.path.append(SERVER_DIR)

SERVERS = ["localhost:50051", "localhost:50052"]

def process_image_grpc(image_path):
    if not image_path or image_path.strip() == "":
        return "EMPTY_PATH"

    target = random.choice(SERVERS)
    
    try:
        channel = grpc.insecure_channel(target)
        stub = sobel_pb2_grpc.SobelServiceStub(channel)
        
        response = stub.ProcessImage(
            sobel_pb2.SobelRequest(input_path=image_path, threshold=100),
            timeout=5
        )
        return f"SUCCESS: {response.output_path} (processed by {target})"
    except Exception as e:
        return f"FAILED: {str(e)}"
    
grpc_udf = udf(process_image_grpc, StringType())

def run_spark_job():
    spark = SparkSession.builder \
        .appName("SobelEdgeStream") \
        .master("local[*]") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    print("Spark Streaming Job Started. Waiting for files in 'input_stream'...")

    input_dir = os.path.join(CURRENT_DIR, "input_stream")
    os.makedirs(input_dir, exist_ok=True)
    
    df = spark.readStream \
        .format("text") \
        .load(input_dir)

    result_df = df.withColumn("processing_result", grpc_udf("value"))

    query = result_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    run_spark_job()