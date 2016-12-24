#!/usr/bin/python

import math
import time
import serial
import sys

import band_plan
import elecraft

ONE_KHZ = 1e3
OK_SWR = 1.3

def KAT500MemorySegmentWidth(frequency):
    if frequency < 3e6:
        return 10e3
    elif frequency < 26e6:
        return 20e3
    elif frequency < 38e6:
        return 100e3
    elif frequency < 60e6:
        return 200e3
    else:
        assert False


def ToggleTune(rig, on_time):
    try:
        rig.TuneToggle()
        time.sleep(on_time)
    finally:
        rig.TuneToggle()

def TuneRigAt(rig, tuner, frequency):
    tuner.ClearFault()

    rig.SetVfoA(frequency)
    time.sleep(0.100)
    tuner.SetBypass(True)
    tuner.ClearMatch()
    time.sleep(0.100)
    ToggleTune(rig, 1.)

    fault = tuner.GetFaultCode()
    if fault > 1:
        print "Ooops. fault=%d" % fault
    bypassed_vswr = tuner.ReadVSWRInBypass() if fault == 0 else 99.99
    tuner.ClearFault()
        
    frequency2 = tuner.ReadFrequency()
    if (math.fabs(frequency - frequency2) / frequency) > 0.05:
        print "Huh?", frequency, frequency2

    if bypassed_vswr > OK_SWR:
        try:
            rig.TuneToggle()
            tuner.FullTune()
        finally:
            rig.TuneToggle()

    fault = tuner.GetFaultCode()
    if fault > 1:
        print "Ooops. fault=%d" % fault

    bypassed = tuner.ReadBypass()
    if not bypassed:
        assert fault == 0
        ToggleTune(rig, 1.)
        match = tuner.ReadMatch()
        vswr = tuner.ReadVSWR()
        print "%10.0f %5.2f  %-10s %5.2f %6.0f %6.0f %s" % (
            frequency / 1e3, bypassed_vswr, "matched", vswr,
            match[0] * 1e9, match[1] * 1e12, match[2])
    elif fault == 0:
        print "%10.0f %5.2f  %-10s" % (
            frequency / 1e3, bypassed_vswr, "bypassed")
    else:
        tuner.SetBypass(True)
        print "%10.0f %5.2f  %-10s" % (
            frequency / 1e3, bypassed_vswr, "failed (%d)" % fault_code)
    tuner.SaveMemory()


def TrainKAT500(rig, tuner, bands):
    antenna = tuner.ReadAntenna()
    print "Erasing memory for antenna #%d" % antenna
    tuner.EraseMemoryAllBands(antenna)
    for band in bands:
        print "* %s *" % band.name
        print "       kHz byswr  status       swr     nH     pF A/T"
        if band.frequency_range.is_discrete:
            # Could skip frequencies that are within a step, but not worth the
            # bother.
            for center in band.frequency_range.discrete_values:
                TuneRigAt(rig, tuner, center)
        else:
            start_frequency = band.frequency_range.min_inclusive
            stop_frequency = band.frequency_range.max_inclusive
            step = KAT500MemorySegmentWidth(start_frequency)
            frequency = start_frequency + int(step/2.)
            while frequency <= stop_frequency:
                TuneRigAt(rig, tuner, frequency)
                frequency += step


def main(argv):
    with serial.Serial(argv[1], 38400) as rig_port:
        rig = elecraft.Transceiver(rig_port)
        with serial.Serial(argv[2], 38400) as tuner_port:
            tuner = elecraft.Tuner(tuner_port)
            tuner.Verify()
            TrainKAT500(rig, tuner, band_plan.ALL_BANDS)
    
if __name__ == "__main__":
    main(sys.argv)
