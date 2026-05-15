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

Each release ships **one zip per typing layout**. Inside that zip you'll find a default and trackpad variant for each half plus a settings-reset image. You pick which `.uf2` to flash to each half based on what you've installed on that side.

`<layout>` is one of `qwerty`, `colemak_dh`, `colemak`, `workman`, `dvorak`.

```
corne_eclipse_<layout>.zip
├── left_corne_eclipse_<layout>.zmk.uf2            ← default left half
├── left_trackpad_corne_eclipse_<layout>.zmk.uf2   ← left half with trackpad instead of display
├── right_corne_eclipse_<layout>.zmk.uf2           ← default right half
├── right_trackpad_corne_eclipse_<layout>.zmk.uf2  ← right half with trackpad instead of display
└── settings_reset-nice_nano_v2-zmk.uf2            ← clean-slate / factory reset
```

**Which file do I flash to each half?**

The PCB is reversible, so you can install a trackpad on either half (or both halves, if you want two trackpads). Pick the variant per half independently:

| File | Flash to | Use when |
|---|---|---|
| `left_corne_eclipse_<layout>.zmk.uf2` | Left half | Default. Use this unless you've installed a trackpad on the left half. nice!view display is supported but optional; this firmware works with or without it. |
| `left_trackpad_corne_eclipse_<layout>.zmk.uf2` | Left half | Only if you've installed a trackpad (Azoteq IQS5xx **or** Cirque Pinnacle) on the left half. The display is disabled since the trackpad uses the display's pins. |
| `right_corne_eclipse_<layout>.zmk.uf2` | Right half | Default. Use this unless you've installed a trackpad on the right half. nice!view display is supported but optional; this firmware works with or without it. |
| `right_trackpad_corne_eclipse_<layout>.zmk.uf2` | Right half | Only if you've installed a trackpad (Azoteq IQS5xx **or** Cirque Pinnacle) on the right half. The display is disabled since the trackpad uses the display's pins. The encoder/switch still works. |

The trackpad variants bundle both Azoteq and Cirque drivers, so a single firmware works for either trackpad type. See [WIRING_TRACKPAD.md](WIRING_TRACKPAD.md) for trackpad wiring.

## Flashing the Firmware

Once a keyboard half is in bootloader mode, it will appear as a USB drive on your computer (named **NICENANO**).

1. Download `corne_eclipse_<layout>.zip` from the [releases](https://github.com/Frosthaven/zmk-config-corne-eclipse/releases) page for your desired typing layout
2. Extract the zip
3. **(Recommended)** Flash `settings_reset-nice_nano_v2-zmk.uf2` to **both halves** first to wipe any saved RGB / BLE / layer state from previous firmware. Otherwise stale NVS can override the new firmware's defaults (e.g. show wrong RGB color, stuck brightness).
4. Put the **left half** into bootloader mode
5. Drag and drop the left-half `.uf2` of your choice (default or `left_trackpad_`) onto the **NICENANO** drive
6. The drive will disconnect automatically when flashing is complete
7. Put the **right half** into bootloader mode
8. Drag and drop the right-half `.uf2` of your choice (default or `right_trackpad_`) onto the **NICENANO** drive
9. The drive will disconnect automatically when flashing is complete

Both halves should now be running the new firmware.

> ⚠️ **The keyboard half must be physically connected to your computer via USB for the `NICENANO` drive to appear.** The reset switch / bootloader key only puts the half into bootloader mode; it does not expose the drive over Bluetooth. If no drive appears after a few seconds: confirm the USB cable is a data cable (not charge-only), try a different USB port, and verify the half is actually in bootloader mode.

## Development / RGB Test Build

A `dev_rgb_test` build is also produced with RGB underglow enabled automatically at boot. Useful during assembly to verify the LED chain works before you've finished wiring everything up or have a working keymap with `RGB_TOG` available. QWERTY layout. Not intended for daily use.

- `left_corne_eclipse_dev_rgb_test.zmk.uf2` for the left half
- `right_corne_eclipse_dev_rgb_test.zmk.uf2` for the right half

Recommended assembly sequence: **settings_reset → dev_rgb_test → confirm LEDs → settings_reset → daily layout build**. The settings reset before each flash ensures the firmware's defaults take effect instead of stale NVS state.

## Resetting to Factory Settings

The `settings_reset-nice_nano_v2-zmk.uf2` is bundled inside every release zip. Flash it whenever you want to wipe stored settings (RGB state, BLE pairings, layer state, etc.) or as a clean-slate step before flashing new firmware.

1. Extract the zip you downloaded
2. Flash `settings_reset-nice_nano_v2-zmk.uf2` to **both halves** using the steps above
3. After resetting both halves, flash your desired layout firmware to both halves again
