#!/bin/bash
cd "$(dirname "$0")"

export GRPC_ENABLE_FORK_SUPPORT=0

PYTHON_EXEC="$(which python)"

# Kill any existing servers
pkill -f sobel_server.py

echo "Using Python at: $PYTHON_EXEC"
echo "Starting Replica 1 on port 50051..."
"$PYTHON_EXEC" sobel_server.py 50051 &
PID1=$!

echo "Starting Replica 2 on port 50052..."
"$PYTHON_EXEC" sobel_server.py 50052 &
PID2=$!

echo "Servers running. PIDs: $PID1, $PID2"
echo "Press ENTER to kill both servers and exit."
read

kill $PID1 $PID2