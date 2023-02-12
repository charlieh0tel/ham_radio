/*
 * Simple calculations of half wavelengths of ham bands.
 *
 * Mike Markowski AB3AP
 * Thu Jun 28 07:01:26 EDT 2012
 */

#include <stdio.h>

/*
 * For a given frequency range, calculate the half wavelength range and print
 * it.  In addition, print up to 4th multiples of each range up to the length
 * of 160m half wavelength.
 *
 * Comments are also printed out, assuming that the output will saved to a file,
 * and that file used by gnuplot for plotting.
 */
void rw(double min_kHz, double max_kHz) {
  
  double lambda0_ft, lambda1_ft;
  double loFreq_MHz = 1.8;
  double lambdaMax_ft = 2 * 468 / loFreq_MHz; /* Max wavelength in band. */
  int n;

  double qtr_ft = 468 / loFreq_MHz / 2;
  printf("# %.3f to %.3f kHz, too short for %f MHz\n",
	 min_kHz, max_kHz, loFreq_MHz);
  printf("%.3f 0\n%.3f 1\n%.3f 1\n%.3f 0\n\n",
	 0., 0+(1e-3), qtr_ft, qtr_ft+(1e-3));
  
  n = 1; /* First multiple. */
  do {
    lambda0_ft = n * 468 / (max_kHz * 1e-3);
    lambda1_ft = n * 468 / (min_kHz * 1e-3);
    /* Print in format gnuplot expects. */
    printf("# %.3f to %.3f kHz, multiple %d\n",
	   min_kHz, max_kHz, n);
    printf("%.3f 0\n%.3f 1\n%.3f 1\n%.3f 0\n\n",
	   lambda0_ft-(1e-3), lambda0_ft,
	   lambda1_ft, lambda1_ft+(1e-3));
    /* Prepare for next multiple. */
    n++;
    /* Change '5' in next line to max number of multiples to calculate. */
  } while (lambda1_ft < lambdaMax_ft && n < 5);
}

/*
 * Print ranges of half wavelengths for ecah ham band.
 */
void printHalfwaves() {

  rw(1800., 2000.);       /* 160m */
  rw(3500., 4000.);       /* 80m */
  rw(5330.5, 5405.);      /* 40m */
  rw(7000., 7300.);       /* 40m */
  rw(10100., 10150.);     /* 30m */
  rw(14000., 14350.);     /* 20m */
  rw(18068., 18168.);     /* 17m */
  rw(21000., 21450.);     /* 15m */
  rw(24890., 24990.);     /* 12m */
  rw(28000., 29700.);     /* 10m */
  rw(50000., 54000.);     /* 6m */
}

int main(int argc, char **argv) {
  printHalfwaves();
  return 0;
}
