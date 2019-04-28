#include <memory.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/timex.h>

int main(int argc, char **argv) {
  if (argc != 2) {
    fprintf(stderr, "usage: %s offset_ms\n", argv[0]);
    exit(1);
  }

  int offset_us = atoi(argv[1]);

  struct timeval offset;
  offset.tv_sec = 0;
  offset.tv_usec = (suseconds_t) offset_us;

  struct timeval now;
  int rc = gettimeofday(&now, NULL);
  if (rc < 0) {
    fprintf(stderr, "%s: gettimeofday failed: %m\n", argv[0]);
    exit(1);
  }

  struct timeval desired;
  timeradd(&now, &offset, &desired);

  rc = settimeofday(&desired, NULL);
  if (rc < 0) {
    fprintf(stderr, "%s: settimeofday failed: %m\n", argv[0]);
    exit(1);
  }

  
#if 0
  struct timex timex;
  memset(&timex, 0, sizeof(timex));
  timex.modes = ADJ_SETOFFSET;
  timex.time.tv_usec = (long) (offset_ms * 1000.);
  
  int rc = adjtimex(&timex);
  if (rc == TIME_OK) {
    exit(0);
  } else {
    fprintf(stderr, "%s: adjtimex failed: %m\n", argv[0]);
    exit(1);
  }
#endif
}
