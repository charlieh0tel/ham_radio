# Antenna Matching Tool — Test Plan

Test cases for `antenna-matching.html`. Each test has a description, steps, and
expected result. Automated by `test-antenna-matching.mjs`.

---

## 1. Page Load & Rendering

### 1.1 No JavaScript Errors
- Load the page
- **Expected:** Zero console errors (excluding favicon 404)

### 1.2 Key Elements Present
- Load the page
- **Expected:** All of these elements exist:
  - `.title`
  - `.smith-chart`
  - `.controls`
  - `.mode-toggle`
  - `.result-panel`
  - `.result-swr`
  - `.diagram-svg`
  - At least 3 `.preset-btn` elements
  - At least 2 `input[type=range]` sliders

### 1.3 Initial Title
- Load the page (no URL params)
- **Expected:** Title contains "Gamma Match" (default mode)

---

## 2. Mathematical Invariants

These must hold after every parameter change.

### 2.1 SWR >= 1
- Read the SWR value from `.result-swr`
- **Expected:** Parsed SWR is >= 1.0

### 2.2 SWR is Finite
- Read the SWR value
- **Expected:** SWR is a finite number (not NaN, not Infinity)

### 2.3 Resistance > 0
- Read the matched impedance from `.result-z`
- **Expected:** The real part (resistance) is > 0

### 2.4 Invariants Hold After Auto-Tune
- Click Auto-Tune, then re-check 2.1–2.3
- **Expected:** All invariants still hold

---

## 3. Gamma Match Controls

### 3.1 Tap Ratio Slider Changes Results
- Record SWR, move the tap ratio slider (`aria-label="Tap ratio"`), record SWR again
- **Expected:** SWR value changed

### 3.2 Gamma Rod Slider Changes Results
- Record SWR, move the gamma rod slider (`aria-label="Gamma rod reactance"`), record SWR again
- **Expected:** SWR value changed

### 3.3 Series Capacitor Slider Changes Results
- Record SWR, move the series cap slider (`aria-label="Series capacitor reactance"`), record SWR again
- **Expected:** SWR value changed

### 3.4 Auto-Tune Converges
- Set sliders to non-optimal values, click Auto-Tune
- **Expected:** SWR < 2.0

---

## 4. Hairpin Match Controls

### 4.1 Shortening Slider Changes Results
- Switch to Hairpin mode
- Record SWR, move the shortening slider (`aria-label="Element shortening reactance"`), record SWR again
- **Expected:** SWR value changed

### 4.2 Hairpin Slider Changes Results
- Record SWR, move the hairpin slider (`aria-label="Hairpin reactance"`), record SWR again
- **Expected:** SWR value changed

### 4.3 Auto-Tune Converges
- Set sliders to non-optimal values, click Auto-Tune
- **Expected:** SWR < 2.0

---

## 5. Presets

### 5.1 Each Preset Loads Correct Impedance
- For each preset button, click it and read the impedance display
- **Expected:** Impedance display matches the preset label values

### 5.2 Each Preset Auto-Tunes
- After clicking each preset, read SWR
- **Expected:** SWR < 2.0

### 5.3 Active State
- Click a preset button
- **Expected:** That button has the `.active` CSS class; others do not

---

## 6. Mode Switching

### 6.1 Gamma Mode Title
- Click the Gamma mode button
- **Expected:** `.title` text is "Gamma Match"

### 6.2 Hairpin Mode Title
- Click the Hairpin mode button
- **Expected:** `.title` text is "Beta (Hairpin) Match"

### 6.3 OCFD Mode Title
- Click the OCFD mode button
- **Expected:** `.title` text is "Off-Center Fed Doublet"

### 6.4 Antenna Impedance Preserved
- Set R=40 and X=−20, switch from Gamma to Hairpin and back
- **Expected:** R and X values are the same after round-trip

---

## 7. URL Parameters

### 7.1 URL Updates on Change
- Move a slider
- **Expected:** `window.location.search` is non-empty (contains params)

### 7.2 Reset Restores Defaults
- Move a slider, then click the Reset button
- **Expected:** Antenna impedance returns to defaults (R=73, X=43)

### 7.3 Round-Trip from URL
- Load page with URL params `?mode=hairpin&r=25&x=0&short=10&hp=80`
- **Expected:**
  - Title is "Beta (Hairpin) Match"
  - Antenna R is 25, X is 0
  - Shortening slider value is 10
  - Hairpin slider value is 80

---

## 8. Physical Calculations

### 8.1 Wavelength Displayed
- Enter a frequency (e.g., 145 MHz) in the freq input
- **Expected:** Wavelength text appears (e.g., "λ = 2.07m")

### 8.2 Capacitor pF Shown (Gamma Mode)
- In Gamma mode with freq set, check for pF hint text
- **Expected:** A "pF" string appears in the controls

### 8.3 Shortening mm/% Shown (Hairpin Mode)
- In Hairpin mode with freq and element diameter set
- **Expected:** Shortening hint shows "mm per side" and "%"

---

## 9. Edge Cases

### 9.1 Extreme Slider Values Don't Crash
- Set R=10, X=−100 (minimum), then R=150, X=100 (maximum)
- **Expected:** No console errors, SWR still finite

### 9.2 SWR Color Classes
- Achieve SWR < 1.2 via auto-tune → class should be `swr-excellent`
- Manually detune to SWR > 2 → class should be `swr-poor`

---

## 10. Antenna Impedance Sliders

### 10.1 Resistance Slider Updates Display
- Move the resistance slider to a new value
- **Expected:** The impedance display updates to show the new R

### 10.2 Reactance Slider Updates Display
- Move the reactance slider to a new value
- **Expected:** The impedance display updates to show the new X

---

## 11. OCFD Mode

### 11.1 OCFD Mode Title
- Click the OCFD mode button
- **Expected:** Title is "Off-Center Fed Doublet"

### 11.2 Feed Offset Slider Changes Results
- In OCFD mode, move feed offset slider (`aria-label="Feed offset"`)
- **Expected:** Feed impedance display changes

### 11.3 Center Impedance at Zero Offset
- Set offset to 0%
- **Expected:** Feed Z ≈ center Z (within rounding)

### 11.4 Impedance Increases With Offset
- Record feed Z resistance at offset 0%, then at 20%
- **Expected:** Resistance at 20% > resistance at 0%

### 11.5 Multiple SWR Values Displayed
- In OCFD mode, check `.swr-table`
- **Expected:** SWR shown for 50Ω, 300Ω, and 450Ω feedlines

### 11.6 OCFD URL Round-Trip
- Load with `?mode=ocfd&ocr=73&ocx=0&off=33`
- **Expected:** Mode is OCFD, center R=73, center X=0, offset=33
