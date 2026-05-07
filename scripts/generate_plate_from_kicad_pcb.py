#!/usr/bin/env python3
"""
Generate a fab cutout bundle (DXF + SVG + PDF + dimensions txt, zipped) from a
KiCad PCB. Edge.Cuts is exported via kicad-cli; dimensions are computed from
the .kicad_pcb's actual Edge.Cuts geometry so the reported size matches the
laser-cut path exactly.

Usage:
    python3 generate_plate_from_kicad_pcb.py                       # process all 3 canonical plates
    python3 generate_plate_from_kicad_pcb.py <input.kicad_pcb>     # process one custom file
    python3 generate_plate_from_kicad_pcb.py <input.kicad_pcb> <output_name>

Outputs land next to the input file. Only the .zip remains after a successful
run; loose .dxf/.svg/.pdf/-dimensions.txt are cleaned up.

Requirements:
    pip3 install ezdxf matplotlib
    kicad-cli (from KiCad 7+; KiCad 10 used for development)
"""

import math
import os
import re
import subprocess
import sys
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUTOUT_DIR = os.path.join(REPO_ROOT, "fabrication", "!for-fabricator-production", "cutout")
SOURCES_DIR = os.path.join(CUTOUT_DIR, "sources")
DEFAULT_INPUTS = [
    os.path.join(SOURCES_DIR, "choc_switchplates.kicad_pcb"),
    os.path.join(SOURCES_DIR, "screen_cover.kicad_pcb"),
    os.path.join(SOURCES_DIR, "base_plate.kicad_pcb"),
]


