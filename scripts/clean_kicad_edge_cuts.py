#!/usr/bin/env python3
"""
Clean orphan and duplicate gr_line / gr_curve / gr_arc entries from a KiCad
.kicad_pcb's Edge.Cuts layer. Writes a backup as <file>.bak before modifying.

An "orphan" is an Edge.Cuts segment whose endpoints don't connect to any other
Edge.Cuts segment (within a 0.01mm tolerance). These are typically leftover
stragglers from copy/paste or partial deletes that prevent the laser-cut path
from polygonizing into closed shapes — and trigger fab "open entities" rejects.

Usage:
    python3 clean_kicad_edge_cuts.py <file.kicad_pcb> [<file.kicad_pcb> ...]
    python3 clean_kicad_edge_cuts.py                # process all 3 canonical sources

Backup:    <file>.bak  (overwrites any existing .bak — keep your own copy if needed)
"""

import math
import os
import re
import shutil
import sys
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_DIR = os.path.join(REPO_ROOT, "fabrication", "!for-fabricator-production", "cutout", "sources")
DEFAULT_INPUTS = [
    os.path.join(SOURCES_DIR, "choc_switchplates.kicad_pcb"),
    os.path.join(SOURCES_DIR, "screen_cover.kicad_pcb"),
    os.path.join(SOURCES_DIR, "base_plate.kicad_pcb"),
]

SNAP_TOL = 0.01  # mm; endpoints within this distance are treated as the same node
ROUND_GRID = 0.01  # mm; coordinates are rounded to this grid in the source file
                   # (welds near-coincident endpoints so they connect exactly)
STITCH_TOL = 0.5   # mm; pairs of open endpoints within this distance get welded
                   # to bridge gaps from manual edits (e.g. 0.1mm corner offsets)


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
                    yield (name, start, k + 1, s[start:k + 1])
                    i = k + 1
                    break
            k += 1
        else:
            break


