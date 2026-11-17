#!/usr/bin/env python3
"""
Slice STL parts for the Bambu Lab A1 mini with Bambu Studio's command line and
write a ready-to-open .gcode.3mf (with plate thumbnails).

Why this script exists: Bambu Studio's CLI does not resolve the "inherits"
chains in its bundled profiles (speeds come out wrong), cannot find presets
synced from the Bambu account, and exports a 3MF that points at thumbnail files
it never wrote. This flattens the profiles, embeds any process overrides in the
output as a renamed user preset (so the GUI keeps them when it re-slices; nothing
is written to Bambu Studio's own preset folders), slices, repairs the thumbnails,
and warns when a part sits too close to the bed edge.

Usage:
  slice_a1mini.py [options] PART.stl[:COUNT] [PART.stl[:COUNT] ...]

Options:
  --out DIR            output folder (default ./sliced)
  --name NAME          output is NAME.gcode.3mf (default "project"); also names
                       the tweaked process preset "<process> - NAME"
  --per-plate N        write one single-plate file per N parts instead of one
                       multi-plate project: NAME_plate_1.gcode.3mf, ... each with
                       its raw gcode beside it as NAME_plate_1.gcode
                       (single-plate files are what the cloud send flow wants;
                       a job that fits one plate needs no --per-plate)
  --filament PRESET    filament preset name (default: the user's COMGROW PETG)
  --process PRESET     process preset name (default "0.20mm Standard @BBL A1M")
  --bed TYPE           "Textured PEI Plate" (default), "Cool Plate", ...
  --set KEY=VALUE      process override, repeatable, e.g. --set wall_loops=4
                       --set brim_type=outer_only --set brim_width=5
                       --set enable_support=1 --set support_type="tree(auto)"
  --orient             let the slicer auto-orient (default: keep STL orientation)
  --no-arrange         keep each STL's own XY position instead of auto-arranging
                       (the bed is 0..180 in X and Y, so centre the part on 90,90
                       in the model; use when the arranger turns a long part and
                       parks it against the bed edge)
  --edge-margin MM     warn when a part is closer than this to the bed edge
                       (default 10)

Run it outside the command sandbox: the CLI initialises GLFW and fails inside.
"""
import json
import os
import re
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.expanduser("~/Applications/BambuStudio.app")
if not os.path.exists(APP):
    APP = "/Applications/BambuStudio.app"
BIN = os.path.join(APP, "Contents/MacOS/BambuStudio")
PROFILES = os.path.join(APP, "Contents/Resources/profiles/BBL")
USER_PRESETS = os.path.expanduser("~/Library/Application Support/BambuStudio/user")

MACHINE = "Bambu Lab A1 mini 0.4 nozzle"
BED_SIZE = 180.0
DEFAULT_PROCESS = "0.20mm Standard @BBL A1M"
DEFAULT_FILAMENT = "COMGROW PETG Basic @Bambu Lab A1 mini 0.4 nozzle"
DEFAULT_BED = "Textured PEI Plate"


def hm(seconds):
    return f"{seconds / 60:.0f} min" if seconds < 7200 else f"{seconds / 3600:.1f} h"


def find_profile(kind, name):
    p = os.path.join(PROFILES, kind, name + ".json")
    if os.path.exists(p):
        return p
    for root, _dirs, files in os.walk(USER_PRESETS):
        if name + ".json" in files:
            return os.path.join(root, name + ".json")
    raise FileNotFoundError(
        f"{kind} preset not found: {name!r}. System presets live in {PROFILES}/{kind}, "
        f"account presets under {USER_PRESETS}.")


