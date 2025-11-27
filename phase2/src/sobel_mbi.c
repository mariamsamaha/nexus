/* sobel_mpi.c
 *
 * Full MPI Sobel edge detector (1D row-wise decomposition).
 *
 * - Rank 0 loads image (via stb_image)
 * - Uses MPI_Scatterv to distribute row blocks
 * - Each rank keeps local_rows + 2 halo rows
 * - Non-blocking halo exchange with MPI_Irecv / MPI_Isend
 * - Overlap: compute interior while halo transfers proceed
 * - Gather results with MPI_Gatherv
 * - Writes output as PGM (binary P5)
 *
 * Compile:
 *   mpicc -O3 -std=c99 -o sobel_mpi sobel_mpi.c
 *
 * Run:
 *   mpirun -np 4 ./sobel_mpi input.png output.pgm [threshold]
 *
 * Requires stb_image.h .
 */

#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

/* Helper to write PGM (P5) */
static int save_pgm(const char *filename, unsigned char *data, int width, int height) {
    FILE *f = fopen(filename, "wb");
    if (!f) return -1;
    if (fprintf(f, "P5\n%d %d\n255\n", width, height) < 0) { fclose(f); return -1; }
    size_t written = fwrite(data, 1, (size_t)width * height, f);
    fclose(f);
    return (written == (size_t)width * height) ? 0 : -1;
}

/* Apply Sobel on a buffer that contains (rows + 2) rows: top halo, real rows, bottom halo.
 * dst has rows * width bytes (no halos).
 */
