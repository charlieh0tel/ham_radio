import dataclasses

@dataclasses.dataclass
class Band:
    name: str
    start_frequency: float
    stop_frequency: float


BANDS=[
    Band(name="160m", start_frequency=1.800e6, stop_frequency=2.000e6),
    Band(name="80m", start_frequency=3.500e6, stop_frequency=4.000e6),
    # 60m is channelized in the US, but this is fine for what we are doing.
    Band(name="60m", start_frequency=5.250e6, stop_frequency=5.450e6),
    Band(name="40m", start_frequency=7.000e6, stop_frequency=7.300e6),
    Band(name="30m", start_frequency=10.100e6, stop_frequency=10.150e6),
    Band(name="20m", start_frequency=14.000e6, stop_frequency=14.350e6),
    Band(name="17m", start_frequency=18.068e6, stop_frequency=18.168e6),
    Band(name="15m", start_frequency=21.000e6, stop_frequency=21.450e6),
    Band(name="12m", start_frequency=24.890e6, stop_frequency=24.990e6),
    Band(name="10m", start_frequency=28.000e6, stop_frequency=29.700e6),
    Band(name="6m", start_frequency=50.000e6, stop_frequency=54.000e6)
]

BAND_BY_NAME={band.name: band for band in BANDS}
