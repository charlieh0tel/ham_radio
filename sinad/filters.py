import numpy as np

class MovingAverageFilter:
    def __init__(self, window_size):
        self.window_size = window_size
        self.data = np.array([])

    def update(self, value):
        self.data = np.append(self.data, value)
        if len(self.data) > self.window_size:
            self.data = self.data[1:]

    def __call__(self):
        if len(self.data) > 0:
            return np.mean(self.data)
        else:
            return 0
