# Hall Effect Corne Eclipse — Implementation Gameplan

## Overview

This document details the full plan to create a hall effect (HE) variant of the Corne Eclipse split keyboard, covering PCB design, component selection, firmware integration with ZMK, and known risks.

---

## 1. Architecture Comparison

| Feature | Current Corne Eclipse | Hall Effect Variant |
|---|---|---|
| Switch type | Mechanical (Choc v1/v2, Cherry MX) | Hall effect magnetic (e.g. Gateron KS-20) |
| Sensing method | Digital matrix scan (row × col) | Analog voltage per switch via hall sensor |
| Switch pins | 2 signal pins (matrix intersection) | 3 pins (VCC, GND, analog signal) |
| Scan hardware | Direct GPIO matrix | Analog multiplexers → ADC |
| MCU | Nice!Nano (nRF52840) | Same — nRF52840 has 8 ADC channels |
| Firmware | ZMK (standard kscan driver) | ZMK + community HE module |
| Features unlocked | N/A | Adjustable actuation, rapid trigger, SOCD |

---

## 2. Component Selection

### 2.1 Hall Effect Switches

**Primary candidate: Gateron KS-20 series**
- MX-compatible housing (fits standard MX plate cutouts — 14×14mm)
- 3-pin: VCC, GND, analog signal output
- Adjustable actuation range: 0.4mm–3.6mm
- Total travel: 4.1±0.2mm
- Built-in hall effect sensor (no external sensor IC needed)
- Available in multiple spring weights (Orange 38gf, White 30gf)

**Alternative: 3D-printed Void Switches** (community, uses discrete hall sensor IC like A1304)

**Note:** Hall effect switches are NOT pin-compatible with Cherry MX mechanical switches. The center pin and signal pin positions differ. A new footprint is required.

### 2.2 Analog Multiplexers

**CD4067B (16:1 analog mux)** — industry standard
- 16 analog channels switched to 1 common output
- 4 digital select lines (S0–S3) + 1 enable
- Package: SOIC-24 or TSSOP-24
- Supply: 3.0–18V (works at 3.3V from Nice!Nano)
- On-resistance: ~125Ω at 3.3V (acceptable for analog sensing)
- Propagation delay: ~250ns

**Per-half requirements (21 switches + 1 encoder = 22 analog channels):**
- 2× CD4067B per half (16 + 6 channels used, 10 spare)
- Shared select lines: 4 GPIO pins for S0–S3
- 2 ADC pins (one per mux output)
- 2 GPIO for enable pins (optional, for power saving)

### 2.3 MCU: Nice!Nano v2 (nRF52840)

**Available ADC pins (AIN0–AIN7 on nRF52840):**

| ADC Channel | Pin | Nice!Nano Usage | Available? |
|---|---|---|---|
| AIN0 | P0.02 | GPIO | Yes |
| AIN1 | P0.03 | GPIO | Yes |
| AIN2 | P0.04 | Battery voltage | **No — reserved** |
| AIN3 | P0.05 | GPIO | Yes |
| AIN4 | P0.28 | GPIO | Yes |
| AIN5 | P0.29 | GPIO | Yes |
| AIN6 | P0.30 | GPIO | Yes |
| AIN7 | P0.31 | GPIO | Yes |

**Available: 7 ADC channels** (AIN2 reserved for battery). Only 2 needed for the mux outputs. Remaining 5 are available for other analog functions if needed.

**GPIO needed per half:**
- 4× mux select lines (S0–S3, shared between both muxes)
- 2× mux enable (optional)
- 2× ADC input (one per mux)
- Total: 6–8 GPIO/ADC pins for the switch matrix

This leaves enough remaining pins for: RGB LED data, I2C (OLED/nice!view), encoder, reset, battery.

### 2.4 Passive Components

- 2× 0.1µF bypass capacitors per CD4067B (VDD-VSS decoupling)
- 1× 10µF bulk capacitor per half (power rail stabilization)
- Optional: RC low-pass filter per mux output (e.g. 100Ω + 10nF) to reduce ADC noise

---

## 3. PCB Design

### 3.1 What Carries Over From Current Design

- Board outline / Edge.Cuts (identical form factor)
- Mounting holes and tenting puck positions
- Nice!Nano MCU footprint and placement
- Nice!View connector position
- JST battery connector
- TRRS/serial connection (for wired split, if used)
- Case, plate, and cover geometry
- GLOW underglow LED positions and wiring (WS2812B chain is independent of switch sensing)
- RGBMOS power switching circuit

