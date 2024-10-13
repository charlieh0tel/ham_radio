#!/usr/bin/python3

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

amplitudes=np.array(
    [-28.83, -31.16, -34.5, -36.33, -40.0, -42.5, -45.16,
     -47.66, -50.0, -52.83, -55.0, -57.5, -59.5, -65.16, -62.33, -70.16,
     -64.66, -75.0, -66.33, -80.5, -67.33, -81.5, -68.0, -83.5, -66.33,
     -85.16, -66.66, -84.16, -65.0, -83.5, -66.5, -83.83, -64.0, -81.5,
     -66.66, -81.83, -68.0, -82.16, -67.83, -82.16, -66.83, -81.33, -66.83,
     -79.5, -66.5, -82.33, -66.83, -78.5, -65.5, -79.16, -63.33, -77.0,
     -62.83, -74.66, -61.0, -73.33, -62.16, -75.16, -63.33, -76.5, -65.33,
     -78.0, -66.66, -81.33, -67.66, -81.33, -66.16, -81.83, -67.33, -81.83,
     -65.33, -85.5, -66.66, -84.5, -68.0, -82.5, -66.5, -82.83, -64.66,
     -82.66, -67.0, -84.16, -63.16, -81.83, -68.5, -83.0, -66.16, -82.33,
     -66.0, -82.0, -68.33, -81.5, -68.0, -83.16, -66.83, -81.83, -68.5,
     -85.0, -66.16, -84.16, -66.16, -83.66, -67.0, -84.5, -68.0, -82.66,
     -67.16, -83.33, -66.5, -84.66, -65.66, -82.66, -67.0, -85.5, -69.16,
     -84.0, -65.66, -84.66, -66.5, -83.0, -67.33, -83.33, -66.5, -83.0,
     -65.66, -84.66, -67.66, -82.16, -67.33, -82.16, -66.66, -83.66,
     -67.66, -83.66, -66.66, -81.83, -65.0, -82.66, -68.16, -83.66, -67.0,
     -83.5, -66.33, -83.83, -65.33, -82.83, -67.33, -84.0, -66.5, -85.33,
     -65.83, -84.0, -67.83, -82.66, -66.66, -82.16, -65.83, -82.83, -66.5,
     -81.5, -66.0, -83.5, -67.5, -85.83, -66.66, -84.0, -67.83, -84.33,
     -66.83, -83.66, -66.83, -85.0, -67.33, -82.66, -66.66, -81.33, -67.16,
     -82.83, -67.16, -81.33, -67.33, -83.16, -67.5, -82.66, -64.5, -83.0,
     -66.83, -82.0, -65.83, -82.33, -66.33, -82.0, -66.16, -84.16, -66.5,
     -85.5, -68.16, -81.66, -65.66, -84.66, -67.66, -86.0, -66.83, -84.83,
     -66.0, -83.66, -69.33, -81.5, -66.83, -82.16, -65.0, -83.66, -66.83,
     -84.16, -64.66, -85.0, -66.33, -84.66, -67.66, -82.66, -65.16, -83.66,
     -64.66, -84.33, -67.16, -82.66, -68.33, -83.83, -66.33, -84.0, -67.5,
     -83.83, -67.16, -83.0, -65.83, -82.0, -68.16, -82.33, -66.0, -83.66,
     -67.5, -81.33, -67.5, -81.5, -68.0, -80.83, -67.83, -82.66, -67.33,
     -83.83, -66.5, -83.5, -67.33, -82.33, -63.83, -83.83, -68.5, -83.83,
     -66.83, -83.0, -67.0, -82.16, -64.33, -82.83, -66.0, -82.83, -68.0,
     -83.33, -68.16, -82.16, -66.16, -83.66, -67.66, -83.0, -67.33, -82.83,
     -66.16, -82.0, -68.16, -82.5, -66.33, -82.5, -67.5, -85.5, -67.16,
     -83.16, -66.0, -82.5, -67.16, -83.16, -65.0, -82.5, -67.16, -83.0,
     -65.5, -83.66, -67.5, -83.83, -65.33, -83.0, -66.16, -83.0, -65.66,
     -82.5, -66.33, -83.33, -68.0, -83.16, -66.16, -80.83, -66.66, -82.0,
     -67.83, -81.16, -67.0, -82.33, -66.83, -84.16, -67.33, -81.83, -67.66,
     -82.0, -68.16, -82.33, -66.66, -83.16, -67.66, -81.83, -68.33, -83.33,
     -67.0, -85.0, -67.16, -82.16, -68.66, -82.83, -66.16, -83.66, -66.5,
     -81.5, -68.0, -84.66, -67.66, -83.33, -68.33, -80.33, -68.0, -83.83,
     -65.66, -81.66, -67.66, -85.66, -65.83, -83.33, -66.16, -79.83, -66.5,
     -81.66, -66.5, -81.5, -66.83, -82.33, -67.5, -82.16, -66.83, -82.16,
     -66.66, -83.16, -66.66, -82.5, -67.5, -82.66, -67.83, -84.33, -66.0,
     -81.66, -67.83, -83.83, -66.66, -84.33, -66.83, -82.0, -67.16, -86.33,
     -67.0, -83.0, -67.33, -83.16, -66.66, -85.33, -68.16, -82.5, -68.5,
     -82.33, -68.66, -83.83, -67.83, -83.16, -65.5, -82.83, -66.0, -82.5,
     -67.5, -81.16, -66.83, -84.33, -66.66, -82.66, -66.83, -83.83, -66.83,
     -82.33, -66.33, -81.33, -66.33, -82.33, -66.0, -82.5, -66.66, -85.0,
     -67.83, -82.83, -67.0, -82.33, -65.0, -83.33, -66.0, -82.66, -66.66,
     -82.83, -66.5, -83.16, -67.33, -82.16, -66.16, -81.83, -68.0, -83.83,
     -66.66, -83.0, -67.0, -83.0, -67.0, -84.0, -67.83, -82.5, -64.16,
     -83.0, -68.16, -83.16, -67.5, -83.33, -68.0, -82.5, -66.83, -81.33,
     -67.16, -82.0, -69.0, -83.5, -68.16, -82.5, -67.33, -80.66, -67.16,
     -81.5, -67.66, -84.83, -65.33, -81.83, -65.33, -83.66, -66.83, -82.66,
     -66.5, -83.5, -68.0, -81.0, -67.33, -81.33, -66.33, -82.0, -67.5,
     -83.16, -67.66, -80.66, -69.0, -84.16, -67.66, -81.0, -67.16, -84.33,
     -67.5, -84.16, -65.33, -84.16, -68.5, -82.0, -66.83, -83.83, -67.33,
     -85.0, -67.5, -82.16, -66.33, -82.33, -67.5, -82.66, -67.66, -83.33,
     -66.16, -82.66, -67.0, -81.83, -66.0, -82.83, -64.33, -84.33, -66.0,
     -82.66, -64.83, -85.33, -67.83, -81.0, -66.5, -83.16, -67.0, -82.33,
     -66.33, -84.66, -67.5, -82.0, -65.0, -83.0, -65.16, -83.0, -67.16,
     -83.5, -67.66, -84.5, -65.33, -83.5, -68.16, -84.16, -66.33, -86.5,
     -67.16, -83.0, -68.5, -82.83, -65.5, -83.5, -67.83, -85.33, -67.33,
     -86.66, -66.83, -83.0, -66.16, -85.33, -66.83, -82.0, -66.16, -83.0,
     -67.16, -84.16, -67.5, -82.66, -66.16, -83.16, -68.0, -81.66, -67.16,
     -81.0, -67.0, -82.66, -67.16, -81.66, -67.0, -83.16, -68.16, -82.5,
     -66.66, -83.0, -66.0, -82.83, -66.16, -82.16, -67.5, -862.83, -67.5,
     -81.33, -67.0, -83.33, -67.0, -84.33, -64.5, -81.66, -67.5, -83.5,
     -65.83])

amplitudes = amplitudes + 100.

frequencies=np.linspace(1e6, 100e6, len(amplitudes), dtype=np.float64)

df = pd.DataFrame({ 'frequency': frequencies,
                    'amplitude': amplitudes})

#ax = df.plot(kind='scatter', x='frequency', y='amplitude', logy=True)

#plt.scatter(frequencies, amplitudes)
plt.plot(frequencies, amplitudes)
plt.yscale("log")
plt.show()
