#!/usr/bin/env python3
"""
Small CAD helpers for printable parts, on manifold3d (tested with 3.5.4) and
trimesh. Copy this file next to your model script, or import it in place:

    import sys, os
    sys.path.insert(0, os.path.expanduser("~/.claude/skills/bambu-a1mini-print/scripts"))
    from cad_helpers import box, prism_xy, prism_yz, cyl_z, cyl_y, rounded, export

    W, D, H = 40.0, 20.0, 10.0          # named dimensions first, millimetres
    part = box(0, W, 0, D, 0, H) - cyl_z(4.0, 0, H, W / 2, D / 2)   # block with a hole
    export(part, "stl/part.stl")        # prints size, volume, watertight, body count

Solids combine with + (union), - (difference) and ^ (intersection), and move
with .translate([x, y, z]) / .rotate([rx, ry, rz]) (degrees) / .mirror([1, 0, 0]).
Model the part in its print orientation, resting on z = 0.

A part that is one 2D profile is easiest as a prism: draw the profile as a
polygon and extrude it. That also gives a print with no overhangs when the
profile lies on the bed. API notes that cost time before: join types live at
manifold3d.JoinType (not CrossSection.JoinType), and a Manifold becomes a mesh
through to_mesh().vert_properties[:, :3] and .tri_verts (see to_trimesh).
"""
import os

import manifold3d
import numpy as np
import trimesh
from manifold3d import CrossSection, FillRule, Manifold

SEGMENTS = 96        # facets for a full circle


def box(x0, x1, y0, y1, z0, z1) -> Manifold:
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def profile(pts) -> CrossSection:
    """2D polygon from (u, v) points. Pass several loops as a list of lists to
    cut holes (even-odd fill)."""
    loops = pts if isinstance(pts[0][0], (list, tuple)) else [pts]
    return CrossSection([[(float(u), float(v)) for u, v in loop] for loop in loops], FillRule.EvenOdd)


def rounded(cs: CrossSection, radius: float) -> CrossSection:
    """Round every corner of a 2D profile: convex ones by `radius`, concave ones
    too (offset in, out, out, in). Handy for fillets that spread stress."""
    j = manifold3d.JoinType.Round
    cs = cs.offset(-radius, j, 2.0, SEGMENTS).offset(radius, j, 2.0, SEGMENTS)     # convex
    return cs.offset(radius, j, 2.0, SEGMENTS).offset(-radius, j, 2.0, SEGMENTS)   # concave


def prism_xy(pts_or_cs, z0, z1) -> Manifold:
    """Profile in the XY plane, extruded along Z."""
    cs = pts_or_cs if isinstance(pts_or_cs, CrossSection) else profile(pts_or_cs)
    return Manifold.extrude(cs, z1 - z0).translate([0.0, 0.0, z0])


def prism_yz(pts_or_cs, x0, x1) -> Manifold:
    """Profile in the YZ plane (points are (y, z)), extruded along X."""
    cs = pts_or_cs if isinstance(pts_or_cs, CrossSection) else profile(pts_or_cs)
    m = Manifold.extrude(cs, x1 - x0)                         # (u, v, w) = (y, z, x)
    m = m.rotate([0.0, 90.0, 0.0]).rotate([90.0, 0.0, 0.0])   # -> (x, y, z)
    return m.translate([x0, 0.0, 0.0])


def cyl_z(radius, z0, z1, cx=0.0, cy=0.0) -> Manifold:
    return Manifold.cylinder(z1 - z0, radius, radius, SEGMENTS).translate([cx, cy, z0])


def cyl_y(radius, y0, y1, cx=0.0, cz=0.0) -> Manifold:
    m = Manifold.cylinder(y1 - y0, radius, radius, SEGMENTS)
    return m.rotate([-90.0, 0.0, 0.0]).translate([cx, y0, cz])


def to_trimesh(m: Manifold) -> trimesh.Trimesh:
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)


def export(m: Manifold, path: str) -> trimesh.Trimesh:
    """Write an STL and print the checks worth doing before slicing. A part
    should be watertight, one body, and sitting on z = 0.
    (Count bodies with Manifold.decompose(): trimesh's split()/body_count need
    scipy or networkx, which are not installed here.)"""
    tm = to_trimesh(m)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tm.export(path)
    lo, hi = tm.bounds
    size = hi - lo
    bodies = len(m.decompose())
    notes = []
    if not tm.is_watertight:
        notes.append("NOT watertight")
    if bodies != 1:
        notes.append(f"{bodies} separate bodies (parts not touching/overlapping?)")
    if abs(lo[2]) > 1e-6:
        notes.append(f"lowest point at z = {lo[2]:.2f}, not on the bed")
    if max(size[0], size[1]) > 160 or size[2] > 180:
        notes.append("larger than the 160 mm brim-safe bed area or 180 mm height")
    print(f"{os.path.basename(path)}: {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm, "
          f"{tm.volume / 1000:.1f} cm3 (about {tm.volume / 1000 * 1.27:.0f} g solid PETG), "
          f"watertight={tm.is_watertight}, bodies={bodies}"
          + ("".join("\n  WARNING: " + n for n in notes)))
    return tm
