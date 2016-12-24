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
        assert False, "Unexpected frequency %f" % frequency


def ToggleTune(rig, on_time):
    try:
        rig.TuneToggle()
        time.sleep(on_time)
    finally:
        rig.TuneToggle()

def ForceBypass(tuner):
    # For some reason we need this loop ...
    for n in xrange(10):
        tuner.SetBypass(True)
        if tuner.ReadBypass():
            return
        time.sleep(0.100)
    assert False, "Failed to set bypass"

def TuneRigAt(rig, tuner, frequency):
    tuner.ClearFault()
    tuner.CancelTune()

    rig.SetVfoA(frequency)
    time.sleep(0.100)
    tuner.ClearMatch()
    ForceBypass(tuner)
    time.sleep(0.100)
    ToggleTune(rig, 1.)

    fault = tuner.GetFaultCode()
    assert fault in [0, 4], "Unexpected fault code %d" % fault
    bypassed_vswr = tuner.ReadVSWRInBypass() if fault == 0 else 99.99
    tuner.ClearFault()
        
    frequency2 = tuner.ReadFrequency()
    if (math.fabs(frequency - frequency2) / frequency) > 0.05:
        print "Huh?", frequency, frequency2

    if bypassed_vswr > OK_SWR:
        xmit_on = False
        try:
            rig.TuneToggle()
            xmit_on = True
            tuner.FullTune()
        finally:
            if xmit_on:
                rig.TuneToggle()
        tuning = tuner.ReadTunePoll()
        if tuning:
            print "Oops ... still tuning?"
            tuner.CancelTune()
        fault = tuner.GetFaultCode()
        assert fault in [0, 1, 4], "Unexpected fault code %d" % fault
        if fault == 0:
            bypassed = tuner.ReadBypass()
            match = tuner.ReadMatch()
            vswr = tuner.ReadVSWR()
            print "%10.0f %5.2f  %-10s %5.2f %6.0f %6.0f %s" % (
                frequency / 1e3, bypassed_vswr,
                ("matched" if not bypassed else "nomatch"), vswr,
                match[0] * 1e9, match[1] * 1e12, match[2])
        else:
            tuner.ClearMatch()
            tuner.SetBypass(True)
            print "%10.0f %5.2f  %-10s" % (
                frequency / 1e3, bypassed_vswr, "failed (%d)" % fault_code)
    else:
        assert fault == 0, "Unexpected fault code %d" % fault
        tuner.ClearMatch()
        tuner.SetBypass(True)
        print "%10.0f %5.2f  %-10s" % (
            frequency / 1e3, bypassed_vswr, "bypassed")
    tuner.SaveMemory()

def TrainKAT500OnBand(rig, tuner, band):
    print "* %s *" % band.name
    print "       kHz byswr  status       swr     nH     pF A/T"
    antenna = tuner.ReadAntenna()
    tuner.EraseMemory(antenna, band)
    time.sleep(3.)               # a couple of seconds say the manual
    if band.frequency_range.is_discrete:
        # Could skip frequencies that are within a step.
        for center in band.frequency_range.discrete_values:
            TuneRigAt(rig, tuner, center)
    else:
        start_frequency = band.frequency_range.min_inclusive
        stop_frequency = band.frequency_range.max_inclusive - ONE_KHZ
        step = KAT500MemorySegmentWidth(start_frequency)
        frequency = start_frequency + int(step/2.)
        while frequency <= stop_frequency:
            TuneRigAt(rig, tuner, frequency)
            frequency += step
    print
    

def TrainKAT500OnBands(rig, tuner, bands):
    for band in bands:
        TrainKAT500OnBand(rig, tuner, band)

def main(argv):
    bands = [band_plan.FindBandByName(name) for name in argv[3:]]
    with serial.Serial(argv[1], 38400) as rig_port:
        rig = elecraft.Transceiver(rig_port)
        with serial.Serial(argv[2], 38400) as tuner_port:
            tuner = elecraft.Tuner(tuner_port)
            tuner.Verify()
            TrainKAT500OnBands(rig, tuner, bands)
    
if __name__ == "__main__":
    main(sys.argv)
