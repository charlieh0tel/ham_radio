#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>

int main(int argc, char **argv) {
  if (argc == 1) {
  struct timeval old_delta;
    int rc = adjtime(NULL, &old_delta);
    if (rc != 0) {
      perror("adjtime");
      exit(1);
    }
    printf("old_delta_sec = %d\n", old_delta.tv_sec);
    printf("old_delta_usec = %d\n", old_delta.tv_usec);

  }

  if (argc != 2) {
    exit(99);
  }

  double n = atof(argv[1]);

  printf("adjusting by %f\n", n);

  struct timeval delta;

  delta.tv_sec = (time_t) n;
  delta.tv_usec = (suseconds_t) (1e6 * (n - delta.tv_sec));

  printf("delta_sec = %d\n", delta.tv_sec);
  printf("delta_usec = %d\n", delta.tv_usec);
  struct timeval old_delta;
  int rc = adjtime(&delta, &old_delta);
  printf("rc=%d\n", rc);
  printf("old_delta_sec = %d\n", old_delta.tv_sec);
  printf("old_delta_usec = %d\n", old_delta.tv_usec);
}