### 3.2 What Must Change

**Switch footprint — NEW required:**
- Hall effect switches (Gateron KS-20) have 3 pins in different positions than MX
- Need: VCC, GND, and signal traces per switch
- Center post hole likely similar to MX (4mm) but verify against KS-20 datasheet
- Plate cutout: 14×14mm (same as MX, so existing MX plates may work)
- No hotswap socket — KS-20 switches are PCB-mount (solder-in) unless a HE-specific hotswap socket exists

**No row/col matrix — replaced with:**
- VCC bus: all switches share a common 3.3V power rail
- GND bus: all switches share common ground
- Individual signal traces: each switch's analog output routes to one mux input
- Mux outputs route to MCU ADC pins

**New components on PCB:**
- 2× CD4067B multiplexer ICs (SOIC-24 or TSSOP-24)
- Bypass capacitors
- Optional analog filtering

**Removed from PCB:**
- Diodes (no matrix → no diodes needed, saves 42 components per board)
- Row/column traces

### 3.3 Wiring Diagram (Per Half)

```
                        ┌─────────────┐
  Switch 1  signal ───▶ │ CH0         │
  Switch 2  signal ───▶ │ CH1         │
  Switch 3  signal ───▶ │ CH2         │
  ...                   │   CD4067B   │──▶ COM ──▶ MCU ADC AIN0
  Switch 16 signal ───▶ │ CH15    #1  │
                        │             │
                        │ S0 S1 S2 S3 │◀── MCU GPIO (shared)
                        │ EN          │◀── MCU GPIO (optional)
                        └─────────────┘

                        ┌─────────────┐
  Switch 17 signal ───▶ │ CH0         │
  Switch 18 signal ───▶ │ CH1         │
  ...                   │   CD4067B   │──▶ COM ──▶ MCU ADC AIN1
  Switch 22 signal ───▶ │ CH5     #2  │
                        │             │
                        │ S0 S1 S2 S3 │◀── MCU GPIO (shared with #1)
                        │ EN          │◀── MCU GPIO (optional)
                        └─────────────┘

  All switches VCC ──── 3.3V rail
  All switches GND ──── GND rail
```

### 3.4 PCB Layout Guidelines

1. **Keep analog traces short** — route switch signals to the nearest mux with minimal trace length to reduce noise pickup
2. **Separate analog and digital** — don't route mux select lines parallel to analog signal traces
3. **Ground plane** — use a solid ground pour under the mux ICs and analog traces
4. **Bypass caps** — place 0.1µF caps as close as possible to each CD4067B VDD/VSS pins
5. **Mux placement** — place one mux near the main key cluster, one near the thumb cluster or split between regions to minimize trace lengths
6. **Star ground** — connect all switch GND pins and mux GND to the same ground pour, avoid daisy-chaining
7. **ADC trace routing** — keep mux COM output → MCU ADC traces short and away from digital noise (RGB data line, I2C clock, etc.)
8. **Optional low-pass filter** — place RC filter pads between mux COM output and ADC input for noise reduction

### 3.5 Per-Key LED Consideration

SHINE per-key LEDs (LED_choc_6028R reverse mount) can remain, but:
- The LED light-pipe hole position must align with the KS-20's LED window (verify against KS-20 datasheet — may differ from MX)
- If KS-20 doesn't have an LED window, per-key backlighting through the switch won't work and LEDs should be repositioned or removed
- Underglow (GLOW WS2812B) is unaffected

---

## 4. Firmware: ZMK Integration

### 4.1 Community Module

