README | [Keymap](KEYMAP.md) | [MX Parts](PARTS_MX.md) | [Building](BUILDING.md) | [Tricks](TRICKS.md)

# Corne Eclipse

![Corne Eclipse With Ceramic Keys](/assets/images/corne-eclipse.webp)

---

![Corne Eclipse Front And Back](/assets/images/corne-eclipse.png)

The Corne Eclipse is a highly customized wireless Corne MX with the following:

- Custom circuit board design
    - JST port with line passthrough for undercarriage battery storage
    - Native support for dual nice!view displays
    - Native support for dual EC11 encoders
    - Native support for Azoteq TPS43 trackpad (right half, replaces encoder and display)
    - Native support for side mounted power switches
    - Native support for tenting puck
- Custom shield casing design (based on Void's case)
    - Undercarriage battery storage
    - Optimized material usage for bottom
    - Native support for tenting puck
- TPS43 trackpad driver support ([AYM1607/zmk-driver-azoteq-iqs5xx](https://github.com/AYM1607/zmk-driver-azoteq-iqs5xx))
- ZMK modifications
    - Display:
        - More accurate battery display (numeric value)
        - Track battery status of both halves on a single nice!view
        - Capslock indicator
    - RGB battery usage optimizations ([zmk-ext-power-smart-idle](https://github.com/Frosthaven/zmk-ext-power-smart-idle)):
        - 20% brightness when not plugged in
        - RGB auto-off on low battery when not plugged in
        - Lights stay on when plugged in
        - Eclipse v3 reversible variant uses a MOSFET that prevents drain when LEDs are off (coming soon)
- Several default typing layouts available in [releases](https://github.com/Frosthaven/zmk-config-corne-eclipse/releases)
    - QWERTY
    - Colemak Mod DH (personal choice!)
    - Colemak
    - Workman
    - DVORAK

*This was a project I initially finished in 2021. Finally updated and open
sourced!*
