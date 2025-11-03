#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#define MAX_PATH 256
#define TILE_SIZE 64  

typedef struct
{
    int width;
    int height;
    int max_val;
    unsigned char *data;
} Image;

static Image *create_image(int width, int height, int max_val)
{
    Image *img = (Image *)malloc(sizeof(Image));
    if (!img)
        return NULL;
    img->width = width;
    img->height = height;
    img->max_val = max_val;
    img->data = (unsigned char *)malloc((size_t)width * (size_t)height);
    if (!img->data)
    {
        free(img);
        return NULL;
    }
    return img;
}

static void free_image(Image *img)
{
    if (!img)
        return;
    free(img->data);
    free(img);
}

static Image *load_image(const char *filename)
{
    int width, height, channels;
    unsigned char *data = stbi_load(filename, &width, &height, &channels, 1); // Force 1 channel (grayscale)

    if (!data)
    {
        fprintf(stderr, "Error: stb_image failed to load %s: %s\n", filename, stbi_failure_reason());
        return NULL;
    }

    Image *img = create_image(width, height, 255);
    if (!img)
    {
        stbi_image_free(data);
        return NULL;
    }

    // Copy grayscale data
    memcpy(img->data, data, width * height);
    stbi_image_free(data);

    return img;
}

static int save_pgm(const char *filename, Image *img)
{
    FILE *file = fopen(filename, "wb");
    if (!file)
    {
        fprintf(stderr, "Error: Cannot create file %s\n", filename);
        return -1;
    }

    fprintf(file, "P5\n%d %d\n%d\n", img->width, img->height, img->max_val);
    fwrite(img->data, sizeof(unsigned char), img->width * img->height, file);

    fclose(file);
    return 0;
}

/*
If (x,y) is outside image boundaries, it clamps to the closest border coordinate.
*/
static unsigned char get_pixel(const Image *img, int x, int y)
{
    if (x < 0)
        x = 0;
    if (x >= img->width)
        x = img->width - 1;
    if (y < 0)
        y = 0;
    if (y >= img->height)
        y = img->height - 1;

    return img->data[y * img->width + x];
}

static void set_pixel(Image *img, int x, int y, unsigned char value)
{
    if (x >= 0 && x < img->width && y >= 0 && y < img->height)
    {
        img->data[y * img->width + x] = value;
    }
}

static void sobel_tile(const Image *input, Image *magnitude, 
                       int start_y, int end_y, int start_x, int end_x)
{
    for (int y = start_y; y < end_y; y++)
    {
        for (int x = start_x; x < end_x; x++)
        {
            int gx = 0;
            int gy = 0;

            gx += -1 * get_pixel(input, x - 1, y - 1) + 1 * get_pixel(input, x + 1, y - 1);
            gx += -2 * get_pixel(input, x - 1, y + 0) + 2 * get_pixel(input, x + 1, y + 0);
            gx += -1 * get_pixel(input, x - 1, y + 1) + 1 * get_pixel(input, x + 1, y + 1);

            gy += -1 * get_pixel(input, x - 1, y - 1) + -2 * get_pixel(input, x + 0, y - 1) + -1 * get_pixel(input, x + 1, y - 1);
            gy += 1 * get_pixel(input, x - 1, y + 1) + 2 * get_pixel(input, x + 0, y + 1) + 1 * get_pixel(input, x + 1, y + 1);

            int mag = (int)sqrt((double)(gx * gx + gy * gy));
            if (mag > 255)
                mag = 255;
            if (mag < 0)
                mag = 0;
            set_pixel(magnitude, x, y, (unsigned char)mag);
        }
    }
}

