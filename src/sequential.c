#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#define MAX_PATH 256
// pic structure
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

// loading image using stb_image as 1-channel grayscale
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
If (x,y) is outside image boundaries, it clamps to the closest border coordinate. This is a common way to handle boundaries for convolution (avoids special casing edges).
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

/*
What are gx and gy?
- gx is the discrete approximation of the derivative in the x (horizontal) direction.
- gy is the derivative in the y (vertical) direction.
They are computed by convolving the 3×3 neighborhood with the Sobel kernels.
*/

static void sobel_magnitude(const Image *input, Image *magnitude)
{
    for (int y = 0; y < input->height; y++)
    {
        for (int x = 0; x < input->width; x++)
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

/*
Converts gradient magnitudes into a binary image:
If mag >= threshold then pixel becomes 255 (white = edge).
Else becomes 0 (black = not edge).
*/

static void threshold_image(const Image *src, Image *dst, unsigned char threshold)
{
    int n = src->width * src->height;
    for (int i = 0; i < n; i++)
    {
        dst->data[i] = (src->data[i] >= threshold) ? 255 : 0;
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
    sobel_magnitude(input, mag);

    Image *out = create_image(input->width, input->height, 255);
    if (!out)
    {
        free_image(mag);
        free_image(input);
        fprintf(stderr, "Error: Out of memory\n");
        return 1;
    }
    threshold_image(mag, out, threshold);

    printf("Saving output image: %s\n", argv[2]);
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
