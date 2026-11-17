#!/usr/bin/env python3
"""Mock-up render: the rack with the four devices in it, drawn as ONE depth-sorted
collection so the tablets occlude each other correctly. python3 mock_render.py OUT.png [elev azim]"""
import glob, os, sys
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]
elev, azim = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (18.0, -125.0)
ZOOM = float(sys.argv[4]) if len(sys.argv) > 4 else 0.72
COL = {"rack": "#e8792b", "ipad-pro": "#9aa0a8", "ipad-mini": "#7d6f9c", "kindle": "#4f6f64"}
tris, cols = [], []
light = np.array([0.35, -0.5, 0.8]); light /= np.linalg.norm(light)
for f in sorted(glob.glob(os.path.join(here, "previews/mock_*.stl"))):
    m = trimesh.load(f)
    v, fc = trimesh.remesh.subdivide_to_size(m.vertices, m.faces, 9.0)
    m = trimesh.Trimesh(v, fc, process=False)
    base = np.array(matplotlib.colors.to_rgb(next(c for k, c in COL.items() if k in os.path.basename(f))))
    shade = 0.55 + 0.45 * np.abs(m.face_normals @ light)
    tris.append(m.vertices[m.faces]); cols.append(np.clip(base[None] * shade[:, None], 0, 1))
tris, cols = np.concatenate(tris), np.concatenate(cols)
fig = plt.figure(figsize=(9, 7), dpi=130); ax = fig.add_subplot(projection="3d", proj_type="ortho")
ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors="none"))
lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0); c, r = (lo + hi) / 2, (hi - lo).max() / 2 * ZOOM
ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
fig.subplots_adjust(0, 0, 1, 1); fig.savefig(out, facecolor="white"); print(out)