// Creates tasks for tiles of the image
static void sobel_magnitude(const Image *input, Image *magnitude)
{
    #pragma omp parallel
    {
        #pragma omp single
        {
            int num_tasks = 0;
            
            for (int tile_y = 0; tile_y < input->height; tile_y += TILE_SIZE)
            {
                for (int tile_x = 0; tile_x < input->width; tile_x += TILE_SIZE)
                {
                    int start_y = tile_y;
                    int end_y = (tile_y + TILE_SIZE < input->height) ? tile_y + TILE_SIZE : input->height;
                    int start_x = tile_x;
                    int end_x = (tile_x + TILE_SIZE < input->width) ? tile_x + TILE_SIZE : input->width;
                    
                    #pragma omp task firstprivate(start_y, end_y, start_x, end_x) shared(input, magnitude)
                    {
                        sobel_tile(input, magnitude, start_y, end_y, start_x, end_x);
                    }
                    num_tasks++;
                }
            }
            
            #pragma omp taskwait
            printf("Created %d tasks for Sobel computation\n", num_tasks);
        }
    }
}

static void threshold_image(const Image *src, Image *dst, unsigned char threshold)
{
    int n = src->width * src->height;
    int chunk_size = 10000;  
    
    #pragma omp parallel
    {
        #pragma omp single
        {
            int num_tasks = 0;
            
            for (int start = 0; start < n; start += chunk_size)
            {
                int end = (start + chunk_size < n) ? start + chunk_size : n;
                
                #pragma omp task firstprivate(start, end) shared(src, dst, threshold)
                {
                    for (int i = start; i < end; i++)
                    {
                        dst->data[i] = (src->data[i] >= threshold) ? 255 : 0;
                    }
                }
                num_tasks++;
            }
            
            #pragma omp taskwait
            printf("Created %d tasks for thresholding\n", num_tasks);
        }
    }
}

int main(int argc, char *argv[])
{
    if (argc < 3)
    {
        fprintf(stderr, "Usage: %s <input_image> <output_image.pgm> [threshold]\n", argv[0]);
        fprintf(stderr, "  threshold: Edge detection threshold (default: 100)\n");
        return 1;
    }

    unsigned char threshold = 100;
    if (argc >= 4)
    {
        int t = atoi(argv[3]);
        if (t < 0)
            t = 0;
        if (t > 255)
            t = 255;
        threshold = (unsigned char)t;
    }

    printf(" OpenMP Task-Based Edge Detection \n");
    printf("Tile size: %d x %d\n", TILE_SIZE, TILE_SIZE);
    printf("Max threads: %d\n", omp_get_max_threads());
    printf("\n");

    printf("Loading image: %s\n", argv[1]);
    Image *input = load_image(argv[1]);
    if (!input)
    {
        return 1;
    }
    printf("Image loaded: %dx%d\n", input->width, input->height);

    Image *mag = create_image(input->width, input->height, 255);
    if (!mag)
    {
        free_image(input);
        fprintf(stderr, "Error: Out of memory\n");
        return 1;
    }

    Image *out = create_image(input->width, input->height, 255);
    if (!out)
    {
        free_image(mag);
        free_image(input);
        fprintf(stderr, "Error: Out of memory\n");
        return 1;
    }

    // execution
    double start = omp_get_wtime();
    
    printf("\n Sobel Magnitude Computation \n");
    double sobel_start = omp_get_wtime();
    sobel_magnitude(input, mag);
    double sobel_end = omp_get_wtime();
    printf("Sobel time: %.6f seconds\n", sobel_end - sobel_start);
    
    printf("\n Thresholding \n");
    double threshold_start = omp_get_wtime();
    threshold_image(mag, out, threshold);
    double threshold_end = omp_get_wtime();
    printf("Threshold time: %.6f seconds\n", threshold_end - threshold_start);
    
    double end = omp_get_wtime();
    printf("\nTask version total runtime: %.6f seconds\n", end - start);

    printf("\nSaving output image: %s\n", argv[2]);
    if (save_pgm(argv[2], out) != 0)
    {
        free_image(out);
        free_image(mag);
        free_image(input);
        return 1;
    }

    free_image(out);
    free_image(mag);
    free_image(input);
    printf("Done.\n");
    return 0;
}