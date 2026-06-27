import math

from beater.geometry import make_eggbeater
from beater.nec import RadiationGrid, Source, build_deck, parse_output

# Trimmed nec2c output covering two sources and a few pattern directions,
# including an exact-zenith row that omits the textual polarization sense.
SAMPLE_OUTPUT = """
                        --------- ANTENNA INPUT PARAMETERS ---------
  TAG   SEG       VOLTAGE (VOLTS)         CURRENT (AMPS)         IMPEDANCE (OHMS)        ADMITTANCE (MHOS)     POWER
  No:   No:     REAL      IMAGINARY     REAL      IMAGINARY     REAL      IMAGINARY    REAL       IMAGINARY   (WATTS)
  100     1  1.0000E+00  0.0000E+00  5.0000E-03  5.0000E-03  1.0000E+02  -1.0000E+02  5.0E-03  5.0E-03  2.5E-03
  200     1  1.0000E+00  0.0000E+00  5.0000E-03 -5.0000E-03  1.0000E+02   1.0000E+02  5.0E-03 -5.0E-03  2.5E-03


                             ---------- RADIATION PATTERNS -----------

 ---- ANGLES -----     ----- POWER GAINS -----       ---- POLARIZATION ----   ---- E(THETA) ----    ----- E(PHI) ------
  THETA      PHI       VERTC    HORIZ    TOTAL       AXIAL      TILT  SENSE   MAGNITUDE    PHASE    MAGNITUDE     PHASE
 DEGREES   DEGREES        DB       DB       DB       RATIO   DEGREES            VOLTS/M   DEGREES     VOLTS/M   DEGREES
    0.00      0.00     2.00     2.00     5.00      0.9800      0.00         1.0E-01      0.00  1.0E-01     90.00
   30.00      0.00     1.00     1.00     3.00      0.8000     10.00 RIGHT   8.0E-02     12.00  6.0E-02     95.00
   60.00      0.00  -999.99  -999.99  -999.99      0.0000      0.00 LINEAR  0.0E+00      0.00  0.0E+00      0.00
"""


def test_parse_sources():
    result = parse_output(SAMPLE_OUTPUT)
    assert len(result.sources) == 2
    a, b = result.sources
    assert a.tag == 100
    assert math.isclose(a.z_real, 100.0)
    assert math.isclose(a.z_imag, -100.0)
    assert math.isclose(a.current_phase_deg, 45.0)
    assert math.isclose(b.current_phase_deg, -45.0)


def test_parse_pattern_handles_missing_sense():
    result = parse_output(SAMPLE_OUTPUT)
    assert len(result.pattern) == 3
    zenith = result.pattern[0]
    assert zenith.sense == "LINEAR"
    assert math.isclose(zenith.axial_ratio, 0.98)
    assert result.pattern[1].sense == "RIGHT"


def test_build_deck_emits_expected_cards():
    egg = make_eggbeater(1.0, 1.0, 0.5, 0.001, 12)
    sources = (
        Source(egg.loop_a.feed_tag, egg.loop_a.feed_segment, 1.0, 0.0),
        Source(egg.loop_b.feed_tag, egg.loop_b.feed_segment, 0.0, -1.0),
    )
    grid = RadiationGrid(9, 7, 0.0, 0.0, 10.0, 15.0)
    deck = build_deck(["test"], egg.wires, sources, True, 145.9, grid)
    assert deck.startswith("CM test")
    assert "GN 1" in deck
    assert "GE -1" in deck
    assert deck.count("\nEX ") == 2
    assert deck.count("\nGW ") == 24
    assert deck.rstrip().endswith("EN")


def test_build_deck_free_space_has_no_ground():
    egg = make_eggbeater(1.0, 1.0, 0.5, 0.001, 12)
    sources = (Source(100, 1, 1.0, 0.0),)
    grid = RadiationGrid(9, 7, 0.0, 0.0, 10.0, 15.0)
    deck = build_deck(["t"], egg.wires, sources, False, 145.9, grid)
    assert "GE 0" in deck
    assert "GN" not in deck
