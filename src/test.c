#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <string.h>
#include <math.h>
#include <errno.h>

static double now_seconds(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr,
            "Usage: %s <mode> [stride|block_size] [iters] [array_size_MB] [block_size]\n"
            "Modes:\n"
            "  stride  <stride_in_elements> [iters=5] [array_MB=512]\n"
            "  block   <block_size> [iters=5] [array_MB=512]\n"
            "Examples:\n"
            "  %s stride 1 5 512\n"
            "  %s stride 32 10 1024\n"
            "  %s block 64 5 512\n",
            argv[0], argv[0], argv[0], argv[0]);
        return 1;
    }

    const char *mode = argv[1];
    long stride_or_bs = 1;
    int iters = 5;
    size_t array_mb = 512;

    if (argc >= 3) stride_or_bs = atol(argv[2]);
    if (argc >= 4) iters = atoi(argv[3]);
    if (argc >= 5) array_mb = (size_t)atoi(argv[4]);
    if (iters <= 0) iters = 1;
    if (stride_or_bs <= 0) stride_or_bs = 1;

    const size_t bytes = array_mb * 1024ull * 1024ull;
    const size_t elem_size = sizeof(long);
    const size_t n_elems = bytes / elem_size;
    if (n_elems < 16) {
        fprintf(stderr, "Array too small.\n");
        return 1;
    }

    void *ptr = NULL;
    int rc = posix_memalign(&ptr, 64, n_elems * elem_size);
    if (rc != 0) {
        fprintf(stderr, "posix_memalign failed: %s\n", strerror(rc));
        return 1;
    }
    long *array = (long *)ptr;

    for (size_t i = 0; i < n_elems; ++i) array[i] = (long)i;

    volatile long warm = 0;
    for (size_t i = 0; i < n_elems; i += 64/elem_size) warm += array[i];
    (void)warm;

    printf("Mode: %s  stride/bs=%ld  iters=%d  array=%zu MB  elements=%zu\n",
           mode, stride_or_bs, iters, array_mb, n_elems);

    volatile long long global_sum = 0;
    double total_time = 0.0;

    if (strcmp(mode, "stride") == 0) {
        size_t stride = (size_t)stride_or_bs;
        if (stride == 0) stride = 1;

        for (int iter = 0; iter < iters; ++iter) {
            double t0 = now_seconds();
            volatile long long sum = 0;
            for (size_t i = 0; i < n_elems; i += stride) {
                sum += array[i];
            }
            double t1 = now_seconds();
            double dt = t1 - t0;
            total_time += dt;
            global_sum += sum;
            printf("  iter %2d: time=%.6fs  accesses=%zu  bytes_read=%zu  avg_access_time=%.3f ns\n",
                   iter, dt, (n_elems + stride - 1) / stride, ((n_elems + stride - 1) / stride) * elem_size,
                   (dt * 1e9) / ((double)((n_elems + stride - 1) / stride)));
        }
    } else if (strcmp(mode, "block") == 0) {
        size_t bs = (size_t)stride_or_bs;
        size_t dim = (size_t)floor(sqrt((double)n_elems));
        if (dim * dim > n_elems) dim--;
        if (dim < 2) { fprintf(stderr, "Array too small for block mode\n"); free(array); return 1; }
        size_t used = dim * dim;
        printf("  Using square matrix %zux%zu (used elements=%zu)\n", dim, dim, used);

        if (bs < 1) bs = 1;
        if (bs > dim) bs = dim;

        for (int iter = 0; iter < iters; ++iter) {
            double t0 = now_seconds();
            volatile long long sum = 0;
            for (size_t by = 0; by < dim; by += bs) {
                for (size_t bx = 0; bx < dim; bx += bs) {
                    size_t y_max = (by + bs < dim) ? by + bs : dim;
                    size_t x_max = (bx + bs < dim) ? bx + bs : dim;
                    for (size_t y = by; y < y_max; ++y) {
                        size_t base = y * dim;
                        for (size_t x = bx; x < x_max; ++x) {
                            sum += array[base + x];
                        }
                    }
                }
            }
            double t1 = now_seconds();
            double dt = t1 - t0;
            total_time += dt;
            global_sum += sum;
            printf("  iter %2d: time=%.6fs  block=%zu  used_bytes=%zu\n",
                   iter, dt, bs, (size_t)used * elem_size);
        }
    } else {
        fprintf(stderr, "Unknown mode '%s' (use 'stride' or 'block')\n", mode);
        free(array);
        return 1;
    }

    double avg_time = total_time / iters;
    size_t bytes_read_est;
    if (strcmp(mode, "stride") == 0) {
        size_t stride = (size_t)stride_or_bs;
        bytes_read_est = ((n_elems + stride - 1) / stride) * elem_size;
    } else {
        size_t dim = (size_t)floor(sqrt((double)n_elems));
        bytes_read_est = dim * dim * elem_size;
    }

    double bandwidth = (double)bytes_read_est / avg_time / (1024.0 * 1024.0); 

    printf("\nAverage time: %.6fs (iters=%d)\n", avg_time, iters);
    printf("Estimated bytes read per iter: %zu bytes  Bandwidth: %.2f MB/s\n", bytes_read_est, bandwidth);
    printf("Checksum: %lld\n", (long long)global_sum); //to prevent optimize away

    free(array);
    return 0;
}