def flatten(kind, name, seen=None):
    """Resolve 'inherits' (parent first, child overrides) and 'include' files."""
    seen = seen or set()
    if name in seen:
        raise RuntimeError("inherits cycle at " + name)
    seen.add(name)
    with open(find_profile(kind, name)) as f:
        data = json.load(f)
    merged = {}
    parent = data.pop("inherits", None)
    if parent:
        merged.update(flatten(kind, parent, seen))
    for inc in data.pop("include", []) or []:
        with open(find_profile(kind, inc)) as f:
            merged.update({k: v for k, v in json.load(f).items() if k not in ("type", "name", "from")})
    merged.update(data)
    merged["name"] = name
    merged["inherits"] = ""
    merged.setdefault("type", kind)            # presets synced from the cloud lack it
    merged.setdefault("instantiation", "true")
    return merged


def parse_args(argv):
    opt = {"out": "sliced", "name": "project", "per_plate": 0, "filament": DEFAULT_FILAMENT,
           "process": DEFAULT_PROCESS, "bed": DEFAULT_BED, "set": {}, "orient": False,
           "edge_margin": 10.0, "parts": []}
    it = iter(argv)
    for a in it:
        if a in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif a == "--out":
            opt["out"] = next(it)
        elif a == "--name":
            opt["name"] = next(it)
        elif a == "--per-plate":
            opt["per_plate"] = int(next(it))
        elif a == "--filament":
            opt["filament"] = next(it)
        elif a == "--process":
            opt["process"] = next(it)
        elif a == "--bed":
            opt["bed"] = next(it)
        elif a == "--set":
            k, _, v = next(it).partition("=")
            opt["set"][k] = v
        elif a == "--orient":
            opt["orient"] = True
        elif a == "--no-arrange":
            opt["arrange"] = False
        elif a == "--edge-margin":
            opt["edge_margin"] = float(next(it))
        elif a.startswith("--"):
            sys.exit(f"unknown option {a} (see --help)")
        else:
            m = re.fullmatch(r"(.+?)(?::(\d+))?", a)
            path, count = os.path.abspath(m.group(1)), int(m.group(2) or 1)
            if not os.path.exists(path):
                sys.exit(f"no such file: {path}")
            opt["parts"].append((path, count))
    if not opt["parts"]:
        sys.exit("no parts given (see --help)")
    names = [os.path.basename(p) for p, _ in opt["parts"]]
    if len(set(names)) != len(names):
        sys.exit("parts must have distinct file names (thumbnails are matched by name)")
    return opt


def write_profiles(opt, out_dir):
    cfg_dir = os.path.join(out_dir, "profiles")
    os.makedirs(cfg_dir, exist_ok=True)
    paths = {}
    for kind, name in (("machine", MACHINE), ("process", opt["process"])):
        flat = flatten(kind, name)
        if kind == "process":
            # Rename and mark as a user preset: otherwise Bambu Studio swaps in the
            # stock system preset when the 3mf is re-sliced in the GUI and silently
            # drops the overrides.
            flat["name"] = f"{name} - {opt['name']}"
            flat["from"] = "User"
            flat.pop("setting_id", None)
            flat["curr_bed_type"] = opt["bed"]
            # Keys are not validated: the slicer silently ignores a misspelt one, so
            # confirm overrides took effect in the "; key = value" footer of the gcode.
            flat.update(opt["set"])
        p = os.path.join(cfg_dir, kind + ".json")
        with open(p, "w") as f:
            json.dump(flat, f, indent=1)
        paths[kind] = p
    flat = flatten("filament", opt["filament"])
    paths["filament"] = os.path.join(cfg_dir, "filament_1.json")
    with open(paths["filament"], "w") as f:
        json.dump(flat, f, indent=1)
    print(f"profiles: {MACHINE} / {opt['process']} - {opt['name']} / {opt['filament']}")
    return paths


def check_bed_fit(path_3mf, margin):
    """The lesson behind this: two 170 mm parts on the 180 mm bed sliced without
    complaint, but sat at the bed edges with the brim clipped, and the whole plate
    came loose mid-print."""
    ok = True
    with zipfile.ZipFile(path_3mf) as z:
        for n in sorted(z.namelist()):
            if not re.fullmatch(r"Metadata/plate_\d+\.json", n):
                continue
            for o in json.loads(z.read(n)).get("bbox_objects", []):
                x0, y0, x1, y1 = o["bbox"][:4]
                gap = min(x0, y0, BED_SIZE - x1, BED_SIZE - y1)
                if gap < margin:
                    ok = False
                    print(f"  WARNING {o['name']}: only {gap:.1f} mm from the bed edge "
                          f"(x {x0:.1f}..{x1:.1f}, y {y0:.1f}..{y1:.1f}). Edge-hugging parts lose "
                          f"their brim and have detached before; use fewer parts per plate.")
    return ok


