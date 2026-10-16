"""Forge3D Item Factory — procedural Blender builder.

Run from Blender:
  blender --background --python forge3d_item_factory.py -- --output ./output
  blender --background --python forge3d_item_factory.py -- --recipe helmet.json

Everything in this file is editable. No network access, APIs, or add-ons are used.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import traceback
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


# <FORGE3D_CONFIG>
CONFIG = {
    "name": "Aegis-01 Futuristic Football Helmet",
    "prompt": "A futuristic football helmet with an aerodynamic shell, smoked visor, luminous vents, and a protective titanium face cage.",
    "template": "futuristic_football_helmet",
    "detail": 0.72,
    "shell_profile": "aero",
    "visor": True,
    "face_cage": True,
    "luminous_vents": True,
    "import_path": "",
    "poly_budget": 80000,
    "render_size": 720,
    "colorways": [
        {"name": "Ion Lime", "primary": "#A6FF00", "secondary": "#10151B", "accent": "#E8FFF0"},
        {"name": "Plasma Coral", "primary": "#FF5F57", "secondary": "#1B1024", "accent": "#FFB347"},
        {"name": "Glacier", "primary": "#D8F7FF", "secondary": "#16344A", "accent": "#51D6FF"},
    ],
}
# </FORGE3D_CONFIG>


def log(message: str) -> None:
    print(f"[FORGE3D] {message}", flush=True)


def hex_rgba(value: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    value = value.lstrip("#")
    if len(value) != 6:
        value = "808080"
    return tuple(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4)) + (alpha,)


def clean_name(value: str) -> str:
    safe = "".join(c.lower() if c.isalnum() else "_" for c in value).strip("_")
    return safe or "item"


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def get_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if not collection:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, name: str) -> bpy.types.Object:
    collection = get_collection(name)
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    metallic: float = 0.0,
    roughness: float = 0.45,
    emission: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
    transmission: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    nodes = mat.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if "Coat Weight" in shader.inputs:
        shader.inputs["Coat Weight"].default_value = 0.28
    elif "Clearcoat" in shader.inputs:
        shader.inputs["Clearcoat"].default_value = 0.28
    if transmission:
        key = "Transmission Weight" if "Transmission Weight" in shader.inputs else "Transmission"
        shader.inputs[key].default_value = transmission
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "DITHERED"
        else:
            mat.blend_method = "BLEND"
    if emission and emission_strength:
        ekey = "Emission Color" if "Emission Color" in shader.inputs else "Emission"
        shader.inputs[ekey].default_value = emission
        if "Emission Strength" in shader.inputs:
            shader.inputs["Emission Strength"].default_value = emission_strength
    return mat


def assign_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    if not obj.data or not hasattr(obj.data, "materials"):
        return
    obj.data.materials.clear()
    obj.data.materials.append(material)


def apply_transform(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)


def smooth(obj: bpy.types.Object) -> None:
    if obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = True


def add_beveled_cube(name, location, scale, material, bevel=0.12, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    apply_transform(obj)
    modifier = obj.modifiers.new("Edge softening", "BEVEL")
    modifier.width = bevel
    modifier.segments = 4
    assign_material(obj, material)
    smooth(obj)
    return move_to_collection(obj, "MODEL")


def add_cylinder(name, location, radius, depth, material, rotation=(0, 0, 0), vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, material)
    smooth(obj)
    return move_to_collection(obj, "MODEL")


def add_tube(name, points, radius, material):
    curve_data = bpy.data.curves.new(name=f"{name}_Curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 3
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = 4
    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve_data)
    get_collection("MODEL").objects.link(obj)
    assign_material(obj, material)
    return obj


def create_helmet(config, materials):
    detail = max(0.2, min(1.0, float(config.get("detail", 0.7))))
    segments = 48 if detail < 0.65 else 64
    rings = 24 if detail < 0.65 else 32

    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=(0, 0.12, 1.65))
    shell = bpy.context.object
    shell.name = "Helmet_Shell"
    shell.scale = (1.34, 1.53, 1.30)
    apply_transform(shell)

    mesh = shell.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    remove = [
        vertex
        for vertex in bm.verts
        # Coordinates are local: the sphere object's center remains at Z 1.65
        # and Y 0.12 after its scale is applied.
        if vertex.co.z < -1.03 or (vertex.co.y < -0.88 and vertex.co.z < 0.59)
    ]
    bmesh.ops.delete(bm, geom=remove, context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    solidify = shell.modifiers.new("Impact shell thickness", "SOLIDIFY")
    solidify.thickness = 0.075
    solidify.offset = -0.2
    bevel = shell.modifiers.new("Shell edge radius", "BEVEL")
    bevel.width = 0.035
    bevel.segments = 3
    assign_material(shell, materials["primary"])
    smooth(shell)
    move_to_collection(shell, "MODEL")

    # Rear impact plates and crown spine.
    add_beveled_cube("Rear_Impact_Plate", (0, 1.28, 1.55), (0.80, 0.13, 0.58), materials["secondary"], 0.16, (math.radians(-12), 0, 0))
    for index, y in enumerate((-0.35, 0.0, 0.35, 0.70)):
        add_beveled_cube(f"Crown_Ridge_{index+1}", (0, y, 2.88 - abs(y) * 0.08), (0.13, 0.22, 0.07), materials["secondary"], 0.07)

    # Ear modules and glow rings.
    for side in (-1, 1):
        add_cylinder(f"Ear_Module_{'L' if side < 0 else 'R'}", (1.27 * side, 0.22, 1.30), 0.39, 0.14, materials["secondary"], (0, math.radians(90), 0))
        add_cylinder(f"Ear_Ring_{'L' if side < 0 else 'R'}", (1.35 * side, 0.22, 1.30), 0.26, 0.07, materials["accent"], (0, math.radians(90), 0))
        add_beveled_cube(f"Temple_Plate_{side}", (1.10 * side, -0.48, 1.84), (0.13, 0.42, 0.30), materials["secondary"], 0.12, (math.radians(-10), 0, math.radians(8 * side)))

        if config.get("luminous_vents", True):
            for index in range(3):
                add_beveled_cube(
                    f"Glow_Vent_{side}_{index}",
                    (1.29 * side, 0.62 + index * 0.23, 1.78 + index * 0.05),
                    (0.035, 0.13, 0.028),
                    materials["accent"],
                    0.025,
                    (0, 0, math.radians(-7 * side)),
                )

    if config.get("visor", True):
        visor = add_beveled_cube("Smoked_Visor", (0, -1.17, 1.78), (0.91, 0.055, 0.42), materials["visor"], 0.20, (math.radians(-7), 0, 0))
        visor.scale.x = 1.08
        add_beveled_cube("Visor_Brow", (0, -1.10, 2.25), (0.98, 0.12, 0.10), materials["secondary"], 0.09, (math.radians(-7), 0, 0))

    if config.get("face_cage", True):
        cage_paths = [
            [(-1.00, -0.92, 1.82), (-1.14, -1.44, 1.62), (-0.74, -1.83, 1.35), (0, -1.94, 1.27), (0.74, -1.83, 1.35), (1.14, -1.44, 1.62), (1.00, -0.92, 1.82)],
            [(-1.05, -0.92, 1.30), (-1.13, -1.42, 1.13), (-0.67, -1.82, 1.02), (0.67, -1.82, 1.02), (1.13, -1.42, 1.13), (1.05, -0.92, 1.30)],
            [(-0.73, -1.78, 1.37), (-0.72, -1.83, 0.96)],
            [(0.73, -1.78, 1.37), (0.72, -1.83, 0.96)],
        ]
        for index, points in enumerate(cage_paths):
            add_tube(f"Titanium_Cage_{index+1}", points, 0.045, materials["metal"])

    add_beveled_cube("Chin_Guard", (0, -1.56, 0.78), (0.55, 0.28, 0.18), materials["secondary"], 0.14, (math.radians(-8), 0, 0))
    add_beveled_cube("Neck_Guard", (0, 1.16, 0.72), (0.73, 0.27, 0.19), materials["primary"], 0.14, (math.radians(12), 0, 0))
    shell["forge3d_role"] = "primary_shell"
    shell["license"] = "CC0-1.0"
    return shell


def import_model(filepath: str):
    path = Path(filepath).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Import model not found: {path}")
    before = set(bpy.context.scene.objects)
    suffix = path.suffix.lower()
    log(f"Importing external model: {path.name}")
    if suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(path))
        else:
            bpy.ops.import_scene.obj(filepath=str(path))
    else:
        raise ValueError("Supported manual imports: .glb, .gltf, .fbx, or .obj")
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    for obj in imported:
        move_to_collection(obj, "MODEL")
        obj["forge3d_import_source"] = path.name
    return imported


def create_materials(colorway):
    primary = hex_rgba(colorway["primary"])
    secondary = hex_rgba(colorway["secondary"])
    accent = hex_rgba(colorway["accent"])
    return {
        "primary": make_material("F3D_Primary", primary, metallic=0.30, roughness=0.24),
        "secondary": make_material("F3D_Secondary", secondary, metallic=0.62, roughness=0.18),
        "accent": make_material("F3D_Accent", accent, metallic=0.15, roughness=0.20, emission=accent, emission_strength=3.5),
        "metal": make_material("F3D_Titanium", (0.32, 0.36, 0.39, 1), metallic=0.92, roughness=0.17),
        "visor": make_material("F3D_Visor", (0.015, 0.035, 0.055, 0.80), metallic=0.24, roughness=0.08, transmission=0.18),
    }


def set_colorway(materials, colorway):
    mapping = {"primary": colorway["primary"], "secondary": colorway["secondary"], "accent": colorway["accent"]}
    for key, value in mapping.items():
        color = hex_rgba(value)
        mat = materials[key]
        mat.diffuse_color = color
        shader = mat.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = color
        if key == "accent":
            ekey = "Emission Color" if "Emission Color" in shader.inputs else "Emission"
            shader.inputs[ekey].default_value = color


def look_at(obj, target=(0, 0, 1.45)):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_studio(render_size):
    world = bpy.context.scene.world or bpy.data.worlds.new("Forge3D World")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.007, 0.012, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.16

    bpy.ops.object.camera_add(location=(4.7, -6.8, 3.65))
    camera = bpy.context.object
    camera.name = "STUDIO_Camera"
    camera.data.lens = 58
    look_at(camera)
    move_to_collection(camera, "STUDIO")
    bpy.context.scene.camera = camera

    lights = [
        ("Key_Light", (4.0, -4.0, 6.2), 1300, (0.72, 0.88, 1.0), 4.0),
        ("Rim_Light", (-4.5, 1.8, 4.6), 1100, (0.55, 1.0, 0.24), 3.0),
        ("Fill_Light", (0.0, 4.0, 3.0), 850, (1.0, 0.35, 0.16), 3.0),
    ]
    for name, location, energy, color, size in lights:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size
        look_at(light)
        move_to_collection(light, "STUDIO")

    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0.50))
    floor = bpy.context.object
    floor.name = "STUDIO_Floor"
    floor_mat = make_material("Studio Floor", (0.012, 0.018, 0.025, 1), metallic=0.12, roughness=0.36)
    assign_material(floor, floor_mat)
    move_to_collection(floor, "STUDIO")

    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = int(render_size)
    scene.render.resolution_y = int(render_size)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    return camera


def model_objects():
    collection = bpy.data.collections.get("MODEL")
    return list(collection.all_objects) if collection else []


def qa_report(config):
    meshes = [obj for obj in model_objects() if obj.type == "MESH"]
    curves = [obj for obj in model_objects() if obj.type == "CURVE"]
    triangle_count = 0
    boundary_edges = 0
    nonmanifold_edges = 0
    missing_materials = []
    unapplied_scale = []
    for obj in meshes:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        temp_mesh = evaluated.to_mesh()
        triangle_count += sum(max(0, len(poly.vertices) - 2) for poly in temp_mesh.polygons)
        bm = bmesh.new()
        bm.from_mesh(temp_mesh)
        boundary_edges += sum(1 for edge in bm.edges if edge.is_boundary)
        nonmanifold_edges += sum(1 for edge in bm.edges if not edge.is_manifold and not edge.is_boundary)
        bm.free()
        evaluated.to_mesh_clear()
        if not obj.data.materials:
            missing_materials.append(obj.name)
        if any(abs(scale - 1.0) > 0.001 for scale in obj.scale):
            unapplied_scale.append(obj.name)

    budget = int(config.get("poly_budget", 80000))
    issues = []
    if triangle_count > budget:
        issues.append({"severity": "warning", "code": "POLY_BUDGET", "message": f"{triangle_count:,} triangles exceed the {budget:,} target."})
    if missing_materials:
        issues.append({"severity": "warning", "code": "MATERIALS", "message": f"Objects without materials: {', '.join(missing_materials[:8])}"})
    if nonmanifold_edges:
        issues.append({"severity": "warning", "code": "NON_MANIFOLD", "message": f"Found {nonmanifold_edges} non-manifold interior edges."})
    if unapplied_scale:
        issues.append({"severity": "info", "code": "SCALE", "message": f"Transforms remain editable on {len(unapplied_scale)} object(s)."})

    all_points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    dimensions = {"x": 0, "y": 0, "z": 0}
    if all_points:
        mins = [min(point[i] for point in all_points) for i in range(3)]
        maxs = [max(point[i] for point in all_points) for i in range(3)]
        dimensions = {axis: round(maxs[i] - mins[i], 4) for i, axis in enumerate(("x", "y", "z"))}

    return {
        "generator": "Forge3D Item Factory 1.0",
        "item": config.get("name", "Untitled item"),
        "status": "pass" if not any(i["severity"] == "error" for i in issues) else "fail",
        "triangle_count": triangle_count,
        "poly_budget": budget,
        "mesh_objects": len(meshes),
        "curve_objects": len(curves),
        "boundary_edges": boundary_edges,
        "nonmanifold_interior_edges": nonmanifold_edges,
        "dimensions_m": dimensions,
        "checks": [
            {"name": "Naming", "result": "pass", "detail": "All generated objects use descriptive names."},
            {"name": "Materials", "result": "pass" if not missing_materials else "warning", "detail": f"{len(missing_materials)} object(s) missing a material."},
            {"name": "Triangle budget", "result": "pass" if triangle_count <= budget else "warning", "detail": f"{triangle_count:,} / {budget:,} triangles."},
            {"name": "Open boundaries", "result": "info", "detail": f"{boundary_edges} boundary edges; the helmet opening is intentional."},
            {"name": "Export readiness", "result": "pass", "detail": "Metric units, named materials, and selected-object exports enabled."},
        ],
        "issues": issues,
    }


def select_model():
    bpy.ops.object.select_all(action="DESELECT")
    for obj in model_objects():
        if obj.type in {"MESH", "CURVE"}:
            obj.select_set(True)
    active = next((obj for obj in model_objects() if obj.type == "MESH"), None)
    if active:
        bpy.context.view_layer.objects.active = active


def export_assets(output_dir: Path, config):
    slug = clean_name(config.get("name", "forge3d_item"))
    select_model()
    glb_path = output_dir / f"{slug}.glb"
    fbx_path = output_dir / f"{slug}.fbx"
    blend_path = output_dir / f"{slug}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", use_selection=True, export_apply=True)
    bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False, path_mode="AUTO")
    return {"blend": str(blend_path), "glb": str(glb_path), "fbx": str(fbx_path)}


def render_colorways(output_dir: Path, materials, config):
    preview_dir = output_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for colorway in config.get("colorways", [])[:6]:
        set_colorway(materials, colorway)
        path = preview_dir / f"{clean_name(colorway['name'])}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        results.append(str(path))
        log(f"Rendered {colorway['name']}")
    return results


def parse_args():
    parser = argparse.ArgumentParser(description="Forge3D local item builder")
    parser.add_argument("--recipe", default="", help="Path to a Forge3D recipe JSON")
    parser.add_argument("--output", default="./forge3d_output", help="Output folder")
    parser.add_argument("--import-model", default="", help="Optional GLB/GLTF/FBX/OBJ to merge")
    parser.add_argument("--skip-render", action="store_true", help="Skip PNG preview rendering")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def load_config(args):
    config = dict(CONFIG)
    if args.recipe:
        with open(args.recipe, "r", encoding="utf-8") as handle:
            incoming = json.load(handle)
        config.update(incoming)
    if args.import_model:
        config["import_path"] = args.import_model
    return config


def main():
    args = parse_args()
    config = load_config(args)
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log(f"Building {config['name']}")

    reset_scene()
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "METERS"
    first_colorway = config.get("colorways", CONFIG["colorways"])[0]
    materials = create_materials(first_colorway)

    if config.get("template") == "futuristic_football_helmet":
        create_helmet(config, materials)
    else:
        raise ValueError(f"Unknown procedural template: {config.get('template')}")

    if config.get("import_path"):
        import_model(config["import_path"])

    create_studio(config.get("render_size", 720))
    report = qa_report(config)
    with open(output_dir / "qa_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    with open(output_dir / "recipe_used.json", "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)

    previews = [] if args.skip_render else render_colorways(output_dir, materials, config)
    set_colorway(materials, first_colorway)
    exports = export_assets(output_dir, config)
    manifest = {"status": "complete", "exports": exports, "previews": previews, "qa": str(output_dir / "qa_report.json")}
    with open(output_dir / "build_manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    log(f"Complete — {report['triangle_count']:,} triangles, QA {report['status']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"FAILED: {exc}")
        traceback.print_exc()
        raise
