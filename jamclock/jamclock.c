#include <assert.h>
#include <memory.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/timex.h>

const int kMicrosecondPerSecond = 1000000;

int main(int argc, char **argv) {
  if (argc != 2) {
    fprintf(stderr, "usage: %s offset_us\n", argv[0]);
    exit(1);
  }

  int offset_total_us = atoi(argv[1]);
  int offset_s = offset_total_us / kMicrosecondPerSecond;
  int offset_us = offset_total_us - (offset_s * kMicrosecondPerSecond);
  assert(offset_total_us == 
	 (offset_s * kMicrosecondPerSecond + offset_us));

  struct timeval offset;
  offset.tv_sec = (time_t) offset_s;
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

  return 0;
}
