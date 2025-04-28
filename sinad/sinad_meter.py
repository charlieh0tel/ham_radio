#! /usr/bin/env python3

import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import pysnr

import filters
import source as source_pkg
import source_digilent
import source_portaudio


_NOISY = False


mplstyle.use('fast')


def run(source, sample_frequency, record_length):
    num_samples = round(sample_frequency * record_length)

    acquisition_nr = 0
    fig = None
    ch1_line = None
    sinad_line = None
    sinad_text = None
    sinad_filter = filters.MovingAverageFilter(8)

    while True:
        acquisition_nr += 1
        if _NOISY:
            print(f"[{acquisition_nr}] Recording {num_samples} samples ...")

        samples = source.read()
        assert len(samples) == num_samples
        t = np.arange(len(samples)) / sample_frequency

        (sinad, _) = pysnr.sinad_signal(samples, fs=sample_frequency)

        sinad_filter.update(sinad)
        filtered_sinad = sinad_filter()

        suptitle_text = (
            f"{source.pretty_name} Acquisition # {acquisition_nr:5d}\n"
            f"{num_samples} samples ({record_length} seconds at {sample_frequency} Hz)")
        filtered_sinad_text = f"SINAD={filtered_sinad:.3f} dB"

        if fig is None:
            fig = plt.figure(figsize=(16, 8))
            fig.suptitle(suptitle_text)
            ch1_axis = fig.add_subplot(111)
            ch1_axis.grid()
            ch1_axis.set_xlabel("acquisition time [s]")
            ch1_axis.set_ylabel("signal [V]")
            x_min = -0.05 * record_length
            x_max = 1.05 * record_length
            ch1_axis.set_xlim(x_min, x_max)
            ch1_axis.set_ylim(*source.data_range())
            (ch1_line, ) = ch1_axis.plot(
                t, samples, color='#346f9f', label="channel 1")
            sinad_axis = ch1_axis.twinx()
            sinad_axis.set_ylabel("SINDAD [dB]")
            sinad_axis.set_ylim(-15, 25)
            sinad_line = sinad_axis.axhline(y=sinad, color='r')
            sinad_text = sinad_axis.text(
                x_min + 0.75 * (x_max - x_min), 22, filtered_sinad_text,
                fontsize=20)
            fig.show()
        else:
            fig.suptitle(suptitle_text)
            ch1_line.set_xdata(t)
            ch1_line.set_ydata(samples)
            sinad_line.set_ydata([sinad] * 2)
            sinad_text.set_text(filtered_sinad_text)

        fig.canvas.draw()
        fig.canvas.flush_events()

        if len(plt.get_fignums()) == 0:
            # User has closed the window, finish.
            break


def main():
    parser = argparse.ArgumentParser(
        description="SINAD Meter")

    parser.add_argument(
        "-S", "--source",
        choices=[source.name for source in source_pkg.SOURCE_REGISTRY],
        default="portaudio",
        help="Selects source.")
    parser.add_argument(
        "--help-source",
        action="store_true",
        dest="help_source",
        help="Prints usage related to selected source.")

    (args, unparsed_args) = parser.parse_known_args()

    source_class = source_pkg.SOURCE_REGISTRY.get(args.source)
    source_parser = argparse.ArgumentParser(
        description=f"SINAD Meter using {source_class.pretty_name}")
    default_sample_frequency = source_class.default_sample_frequency()
    source_parser.add_argument(
        "-s", "--sample-frequency",
        type=float,
        default=default_sample_frequency,
        help=f"sample frequency, in samples per second (default: {default_sample_frequency} Hz)")

    default_record_length = source_class.default_record_length()
    source_parser.add_argument(
        "-r", "--record-length",
        type=float,
        default=default_record_length,
        help=f"record length, in seconds (default: {default_record_length} s)")

    source_class.augment_argparse(source_parser)
    if args.help_source:
        source_parser.print_help()
        return
    source_args = source_parser.parse_args(args=unparsed_args)

    with source_class(source_args) as source:
        run(source, source_args.sample_frequency, source_args.record_length)


if __name__ == "__main__":
    main()
