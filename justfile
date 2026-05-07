default: build

# Generate the laser-cuttable acrylic shell base bundle from STL.
acrylic:
    python3 scripts/generate_acrylic_base_from_stl.py

# Generate fab cutout ZIPs (DXF + SVG + PDF + dimensions) for all choc 1.2mm plates from KiCad.
plates:
    python3 scripts/generate_plate_from_kicad_pcb.py

# Run all production builds. Add new build steps as recipes and list them here.
build: acrylic plates
