#include <endian.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

int getIdx(int r, int c, int ncols) { return ncols * r + c; }
const char *getFileExt(const char *filename);
int16_t calcInterp(int16_t *demGrid, int i, int j, int bi, int bj, int rate,
                   int ncols);
int16_t interpRow(int16_t *demGrid, int i, int j, int bj, int rate, int ncols);
int16_t interpCol(int16_t *demGrid, int i, int j, int bi, int rate, int ncols);

int main(int argc, char **argv) {

  // Parse input filename, rate, and optional output filename
  const char *defaultOutfile = "elevation.dem";
  if (argc < 3) {
    fprintf(stderr,
            "Usage: ./dem filename rate [ncols] [nrows] "
            "[outfilename] \n"
            "filename must be .hgt or .dem extension.\n"
            "Rate must be a positive integer.\n"
            "ncols = width of DEM/HGT, ncows = height\n"
            "Default outfile name: %s\n",
            defaultOutfile);
    return EXIT_FAILURE;
  }
  char *filename = argv[1];
  int rate = atoi(argv[2]);
  int ncols = atoi(argv[3]);
  int nrows = atoi(argv[4]);

  // If reading in a .hgt, must swap bytes of integers
  bool swapBytes = (strcmp(getFileExt(filename), ".hgt") == 0);
  printf("Swapping bytes: %d\n", swapBytes);

  // Optional input:
  const char *outfileUp;
  if (argc < 6) {
    outfileUp = defaultOutfile;
    printf("Using %s as output file for upsampling.\n", outfileUp);
  } else {
    outfileUp = argv[5];
    if (strcmp(getFileExt(outfileUp), ".dem") != 0) {
      fprintf(stderr, "Error: Outfile name must be .dem: %s\n", outfileUp);
      return EXIT_FAILURE;
    }
  }

  printf("Reading from %s\n", filename);
  printf("Upsampling by %d\n", rate);

  FILE *fp = fopen(filename, "r");
  if (fp == NULL) {
    fprintf(stderr, "Failure to open %s. Exiting.\n", filename);
    return EXIT_FAILURE;
  }

  int nbytes = 2;
  int16_t buf[1];
  int16_t *demGrid = (int16_t *)malloc(nrows * ncols * sizeof(*demGrid));

  int i = 0, j = 0;
  for (i = 0; i < nrows; i++) {
    for (j = 0; j < ncols; j++) {
      if (fread(buf, nbytes, 1, fp) != 1) {
        fprintf(stderr, "Read failure from %s\n", filename);
        return EXIT_FAILURE;
      }
      if (swapBytes) {
        demGrid[getIdx(i, j, ncols)] = be16toh(*buf);
      } else {
        demGrid[getIdx(i, j, ncols)] = *buf;
      }
    }
  }
  fclose(fp);

  // Interpolation
  short bi = 0, bj = 0;
  // Size of one side for upsampled
  // Example: 3 points at x = (0, 1, 2), rate = 2 becomes 5 points:
  //    x = (0, .5, 1, 1.5, 2)
  int upNrows = rate * (nrows - 1) + 1;
  int upNcols = rate * (ncols - 1) + 1;
  printf("New size of upsampled DEM: %d rows, %d cols.\n", upNrows, upNcols);
  int16_t *upDemGrid =
      (int16_t *)malloc(upNrows * upNcols * sizeof(*upDemGrid));

  for (int i = 0; i < nrows - 1; i++) {
    for (int j = 0; j < ncols - 1; j++) {
      // At each point of the smaller DEM, walk bi, bj up to rate and find
      // interp value
      while (bi < rate) {
        int curBigi = rate * i + bi;
        while (bj < rate) {
          int16_t interpValue = calcInterp(demGrid, i, j, bi, bj, rate, ncols);
          int curBigj = rate * j + bj;
          upDemGrid[getIdx(curBigi, curBigj, upNcols)] = interpValue;
          ++bj;
        }
        bj = 0; // reset the bj column back to 0 for this (i, j)
        ++bi;
      }
      bi = 0; // reset the bi row back to 0 for this (i, j)
    }
  }

  // Also must interpolate the last row/column: OOB for 2D interp, use 1D
  // Copy last col:
  bi = 0;
  for (i = 0; i < (nrows - 1); i++) {
    j = (ncols - 1); // Last col
    bj = 0;          // bj stays at 0 when j is max index
    int curBigj = rate * j + bj;
    while (bi < rate) {
      int16_t interpValue = interpCol(demGrid, i, j, bi, rate, ncols);
      int curBigi = rate * i + bi;
      upDemGrid[getIdx(curBigi, curBigj, upNcols)] = interpValue;
      ++bi;
    }
    bi = 0; // reset the bi row back to 0 for this (i, j)
  }

  // Copy last row:
  bj = 0;
  for (j = 0; j < (ncols - 1); j++) {
    i = (nrows - 1); // Last row
    bi = 0;          // bi stays at 0 when i is max index
    int curBigi = rate * i + bi;
    while (bj < rate) {
      int16_t interpValue = interpRow(demGrid, i, j, bj, rate, ncols);
      int curBigj = rate * j + bj;
      upDemGrid[getIdx(curBigi, curBigj, upNcols)] = interpValue;
      ++bj;
    }
    bj = 0; // reset the bj column back to 0 for this (i, j)
  }
  // Last, copy bottom right point
  upDemGrid[getIdx(upNrows - 1, upNcols - 1, upNcols)] =
      demGrid[getIdx(nrows - 1, ncols - 1, ncols)];

  printf("Finished with upsampling, writing to disk\n");

  fp = fopen(outfileUp, "wb");

  fwrite(upDemGrid, sizeof(int16_t), upNrows * upNcols, fp);
  fclose(fp);
  printf("%s write complete.\n", outfileUp);
  free(demGrid);
  free(upDemGrid);
  return 0;
}

const char *getFileExt(const char *filename) {
  // Finds the last . in a char*
  const char *dot = strrchr(filename, '.');
  if (!dot || dot == filename)
    return "";
  return dot;
}

int16_t calcInterp(int16_t *demGrid, int i, int j, int bi, int bj, int rate,
                   int ncols) {
  int16_t h1 = demGrid[getIdx(i, j, ncols)];
  int16_t h2 = demGrid[getIdx(i, j + 1, ncols)];
  int16_t h3 = demGrid[getIdx(i + 1, j, ncols)];
  int16_t h4 = demGrid[getIdx(i + 1, j + 1, ncols)];

  int a00 = h1;
  int a10 = h2 - h1;
  int a01 = h3 - h1;
  int a11 = h1 - h2 - h3 + h4;
  // x and y are between 0 and 1: how far in the 1x1 cell we are
  float x = (float)bj / rate;
  float y = (float)bi / rate;
  // Final result is cast back to int16_t by return type
  return a00 + (a10 * x) + (a01 * y) + (a11 * x * y);
}

int16_t interpRow(int16_t *demGrid, int i, int j, int bj, int rate, int ncols) {
  // x is between 0 and 1: how far along row between orig points
  float x = (float)bj / rate;

  int16_t h1 = demGrid[getIdx(i, j, ncols)];
  int16_t h2 = demGrid[getIdx(i, j + 1, ncols)];

  return x * h2 + (1 - x) * h1;
}

int16_t interpCol(int16_t *demGrid, int i, int j, int bi, int rate, int ncols) {
  // y is between 0 and 1: how far along column
  float y = (float)bi / rate;

  int16_t h1 = demGrid[getIdx(i, j, ncols)];
  int16_t h2 = demGrid[getIdx(i + 1, j, ncols)];

  return y * h2 + (1 - y) * h1;
}
