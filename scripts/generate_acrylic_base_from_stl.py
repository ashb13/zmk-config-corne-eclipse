#!/usr/bin/env python3
"""
Generate the acrylic shell base fab bundle from an STL — slices at the topmost
layer and exports a DXF + SVG + PDF + dimensions txt, zipped (only the .zip
remains; loose intermediates are cleaned up).

Usage:
    python3 generate_acrylic_base_from_stl.py                       # canonical project default
    python3 generate_acrylic_base_from_stl.py <input.stl>           # custom input, derived output name
    python3 generate_acrylic_base_from_stl.py <input.stl> <name>    # custom input and output name

Requirements:
    pip3 install trimesh scipy shapely networkx ezdxf matplotlib numpy
"""

import sys
import os
import trimesh
import numpy as np
import ezdxf
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(
    REPO_ROOT,
    "fabrication",
    "!for-fabricator-production",
    "cutout",
    "sources",
    "corne-eclipse-acrylic-lp-acrylic-only.stl",
)
DEFAULT_OUTPUT_NAME = "corne-eclipse-shell-acrylic-base"
DEFAULT_OUTPUT_DIR = os.path.dirname(os.path.dirname(DEFAULT_INPUT))  # cutout/, parent of sources/


def stl_to_dxf(input_path, output_name=None, output_dir=None):
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(input_path))
    if output_name is None:
        output_name = os.path.splitext(os.path.basename(input_path))[0]

    dxf_path = os.path.join(output_dir, f"{output_name}.dxf")
    svg_path = os.path.join(output_dir, f"{output_name}.svg")
    pdf_path = os.path.join(output_dir, f"{output_name}.pdf")
    zip_path = os.path.join(output_dir, f"{output_name}.zip")

    # Load STL
    print(f"Loading: {input_path}")
    mesh = trimesh.load(input_path)
    print(f"STL bounds: {mesh.extents[0]:.4f} x {mesh.extents[1]:.4f} x {mesh.extents[2]:.4f} mm")

    # Project the mesh straight down onto the XY plane to get its 2D silhouette.
    # This treats only THROUGH-HOLES as inner rings — counterbores / blind pockets
    # are covered by material on the other side and don't appear, so screw holes
    # come out as a single ring at the actual through-hole diameter (not the larger
    # countersink ring you'd get from a top-slice).
    from trimesh.path.polygons import projected
    silhouette = projected(mesh, normal=[0, 0, 1])
    if silhouette is None or silhouette.is_empty:
        print("Error: Could not extract a projected silhouette")
        sys.exit(1)

    polys = list(silhouette.geoms) if silhouette.geom_type == "MultiPolygon" else [silhouette]
    n_outer = len(polys)
    n_holes = sum(len(p.interiors) for p in polys)
    print(f"Silhouette: {silhouette.bounds[2]-silhouette.bounds[0]:.4f} x {silhouette.bounds[3]-silhouette.bounds[1]:.4f} mm  "
          f"({n_outer} outer ring{'s' if n_outer != 1 else ''}, {n_holes} hole{'s' if n_holes != 1 else ''})")

    # Export DXF: each ring (exterior + interiors) is a closed lwpolyline
    doc = ezdxf.new()
    msp = doc.modelspace()
    for p in polys:
        msp.add_lwpolyline(list(p.exterior.coords), close=True)
        for interior in p.interiors:
            msp.add_lwpolyline(list(interior.coords), close=True)
    doc.saveas(dxf_path)
    print(f"DXF saved: {dxf_path}")

    # Export SVG: build one <path> with subpaths for exteriors + interiors.
    # fill-rule="evenodd" makes interiors render as holes.
    bx0, by0, bx1, by1 = silhouette.bounds
    vb_x = bx0
    vb_y = -by1   # SVG Y is flipped
    vb_w = bx1 - bx0
    vb_h = by1 - by0

    def ring_to_path(coords):
        parts = []
        for j, (x, y) in enumerate(coords):
            cmd = "M" if j == 0 else "L"
            parts.append(f"{cmd}{x:.6f},{-y:.6f}")
        parts.append("Z")
        return "".join(parts)

    path_d = ""
    for p in polys:
        path_d += ring_to_path(list(p.exterior.coords)) + " "
        for interior in p.interiors:
            path_d += ring_to_path(list(interior.coords)) + " "

    svg_content = f'''<svg
  width="{vb_w:.4f}mm"
  height="{vb_h:.4f}mm"
  viewBox="{vb_x:.6f} {vb_y:.6f} {vb_w:.6f} {vb_h:.6f}"
  xmlns="http://www.w3.org/2000/svg">
  <path d="{path_d.strip()}" fill="black" fill-rule="evenodd" stroke="black" stroke-width="0.1"/>
</svg>'''

    with open(svg_path, 'w') as f:
        f.write(svg_content)
    print(f"SVG saved: {svg_path}")

    # Export PDF
    try:
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp)
        ax.set_aspect('equal')
        w_mm = silhouette.bounds[2] - silhouette.bounds[0]
        h_mm = silhouette.bounds[3] - silhouette.bounds[1]
        ax.set_title(f'{output_name}\n{w_mm:.2f} x {h_mm:.2f} mm')
        fig.savefig(pdf_path, bbox_inches='tight', dpi=300)
        plt.close(fig)
        print(f"PDF saved: {pdf_path}")
    except ImportError:
        print("Warning: matplotlib not installed, skipping PDF generation")
        pdf_path = None

    # Export dimensions text file
    txt_path = os.path.join(output_dir, f"{output_name}-dimensions.txt")
    w_mm = silhouette.bounds[2] - silhouette.bounds[0]
    h_mm = silhouette.bounds[3] - silhouette.bounds[1]
    with open(txt_path, 'w') as f:
        f.write(f"File: {output_name}\n")
        f.write(f"Width:  {w_mm:.2f} mm ({w_mm / 25.4:.2f} in)\n")
        f.write(f"Height: {h_mm:.2f} mm ({h_mm / 25.4:.2f} in)\n")
    print(f"TXT saved: {txt_path}")

    # ZIP
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(dxf_path, f"{output_name}.dxf")
        zf.write(svg_path, f"{output_name}.svg")
        zf.write(txt_path, f"{output_name}-dimensions.txt")
        if pdf_path and os.path.exists(pdf_path):
            zf.write(pdf_path, f"{output_name}.pdf")
    print(f"ZIP saved: {zip_path}")
    print(f"\nDimensions to provide to fab: {w_mm:.2f} x {h_mm:.2f} mm ({w_mm / 25.4:.2f} x {h_mm / 25.4:.2f} in)")

    # Clean up loose files — only the ZIP should remain
    for path in (dxf_path, svg_path, txt_path, pdf_path):
        if path and os.path.exists(path):
            os.remove(path)
    print(f"Cleaned up loose files; only {os.path.basename(zip_path)} remains.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Canonical run: input from sources/, output to cutout/ (parent of sources/)
        stl_to_dxf(DEFAULT_INPUT, DEFAULT_OUTPUT_NAME, output_dir=DEFAULT_OUTPUT_DIR)
    else:
        input_path = sys.argv[1]
        output_name = sys.argv[2] if len(sys.argv) > 2 else None
        stl_to_dxf(input_path, output_name)