def slice_one(opt, paths, parts, out_dir, out_name):
    for f in os.listdir(out_dir):
        if f == "result.json" or re.fullmatch(r"plate_\d+\.gcode", f) or f == out_name:
            os.remove(os.path.join(out_dir, f))
    cmd = [BIN, "--debug", "1",
           "--load-settings", f"{paths['machine']};{paths['process']}",
           "--load-filaments", paths["filament"],
           "--load-filament-ids", ",".join("1" for _ in parts),
           "--clone-objects", ",".join(str(c) for _, c in parts),
           "--arrange", "1" if opt.get("arrange", True) else "0", "--orient", "1" if opt["orient"] else "0",
           "--slice", "0",
           "--export-3mf", out_name,
           "--outputdir", out_dir] + [p for p, _ in parts]
    r = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True)
    for line in (r.stdout + r.stderr).splitlines():
        # GLFW errors are expected (no window in a CLI run) and harmless.
        if "error" in line.lower() and "can not find key" not in line and "glfw" not in line.lower():
            print("  " + line)
    res = os.path.join(out_dir, "result.json")
    if not os.path.exists(res):
        sys.exit("Bambu Studio CLI wrote no result.json. If this ran inside a command "
                 "sandbox, rerun with the sandbox disabled (the CLI needs GLFW).")
    with open(res) as f:
        result = json.load(f)
    if result.get("return_code") != 0:
        sys.exit(f"slice failed: {result.get('return_code')} {result.get('error_string')}")
    total = 0
    for p in result.get("sliced_plates", []):
        s = p.get("total_predication", 0)
        total += s
        g = sum(fl.get("total_used_g", 0) for fl in p.get("filaments", []))
        warn = p.get("warning_message") or ""
        print(f"  plate {p['id']}: {hm(s)}, {g:.1f} g: "
              + ", ".join(o.get("name", "?") for o in p.get("objects", []))
              + (f"  [slicer warning: {warn}]" if warn else ""))
    out_3mf = os.path.join(out_dir, out_name)
    subprocess.run([sys.executable, os.path.join(HERE, "fix_3mf_thumbnails.py"), out_3mf]
                   + [p for p, _ in parts], check=True, stdout=subprocess.DEVNULL)
    check_bed_fit(out_3mf, opt["edge_margin"])
    if opt["per_plate"]:       # keep each file's gcode; the next slice reuses plate_1.gcode
        os.replace(os.path.join(out_dir, "plate_1.gcode"), out_3mf[:-len(".3mf")])
    print(f"  -> {out_3mf}")
    return total


def main():
    opt = parse_args(sys.argv[1:])
    out_dir = os.path.abspath(opt["out"])
    os.makedirs(out_dir, exist_ok=True)
    paths = write_profiles(opt, out_dir)
    total = 0
    if opt["per_plate"]:
        items = [p for p, c in opt["parts"] for _ in range(c)]
        n = opt["per_plate"]
        for i, group in enumerate((items[j:j + n] for j in range(0, len(items), n)), 1):
            merged = []
            for p in group:
                if merged and merged[-1][0] == p:
                    merged[-1] = (p, merged[-1][1] + 1)
                else:
                    merged.append((p, 1))
            print(f"plate file {i}:")
            total += slice_one(opt, paths, merged, out_dir, f"{opt['name']}_plate_{i}.gcode.3mf")
    else:
        total = slice_one(opt, paths, opt["parts"], out_dir, f"{opt['name']}.gcode.3mf")
    print(f"total print time: {hm(total)}")


if __name__ == "__main__":
    main()