static void sobel_on_local_chunk(const unsigned char *src_with_halo, unsigned char *dst, int width, int rows) {
    // src_with_halo layout: row 0 = top halo, rows 1..rows = real rows, row rows+1 = bottom halo
    for (int r = 0; r < rows; ++r) {
        int y = r + 1; // center row in src_with_halo
        unsigned char *dst_row = dst + r * width;
        const unsigned char *row_m1 = src_with_halo + (y - 1) * width;
        const unsigned char *row_0  = src_with_halo + (y    ) * width;
        const unsigned char *row_p1 = src_with_halo + (y + 1) * width;
        for (int x = 0; x < width; ++x) {
            int xm1 = (x == 0) ? 0 : x - 1;
            int xp1 = (x == width - 1) ? width - 1 : x + 1;

            int p00 = row_m1[xm1];
            int p01 = row_m1[x];
            int p02 = row_m1[xp1];

            int p10 = row_0[xm1];
            int p11 = row_0[x];
            int p12 = row_0[xp1];

            int p20 = row_p1[xm1];
            int p21 = row_p1[x];
            int p22 = row_p1[xp1];

            int gx = -p00 + p02 - 2*p10 + 2*p12 - p20 + p22;
            int gy = -p00 - 2*p01 - p02 + p20 + 2*p21 + p22;
            int mag = (int)round(sqrt((double)(gx*gx + gy*gy)));
            if (mag > 255) mag = 255;
            dst_row[x] = (unsigned char)mag;
        }
    }
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);

    int rank = 0, size = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 3) {
        if (rank == 0) fprintf(stderr, "Usage: %s <input_image> <output_image.pgm> [threshold]\n", argv[0]);
        MPI_Finalize();
        return 1;
    }

    const char *infile = argv[1];
    const char *outfile = argv[2];
    int threshold = 100;
    if (argc >= 4) {
        int t = atoi(argv[3]);
        if (t < 0) t = 0;
        if (t > 255) t = 255;
        threshold = t;
    }

    int width = 0, height = 0;
    unsigned char *full_image = NULL; // only on rank 0

    if (rank == 0) {
        int channels;
        unsigned char *img = stbi_load(infile, &width, &height, &channels, 1); // force grayscale
        if (!img) {
            fprintf(stderr, "Error: failed to load image %s\n", infile);
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        full_image = img; // will be freed after scatter
    }

    /* Broadcast image dimensions to all ranks */
    MPI_Bcast(&width, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&height, 1, MPI_INT, 0, MPI_COMM_WORLD);

    if (width <= 0 || height <= 0) {
        if (rank == 0) fprintf(stderr, "Invalid image dimensions\n");
        MPI_Finalize();
        return 1;
    }

    /* Compute rows per rank (block-split with remainder) */
    int base = height / size;
    int rem  = height % size;
    int local_rows = base + (rank < rem ? 1 : 0);

    /* Prepare Scatterv / Gatherv metadata on root */
    int *send_counts = NULL;
    int *displs = NULL;
    if (rank == 0) {
        send_counts = (int *)malloc(size * sizeof(int));
        displs = (int *)malloc(size * sizeof(int));
        int offset = 0;
        for (int r = 0; r < size; ++r) {
            int rowsr = base + (r < rem ? 1 : 0);
            send_counts[r] = rowsr * width; // bytes (unsigned char)
            displs[r] = offset;
            offset += send_counts[r];
        }
    }

    /* Allocate local buffer with two halo rows: (local_rows + 2) * width */
    size_t local_buf_bytes = (size_t)(local_rows + 2) * width;
    unsigned char *local_with_halo = (unsigned char *)malloc(local_buf_bytes);
    if (!local_with_halo) {
        fprintf(stderr, "Rank %d: OOM allocating local_with_halo\n", rank);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    /* Initialize halos to zero (or any value); we'll overwrite halos via communication. */
    memset(local_with_halo, 0, local_buf_bytes);

    /* Scatter the real rows into local_with_halo + width (skip top halo slot) */
    MPI_Scatterv(full_image, send_counts, displs, MPI_UNSIGNED_CHAR,
                 local_with_halo + width, local_rows * width, MPI_UNSIGNED_CHAR,
                 0, MPI_COMM_WORLD);

    /* root can free full_image now */
    if (rank == 0 && full_image) {
        stbi_image_free(full_image);
        full_image = NULL;
    }

    /* Local output buffer (no halos): local_rows * width */
    unsigned char *local_out = (unsigned char *)malloc((size_t)local_rows * width);
    if (!local_out) {
        fprintf(stderr, "Rank %d: OOM allocating local_out\n", rank);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    /* Determine neighbors (use MPI_PROC_NULL where appropriate) */
    int above = (rank == 0) ? MPI_PROC_NULL : rank - 1;
    int below = (rank == size - 1) ? MPI_PROC_NULL : rank + 1;

    /* Non-blocking halo exchange */
    MPI_Request reqs[4];
    int reqcnt = 0;
    /* Irecv top halo into local_with_halo[0 * width] from above */
    if (above != MPI_PROC_NULL) {
        MPI_Irecv(local_with_halo + 0 * width, width, MPI_UNSIGNED_CHAR, above, 100, MPI_COMM_WORLD, &reqs[reqcnt++]);
    } else {
        /* clamp top halo to first real row */
        memcpy(local_with_halo + 0 * width, local_with_halo + 1 * width, width);
    }
    /* Irecv bottom halo into local_with_halo[(local_rows+1)*width] from below */
    if (below != MPI_PROC_NULL) {
        MPI_Irecv(local_with_halo + (local_rows + 1) * width, width, MPI_UNSIGNED_CHAR, below, 101, MPI_COMM_WORLD, &reqs[reqcnt++]);
    } else {
        /* clamp bottom halo to last real row */
        memcpy(local_with_halo + (local_rows + 1) * width, local_with_halo + local_rows * width, width);
    }

    /* Isend first real row to above (tag 101) */
    if (above != MPI_PROC_NULL) {
        MPI_Isend(local_with_halo + 1 * width, width, MPI_UNSIGNED_CHAR, above, 101, MPI_COMM_WORLD, &reqs[reqcnt++]);
    }
    /* Isend last real row to below (tag 100) */
    if (below != MPI_PROC_NULL) {
        MPI_Isend(local_with_halo + local_rows * width, width, MPI_UNSIGNED_CHAR, below, 100, MPI_COMM_WORLD, &reqs[reqcnt++]);
    }

    /* Timing: measure overlap. We measure from before posting to after finalization */
    double t_start = MPI_Wtime();

    /* Compute interior rows: those that don't depend on halos
       interior rows in local index: 1 .. local_rows-2  (if local_rows >= 3)
       We'll compute them by passing a pointer to src_with_halo at (interior_start-1)*width so sobel_on_local_chunk sees appropriate halos.
       Simpler: compute rows r = 1..local_rows-2 by calling sobel_on_local_chunk with src offset such that its y=r maps correctly.
    */
    if (local_rows >= 3) {
        int interior_start = 1;
        int interior_end = local_rows - 2;
        int interior_count = interior_end - interior_start + 1;
        /* src pointer should be local_with_halo + (interior_start - 1) * width
           so that when sobel_on_local_chunk treats its internal y=1..interior_count, original mapping works */
        unsigned char *src_ptr = local_with_halo + (interior_start - 1) * width;
        unsigned char *dst_ptr = local_out + (interior_start - 1) * width;
        sobel_on_local_chunk(src_ptr, dst_ptr, width, interior_count);
    }

    double t_after_interior = MPI_Wtime();

    /* Wait for halo communication to finish before computing boundaries */
    if (reqcnt > 0) {
        MPI_Waitall(reqcnt, reqs, MPI_STATUSES_IGNORE);
    }

    double t_after_wait = MPI_Wtime();

    /* Compute boundary rows:
       - top boundary (local row 0): src pointer = local_with_halo + 0*width (has top halo at row 0)
       - bottom boundary (local row local_rows-1): src pointer = local_with_halo + (local_rows-1)*width
    */
    if (local_rows >= 1) {
        sobel_on_local_chunk(local_with_halo + 0 * width, local_out + 0 * width, width, 1);
        if (local_rows > 1) {
            sobel_on_local_chunk(local_with_halo + (local_rows - 1) * width, local_out + (local_rows - 1) * width, width, 1);
        }
    }

    double t_end = MPI_Wtime();

    /* Thresholding: produce binary output */
    for (int i = 0; i < local_rows * width; ++i) {
        local_out[i] = (local_out[i] >= threshold) ? 255 : 0;
    }

    /* Gather results back to rank 0 */
    unsigned char *full_out = NULL;
    if (rank == 0) {
        full_out = (unsigned char *)malloc((size_t)width * height);
        if (!full_out) { fprintf(stderr, "Rank 0: OOM allocating full_out\n"); MPI_Abort(MPI_COMM_WORLD, 1); }
    }

    MPI_Gatherv(local_out, local_rows * width, MPI_UNSIGNED_CHAR,
                full_out, send_counts, displs, MPI_UNSIGNED_CHAR,
                0, MPI_COMM_WORLD);

    /* Collect timing info: compute max across ranks to represent worst-case */
    double local_total = t_end - t_start;
    double local_interior = t_after_interior - t_start;
    double local_wait = t_after_wait - t_after_interior;
    double max_total = 0.0, max_interior = 0.0, max_wait = 0.0;
    MPI_Reduce(&local_total, &max_total, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&local_interior, &max_interior, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&local_wait, &max_wait, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        printf("Max total runtime: %f s\n", max_total);
        printf("Max interior time (overlap candidate): %f s\n", max_interior);
        printf("Max wait time (waiting for halos): %f s\n", max_wait);
        if (save_pgm(outfile, full_out, width, height) != 0) {
            fprintf(stderr, "Error: failed to save output %s\n", outfile);
        } else {
            printf("Saved output to %s\n", outfile);
        }
    }

    /* cleanup */
    free(local_with_halo);
    free(local_out);
    if (rank == 0) {
        free(full_out);
        free(send_counts);
        free(displs);
    }

    MPI_Finalize();
    return 0;
}
