[README](README.md) | [Keymap](KEYMAP.md) | [MX Parts](PARTS_MX.md) | [Building](BUILDING.md) | [Tricks](TRICKS.md)

# Wiring the Azoteq TPS43 Trackpad

This guide covers how to wire an Azoteq TPS43 trackpad module to the **right half** of the Corne Eclipse. The trackpad uses the encoder's GPIO pin for its interrupt line, so a rotary encoder cannot be used on the right half at the same time. A key switch can still be installed in the encoder position.

## Prerequisites

- Azoteq TPS43-201A-B touchpad module (available from [HolyKeebs](https://holykeebs.com/products/touchpad-module) or as a standalone component)
- 5 thin wires (28-30 AWG recommended)
- Soldering iron and solder
- The right encoder must **not** be installed (a key switch in that position is fine)
- The right half **nice!view display must be removed** (the trackpad and nice!view share the same pins — see below)

## Display Limitation

The trackpad communicates over I2C using pins P0.17 (SDA) and P0.20 (SCL). The nice!view display uses these same physical pins for SPI. The nRF52840 cannot run both I2C and SPI on the same pins simultaneously, so **the right half cannot use a nice!view display when the trackpad is installed**. The OLED display also cannot be used, as it is disabled in the trackpad firmware to avoid conflicts.

The left half display is unaffected.

## Wiring Diagram

Five connections are needed:

| TPS43 Pad | nice!nano Connection | Pin | Notes |
|-----------|---------------------|-----|-------|
| SDA | I2C data line | P0.17 (pro_micro SDA) | |
| SCL | I2C clock line | P0.20 (pro_micro SCL) | |
| RDY | Interrupt / data ready | P1.04 (pro_micro 8) | Active high, directly to nice!nano |
| VCC | 3.3V power | 3.3V | From nice!nano 3.3V rail |
| GND | Ground | GND | Any ground pad |

## Connection Points

### I2C (SDA and SCL)

Solder to the nice!nano's pro_micro SDA and SCL pads. If you previously had an OLED installed, the header pads on the PCB where the OLED connected are a convenient solder point for these lines.

### RDY (Interrupt)

Solder to the nice!nano's pro_micro pin 8 pad. This is the pad normally used for the encoder's A signal. Since the encoder is not installed, this pad is free.

### Power (VCC and GND)

Use the nice!nano's 3.3V and GND pads. These are available on the pro_micro header or directly on the nice!nano board.

## Important Notes

- The TPS43 I2C address is **0x74**
- The RDY pin is **active high** — no pull-up resistor is needed
- The TPS43 requires a **1mm dielectric overlay** (glass or acrylic) for proper capacitive sensing. The HolyKeebs kit includes a matte grey glass overlay
- Keep wires as short as practical to reduce I2C noise
- Flash the `trackpad_and_switch` firmware variant after wiring

## Firmware

Use the `right_corne_eclipse_<layout>_trackpad_and_switch.uf2` firmware file from the [releases](https://github.com/Frosthaven/zmk-config-corne-eclipse/releases) page. See [FLASHING.md](FLASHING.md) for flashing instructions.

## Trackpad Features

With the default firmware configuration, the trackpad supports:

- Single-finger cursor movement
- Single-finger tap for left click
- Two-finger tap for right click
- Press and hold for drag
- Two-finger vertical and horizontal scroll
