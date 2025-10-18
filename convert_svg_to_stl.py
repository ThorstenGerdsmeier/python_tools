# Blender 2.93+ / 3.x / 4.x
# - Set the CONFIG paths/values, then run in Blender's Scripting workspace
# - Or run headless: blender -b -P this_script.py

import bpy
import os
import math
import xml.etree.ElementTree as ET

# =========================
# ======= CONFIG ==========
# =========================
SVG_PATH = r"/absolute/path/to/window.svg"
OUT_STL_PATH = r"/absolute/path/to/window.stl"
EXTRUDE_MM = 30.0  # thickness in mm
# =========================

# -------- SVG size parsing (mm) --------
def parse_svg_mm(svg_path):
    """Return (width_mm, height_mm) from SVG width/height or viewBox."""
    def _mm_from_unit(s):
        if s is None:
            return None
        s = s.strip().lower()
        num, unit = "", ""
        for ch in s:
            if ch.isdigit() or ch in ".-+eE":
                num += ch
            else:
                unit += ch
        if not num:
            return None
        try:
            val = float(num)
        except ValueError:
            return None

        unit = unit.strip()
        if unit in ("", "px"):  # fall back via viewBox if possible
            return None
        if unit == "mm":
            return val
        if unit == "cm":
            return val * 10.0
        if unit == "m":
            return val * 1000.0
        if unit in ("in", "inch"):
            return val * 25.4
        if unit == "pt":  # 1/72 in
            return val * (25.4 / 72.0)
        if unit == "pc":  # 12 pt
            return val * (25.4 / 6.0)
        return None

    tree = ET.parse(svg_path)
    root = tree.getroot()
    tag = root.tag
    if "}" in tag:
        _ = tag.split("}")[0] + "}"  # namespace (unused)

    w_mm = _mm_from_unit(root.get("width"))
    h_mm = _mm_from_unit(root.get("height"))
    if w_mm is not None and h_mm is not None:
        return w_mm, h_mm

    # Fallback: viewBox in px at 96 DPI -> mm
    vb = root.get("viewBox")
    if vb:
        parts = vb.replace(",", " ").split()
        if len(parts) == 4:
            try:
                _, _, vb_w, vb_h = map(float, parts)
                px_to_mm = 25.4 / 96.0
                return vb_w * px_to_mm, vb_h * px_to_mm
            except Exception:
                pass

    def _unitless_to_mm(s):
        try:
            return float(s) * (25.4 / 96.0)
        except Exception:
            return None

    if w_mm is None and root.get("width"):
        w_mm = _unitless_to_mm(root.get("width"))
    if h_mm is None and root.get("height"):
        h_mm = _unitless_to_mm(root.get("height"))

    if w_mm is None or h_mm is None:
        raise RuntimeError("Could not determine SVG size in mm (missing width/height/viewBox).")
    return w_mm, h_mm

# -------- Scene units --------
def set_scene_to_mm():
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.001  # display mm (1 m = 1000 mm)

# -------- Import / selection helpers --------
def import_svg(svg_path):
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=svg_path)
    after = set(bpy.data.objects)
    return [obj for obj in (after - before)]

def select_only(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        if o and o.name in bpy.data.objects:
            o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]

# -------- Bounds --------
def get_bounds_world(objs):
    import mathutils
    mins = mathutils.Vector(( math.inf,  math.inf,  math.inf))
    maxs = mathutils.Vector((-math.inf, -math.inf, -math.inf))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        eo = o.evaluated_get(depsgraph)
        for v in eo.bound_box:
            wp = eo.matrix_world @ mathutils.Vector(v)
            mins.x = min(mins.x, wp.x); mins.y = min(mins.y, wp.y); mins.z = min(mins.z, wp.z)
            maxs.x = max(maxs.x, wp.x); maxs.y = max(maxs.y, wp.y); maxs.z = max(maxs.z, wp.z)
    size = maxs - mins
    return mins, maxs, size

