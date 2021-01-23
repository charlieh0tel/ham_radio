#include <stdio.h>
#include <stdlib.h>
#include <sys/timex.h>
#include <string.h>

int main(int argc, char **argv) {
  if (argc != 2) {
    exit(99);
  }

  double n = atof(argv[1]);

  printf("adjusting by %f\n", n);

  struct timex timex;
  memset(&timex, 0, sizeof(timex));

  timex.modes = ADJ_NANO | ADJ_OFFSET;
  timex.offset = (long) (n * 1e9);

  int rc = adjtimex(&timex);
  printf("rc=%d\n", rc);
}
