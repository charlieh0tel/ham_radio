import dataclasses
import enum
import io
import struct
import time

import numpy as np

import pymeasure
import pymeasure.instruments
import pymeasure.instruments.validators
import pyvisa.errors

import ablock


class HP8560E(pymeasure.instruments.Instrument):
    N_POINTS = 601
    _A_BLOCK_SIZE = 4 + 2 * N_POINTS
    _BOOLS = {True: "ON", False: "OFF"}
    _SWEEP_COUPLING = {"SA", "SR"}
    _AMPLITUDE_UNITS = {"DBM", "DBMV", "DBUV", "V", "W", "AUTO", "MAN"}

    def __init__(self, adapter, name="HP 8560E Spectrum Analyzer", **kwargs):
        super().__init__(adapter, name, includeSCPI=False, **kwargs)

    start_frequency = pymeasure.instruments.Instrument.control(
        "FA?;", "FA %e;",
        """A floating point property that represents the start frequency
        in Hz. This property can be set.
        """
    )
    stop_frequency = pymeasure.instruments.Instrument.control(
        "FB?;", "FB %e;",
        """A floating point property that represents the stop frequency
        in Hz. This property can be set.
        """
    )        
    center_frequency = pymeasure.instruments.Instrument.control(
        "CF?;", "CF %e;",
        """A floating point property that represents the center frequency
        in Hz. This property can be set.
        """
    )
    span = pymeasure.instruments.Instrument.control(
        "SP?;", "SP %e;",
        """A floating point property that represents the span in Hz.
        This property can be set.
        """
    )
    reference_level = pymeasure.instruments.Instrument.control(
        "RL?;", "RL %e dB;",
        """A floating point property that represents the reference level
        in the dB.  This property can be set.
        """
    )
    resolution_bandwidth = pymeasure.instruments.Instrument.control(
        "RB?;", "RB %e;",
        """A floating point property that represents the resolution
        bandwidth.  This property can be set.
        """
    )
    video_bandwidth = pymeasure.instruments.Instrument.control(
        "VB?;", "VB %e;",
        """A floating point property that represents the video
        bandwidth.  This property can be set.
        """
    )
    sweep_time = pymeasure.instruments.Instrument.control(
        "ST?;", "ST %e;",
        """A floating point property that represents the sweep
        time.  This property can be set.
        """
    )
    log_scale = pymeasure.instruments.Instrument.control(
        "LG?;", "LG %e;",
        """A floating point property that represents the log
        scale.  This property can be set.
        """
    )
    source_power = pymeasure.instruments.Instrument.control(
        "SRCPWR?;", "SRCPWR %s;",
        """A boolean property that enables or disables the
        tracking generator.  This property can be set.
        """,
        validator=pymeasure.instruments.validators.strict_discrete_set,
        values=_BOOLS,
        map_values=True
    )
    normalize = pymeasure.instruments.Instrument.control(
        "NORMLIZE?;", "NORMLIZE %s;",
        """A boolean property that enables or disables the
        tracking generator.  This property can be set.
        """,
        validator=pymeasure.instruments.validators.strict_discrete_set,
        values=_BOOLS,
        map_values=True
    )
    sweep_couple = pymeasure.instruments.Instrument.control(
        "SWPCPL?;", "SWPCPL %s;",
        """A property that sets the sweep coupling.  This property can be set.
        """,
        validator=pymeasure.instruments.validators.strict_discrete_set,
        values=_SWEEP_COUPLING,
    )
    amplitude_units = pymeasure.instruments.Instrument.control(
        "AUNITS?", "AUNITS %s",
        """A property that sets the amplitude units.  This property can be set.
        """,
        validator=pymeasure.instruments.validators.strict_discrete_set,
        values=_AMPLITUDE_UNITS
    )
    trace_a = pymeasure.instruments.Instrument.measurement(
        "TDF P;TRA?",
        """A property for the data points of trace A in parameter units.
        """
        )
    trace_b = pymeasure.instruments.Instrument.measurement(
        "TDF P;TRB?",
        """A property for the data points of trace B in parameter units."
        """
        )
    log_scale = pymeasure.instruments.Instrument.control(
        "LG?", "LG %d DB",
        """
        Control the logarithmic amplitude scale. When in linear
        mode, querying 'logarithmic_scale' returns a “0”.
        Allowed values are 0, 1, 2, 5, 10

        Type: :class:`int`

        .. code-block:: python

            if instr.logarithmic_scale:
                pass

            # set the scale to 10 db per division
            instr.logarithmic_scale = 10

        """,
        cast=int,
        validator=pymeasure.instruments.validators.strict_discrete_set,
        values=[0, 1, 2, 5, 10]
    )


    @property
    def frequencies(self):
        """ Returns a numpy array of frequencies in Hz that
        correspond to the current settings of the instrument.
        """
        return np.linspace(
            self.start_frequency,
            self.stop_frequency,
            self.N_POINTS,
            dtype=np.float64
        )

    def take_sweep(self):
        self.write("TS;")
        self.wait_for_done()
        
    def preset(self):
        self.write("IP;")

    def set_single_sweep_mode(self):
        self.write("SNGLS;")

    def wait_for_done(self):
        """
        # Needed for prologix.  Any better way?
        done = self.ask("DONE?;").strip()
        while not done:
            time.sleep(0.25)
            done = self.read()
        """

        """
        # Needed for VISA with small timeout.
        while True:
            try:
                self.ask("DONE?", query_delay=0.250)
                return
            except pyvisa.errors.VisaIOError:
                pass
        """

        # Seems to be OK for VISA with much increased timeout.
        self.ask("DONE?;")

    def read_trace(self, which='A'):
        amplitude_units = self.amplitude_units
        reference_level = self.reference_level
        log_scale = self.log_scale
        frequencies = self.frequencies
        self.write(f"TDF A;TR{which}?;")
        trace_data = self.read_bytes(self._A_BLOCK_SIZE)
        trace_mu = ablock.from_ablock_u16(trace_data)
        return self.Trace(amplitude_units=amplitude_units,
                          reference_level=reference_level,
                          log_scale=log_scale,
                          frequencies=frequencies,
                          trace_mu=trace_mu)

    def write_trace(self, trace, which='A'):
        self.amplitude_units = trace.amplitude_units
        self.reference_level = trace.reference_level
        self.log_scale = trace.log_scale
        self.write("TDF A;")
        trace_data = ablock.to_ablock_u16(trace.trace_mu)
        self.write_bytes(b'TR' + bytes(which, "ascii") +
                         trace_data)


    @dataclasses.dataclass
    class Trace:
        amplitude_units: str
        reference_level: float
        log_scale: int
        frequencies: [float]
        trace_mu: [int]

        def to_parameter_units(self):
            if self.amplitude_units.startswith("DB"):
                return map(lambda x: self.reference_level + self.log_scale * (x / 60. - 10.),
                           self.trace_mu)
            else:
                return map(lambda x: self.reference_level * (x / 600.),
                           self.trace_mu)
