/* mpi_latency_bandwidth.c
 *
 * Simple MPI microbench: latency (round-trip / 2) and bandwidth (one-way).
 *
 * Usage: mpirun -np 2 ./mpi_latency_bandwidth [min_exp] [max_exp]
 *   min_exp:  power-of-two exponent for smallest message (default 0 => 1 byte)
 *   max_exp:  power-of-two exponent for largest message (default 22 => 4MB)
 *
 * Produces CSV output to stdout: type,size_bytes,avg_time_s,bandwidth_MBps
 *
 * compile
mpicc -O3 -std=c99 -o mpi_latency_bandwidth mpi_latency_bandwidth.c
***************************
* run (must use exactly 2 ranks)
mpirun -np 2 ./mpi_latency_bandwidth 0 22 > latency_bandwidth.csv
 */
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank=0, size=1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    if (size != 2) {
        if (rank==0) fprintf(stderr, "This microbench requires exactly 2 ranks.\n");
        MPI_Finalize();
        return 1;
    }

    int min_exp = 0;
    int max_exp = 22;
    if (argc >= 2) min_exp = atoi(argv[1]);
    if (argc >= 3) max_exp = atoi(argv[2]);

    const int SKIP_SMALL = 100;
    const int ITER_SMALL = 1000;
    const int SKIP_LARGE = 10;
    const int ITER_LARGE = 100;

    if (rank == 0) {
        printf("#type,size_bytes,avg_time_s,bandwidth_MBps\n");
    }

    for (int e = min_exp; e <= max_exp; ++e) {
        int size_bytes = 1 << e;
        char *buf = (char*)malloc(size_bytes);
        memset(buf, 0, size_bytes);

        if (size_bytes <= 1024) {
            // latency (ping-pong)
            // rank0 sends to rank1, rank1 echoes back. Measure round-trip.
            // Skip initial warmup
            for (int i=0;i<SKIP_SMALL;i++) {
                if (rank==0) { MPI_Send(buf, size_bytes, MPI_BYTE, 1, 1, MPI_COMM_WORLD); MPI_Recv(buf, size_bytes, MPI_BYTE, 1, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE); }
                else         { MPI_Recv(buf, size_bytes, MPI_BYTE, 0, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE); MPI_Send(buf, size_bytes, MPI_BYTE, 0, 1, MPI_COMM_WORLD); }
            }
            double t0 = MPI_Wtime();
            for (int i=0;i<ITER_SMALL;i++) {
                if (rank==0) { MPI_Send(buf, size_bytes, MPI_BYTE, 1, 1, MPI_COMM_WORLD); MPI_Recv(buf, size_bytes, MPI_BYTE, 1, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE); }
                else         { MPI_Recv(buf, size_bytes, MPI_BYTE, 0, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE); MPI_Send(buf, size_bytes, MPI_BYTE, 0, 1, MPI_COMM_WORLD); }
            }
            double t1 = MPI_Wtime();
            double avg_roundtrip = (t1 - t0) / (double)ITER_SMALL;
            double latency = avg_roundtrip / 2.0;
            if (rank==0) {
                printf("latency,%d,%.9e,%.6f\n", size_bytes, latency, 0.0);
            }
        } else {
            // bandwidth measurement: one-way transfer from 0 -> 1
            // We'll do a ping to synchronize, then time multiple sends
            for (int i=0;i<SKIP_LARGE;i++) {
                if (rank==0) MPI_Send(buf, size_bytes, MPI_BYTE, 1, 2, MPI_COMM_WORLD);
                else          MPI_Recv(buf, size_bytes, MPI_BYTE, 0, 2, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            }
            double t0 = MPI_Wtime();
            for (int i=0;i<ITER_LARGE;i++) {
                if (rank==0) MPI_Send(buf, size_bytes, MPI_BYTE, 1, 2, MPI_COMM_WORLD);
                else          MPI_Recv(buf, size_bytes, MPI_BYTE, 0, 2, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            }
            double t1 = MPI_Wtime();
            double total_time = (t1 - t0);
            // average one-way time per message:
            double avg_one_way = total_time / (double)ITER_LARGE;
            double bw_MBps = ((double)size_bytes) / (1024.0*1024.0) / avg_one_way;
            if (rank==0) {
                printf("bandwidth,%d,%.9e,%.6f\n", size_bytes, avg_one_way, bw_MBps);
            }
        }
        free(buf);
        MPI_Barrier(MPI_COMM_WORLD);
    }

    MPI_Finalize();
    return 0;
}
