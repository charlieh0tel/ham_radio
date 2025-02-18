#! /usr/bin/env python3

import argparse
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import pysnr

from pydwf import (DwfLibrary, DwfEnumConfigInfo, DwfAnalogOutNode, DwfAnalogOutFunction, DwfAcquisitionMode,
                   DwfTriggerSource, DwfAnalogInTriggerType, DwfTriggerSlope, DwfState, DwfAnalogInFilter,
                   PyDwfError)
from pydwf.utilities import openDwfDevice


_NOISY = False


mplstyle.use('fast')


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


def configure_analog_output(device, channel, frequency, amplitude,
                            offset, symmetry=None):
    analogOut = device.analogOut
    analogOut.reset(-1)  # Reset both channels.

    node = DwfAnalogOutNode.Carrier
    analogOut.nodeEnableSet(channel, node, True)
    analogOut.nodeFunctionSet(channel, node, DwfAnalogOutFunction.Sine)
    analogOut.nodeFrequencySet(channel, node, frequency)
    analogOut.nodeAmplitudeSet(channel, node, amplitude)
    if symmetry:
        analogOut.nodeSymmetrySet(channel, node, symmetry)
    analogOut.nodeOffsetSet(channel, node, offset)
    analogOut.nodePhaseSet(channel, node, 0.)

    analogOut.configure(channel, True)


def run(analogIn, sample_frequency, record_length):
    analogIn.channelEnableSet(0, True)
    analogIn.channelFilterSet(0, DwfAnalogInFilter.Average)
    analogIn.channelRangeSet(0, 5.0)

    analogIn.acquisitionModeSet(DwfAcquisitionMode.Record)
    analogIn.frequencySet(sample_frequency)
    analogIn.recordLengthSet(record_length)

    num_samples = round(sample_frequency * record_length)
    acquisition_nr = 0
    fig = None
    ch1_line = None
    sinad_line = None
    sinad_text = None
    sinad_filter = MovingAverageFilter(4)

    while True:
        acquisition_nr += 1  # Increment acquisition number.
        if _NOISY:
            print("[{}] Recording {} samples ...".format(
                acquisition_nr, num_samples))

        samples = []
        total_samples_lost = total_samples_corrupted = 0
        analogIn.configure(False, True)  # Start acquisition sequence.

        while True:
            status = analogIn.status(True)
            (current_samples_available, current_samples_lost,
             current_samples_corrupted) = analogIn.statusRecord()

            total_samples_lost += current_samples_lost
            total_samples_corrupted += current_samples_corrupted

            if current_samples_lost != 0:
                lost_samples = np.full(current_samples_lost, np.nan)
                samples.append(lost_samples)

            if current_samples_available != 0:
                data = analogIn.statusData(0, current_samples_available)
                samples.append(data)

            if status == DwfState.Done:
                time_of_first_sample = 0.0
                break

        if total_samples_lost != 0:
            print("[{}] - WARNING - {} samples were lost! Reduce sample frequency.".format(
                acquisition_nr, total_samples_lost))

        if total_samples_corrupted != 0:
            print("[{}] - WARNING - {} samples could be corrupted! Reduce sample frequency.".format(
                acquisition_nr, total_samples_corrupted))

        samples = np.concatenate(samples)

        if len(samples) > num_samples:
            discard_count = len(samples) - num_samples
            if _NOISY:
                print("[{}] - NOTE - discarding oldest {} of {} samples ({:.1f}%); keeping {} samples.".format(
                    acquisition_nr,
                    discard_count, len(samples), 100.0 * discard_count / len(samples), num_samples))
            samples = samples[discard_count:]

        # Calculate sample time of each of the samples.
        t = time_of_first_sample + np.arange(len(samples)) / sample_frequency

        (sinad, _) = pysnr.sinad_signal(samples, fs=sample_frequency)
        sinad_filter.update(sinad)

        if fig is None:
            fig = plt.figure(figsize=(16, 8))
            fig.suptitle(f"Analog CH1 acquisition {acquisition_nr:5d}\n"
                         f"{num_samples} samples ({record_length} seconds at {sample_frequency} Hz)")
            ch1_axis = fig.add_subplot(111)
            ch1_axis.grid()
            ch1_axis.set_xlabel("acquisition time [s]")
            ch1_axis.set_ylabel("signal [V]")
            x_min = -0.05 * record_length
            x_max = 1.05 * record_length
            ch1_axis.set_xlim(x_min, x_max)
            ch1_axis.set_ylim(-2, 2)
            (ch1_line, ) = ch1_axis.plot(
                t, samples, color='#346f9f', label="channel 1")

            sinad_axis = ch1_axis.twinx()
            sinad_axis.set_ylabel("SINDAD [dB]")
            sinad_axis.set_ylim(-15, 25)
            sinad_line = sinad_axis.axhline(y=sinad, color='r')
            filtered_sinad = sinad_filter()
            sinad_text = sinad_axis.text(
                0, -9, f"SINAD={filtered_sinad:.3f} dB")
            fig.show()
        else:
            fig.suptitle(f"Analog CH1 acquisition {acquisition_nr:5d}\n"
                         f"{num_samples} samples ({record_length} seconds at {sample_frequency} Hz)")
            ch1_line.set_xdata(t)
            ch1_line.set_ydata(samples)
            sinad_line.set_ydata([sinad] * 2)
            filtered_sinad = sinad_filter()
            sinad_text.set_text(f"SINAD={filtered_sinad:.3f} dB")

        fig.canvas.draw()
        fig.canvas.flush_events()

        if len(plt.get_fignums()) == 0:
            # User has closed the window, finish.
            break


def main():
    parser = argparse.ArgumentParser(
        description="SINAD Meter")

    DEFAULT_SAMPLE_FREQUENCY = 16.0e3
    DEFAULT_RECORD_LENGTH = 500e-3

    parser.add_argument(
        "-sn", "--serial-number-filter",
        type=str,
        nargs='?',
        dest="serial_number_filter",
        help="serial number filter to select a specific Digilent Waveforms device"
    )

    parser.add_argument(
        "-fs", "--sample-frequency",
        type=float,
        default=DEFAULT_SAMPLE_FREQUENCY,
        help="sample frequency, in samples per second (default: {} Hz)".format(
            DEFAULT_SAMPLE_FREQUENCY)
    )

    parser.add_argument(
        "-r", "--record-length",
        type=float,
        default=DEFAULT_RECORD_LENGTH,
        help="record length, in seconds (default: {} s)".format(
            DEFAULT_RECORD_LENGTH)
    )

    parser.add_argument(
        "-o", "--enable-ch1-output",
        action="store_true",
        dest="enable_ch1_out",
        help="enable ch1 output"
    )

    args = parser.parse_args()

    dwf = DwfLibrary()

    def maximize_analog_in_buffer_size(configuration_parameters):
        """Select the configuration with the highest possible analog in buffer size."""
        return configuration_parameters[DwfEnumConfigInfo.AnalogInBufferSize]

    try:
        with openDwfDevice(dwf, serial_number_filter=args.serial_number_filter,
                           score_func=maximize_analog_in_buffer_size) as device:

            if args.enable_ch1_out:
                configure_analog_output(device, 0, frequency=100, amplitude=1.,
                                        offset=0., symmetry=0.25)

            run(device.analogIn, args.sample_frequency, args.record_length)
    except PyDwfError as exception:
        print("PyDwfError:", exception)


if __name__ == "__main__":
    main()
