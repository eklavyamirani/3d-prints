#!/usr/bin/env python3
"""
Add plate thumbnails to a .gcode.3mf produced by the Bambu Studio CLI.

Headless CLI runs cannot open an OpenGL window, so they write a 3MF whose
_rels/.rels points at Metadata/plate_1.png etc. without the files existing.
Bambu Studio's GUI chokes on that. This renders each plate from the object
bounding boxes in Metadata/plate_N.json plus the STLs and inserts
plate_N.png, plate_N_small.png, plate_no_light_N.png, top_N.png and pick_N.png,
and registers them in model_settings.config.

Usage: python3 fix_3mf_thumbnails.py sliced/splash_guard_A1mini.gcode.3mf
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
BED = 180.0


def mesh_for(name):
    base = re.sub(r"(\.stl)(_\d+)?$", r"\1", name)
    return trimesh.load(os.path.join(HERE, "stl", base), force="mesh")


def render_plate(plate, elev, azim, size_px, light=True):
    fig = plt.figure(figsize=(size_px / 100, size_px / 100), dpi=100)
    ax = fig.add_subplot(111, projection="3d")
    # bed
    bed = np.array([[[0, 0, 0], [BED, 0, 0], [BED, BED, 0], [0, BED, 0]]], float)
    ax.add_collection3d(Poly3DCollection(bed, facecolors="#2b2f33", edgecolors="#55595e", alpha=1.0))
    lightdir = np.array([0.3, -0.5, 0.8])
    lightdir /= np.linalg.norm(lightdir)
    for obj in plate["bbox_objects"]:
        m = mesh_for(obj["name"]).copy()
        bb = obj["bbox"]
        lo = m.bounds[0]
        m.apply_translation([bb[0] - lo[0], bb[1] - lo[1], -lo[2]])
        tri = m.vertices[m.faces]
        shade = 0.55 + 0.45 * np.clip(m.face_normals @ lightdir, 0, 1) if light else np.full(len(tri), 0.8)
        base = np.array([0.0, 0.68, 0.26])
        cols = np.clip(base[None, :] * shade[:, None], 0, 1)
        ax.add_collection3d(Poly3DCollection(tri, facecolors=cols, edgecolors="none"))
    ax.set_xlim(0, BED)
    ax.set_ylim(0, BED)
    ax.set_zlim(0, BED)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.subplots_adjust(0, 0, 1, 1)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="#1e2124")
    plt.close(fig)
    return buf.getvalue()


def blank_png(size_px, rgba=(0, 0, 0, 255)):
    fig = plt.figure(figsize=(size_px / 100, size_px / 100), dpi=100)
    fig.patch.set_facecolor(tuple(c / 255 for c in rgba))
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def main(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        plates = sorted(n for n in names if re.fullmatch(r"Metadata/plate_\d+\.json", n))
        settings = z.read("Metadata/model_settings.config").decode()
        images = {}
        for pj in plates:
            idx = int(re.search(r"plate_(\d+)\.json", pj).group(1))
            plate = json.loads(z.read(pj))
            print(f"plate {idx}: " + ", ".join(o["name"] for o in plate["bbox_objects"]))
            images[f"Metadata/plate_{idx}.png"] = render_plate(plate, 32, -60, 512)
            images[f"Metadata/plate_{idx}_small.png"] = render_plate(plate, 32, -60, 128)
            images[f"Metadata/plate_no_light_{idx}.png"] = render_plate(plate, 32, -60, 512, light=False)
            images[f"Metadata/top_{idx}.png"] = render_plate(plate, 90, -90, 512)
            images[f"Metadata/pick_{idx}.png"] = blank_png(512)
            block_re = re.compile(rf'(<metadata key="plater_id" value="{idx}"/>\n)')
            extra = (f'    <metadata key="thumbnail_file" value="Metadata/plate_{idx}.png"/>\n'
                     f'    <metadata key="thumbnail_no_light_file" value="Metadata/plate_no_light_{idx}.png"/>\n'
                     f'    <metadata key="top_file" value="Metadata/top_{idx}.png"/>\n'
                     f'    <metadata key="pick_file" value="Metadata/pick_{idx}.png"/>\n')
            if f'value="Metadata/plate_{idx}.png"' not in settings:
                settings = block_re.sub(lambda m: m.group(1) + extra, settings, count=1)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".3mf", dir=os.path.dirname(path))
        tmp.close()
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as out:
            for n in names:
                if n in images or n == "Metadata/model_settings.config":
                    continue
                info = z.getinfo(n)
                out.writestr(info, z.read(n))
            out.writestr("Metadata/model_settings.config", settings)
            for n, data in images.items():
                out.writestr(n, data, compress_type=zipfile.ZIP_STORED)
    shutil.move(tmp.name, path)
    print("updated", path)


if __name__ == "__main__":
    main(sys.argv[1])
