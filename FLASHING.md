# Flashing Firmware

This guide covers how to flash firmware to the Corne Eclipse keyboard. Each half of the keyboard must be flashed separately.

## Entering Bootloader Mode

There are two ways to put a keyboard half into bootloader mode:

### Option 1: From the System Layer

1. Activate the **SYSTEM** layer (hold both lower and raise keys simultaneously)
2. Press the **Bootloader** key on the side you want to flash
   - The left **Bootloader** key puts the **left half** into bootloader mode
   - The right **Bootloader** key puts the **right half** into bootloader mode

### Option 2: Using the Physical Reset Switch

If the keyboard is unresponsive or you can't access the system layer:

1. Locate the **reset switch** on top of the board, above the power switch
2. Press the reset switch **twice in quick succession** (double-tap)
3. The keyboard half will enter bootloader mode

## Choosing the Right Firmware

Each release ships a separate zip per typing layout × right-half hardware combination. Pick one zip that matches both your desired default typing layer **and** what's installed in the right-half encoder position. Every zip contains the correct left + right `.uf2` pair already.

| Zip | Use When |
|-----|----------|
| `corne_eclipse_<layout>.zip` | Right half has a **rotary encoder or key switch** in the encoder position (no trackpad) |
| `corne_eclipse_<layout>_azoteq.zip` | Right half has an **Azoteq IQS5xx** trackpad (TPS43, TPS50, TPS65) wired up |
| `corne_eclipse_<layout>_cirque.zip` | Right half has a **Cirque Pinnacle** trackpad (TM040040 / TM035035) wired up |

`<layout>` is one of `qwerty`, `colemak_dh`, `colemak`, `workman`, `dvorak`. See [WIRING_TRACKPAD.md](WIRING_TRACKPAD.md) for wiring details on either trackpad module.

## Flashing the Firmware

Once a keyboard half is in bootloader mode, it will appear as a USB drive on your computer (named **NICENANO**).

1. Download the zip that matches your layout + right-half hardware from the [releases](https://github.com/Frosthaven/zmk-config-corne-eclipse/releases) page
2. Extract the zip — you'll get a `left_corne_eclipse_<layout>.zmk.uf2` and a matching `right_corne_eclipse_<layout>_*.zmk.uf2`
3. Put the **left half** into bootloader mode
4. Drag and drop the **left** `.uf2` file onto the **NICENANO** drive
5. The drive will disconnect automatically when flashing is complete
6. Put the **right half** into bootloader mode
7. Drag and drop the **right** `.uf2` file onto the **NICENANO** drive
8. The drive will disconnect automatically when flashing is complete

Both halves should now be running the new firmware.

> ⚠️ **The keyboard half must be physically connected to your computer via USB for the `NICENANO` drive to appear.** The reset switch / bootloader key only puts the half into bootloader mode — it does not expose the drive over Bluetooth. If no drive appears after a few seconds: confirm the USB cable is a data cable (not charge-only), try a different USB port, and verify the half is actually in bootloader mode.

## Development / RGB Test Build

A `dev_rgb_test` build is also produced with RGB underglow enabled automatically at boot. Useful during assembly to verify the LED chain works before you've finished wiring everything up or have a working keymap with `RGB_TOG` available. QWERTY layout. Not intended for daily use — flash a regular layout build once you've confirmed the LEDs work.

- `left_corne_eclipse_dev_rgb_test.zmk.uf2` — left half
- `right_corne_eclipse_dev_rgb_test.zmk.uf2` — right half

## Resetting to Factory Settings

If your keyboard is misbehaving (keys not working, Bluetooth issues, etc.), you can flash the **settings reset firmware** to clear all stored settings:

1. Download `settings_reset-nice_nano_v2-zmk.uf2` from the [releases](https://github.com/Frosthaven/zmk-config-corne-eclipse/releases) page
2. Flash this file to **both halves** using the steps above
3. After resetting both halves, flash your desired layout firmware to both halves again
