"""Does the return path resonate on its own?

The probe showed |Z| at a quarter-wave antenna swinging 133 -> 3500 ohm with
nothing but the return length changing.  If the return is a resonator in its
own right, |Z| should peak where the drop plus the return run approaches a
half-wave multiple, independent of the antenna wire.
"""

import numpy as np

from nec_model import C, end_fed_zin

FREQ_HZ = 14.2e6
HEIGHT_M = 10.0
ANTENNA_RATIOS = (0.25, 0.375)  # both low-Z points, away from half waves


if __name__ == "__main__":
    lam = C / FREQ_HZ
    print(f"lambda = {lam:.2f} m, h = {HEIGHT_M} m, average ground")
    print("return path electrical length counts the vertical drop too.\n")
    print(f"{'ret run':>8} {'drop+run':>9} {'/lambda':>8}", end="")
    for r in ANTENNA_RATIOS:
        print(f" {'|Z| @ ' + str(r) + 'lam':>16}", end="")
    print()
    for ret in np.arange(2.0, 32.0, 1.5):
        total = HEIGHT_M + ret
        print(f"{ret:8.1f} {total:9.1f} {total / lam:8.3f}", end="")
        for ratio in ANTENNA_RATIOS:
            z = end_fed_zin(ratio * lam, FREQ_HZ, HEIGHT_M, ret)
            print(f" {abs(z):16.1f}", end="")
        print()