**Repository:** [cr3eperall/zmk-feature-hall-effect](https://github.com/cr3eperall/zmk-feature-hall-effect)

**Features provided:**
- Adjustable actuation point (runtime configurable)
- Rapid trigger (re-actuation on direction change)
- SOCD (simultaneous opposing cardinal direction handling)
- Mouse input emulation
- Gamepad input emulation
- Split keyboard support (`he,input-split` binding)

**Drivers available:**
- `he,kscan-direct-pulsed` — for direct ADC wiring (not practical for 42 switches)
- `he,kscan-multiplexer` — for CD4067B mux wiring (this is what we need)

### 4.2 Integration Steps

1. **Add module to ZMK config:**
   ```yaml
   # In west.yml manifest
   projects:
     - name: zmk-feature-hall-effect
       url: https://github.com/cr3eperall/zmk-feature-hall-effect
       revision: main
   ```

2. **Create devicetree overlay** for the Corne Eclipse HE variant:
   - Define 2× CD4067B mux instances with select GPIO pins and ADC channel
   - Map each switch to a mux channel
   - Configure actuation thresholds, rapid trigger parameters
   - Set up `he,input-split` for the peripheral half

3. **Calibration routine:**
   - Each hall sensor has slightly different voltage range
   - Need to implement or use the module's calibration to map raw ADC values → distance
   - Store calibration data in flash/settings

4. **Battery monitoring:**
   - The module includes a custom battery driver for nRF52840
   - AIN2 (P0.04) remains dedicated to battery voltage sensing (unchanged)

### 4.3 Known Firmware Limitations

- **nRF52840 ADC anomaly (errata 212):** certain chip revisions (CKAA-Dx0 or QIAA-Dx0) have a bug where switching between single-channel and multi-channel ADC modes breaks the ADC. The module works around this by using single-mode continuously. Verify your Nice!Nano's chip revision.
- **Scan rate:** analog sensing is slower than digital matrix scan. With 2 muxes × 16 channels × ADC conversion time (~15µs per sample at 10-bit), expect ~0.5ms per full scan — still well under 1ms, adequate for 1000Hz+ polling.
- **No official ZMK merge yet:** the community module is not part of mainline ZMK. You depend on the module author for updates. However, PR #2980 on the ZMK repo suggests official support is being worked on.

---

## 5. Implementation Phases

### Phase 1: Validate Hardware (1–2 weeks)
- [ ] Obtain Gateron KS-20 switches and measure exact pin positions, center post diameter, and overall dimensions
- [ ] Create KiCad footprint for KS-20 (or find community footprint)
- [ ] Prototype one switch + CD4067B + Nice!Nano on a breadboard/perfboard
- [ ] Verify ADC readings through the mux with the cr3eperall ZMK module
- [ ] Test calibration and actuation point adjustment
- [ ] Verify Nice!Nano chip revision for ADC errata 212

### Phase 2: PCB Design (2–3 weeks)
- [ ] Copy the Corne Eclipse MX board as starting point (outline, mounting holes, MCU, connectors)
- [ ] Remove all SW/ENC footprints, diodes, and matrix traces
- [ ] Create and place KS-20 switch footprints at same grid positions
- [ ] Place 2× CD4067B mux ICs per half
- [ ] Route VCC/GND buses to all switches
- [ ] Route individual analog signal traces from switches to mux inputs
- [ ] Route mux select lines (4× GPIO) and COM outputs (2× ADC)
- [ ] Add bypass caps and optional RC filters
- [ ] Run DRC, verify clearances
- [ ] Update plate files if KS-20 cutout differs from MX

### Phase 3: Firmware (1–2 weeks, parallel with Phase 2)
- [ ] Fork ZMK config, add cr3eperall/zmk-feature-hall-effect module
- [ ] Write devicetree overlay for Corne Eclipse HE with mux driver
- [ ] Implement per-switch channel mapping
- [ ] Configure split keyboard communication with `he,input-split`
- [ ] Test rapid trigger and SOCD features
- [ ] Implement and test calibration storage

### Phase 4: Fabrication & Assembly (2–3 weeks)
- [ ] Order PCBs (JLCPCB, same process as current boards)
- [ ] Order components: KS-20 switches, CD4067B, passives
- [ ] Solder and assemble
- [ ] Flash firmware, run calibration
- [ ] Verify all 42 switches respond with correct analog range
- [ ] Test split communication, battery life, RGB

### Phase 5: Refinement
- [ ] Tune actuation points and rapid trigger sensitivity
- [ ] Profile battery life impact (analog sensing draws more power than digital matrix)
- [ ] Consider power optimization: disable mux enable pins when idle, reduce scan rate during idle
- [ ] Evaluate whether per-key LEDs align with KS-20 LED window

---

## 6. Bill of Materials (Per Half)

| Component | Quantity | Package | Notes |
|---|---|---|---|
| Gateron KS-20 switch | 21 (+1 encoder?) | Through-hole | Verify encoder compatibility |
| CD4067B mux | 2 | SOIC-24 or TSSOP-24 | 16-ch analog mux |
| 0.1µF ceramic cap | 4 | 0402 or 0603 | Mux bypass (2 per mux: VDD-VSS, VEE-VSS) |
| 10µF ceramic cap | 1 | 0603 or 0805 | Bulk power rail decoupling |
| 100Ω resistor (optional) | 2 | 0402 or 0603 | RC filter per mux output |
| 10nF ceramic cap (optional) | 2 | 0402 or 0603 | RC filter per mux output |
| Nice!Nano v2 | 1 | Module | nRF52840-based |
| Nice!View | 1 | Module | OLED display |
| WS2812B (GLOW) | 6 | PLCC4 5×5mm | Underglow LEDs (unchanged) |
| LED_6028R (SHINE) | 21 | 6028 reverse mount | Per-key LED (if KS-20 has LED window) |
| AO3401A MOSFET | 1 | SOT-23-3 | RGB power switch (unchanged) |
| Resistors (RGB) | 1 | 0402/0603 | Gate pullup for MOSFET (unchanged) |
| JST connector | 1 | PH 2-pin | Battery (unchanged) |
| Tenting puck mount | 1 | Custom | 3× M2 holes (unchanged) |

---

## 7. Open Questions & Risks

1. **KS-20 exact footprint** — no public KiCad footprint exists. Need to measure switches or find community footprint. Pin positions, center post size, and alignment pin locations are unknown until hands-on measurement.

2. **Hotswap for HE switches?** — standard Kailh hotswap sockets won't work (different pin layout). Mill-Max sockets on individual pins might work but adds height and cost. Likely solder-only initially.

3. **Encoder compatibility** — the rotary encoder (EC11/EC12) is a mechanical device, not hall effect. It can remain as-is with its own GPIO pins. However, if a switch shares the encoder position (ENC_SW combo footprint), that switch portion needs to be hall effect while the encoder remains digital. This requires careful pin routing — the encoder's digital output goes to GPIO, the switch's analog output goes to mux.

4. **Battery life** — analog sensing draws more current than passive digital matrix scan. The CD4067B draws ~100µA quiescent, and each ADC conversion consumes MCU power. Estimate 10–20% reduction in battery life vs current design. Can be mitigated by reducing scan rate during idle and disabling mux enable pins during sleep.

5. **Nice!Nano chip errata** — verify your specific Nice!Nano's nRF52840 chip revision isn't affected by ADC errata 212. If affected, you're limited to single-channel ADC mode (still workable with the mux approach since you read one channel at a time).

6. **Module stability** — the cr3eperall ZMK module is community-maintained, not official. If the author abandons it and ZMK's mainline PR (#2980) isn't merged, you'd need to maintain it yourself.

7. **Plate compatibility** — Gateron KS-20 uses an MX-compatible housing, so the 14×14mm plate cutout SHOULD work. Verify that the KS-20's bottom protrusions clear your current plate thickness (1.5mm for MX plates).

---

## 8. Reference Links

- [cr3eperall/zmk-feature-hall-effect](https://github.com/cr3eperall/zmk-feature-hall-effect) — ZMK community module for HE support
- [ZMK Issue #2096 — Hall Effect Support Discussion](https://github.com/zmkfirmware/zmk/issues/2096) — official issue tracker
- [ZMK PR #2980 — Hall Keyscan Driver](https://github.com/zmkfirmware/zmk/pull/2980) — WIP official driver
- [Macrolev — Open Source HE Keyboard](https://github.com/heiso/macrolev) — reference split HE keyboard design
- [Void Switch 65% — Reference HE PCB](https://github.com/riskable/void_switch_65_pct) — KiCad reference project
- [Gateron KS-20 Product Page](https://www.gateron.com/products/gateron-ks-20-magnetic-orange-hall-sensor-switch-set) — switch specs
- [CD4067B Datasheet & Design Guide](https://components101.com/article/cd4067-16-channel-analog-multiplexer-demultiplexer) — mux reference
- [nRF52840 ADC Pin Mappings](https://tomasmcguinness.com/2025/01/12/nrf52840-adc-pin-mappings/) — ADC channel reference
- [Nice!Nano Pinout](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/) — MCU pin availability
- [Hall Effect Keyboard Sensing Explained — Deskthority](https://deskthority.net/viewtopic.php?t=18163) — theory and wiring
