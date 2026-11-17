#!/usr/bin/env python3
"""
Render a shaded PNG preview of one or more STL files (no OpenGL needed), so the
user can see a design before any plastic is spent.

Usage: render_stl.py OUT.png PART.stl [PART.stl ...] [--elev 25] [--azim -60]
Several STLs are drawn together in their own coordinates (handy for an assembly).
Useful second views: --elev 90 --azim -90 (top), --elev 0 --azim -90 (front),
--elev 0 --azim 0 (side). The projection is orthographic, so those are true views.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

COLORS = ["#2e9e5b", "#3b7dd8", "#d98a2b", "#b0489c", "#8a8f98"]


def main(argv):
    elev, azim, files = 25.0, -60.0, []
    it = iter(argv)
    for a in it:
        if a == "--elev":
            elev = float(next(it))
        elif a == "--azim":
            azim = float(next(it))
        else:
            files.append(a)
    if len(files) < 2:
        sys.exit(__doc__)
    out, stls = files[0], files[1:]
    meshes = [trimesh.load(p, force="mesh") for p in stls]
    # matplotlib sorts whole triangles by depth, so large flat faces draw in the
    # wrong order and look like dark holes. Small triangles keep the error small.
    span = max(float((m.bounds[1] - m.bounds[0]).max()) for m in meshes)
    meshes = [trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(m.vertices, m.faces, span / 24),
                              process=False) for m in meshes]
    fig = plt.figure(figsize=(9, 9), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_proj_type("ortho")
    light = np.array([0.3, -0.6, 0.75])
    light /= np.linalg.norm(light)
    for i, m in enumerate(meshes):
        shade = 0.55 + 0.45 * np.clip(m.face_normals @ light, 0, 1)
        base = np.array(matplotlib.colors.to_rgb(COLORS[i % len(COLORS)]))
        ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], edgecolors="none",
                                             facecolors=np.clip(base[None, :] * shade[:, None], 0, 1)))
    lo = np.min([m.bounds[0] for m in meshes], axis=0)
    hi = np.max([m.bounds[1] for m in meshes], axis=0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.subplots_adjust(0, 0, 1, 1)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fig.savefig(out, facecolor="white")
    size = hi - lo
    print(f"{out}: bounding box {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm")


if __name__ == "__main__":
    main(sys.argv[1:])