def get_endpoints(name, block):
    """Return [(start_x, start_y), (end_x, end_y)] for line/arc/curve, or [] if closed."""
    if name == "gr_line" or name == "gr_arc":
        sm = re.search(r"\(start\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
        em = re.search(r"\(end\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
        if sm and em:
            return [(float(sm.group(1)), float(sm.group(2))),
                    (float(em.group(1)), float(em.group(2)))]
    elif name == "gr_curve":
        ctrl = re.findall(r"\(xy\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", block)
        if len(ctrl) >= 4:
            return [(float(ctrl[0][0]), float(ctrl[0][1])),
                    (float(ctrl[-1][0]), float(ctrl[-1][1]))]
    return []


def round_coord_token(s, grid):
    """Round all (start|end|mid|center|xy NUM NUM) coordinate tokens to `grid` mm."""
    def repl(m):
        prefix = m.group(1)
        x = round(float(m.group(2)) / grid) * grid
        y = round(float(m.group(3)) / grid) * grid
        # Determine decimals from the grid value (0.01 -> 2 decimals)
        decimals = max(0, -int(math.floor(math.log10(grid))))
        return f"({prefix} {x:.{decimals}f} {y:.{decimals}f})"
    return re.sub(r"\((start|end|mid|center|xy)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", repl, s)


def stitch_open_endpoints(text, tol=STITCH_TOL):
    """Find pairs of open Edge.Cuts endpoints within `tol` and weld them by
    moving one endpoint to the other's location. This bridges gaps from manual
    edits where a corner ends up offset by sub-mm.
    Returns (new_text, n_stitched)."""
    # Parse all Edge.Cuts segments + their endpoints, EXCLUDING degenerates
    # (items with start ≈ end). Degenerate curves/lines have both endpoints
    # at the same node, which falsely makes the node appear degree-2 even
    # though no real segment connects there.
    DEGEN_TOL = 0.001
    items = []
    for name, start, end, block in iter_blocks(text, ["gr_line", "gr_arc", "gr_curve"]):
        if 'layer "Edge.Cuts"' not in block:
            continue
        eps = get_endpoints(name, block)
        if not eps:
            continue
        if math.hypot(eps[1][0] - eps[0][0], eps[1][1] - eps[0][1]) < DEGEN_TOL:
            continue  # skip degenerate
        items.append((name, start, end, block, eps))

    # Build the endpoint graph at fine precision; find degree-1 nodes
    fine_tol = 0.001
    def fkey(p):
        return (round(p[0] / fine_tol) * fine_tol, round(p[1] / fine_tol) * fine_tol)
    deg = defaultdict(int)
    for _, _, _, _, eps in items:
        deg[fkey(eps[0])] += 1
        deg[fkey(eps[1])] += 1

    # List of open endpoints (degree 1) + which item they came from
    open_eps = []
    for idx, (_, _, _, _, eps) in enumerate(items):
        for which, ep in enumerate(eps):
            if deg[fkey(ep)] == 1:
                open_eps.append((idx, which, ep))

    if not open_eps:
        return text, 0

    # Greedy nearest-neighbor pairing: for each open endpoint, find the closest
    # OTHER open endpoint within tol, and weld them by moving both to the midpoint.
    # Use a spatial bucket to speed up the search.
    bucket = defaultdict(list)
    for i, (_, _, ep) in enumerate(open_eps):
        bx = int(ep[0] / tol); by = int(ep[1] / tol)
        bucket[(bx, by)].append(i)

    used = [False] * len(open_eps)
    pairs = []
    for i, (_, _, ep) in enumerate(open_eps):
        if used[i]: continue
        bx = int(ep[0] / tol); by = int(ep[1] / tol)
        best_j = -1
        best_d2 = (tol * tol)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in bucket.get((bx + dx, by + dy), []):
                    if j == i or used[j]: continue
                    other = open_eps[j][2]
                    d2 = (ep[0] - other[0])**2 + (ep[1] - other[1])**2
                    if d2 < best_d2:
                        best_d2 = d2
                        best_j = j
        if best_j >= 0:
            pairs.append((i, best_j))
            used[i] = used[best_j] = True

    if not pairs:
        return text, 0

    # For each pair, compute the midpoint and update the source coordinates.
    # We do this by REPLACING the exact coord pair in the s-expression block.
    # Build replacement map: (idx, which) → midpoint
    target = {}
    for i, j in pairs:
        ep_i = open_eps[i][2]
        ep_j = open_eps[j][2]
        mid = ((ep_i[0] + ep_j[0]) / 2, (ep_i[1] + ep_j[1]) / 2)
        target[(open_eps[i][0], open_eps[i][1])] = (ep_i, mid)
        target[(open_eps[j][0], open_eps[j][1])] = (ep_j, mid)

    # Walk items back-to-front and rewrite blocks
    out = list(text)
    decimals = max(0, -int(math.floor(math.log10(ROUND_GRID))))
    for idx in range(len(items) - 1, -1, -1):
        name, start, end, block, eps = items[idx]
        repl_pairs = []
        for which in (0, 1):
            tk = (idx, which)
            if tk in target:
                old_pt, new_pt = target[tk]
                repl_pairs.append((which, old_pt, new_pt))
        if not repl_pairs:
            continue
        new_block = block
        for which, old_pt, new_pt in repl_pairs:
            # Match the coord token in the block. For lines/arcs, look for
            # (start ...) or (end ...). For curves, look for the matching xy.
            old_x_str = f"{old_pt[0]:.{decimals}f}"
            old_y_str = f"{old_pt[1]:.{decimals}f}"
            new_x_str = f"{new_pt[0]:.{decimals}f}"
            new_y_str = f"{new_pt[1]:.{decimals}f}"
            if name == "gr_line":
                tag = "start" if which == 0 else "end"
                new_block = re.sub(
                    rf"\({tag}\s+-?\d+\.?\d*\s+-?\d+\.?\d*\)",
                    f"({tag} {new_x_str} {new_y_str})", new_block, count=1)
            elif name == "gr_arc":
                tag = "start" if which == 0 else "end"
                new_block = re.sub(
                    rf"\({tag}\s+-?\d+\.?\d*\s+-?\d+\.?\d*\)",
                    f"({tag} {new_x_str} {new_y_str})", new_block, count=1)
            elif name == "gr_curve":
                # The first and last (xy ... ...) inside the block are P0 and P3.
                xy_matches = list(re.finditer(r"\(xy\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", new_block))
                if xy_matches:
                    target_match = xy_matches[0] if which == 0 else xy_matches[-1]
                    s_off, e_off = target_match.span()
                    new_block = new_block[:s_off] + f"(xy {new_x_str} {new_y_str})" + new_block[e_off:]
        out[start:end] = list(new_block)

    return "".join(out), len(pairs)


def wall_open_endpoints(text, max_gap_mm=30.0):
    """Find pairs of remaining open Edge.Cuts endpoints (after stitching) and
    add a gr_line between each pair — these are the 'walls' that close former
    mouse-bite gaps. Returns (new_text, n_walls_added)."""
    DEGEN_TOL_LOCAL = 0.001
    items = []
    for name, start, end, block in iter_blocks(text, ["gr_line", "gr_arc", "gr_curve"]):
        if 'layer "Edge.Cuts"' not in block:
            continue
        eps = get_endpoints(name, block)
        if not eps:
            continue
        if math.hypot(eps[1][0] - eps[0][0], eps[1][1] - eps[0][1]) < DEGEN_TOL_LOCAL:
            continue
        items.append((name, start, end, block, eps))

    if not items:
        return text, 0

    fine_tol = 0.001
    def fkey(p):
        return (round(p[0] / fine_tol) * fine_tol, round(p[1] / fine_tol) * fine_tol)
    deg = defaultdict(int)
    for _, _, _, _, eps in items:
        deg[fkey(eps[0])] += 1
        deg[fkey(eps[1])] += 1

    open_eps = []
    for ep, d in deg.items():
        if d == 1:
            open_eps.append(ep)

    if len(open_eps) < 2:
        return text, 0

    # Greedy nearest-neighbor pairing across remaining opens (any distance)
    used = [False] * len(open_eps)
    pairs = []
    for i in range(len(open_eps)):
        if used[i]: continue
        best_j = -1
        best_d = max_gap_mm + 1
        for j in range(i + 1, len(open_eps)):
            if used[j]: continue
            d = math.hypot(open_eps[i][0] - open_eps[j][0], open_eps[i][1] - open_eps[j][1])
            if d < best_d and d <= max_gap_mm:
                best_d = d
                best_j = j
        if best_j >= 0:
            pairs.append((open_eps[i], open_eps[best_j]))
            used[i] = used[best_j] = True

    if not pairs:
        return text, 0

    # Find the kicad_pcb's (kicad_pcb ...) block end so we can insert new gr_line
    # entries before it. Simpler: insert at the end of the file, just before the
    # final closing paren of the (kicad_pcb ...) block.
    # Find the LAST ')' in the file (that closes kicad_pcb)
    insertion_point = len(text)
    while insertion_point > 0 and text[insertion_point - 1] in (' ', '\t', '\n'):
        insertion_point -= 1
    if insertion_point > 0 and text[insertion_point - 1] == ')':
        insertion_point -= 1  # before final ')'

    # Build wall gr_line entries (KiCad 10 format).
    # If the pair isn't axis-aligned, add TWO segments forming an L-shape so the
    # wall follows orthogonal lines (matches PCB conventions). Otherwise a single
    # straight line is enough.
    decimals = max(0, -int(math.floor(math.log10(ROUND_GRID))))
    wall_blocks = []
    import uuid

    def gr_line(ax, ay, bx, by):
        return (
            f'\n\t(gr_line\n'
            f'\t\t(start {ax:.{decimals}f} {ay:.{decimals}f})\n'
            f'\t\t(end {bx:.{decimals}f} {by:.{decimals}f})\n'
            f'\t\t(stroke (width 0.05) (type solid))\n'
            f'\t\t(layer "Edge.Cuts")\n'
            f'\t\t(uuid "{uuid.uuid4()}")\n'
            f'\t)\n'
        )

    AXIS_TOL = 0.005
    for (a, b) in pairs:
        ax, ay = a
        bx, by = b
        if abs(ax - bx) < AXIS_TOL or abs(ay - by) < AXIS_TOL:
            # Already axis-aligned — single segment.
            wall_blocks.append(gr_line(ax, ay, bx, by))
        else:
            # L-shape with corner at (ax, by): vertical first, then horizontal.
            # This avoids overlapping with horizontal segments that often share
            # endpoint A (the typical pattern: a top-edge horizontal ending at A,
            # and a vertical ending at B at a different Y).
            wall_blocks.append(gr_line(ax, ay, ax, by))
            wall_blocks.append(gr_line(ax, by, bx, by))

    new_text = text[:insertion_point] + "".join(wall_blocks) + text[insertion_point:]
    return new_text, len(pairs)


def clean_file(path):
    text = open(path).read()

    # Step 1: Round all Edge.Cuts coordinates to ROUND_GRID. This welds
    # near-coincident endpoints (precision ≤ ROUND_GRID) so they connect
    # exactly. We round the whole file but only inside Edge.Cuts blocks; do
    # this by walking the blocks and rewriting them in place.
    pieces = []
    cursor = 0
    rounded_count = 0
    for name, start, end, block in iter_blocks(text, ["gr_line", "gr_arc", "gr_curve"]):
        if 'layer "Edge.Cuts"' not in block:
            continue
        # Append everything up to this block, then the rounded block
        pieces.append(text[cursor:start])
        new_block = round_coord_token(block, ROUND_GRID)
        if new_block != block:
            rounded_count += 1
        pieces.append(new_block)
        cursor = end
    pieces.append(text[cursor:])
    text = "".join(pieces)
    if rounded_count:
        print(f"  [{os.path.basename(path)}] rounded coords on {rounded_count} Edge.Cuts segments to {ROUND_GRID}mm grid")

    # Step 2a: Iterative tight-tol stitching. Weld near-coincident open endpoints
    # (precision-induced gaps) by moving them to their midpoint.
    total_stitched = 0
    for iteration in range(10):
        text, n_stitched = stitch_open_endpoints(text, tol=STITCH_TOL)
        total_stitched += n_stitched
        if n_stitched == 0:
            break
    if total_stitched:
        print(f"  [{os.path.basename(path)}] stitched {total_stitched} open endpoint pairs (gap ≤ {STITCH_TOL}mm)")

    # Step 2b: Bridge-walling. Any remaining open endpoint pairs are large gaps
    # (e.g. where mouse bites used to connect to other plates). The user's
    # intent is to replace these with WALLS — straight gr_line segments between
    # the open pair, closing the boundary. Cap the per-pair gap at 30mm so we
    # don't accidentally connect unrelated open endpoints across the plate.
    text, walls_added = wall_open_endpoints(text, max_gap_mm=30.0)
    if walls_added:
        print(f"  [{os.path.basename(path)}] added {walls_added} wall segment(s) to close large gaps (mouse-bite locations)")

    # Locate every gr_line/gr_arc/gr_curve on Edge.Cuts in the rounded+stitched text
    items = []
    for name, start, end, block in iter_blocks(text, ["gr_line", "gr_arc", "gr_curve"]):
        if 'layer "Edge.Cuts"' not in block:
            continue
        eps = get_endpoints(name, block)
        if not eps:
            continue
        items.append((name, start, end, block, eps))

    if not items:
        print(f"  [{os.path.basename(path)}] no Edge.Cuts segments found — skipping")
        return

    # Build endpoint graph (node = quantized endpoint)
    def key(p):
        return (round(p[0] / SNAP_TOL) * SNAP_TOL, round(p[1] / SNAP_TOL) * SNAP_TOL)

    DEGEN_TOL = 0.001  # mm — segments shorter than this are degenerate (zero-length artifacts)

    # First pass: flag degenerates (start ≈ end). They produce phantom branches in
    # the endpoint graph because both endpoints map to the same node.
    degen_idxs = set()
    for idx, (name, _, _, _, eps) in enumerate(items):
        dx = eps[1][0] - eps[0][0]
        dy = eps[1][1] - eps[0][1]
        if math.hypot(dx, dy) < DEGEN_TOL:
            degen_idxs.add(idx)

    # Build the endpoint graph EXCLUDING degenerates so degree counts are honest
    node_count = defaultdict(int)
    for idx, (name, _, _, _, eps) in enumerate(items):
        if idx in degen_idxs:
            continue
        for ep in eps:
            node_count[key(ep)] += 1

    # Orphan: both endpoints have degree 1 (no other segment shares them)
    # Duplicate: same (kind, frozenset of snapped endpoints) signature
    seen_sigs = {}
    orphan_idxs = []
    duplicate_idxs = []
    for idx, (name, _, _, _, eps) in enumerate(items):
        if idx in degen_idxs:
            continue
        deg_a = node_count[key(eps[0])]
        deg_b = node_count[key(eps[1])]
        if deg_a == 1 and deg_b == 1:
            orphan_idxs.append(idx)
            continue
        sig = (name, frozenset([key(eps[0]), key(eps[1])]))
        if sig in seen_sigs:
            duplicate_idxs.append(idx)
        else:
            seen_sigs[sig] = idx

    # Find connected components, and within each remove SMALL components
    # (≤ 12 segments — small leftover scraps) that have any open endpoints.
    # We avoid removing the outer plate boundary (large component) even if it
    # has open endpoints — the buffer-based DXF generator can bridge those.
    parent_uf = {}
    def find_uf(x):
        while parent_uf[x] != x:
            parent_uf[x] = parent_uf[parent_uf[x]]
            x = parent_uf[x]
        return x
    def union_uf(a, b):
        ra, rb = find_uf(a), find_uf(b)
        if ra != rb: parent_uf[ra] = rb

    excluded = set(degen_idxs) | set(orphan_idxs) | set(duplicate_idxs)
    for idx, (_, _, _, _, eps) in enumerate(items):
        if idx in excluded: continue
        ka, kb = key(eps[0]), key(eps[1])
        for k in (ka, kb):
            if k not in parent_uf: parent_uf[k] = k
        union_uf(ka, kb)

    component_idxs = defaultdict(list)
    for idx, (_, _, _, _, eps) in enumerate(items):
        if idx in excluded: continue
        component_idxs[find_uf(key(eps[0]))].append(idx)

    SCRAP_MAX_SEGS = 12  # remove "stray scrap" components no larger than this
    scrap_idxs = []
    for root, idxs in component_idxs.items():
        if len(idxs) > SCRAP_MAX_SEGS:
            continue
        local_count = defaultdict(int)
        for idx in idxs:
            eps = items[idx][4]
            local_count[key(eps[0])] += 1
            local_count[key(eps[1])] += 1
        if any(d != 2 for d in local_count.values()):
            # Small open/branching component — leftover stray. Remove.
            scrap_idxs.extend(idxs)

    to_remove = sorted(set(list(degen_idxs) + orphan_idxs + duplicate_idxs + scrap_idxs))
    print(f"  [{os.path.basename(path)}] {len(items)} Edge.Cuts segments; "
          f"{len(degen_idxs)} degenerate, {len(orphan_idxs)} orphans, "
          f"{len(duplicate_idxs)} duplicates, {len(scrap_idxs)} scraps "
          f"→ removing {len(to_remove)}")

    if not to_remove:
        return

    # Backup
    bak = path + ".bak"
    shutil.copy2(path, bak)
    print(f"    backup: {bak}")

    # Remove the byte ranges of the items to delete (work back-to-front to keep
    # earlier offsets valid).
    ranges = sorted([(items[i][1], items[i][2]) for i in to_remove], reverse=True)
    out = text
    for s_off, e_off in ranges:
        # Also swallow trailing newline/whitespace if present so we don't leave a blank line
        end_with_ws = e_off
        while end_with_ws < len(out) and out[end_with_ws] in (" ", "\t"):
            end_with_ws += 1
        if end_with_ws < len(out) and out[end_with_ws] == "\n":
            end_with_ws += 1
        out = out[:s_off] + out[end_with_ws:]

    open(path, "w").write(out)
    print(f"    wrote: {path}")


def main(argv):
    inputs = argv[1:] if len(argv) > 1 else DEFAULT_INPUTS
    for path in inputs:
        if not os.path.exists(path):
            print(f"  [skip] not found: {path}")
            continue
        clean_file(path)


if __name__ == "__main__":
    main(sys.argv)
