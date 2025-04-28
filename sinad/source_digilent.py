#
# Analog Discovery 3 audio source.
#

import numpy as np

from pydwf import (DwfLibrary, DwfEnumConfigInfo, DwfAnalogOutNode,
                   DwfAnalogOutFunction, DwfAcquisitionMode, DwfState,
                   DwfAnalogInFilter)
from pydwf.utilities import openDwfDevice

import source


class DigilentSource(source.Source):
    name: str = "digilent"
    pretty_name: str = "Digilent DWF Source"

    @staticmethod
    def default_sample_frequency():
        return 16.0e3

    @staticmethod
    def default_record_length():
        return 200e-3

    @staticmethod
    def augment_argparse(parser):
        parser.add_argument(
            "-sn", "--serial-number-filter",
            type=str,
            nargs='?',
            dest="serial_number_filter",
            help="serial number filter to select a specific Digilent Waveforms device"
        )
        #
        # Useful hack.
        parser.add_argument(
            "-o", "--enable-ch1-output",
            action="store_true",
            dest="enable_ch1_out",
            help="enable ch1 output"
        )

    def __init__(self, args):
        self._num_samples =  round(args.sample_frequency * args.record_length)
        self._dwf = DwfLibrary()
        self._device = openDwfDevice(
            self._dwf,
            serial_number_filter=args.serial_number_filter,
            score_func=(
                lambda param: param[DwfEnumConfigInfo.AnalogInBufferSize]))
        self._analog_in = self._device.analogIn
        self._analog_in.channelEnableSet(0, True)
        self._analog_in.channelFilterSet(0, DwfAnalogInFilter.Average)
        self._analog_in.channelRangeSet(0, 5.0)
        self._analog_in.acquisitionModeSet(DwfAcquisitionMode.Record)
        self._analog_in.frequencySet(args.sample_frequency)
        self._analog_in.recordLengthSet(args.record_length)
        if args.enable_ch1_out:
            _configure_analog_output(
                self._device,
                0,
                frequency=100,
                amplitude=1.,
                offset=0.,
                symmetry=0.25)

    def close(self):
        self._device.close()

    def read(self):
        samples = []
        total_samples_lost = 0
        total_samples_corrupted = 0
        self._device.analogIn.configure(False, True)
        while True:
            status = self._analog_in.status(True)

            (current_samples_available, current_samples_lost,
             current_samples_corrupted) = self._analog_in.statusRecord()
            total_samples_lost += current_samples_lost
            total_samples_corrupted += current_samples_corrupted

            if current_samples_available != 0:
                current_samples = self._analog_in.statusData(0, current_samples_available)
                samples.append(current_samples)

            if status == DwfState.Done:
                break


        if total_samples_lost > 0:
            print(f"DigilentSource: {total_samples_lost} list samples in acquisition")
        if total_samples_corrupted > 0:
            print(f"DigilentSource: {total_samples_corrupted} corrupted samples in acquisition")

        samples = np.concatenate(samples)
        if len(samples) > self._num_samples:
            discard_count = len(samples) - self._num_samples
            #print(f"discarding oldest {discard_count} samples out of {len(samples)}")
            samples = samples[discard_count:]

        return samples

    def data_range(self):
        return (-2.0, 2.0)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_args):
        self.stop()
        self.close()


def _configure_analog_output(device, channel, frequency, amplitude,
                             offset, symmetry=None):
    analog_out = device.analogOut
    analog_out.reset(-1)  # Reset both channels.

    node = DwfAnalogOutNode.Carrier
    analog_out.nodeEnableSet(channel, node, True)
    analog_out.nodeFunctionSet(channel, node, DwfAnalogOutFunction.Sine)
    analog_out.nodeFrequencySet(channel, node, frequency)
    analog_out.nodeAmplitudeSet(channel, node, amplitude)
    if symmetry:
        analog_out.nodeSymmetrySet(channel, node, symmetry)
        analog_out.nodeOffsetSet(channel, node, offset)
        analog_out.nodePhaseSet(channel, node, 0.)

    analog_out.configure(channel, True)


#
source.SOURCE_REGISTRY.register(DigilentSource)