def edge_cuts_bbox(pcb_path):
    """Return (x_min, y_min, x_max, y_max) in mm for Edge.Cuts geometry."""
    text = open(pcb_path).read()

    def iter_blocks(s, names):
        i = 0
        while i < len(s):
            best = None
            for n in names:
                tok = f"({n}"
                j = s.find(tok, i)
                while j != -1 and j + len(tok) < len(s) and s[j + len(tok)] not in (" ", "\n", "\t", "("):
                    j = s.find(tok, j + 1)
                if j != -1 and (best is None or j < best[0]):
                    best = (j, n)
            if best is None:
                break
            start, name = best
            depth = 0
            k = start
            while k < len(s):
                c = s[k]
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        yield name, s[start:k + 1]
                        i = k + 1
                        break
                k += 1
            else:
                break

    xs, ys = [], []

    def add(x, y):
        xs.append(x)
        ys.append(y)

    for name, block in iter_blocks(text, ["gr_line", "gr_arc", "gr_circle", "gr_curve", "gr_poly", "gr_rect"]):
        if 'layer "Edge.Cuts"' not in block:
            continue
        if name == "gr_line":
            sm = re.search(r"\(start\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
            em = re.search(r"\(end\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
            if sm and em:
                add(float(sm.group(1)), float(sm.group(2)))
                add(float(em.group(1)), float(em.group(2)))
        elif name == "gr_arc":
            sm = re.search(r"\(start\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
            mm = re.search(r"\(mid\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
            em = re.search(r"\(end\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
            if sm and mm and em:
                sx, sy = float(sm.group(1)), float(sm.group(2))
                mx, my = float(mm.group(1)), float(mm.group(2))
                ex, ey = float(em.group(1)), float(em.group(2))
                add(sx, sy); add(mx, my); add(ex, ey)
                # Sample for true arc extents
                ax_, ay_ = sx - mx, sy - my
                bx_, by_ = ex - mx, ey - my
                d_ = 2 * (ax_ * by_ - ay_ * bx_)
                if abs(d_) > 1e-9:
                    ux = (by_ * (ax_ * ax_ + ay_ * ay_) - ay_ * (bx_ * bx_ + by_ * by_)) / d_ + mx
                    uy = (ax_ * (bx_ * bx_ + by_ * by_) - bx_ * (ax_ * ax_ + ay_ * ay_)) / d_ + my
                    r = math.hypot(sx - ux, sy - uy)
                    a0 = math.atan2(sy - uy, sx - ux)
                    a2 = math.atan2(ey - uy, ex - ux)
                    am = math.atan2(my - uy, mx - ux)
                    # walk from a0 to a2 passing through am
                    delta = a2 - a0
                    if delta <= 0:
                        delta += 2 * math.pi
                    # check whether the CCW walk passes am
                    da_m = (am - a0) % (2 * math.pi)
                    if da_m > delta:
                        delta -= 2 * math.pi  # walk CW instead
                    for i in range(33):
                        t = i / 32
                        a = a0 + t * delta
                        add(ux + r * math.cos(a), uy + r * math.sin(a))
        elif name == "gr_circle":
            cm = re.search(r"\(center\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
            em = re.search(r"\(end\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
            if cm and em:
                cx, cy = float(cm.group(1)), float(cm.group(2))
                ex, ey = float(em.group(1)), float(em.group(2))
                r = math.hypot(ex - cx, ey - cy)
                add(cx - r, cy - r); add(cx + r, cy + r)
        elif name == "gr_curve":
            ctrl = [(float(a), float(b)) for a, b in re.findall(r"\(xy\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)]
            if len(ctrl) >= 4:
                P0, P1, P2, P3 = ctrl[:4]
                for i in range(33):
                    t = i / 32; mt = 1 - t
                    add(mt**3 * P0[0] + 3*mt**2*t * P1[0] + 3*mt*t**2 * P2[0] + t**3 * P3[0],
                        mt**3 * P0[1] + 3*mt**2*t * P1[1] + 3*mt*t**2 * P2[1] + t**3 * P3[1])
        elif name == "gr_poly":
            for a, b in re.findall(r"\(xy\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block):
                add(float(a), float(b))
        elif name == "gr_rect":
            sm = re.search(r"\(start\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
            em = re.search(r"\(end\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
            if sm and em:
                add(float(sm.group(1)), float(sm.group(2)))
                add(float(em.group(1)), float(em.group(2)))

    if not xs:
        raise RuntimeError(f"No Edge.Cuts geometry found in {pcb_path}")
    return min(xs), min(ys), max(xs), max(ys)


def svg_dimensions_mm(svg_path):
    """Read width/height (in mm) from a kicad-cli SVG. Authoritative — kicad-cli
    excludes degenerate geometry from --fit-page-to-board, so its viewBox is the
    true cut size."""
    text = open(svg_path).read()
    m = re.search(r'width="([\d.]+)mm"\s+height="([\d.]+)mm"', text)
    if not m:
        raise RuntimeError(f"Couldn't parse width/height from {svg_path}")
    return float(m.group(1)), float(m.group(2))


def kicad_pcb_to_fab_zip(input_path, output_name=None, output_dir=None):
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(input_path))
    if output_name is None:
        output_name = os.path.splitext(os.path.basename(input_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    dxf_path = os.path.join(output_dir, f"{output_name}.dxf")
    svg_path = os.path.join(output_dir, f"{output_name}.svg")
    pdf_path = os.path.join(output_dir, f"{output_name}.pdf")
    txt_path = os.path.join(output_dir, f"{output_name}-dimensions.txt")
    zip_path = os.path.join(output_dir, f"{output_name}.zip")

    print(f"\nProcessing: {input_path}")

    # SVG first — its viewBox gives us the authoritative cut dimensions
    subprocess.run([
        "kicad-cli", "pcb", "export", "svg",
        "--layers", "Edge.Cuts",
        "--black-and-white",
        "--fit-page-to-board",
        "--exclude-drawing-sheet",
        "--mode-single",
        "--page-size-mode", "2",
        "-o", svg_path,
        input_path,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    w_mm, h_mm = svg_dimensions_mm(svg_path)
    print(f"  SVG saved: {svg_path}")
    print(f"  Cut dimensions (from SVG): {w_mm:.4f} x {h_mm:.4f} mm")

    # Sanity check against direct .kicad_pcb parsing — flag if very different
    # (this catches cases where the user might want to investigate, e.g. orphan
    # geometry that kicad-cli ignored)
    try:
        x0, y0, x1, y1 = edge_cuts_bbox(input_path)
        parsed_w, parsed_h = x1 - x0, y1 - y0
        if abs(parsed_w - w_mm) > 0.5 or abs(parsed_h - h_mm) > 0.5:
            print(f"  Note: parser bbox is {parsed_w:.2f} x {parsed_h:.2f} mm "
                  f"(differs from SVG by {parsed_w-w_mm:+.2f} x {parsed_h-h_mm:+.2f}); "
                  f"likely orphan/degenerate geometry in source — using SVG size.")
    except Exception:
        pass

    # DXF via kicad-cli (mm units, single-file mode)
    subprocess.run([
        "kicad-cli", "pcb", "export", "dxf",
        "--layers", "Edge.Cuts",
        "--output-units", "mm",
        "--mode-single",
        "-o", dxf_path,
        input_path,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print(f"  DXF saved: {dxf_path}")

    # PDF via ezdxf + matplotlib
    try:
        import ezdxf
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ctx = RenderContext(doc)
        backend = MatplotlibBackend(ax)
        Frontend(ctx, backend).draw_layout(msp)
        ax.set_aspect("equal")
        ax.set_title(f"{output_name}\n{w_mm:.2f} x {h_mm:.2f} mm")
        fig.savefig(pdf_path, bbox_inches="tight", dpi=300)
        plt.close(fig)
        print(f"  PDF saved: {pdf_path}")
    except ImportError:
        print("  Warning: matplotlib/ezdxf missing — skipping PDF")
        pdf_path = None

    # Dimensions txt
    with open(txt_path, "w") as f:
        f.write(f"File: {output_name}\n")
        f.write(f"Width:  {w_mm:.2f} mm ({w_mm / 25.4:.2f} in)\n")
        f.write(f"Height: {h_mm:.2f} mm ({h_mm / 25.4:.2f} in)\n")
    print(f"  TXT saved: {txt_path}")

    # ZIP
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(dxf_path, f"{output_name}.dxf")
        zf.write(svg_path, f"{output_name}.svg")
        zf.write(txt_path, f"{output_name}-dimensions.txt")
        if pdf_path and os.path.exists(pdf_path):
            zf.write(pdf_path, f"{output_name}.pdf")
    print(f"  ZIP saved: {zip_path}")
    print(f"  Dimensions to provide to fab: {w_mm:.2f} x {h_mm:.2f} mm ({w_mm / 25.4:.2f} x {h_mm / 25.4:.2f} in)")

    # Cleanup loose files
    for p in (dxf_path, svg_path, txt_path, pdf_path):
        if p and os.path.exists(p):
            os.remove(p)
    print(f"  Cleaned up loose files; only {os.path.basename(zip_path)} remains.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Canonical run: inputs from sources/, outputs to cutout/ (parent of sources/)
        for inp in DEFAULT_INPUTS:
            kicad_pcb_to_fab_zip(inp, output_dir=CUTOUT_DIR)
    else:
        input_path = sys.argv[1]
        output_name = sys.argv[2] if len(sys.argv) > 2 else None
        kicad_pcb_to_fab_zip(input_path, output_name)