# -------- Auto scaling (width vs height) --------
def scale_import_to_mm_auto(objs, target_w_mm, target_h_mm, ar_warn_tol=0.01):
    """
    Uniformly scale so either width OR height matches, chosen automatically.
    - ar_warn_tol: relative tolerance for aspect-ratio mismatch warning (e.g., 0.01 = 1%)
    Returns dict with details (chosen_axis, scale, width_mm_after, height_mm_after).
    """
    _, _, size = get_bounds_world(objs)
    cur_w_m = max(size.x, 1e-12)
    cur_h_m = max(size.y, 1e-12)

    target_w_m = target_w_mm / 1000.0
    target_h_m = target_h_mm / 1000.0

    s_w = target_w_m / cur_w_m
    s_h = target_h_m / cur_h_m

    # Decide which dimension differs more (relative error)
    rel_err_w = abs(cur_w_m - target_w_m) / max(target_w_m, 1e-12)
    rel_err_h = abs(cur_h_m - target_h_m) / max(target_h_m, 1e-12)
    if rel_err_h > rel_err_w:
        chosen_axis = "height"
        s = s_h
    else:
        chosen_axis = "width"
        s = s_w

    # Apply uniform scale
    for o in objs:
        o.scale = (o.scale[0] * s, o.scale[1] * s, o.scale[2] * s)

    # Apply transform
    select_only(objs)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Report final (after apply)
    _, _, size_after = get_bounds_world(objs)
    final_w_mm = size_after.x * 1000.0
    final_h_mm = size_after.y * 1000.0

    # Warn if aspect ratios are inconsistent (uniform scaling can't fix this)
    svg_ar = target_w_mm / max(target_h_mm, 1e-12)
    imp_ar = final_w_mm / max(final_h_mm, 1e-12)
    if abs(svg_ar - imp_ar) / max(svg_ar, 1e-12) > ar_warn_tol:
        print(
            "[Warning] Imported aspect ratio differs from SVG's declared ratio. "
            "Uniform scaling matched %s, but the other axis will not be exact. "
            "Consider checking the SVG (units/viewBox/padding). "
            f"(SVG AR={svg_ar:.6f}, Imported AR≈{imp_ar:.6f})" % chosen_axis
        )

    print(f"[AutoScale] Chosen axis: {chosen_axis}, scale={s:.6f}")
    print(f"[AutoScale] Target (mm): W={target_w_mm:.3f}, H={target_h_mm:.3f}")
    print(f"[AutoScale] Final  (mm): W≈{final_w_mm:.3f}, H≈{final_h_mm:.3f}")

    return {
        "chosen_axis": chosen_axis,
        "scale": s,
        "width_mm_after": final_w_mm,
        "height_mm_after": final_h_mm,
    }

# -------- Extrude / convert / export --------
def extrude_curves_mm(curve_objs, extrude_mm):
    extrude_m = extrude_mm / 1000.0
    for o in curve_objs:
        if o.type == 'CURVE':
            o.data.extrude = extrude_m
            o.data.dimensions = '2D'
            o.data.fill_mode = 'BOTH'

def convert_selection_to_mesh():
    bpy.ops.object.convert(target='MESH', keep_original=False)

def export_selected_stl(path):
    bpy.ops.export_mesh.stl(filepath=path, use_selection=True, use_scene_unit=True)

# -------- Main --------
def main(svg_path, out_stl_path, extrude_mm):
    if not os.path.isfile(svg_path):
        raise FileNotFoundError(svg_path)

    set_scene_to_mm()

    w_mm, h_mm = parse_svg_mm(svg_path)
    imported = import_svg(svg_path)

    curve_objs = [o for o in imported if o.type == 'CURVE']
    if not curve_objs:
        raise RuntimeError("No curve objects were imported from the SVG.")

    select_only(curve_objs)

    # Auto choose width or height as scaling anchor
    scale_info = scale_import_to_mm_auto(curve_objs, w_mm, h_mm, ar_warn_tol=0.01)

    # Extrude, convert, export
    extrude_curves_mm(curve_objs, extrude_mm=extrude_mm)
    select_only(curve_objs)
    convert_selection_to_mesh()
    export_selected_stl(out_stl_path)

    print(f"Done. Exported STL: {out_stl_path}")
    print(f"Auto-scaling summary: {scale_info}")

if __name__ == "__main__":
    main(SVG_PATH, OUT_STL_PATH, EXTRUDE_MM)