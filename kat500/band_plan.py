#
# Band plan for United States
#

class DiscreteRange(object):
    def __init__(self, discrete_values):
        self._discrete_values = set(discrete_values)

    @property
    def discrete_values(self):
        return self._discrete_values

    @property
    def is_discrete(self):
        return True

    def InBand(self, frequency):
        # This is prety lame.
        return frequency in self._discrete_values

    def __repr__(self):
        return str(self._discrete_values)


class ContinuousRange(object):
    def __init__(self, min_inclusive, max_inclusive):
        assert min_inclusive <= max_inclusive
        self._min_inclusive = min_inclusive
        self._max_inclusive = max_inclusive

    @property
    def min_inclusive(self):
        return self._min_inclusive

    @property
    def max_inclusive(self):
        return self._max_inclusive

    @property
    def is_discrete(self):
        return False

    def InBand(self, frequency):
        return (frequency >= self._min_inclusive and
                frequency <= self._max_inclusive)

    def __repr__(self):
        return "[%s, %s]" % (self._min_inclusive, self._max_inclusive)


class Band(object):
    def __init__(self, wavelength_meter, frequency_range):
        self._wavelength_meter = wavelength_meter
        self._frequency_range = frequency_range

    @property
    def name(self):
        return "%dm" % self._wavelength_meter

    @property
    def frequency_range(self):
        return self._frequency_range

    @property
    def wavelength_meter(self):
        return self._wavelength_meter

    def __repr__(self):
        return "<Band %s %s>" % (self._name, self._frequency_range)


BAND_160M = Band(160, ContinuousRange(1.8e6, 2e6))
BAND_80M = Band(80, ContinuousRange(3.5e6, 4.0e6))
BAND_60M = Band(60,
                DiscreteRange([5.332e6, 5.348e6, 5.3585e6, 5.373e6, 5.405e6]))
BAND_40M = Band(40, ContinuousRange(7e6, 7.3e6))
BAND_30M = Band(30, ContinuousRange(10.1e6, 10.15e6))
BAND_20M = Band(20, ContinuousRange(14e6, 14.35e6))
BAND_17M = Band(17, ContinuousRange(18.068e6, 18.168e6))
BAND_15M = Band(15, ContinuousRange(21e6, 21.45e6))
BAND_12M = Band(12, ContinuousRange(24.89e6, 24.99e6))
BAND_10M = Band(10, ContinuousRange(28e6, 29.7e6))
BAND_6M = Band(6, ContinuousRange(50e6, 54e6))

ALL_BANDS = [BAND_160M, BAND_80M, BAND_60M, BAND_40M,
             BAND_30M, BAND_20M, BAND_17M, BAND_15M,
             BAND_12M, BAND_10M, BAND_6M]


def FindBandByFrequency(frequency):
    # This doesn't work very well for 60m.
    for band in ALL_BANDS:
        if band.InBand(frequency):
            return band
    return None

def FindBandByName(name):
    for band in ALL_BANDS:
        if band.name == name:
            return band
    assert False, "No such band as %s" % name
