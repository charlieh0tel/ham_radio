# Elecraft transceiver control.   Rest is TBD.

import band_plan

_DEBUG=False

class _Device(object):
    def __init__(self, serial, wakeup_required=False):
        self._serial = serial
        self._wakeup_required = wakeup_required
        serial.timeout = 0.250

    def _WakeUp(self):
        if _DEBUG: print "_WakeUp"
        i = 0
        while i < 2:
            self._serial.write(";")
            self._serial.flush()
            c = self._serial.read()
            if (c and c[0] == ';'):
                i += 1
        if _DEBUG: print "_WakeUp done"

    def _ReadUntilSemi(self):
        result = bytes()
        while True:
            c = self._serial.read()
            if _DEBUG: print "Read: \"%s\"" % c
            if (c and c[0] == ';'):
                return result
            result += c
            
    def _SendCommandNoResponse(self, command):
        if self._wakeup_required:
            self._WakeUp()
        command += ";"
        if _DEBUG: print "_SendCommand \"%s\"" % command
        self._serial.write(command)
        self._serial.flush()

    def _SendCommand(self, command):
        self._SendCommandNoResponse(command)
        while True:
            response = self._ReadUntilSemi()
            if _DEBUG: print "response=\"%s\"" % response
            if response == command:
                return

    def _SendQuery(self, command):
        self._SendCommandNoResponse(command)
        response = self._ReadUntilSemi()
        if _DEBUG: print "response=\"%s\"" % response
        return response

    def _SendTaggedQuery(self, command):
        self._SendCommandNoResponse(command)
        while True:
            response = self._ReadUntilSemi()
            if _DEBUG: print "response=\"%s\"" % response
            if response.startswith(command):
                return response[len(command):]

            

class Transceiver(_Device):
    def __init__(self, serial):
        super(Transceiver, self).__init__(serial)

    @classmethod
    def _SetFrequencyCommand(cls, vfo, frequency):
        return "F%s%011d" % (vfo, frequency)

    def SetVfoA(self, frequency):
        command = self._SetFrequencyCommand("A", frequency)
        self._SendCommand(command)

    def TuneToggle(self):
        self._SendCommandNoResponse("SWH16") # no response generated


class Tuner(_Device):
    def __init__(self, serial):
        super(Tuner, self).__init__(serial, wakeup_required=True)

    def Verify(self):
        response = self._SendQuery("I")
        assert response.lower() == "kat500"

    def ReadBypass(self):
        response = self._SendTaggedQuery("BYP")
        assert response == "N" or response == "B"
        return response == "B"

    def SetBypass(self, bypassed):
        command = "BYPB" if bypassed else "BYPN"
        self._SendCommandNoResponse(command)

    _Cs=[8e-12, 22e-12, 39e-12, 82e-12, 180e-12, 330e-12, 680e-12, 1360e-12]

    _Ls=[50e-9, 110e-9, 230e-9, 480e-9, 1000e-9, 2100e-9, 4400e-9, 9000e-9]

    @staticmethod
    def _ComputeLC(bitmap, mapping):
        total = 0.
        for bit in xrange(0, 8):
            if bitmap & (1<<bit):
                total += mapping[bit]
        return total
        
    def ReadCapacitance(self):
        bits = int(self._SendTaggedQuery("C"), 16);
        return self._ComputeLC(bits, self._Cs)

    def ReadInductance(self):
        bits = int(self._SendTaggedQuery("L"), 16);
        return self._ComputeLC(bits, self._Ls)
    
    def ReadCapacitorSide(self):
        response = self._SendTaggedQuery("SIDE")
        assert response == "T" or response == "A"
        return response

    def ClearMatch(self):
        self._SendCommandNoResponse("C00")
        self._SendCommandNoResponse("L00")

    def ReadMatch(self):
        """Returns match (L, C, side) with L in [H] and C in [F] and side
        being either "T" or "A" or None if in bypass."""
        l = self.ReadInductance()
        c = self.ReadCapacitance()
        side = self.ReadCapacitorSide()
        return (l, c, side)

    def ReadFrequency(self):
        return int(self._SendTaggedQuery("F")) * 1000.

    def ReadVSWR(self):
        return float(self._SendTaggedQuery("VSWR"))

    def ReadVSWRInBypass(self):
        return float(self._SendTaggedQuery("VSWR"))
    
    def ClearFault(self):
        self._SendCommandNoResponse("FLTC")

    def GetFaultCode(self):
        return int(self._SendTaggedQuery("FLT"))

    def FullTune(self):
        return self._SendCommand("FT")

    def CancelTune(self):
        return self._SendCommandNoResponse("CT")

    def ReadTunePoll(self):
        result = int(self._SendTaggedQuery("TP"))
        assert result in [0, 1]
        return bool(result)
        
    def SaveMemory(self, frequency=0):
        self._SendCommandNoResponse("SM%d" % frequency)

    def ReadAntenna(self):
        return int(self._SendTaggedQuery("AN"))

    def SetAntenna(self, antenna):
        assert antenna >= 1 and antenna <= 3
        self._SendCommandNoResponse("AN%d" % antenna)

    # Band number to wavelength [m]
    _BANDMAP= [(0, 160), (1, 80), (2, 60), (3, 40), (4, 30),
               (5, 20), (6, 17), (7, 15), (8, 12), (9, 10), (10, 6)]
    _BAND_NUMBER_TO_METER=dict(_BANDMAP)
    _BAND_METER_TO_NUMBER=dict(reversed(item) for item in _BANDMAP)

    def EraseMemory(self, antenna, band):
        band_num = self._BAND_METER_TO_NUMBER[band.wavelength_meter]
        self._SendCommandNoResponse("EM%02d%d" % (band_num, antenna))

    def EraseMemoryAllBands(self, antenna):
        for (band_num, _) in self._BANDMAP:
            self._EraseMemory(antenna, band_num)
