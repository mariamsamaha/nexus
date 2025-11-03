CC= gcc
CFLAGS=-o3 -march=native -Wall
OMP_FLAGS= -fopenmp
all: build/sobel_seq build/sobel_par
build/sobel_seq: src/sequential.c
$(CC) $(CFLAGS) -o $@ $<
build/sobel_par: src/parallel.c
$(CC) $(CFLAGS) $(OMP_FLAGS) -o $@ $<
