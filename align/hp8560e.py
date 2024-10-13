import io
import struct
import time

import numpy as np

import pymeasure
import pymeasure.instruments


class HP8560E(pymeasure.instruments.Instrument):
    N_POINTS = 601
    _BOOLS = {True: "ON", False: "OFF"}
    _SWEEP_COUPLING = {"SA", "SR"}

    def __init__(self, adapter, name="HP 8560E Spectrum Analyzer", **kwargs):
        super().__init__(adapter, name, includeSCPI=False, **kwargs)

    # not needed with later pymeasure
    def reset(self):
        raise NotImplementedError("No SCPI")

    # not needed with later pymeasure
    def clear(self):
        raise NotImplementedError("No SCPI")

    
    log_scale = pymeasure.instruments.Instrument.setting(
        "IP;",
        """Preset the instrument."""
    )

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

    trace_a = pymeasure.instruments.Instrument.control(
        "TDF P;TRA?", "TDF P;TRA %s;",
        """A property for the data points of trace A.  This property
        can be set.
        """,
        set_process = lambda value: " ".join(map(lambda v: "%.2f" % v, value)))

    trace_b = pymeasure.instruments.Instrument.control(
        "TDF P;TRB?", "TDF P;TRB %s;",
        """A property for the data points of trace B.  This property
        can be set.
        """,
        set_process = lambda value: " ".join(map(lambda v: "%.2f" % v, value)))

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
        # Seems like there should be a better way.
        done = self.ask("DONE?;").strip()
        while not done:
            time.sleep(0.25)
            done = self.read()
