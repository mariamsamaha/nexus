#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define ARRAY_SIZE (1024 * 1024 * 64) // 512MB

int main(int argc, char *argv[]) {

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <stride>\n", argv[0]);
        fprintf(stderr, "   e.g., ./stride_test 1  (for sequential access)\n");
        fprintf(stderr, "   e.g., ./stride_test 16 (for strided access)\n");
        return 1;
    }

    int stride = atoi(argv[1]);
    if (stride <= 0) stride = 1;

    long *array = malloc(sizeof(long) * ARRAY_SIZE); //heap allocation
    if (!array) {
        perror("Failed to allocate memory");
        return 1;
    }

    for (long i = 0; i < ARRAY_SIZE; i++) {
        array[i] = i;
    }

    printf("Running test with stride = %d\n", stride);
    clock_t start = clock();

    volatile long temp = 0; 

    for (long i = 0; i < ARRAY_SIZE; i += stride) {
        temp += array[i];
    }
    
    clock_t end = clock();
    double time_spent = (double)(end - start) / CLOCKS_PER_SEC;
    
    printf("Done. Result: %ld\n", temp);
    printf("Time taken: %f seconds\n", time_spent);

    free(array);
    return 0;
}