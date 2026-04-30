[README](README.md) | [Keymap](KEYMAP.md) | [MX Parts](PARTS_MX.md) | [Building](BUILDING.md) | [Tricks](TRICKS.md)

# Wiring a Trackpad to the Right Half

The right half of the Corne Eclipse can host one of two trackpad modules:

- **Azoteq TPS43** (rectangular, 43×40 mm) — *EOL as of April 2024; aftermarket stock only.*
- **Cirque Pinnacle** (GlidePoint Circle TM040040 40 mm round / TM035035 35 mm round) — actively produced, recommended for new builds.

Both modules use the same I²C interface and the same encoder GPIO pin for their interrupt, so the wiring approach is identical apart from the module itself. In either case, a rotary encoder cannot be installed on the right half at the same time (a key switch in the encoder position is still fine).

## Display Limitation (applies to both trackpads)

The trackpad communicates over I²C using pins P0.17 (SDA) and P0.20 (SCL). The nice!view display uses these same physical pins for SPI. The nRF52840 cannot run both I²C and SPI on the same pins simultaneously, so **the right half cannot use a nice!view display when the trackpad is installed**. The OLED display is also disabled in the trackpad firmware to avoid conflicts.

The left half display is unaffected.

---

## Azoteq TPS43 Wiring

### Prerequisites

- Azoteq TPS43-201A-B touchpad module (limited aftermarket availability — e.g. [HolyKeebs](https://holykeebs.com/products/touchpad-module))
- 5 thin wires (28-30 AWG recommended)
- Soldering iron and solder
- The right encoder must **not** be installed (a key switch in that position is fine)
- The right half nice!view display must be removed

### Wiring Diagram

| TPS43 Pad | nice!nano Connection | Pin | Notes |
|-----------|---------------------|-----|-------|
| SDA | I²C data line | P0.17 (pro_micro SDA / pad 2) | |
| SCL | I²C clock line | P0.20 (pro_micro SCL / pad 3) | |
| RDY | Interrupt / data ready | P1.04 (pro_micro pad 8) | Active high, directly to nice!nano |
| VCC | 3.3 V power | 3.3 V | From nice!nano 3.3 V rail |
| GND | Ground | GND | Any ground pad |

### Connection Points

**I²C (SDA and SCL):** Solder to the nice!nano's pro_micro SDA and SCL pads. If you previously had an OLED installed, the header pads on the PCB where the OLED connected are a convenient solder point for these lines.

**RDY (Interrupt):** Solder to the nice!nano's pro_micro pin 8 pad. This is the pad normally used for the encoder's A signal. Since the encoder is not installed, this pad is free.

**Power (VCC and GND):** Use the nice!nano's 3.3 V and GND pads.

### Notes

- The TPS43 I²C address is **0x74**
- The RDY pin is **active high** — no pull-up resistor is needed
- The TPS43 requires a **1 mm dielectric overlay** (glass or acrylic) for proper capacitive sensing. The HolyKeebs kit includes a matte grey glass overlay
- Keep wires as short as practical to reduce I²C noise

### Firmware

Flash `right_corne_eclipse_<layout>_azoteq_trackpad_and_switch.uf2` from the [releases](https://github.com/Frosthaven/zmk-config-corne-eclipse/releases) page. See [FLASHING.md](FLASHING.md) for flashing instructions.

---

## Cirque Pinnacle Wiring

### Prerequisites

- Cirque GlidePoint Circle trackpad module: **TM040040** (40 mm) or **TM035035** (35 mm). Available from [keycapsss](https://keycapsss.com/keyboard-parts/parts/211/glidepoint-cirque-trackpad-tm040040-tm035035), DigiKey, Mouser, or Cirque directly.
- 5 thin wires (28-30 AWG recommended)
- Soldering iron and solder
- The right encoder must **not** be installed (a key switch in that position is fine)
- The right half nice!view display must be removed

Cirque modules ship in a few form factors — most commonly a flat self-adhesive flex or an FFC ribbon. The electrical connections are the same across them; only the physical pad layout / connector differs. Match each wire below by its signal name on your specific module.

### Wiring Diagram

| Cirque Signal | nice!nano Connection | Pin | Notes |
|---------------|---------------------|-----|-------|
| SDA | I²C data line | P0.17 (pro_micro SDA / pad 2) | |
| SCL | I²C clock line | P0.20 (pro_micro SCL / pad 3) | |
| DR (Data Ready) | Interrupt | P1.04 (pro_micro pad 8) | Active high |
| VDD | 3.3 V power | 3.3 V | From nice!nano 3.3 V rail |
| GND | Ground | GND | Any ground pad |

### Notes

- The Cirque Pinnacle I²C address is **0x2A** by default. If your module has the R1 solder jumper bridged the address becomes **0x2C** — in that case the overlay needs `reg = <0x2c>` instead of `<0x2a>`.
- DR is **active high**, matching the TPS43 — no pull-up needed.
- The Cirque ASIC is **3.3 V** only. Do not wire VDD to the 5 V rail.
- Cursor direction (X/Y polarity) depends on how you mount the module relative to the keyboard. If movement feels inverted after flashing, adjust the `input-processors` line in `config/boards/shields/corne_eclipse/corne_eclipse_right.overlay`.

### Firmware

Flash `right_corne_eclipse_<layout>_cirque_trackpad_and_switch.uf2` from the [releases](https://github.com/Frosthaven/zmk-config-corne-eclipse/releases) page. See [FLASHING.md](FLASHING.md) for flashing instructions.

---

## Trackpad Features

With the default firmware configuration, both trackpads support:

- Single-finger cursor movement
- Single-finger tap for left click
- Two-finger tap for right click
- Press and hold for drag
- Two-finger vertical and horizontal scroll
