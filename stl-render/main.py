#!/usr/bin/env python3
"""
render_stl_open3d.py

Render an STL file to solid grayscale PNG images using Open3D offscreen rendering.
Supports rendering the object only up to selected completed layer numbers.

Key behavior:
- Keeps STL in original units for layer clipping
- Uses trimesh slice_plane(..., cap=True) for clean capped cuts
- Uses Open3D only for rendering
- Keeps the original defaultLit rendering style
- Normalizes only for rendering, not for clipping

Examples:
    python render_stl_open3d.py open-faced-cube.stl --out render_out
    python render_stl_open3d.py open-faced-cube.stl --out render_out --single
    python render_stl_open3d.py open-faced-cube.stl --out render_out --layer-number 50 --layer-height 0.2 --single
    python render_stl_open3d.py open-faced-cube.stl --out render_out --layers 10 20 30 40 50 --layer-height 0.2 --single
"""

from __future__ import annotations

import os
#os.environ.setdefault("OPEN3D_CPU_RENDERING", "true")
os.environ.setdefault("EGL_PLATFORM", "surfaceless")

import argparse
import traceback
import math
import time
from pathlib import Path

import numpy as np
import open3d as o3d
import trimesh
from PIL import Image, ImageDraw, ImageOps

enable_trace = True
enable_debug = True
enable_info = True

NANOSECOND = 1000000000

def log_trace(msg: str):
    if enable_trace:
        print(f"[TRACE] {msg}")

def log_debug(msg: str):
    if enable_debug:
        print(f"[DEBUG] {msg}")

def log_info(msg: str):
    if enable_log:
        print(f"[ INFO] {msg}")

def load_mesh(path: str | Path) -> o3d.geometry.TriangleMesh:
    mesh = o3d.io.read_triangle_mesh(str(path))

    if mesh.is_empty():
        raise RuntimeError(f"Failed to load mesh from {path}")

    mesh.compute_triangle_normals()
    mesh.compute_vertex_normals()

    return mesh

def prepare_mesh_for_render(
    mesh: o3d.geometry.TriangleMesh,
) -> tuple[o3d.geometry.TriangleMesh, np.ndarray, float]:
    """
    Center and scale a copy of the mesh only for rendering/camera framing.
    Do NOT use this for clipping.

    Returns:
        render_mesh   : normalized copy of the mesh
        render_center : original bbox center before normalization
        render_extent : max original bbox extent before normalization
    """
    render_mesh = o3d.geometry.TriangleMesh(mesh)

    bbox = render_mesh.get_axis_aligned_bounding_box()
    center = bbox.get_center()
    extent = np.max(bbox.get_extent())

    render_mesh.translate(-center)

    if extent > 0:
        render_mesh.scale(1.0 / extent, center=(0.0, 0.0, 0.0))

    render_mesh.compute_triangle_normals()
    # render_mesh.compute_vertex_normals()

    return render_mesh, np.asarray(center, dtype=float), float(extent)

def get_printer_cameras() -> dict[str, dict[str, np.ndarray | float]]:
    """
    Five fixed cameras:
      - one at each top corner of the printer
      - one top-down camera in the center

    These are defined in normalized render space, where the object is centered
    near the origin and scaled to roughly fit inside [-0.5, 0.5].
    """
    target = np.array([0.0, 0.0, -0.05], dtype=float)
    up = np.array([0.0, 0.0, 1.0], dtype=float)

    return {
        "front_left_top": {
            "eye": np.array([-1.35, -1.35, 1.15], dtype=float),
            "target": target,
            "up": up,
            "fov": 55.0,
        },
        "front_right_top": {
            "eye": np.array([1.35, -1.35, 1.15], dtype=float),
            "target": target,
            "up": up,
            "fov": 55.0,
        },
        "back_left_top": {
            "eye": np.array([-1.35, 1.35, 1.15], dtype=float),
            "target": target,
            "up": up,
            "fov": 55.0,
        },
        "back_right_top": {
            "eye": np.array([1.35, 1.35, 1.15], dtype=float),
            "target": target,
            "up": up,
            "fov": 55.0,
        },
        "top_center": {
            "eye": np.array([0.0, 0.0, 2.0], dtype=float),
            "target": np.array([0.0, 0.0, 0.0], dtype=float),
            "up": np.array([0.0, 1.0, 0.0], dtype=float),
            "fov": 42.0,
        },
    }

def open3d_to_trimesh(mesh: o3d.geometry.TriangleMesh) -> trimesh.Trimesh:
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.triangles, dtype=np.int64)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=True)


def trimesh_to_open3d(mesh_tm: trimesh.Trimesh) -> o3d.geometry.TriangleMesh:
    mesh_o3d = o3d.geometry.TriangleMesh()
    mesh_o3d.vertices = o3d.utility.Vector3dVector(np.asarray(mesh_tm.vertices, dtype=np.float64))
    mesh_o3d.triangles = o3d.utility.Vector3iVector(np.asarray(mesh_tm.faces, dtype=np.int32))
    mesh_o3d.remove_duplicated_vertices()
    mesh_o3d.remove_degenerate_triangles()
    mesh_o3d.remove_unreferenced_vertices()
    mesh_o3d.compute_triangle_normals()
    return mesh_o3d

def clip_mesh_at_layer(
    mesh: o3d.geometry.TriangleMesh,
    layer_number: int,
    layer_height: float,
) -> tuple[o3d.geometry.TriangleMesh, float]:
    """
    Clip the mesh at:
        z_cut = z_min + layer_number * layer_height

    Keeps geometry with z <= z_cut, and caps the cut cleanly.
    """

    if layer_number <= 0:
        raise ValueError("layer_number must be >= 0")

    bbox = mesh.get_axis_aligned_bounding_box()
    z_min = float(bbox.min_bound[2])
    z_max = float(bbox.max_bound[2])

    z_cut = z_min + layer_number * layer_height

    log_debug(f"layer={layer_number} | z_min={z_min:.3f} | z_cut={z_cut:.3f} | z_max={z_max:.3f}")

    if z_cut <= z_min:
        return o3d.geometry.TriangleMesh(), z_cut

    if z_cut >= z_max:
        full_mesh = o3d.geometry.TriangleMesh(mesh)
        full_mesh.compute_triangle_normals()

        return full_mesh, z_cut

    mesh_tm = open3d_to_trimesh(mesh)

    # slice_plane keeps the positive-normal side.
    # To keep everything with z <= z_cut, use downward normal.
    clipped_tm = mesh_tm.slice_plane(
        plane_origin=np.array([0.0, 0.0, z_cut], dtype=np.float64),
        plane_normal=np.array([0.0, 0.0, -1.0], dtype=np.float64),
        cap=True,
    )

    if clipped_tm is None or len(clipped_tm.faces) == 0:
        return o3d.geometry.TriangleMesh(), z_cut

    clipped_tm.remove_unreferenced_vertices()

    return trimesh_to_open3d(clipped_tm), z_cut

def make_renderer(width: int, height: int, bg=(1.0, 1.0, 1.0, 1.0)) -> o3d.visualizaion.render.OffscreenRenderer:
    renderer = o3d.visualization.rendering.OffscreenRenderer(width, height)
    renderer.scene.set_background(bg)
    return renderer

def render_view_with_renderer(
    renderer,
    mesh: o3d.geometry.TriangleMesh,
    out_path: Path,
    width: int,
    height: int,
    camera: dict[str, np.ndarray | float],
):
    if mesh.is_empty():
        Image.new("RGB", (width, height), "white").save(out_path)
        return

    render_mesh, _, _ = prepare_mesh_for_render(mesh)

    material = o3d.visualization.rendering.MaterialRecord()
    material.shader = "defaultLit"
    material.base_color = (0.75, 0.75, 0.75, 1.0)
    material.base_roughness = 1.0
    material.base_reflectance = 0.0

    renderer.scene.add_geometry("mesh", render_mesh, material)

    eye = np.asarray(camera["eye"], dtype=float)
    target = np.asarray(camera["target"], dtype=float)
    up = np.asarray(camera["up"], dtype=float)
    fov_deg = float(camera["fov"])

    renderer.setup_camera(fov_deg, target, eye, up)

    img = renderer.render_to_image()
    o3d.io.write_image(str(out_path), img)

    renderer.scene.remove_geometry("mesh")

def make_contact_sheet(image_paths: list[Path], out_path: Path, cols: int = 3, pad: int = 20):
    imgs = [Image.open(p).convert("RGB") for p in image_paths]

    if not imgs:
        return

    max_w = max(im.width for im in imgs)
    max_h = max(im.height for im in imgs)

    tiles = []

    for path, im in zip(image_paths, imgs):
        tile = Image.new("RGB", (max_w, max_h + 40), "white")
        contained = ImageOps.contain(im, (max_w, max_h))
        x = (max_w - contained.width) // 2
        y = (max_h - contained.height) // 2
        tile.paste(contained, (x, y))

        draw = ImageDraw.Draw(tile)
        draw.text((10, max_h + 10), path.stem, fill="black")
        tiles.append(tile)

    rows = math.ceil(len(tiles) / cols)
    sheet_w = cols * max_w + (cols + 1) * pad
    sheet_h = rows * (max_h + 40) + (rows + 1) * pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")

    for i, tile in enumerate(tiles):
        r = i // cols
        c = i % cols
        x = pad + c * (max_w + pad)
        y = pad + r * (max_h + 40 + pad)
        sheet.paste(tile, (x, y))

    sheet.save(out_path)

def parse_args():
    p = argparse.ArgumentParser(description="Render STL to solid grayscale CAD-like PNGs with Open3D.")
    p.add_argument("stl", help="Path to STL file")
    p.add_argument("--out", default="render_out", help="Output folder")
    p.add_argument("--width", type=int, default=800, help="Image width")
    p.add_argument("--height", type=int, default=800, help="Image height")
    p.add_argument("--single", action="store_true", help="Render only one screenshot-like angle")

    p.add_argument("--layer-height", type=float, help="Layer height in STL units, usually mm")
    p.add_argument("--layer-number", type=int, help="Render one completed layer number")
    p.add_argument("--layers", type=int, nargs="+", help="Render several completed layer numbers")
    p.add_argument(
        "--camera",
        choices=[
            "front_left_top",
            "front_right_top",
            "back_left_top",
            "back_right_top",
            "top_center",
        ],
        help="Render only one named printer camera view",
    )

    return p.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.layer_number is not None and args.layers is not None:
        raise ValueError("Use either --layer-number or --layers, not both.")

    if (args.layer_number is not None or args.layers is not None) and args.layer_height is None:
        raise ValueError("--layer-height is required when using --layer-number or --layers.")

    base_mesh = load_mesh(args.stl)
    all_cameras = get_printer_cameras()

    if args.camera is not None:
        cameras = {args.camera: all_cameras[args.camera]}
    elif args.single:
        cameras = {
            "front_left_top": all_cameras["front_left_top"],
        }
    else:
        cameras = all_cameras

    start = time.monotonic_ns()

    renderer = make_renderer(args.width, args.height)

    end = time.monotonic_ns()
    duration = end - start
    duration_f = duration / NANOSECOND

    log_trace(f"render init: {duration} nsec {duration_f:.9f} sec")

    try:
        # Original full-geometry rendering
        if args.layer_number is None and args.layers is None:
            image_paths = []

            for name, camera in cameras.items():
                out_path = out_dir / f"{name}.png"
                render_view_with_renderer(
                    renderer=renderer,
                    mesh=base_mesh,
                    out_path=out_path,
                    width=args.width,
                    height=args.height,
                    camera=camera,
                )
                image_paths.append(out_path)
                print(f"Saved {out_path}")

            if len(image_paths) > 1:
                sheet_path = out_dir / "contact_sheet.png"
                make_contact_sheet(image_paths, sheet_path)
                print(f"Saved {sheet_path}")
            return

        # Layer-based rendering
        requested_layers = [args.layer_number] if args.layer_number is not None else args.layers

        log_debug(f"requested layers: {requested_layers}")

        for layer in requested_layers:
            start = time.monotonic_ns()

            clipped_mesh, z_cut = clip_mesh_at_layer(base_mesh, layer, args.layer_height)

            end = time.monotonic_ns()
            duration = end - start
            duration_f = duration / 1000000000

            log_trace(f"clip mesh time: {duration} nsec {duration_f:.9f} sec")

            layer_paths = []

            for name, camera in cameras.items():
                out_path = out_dir / f"layer_{layer:04d}_{name}.png"

                start = time.monotonic_ns()

                render_view_with_renderer(
                    renderer=renderer,
                    mesh=clipped_mesh,
                    out_path=out_path,
                    width=args.width,
                    height=args.height,
                    camera=camera,
                )

                end = time.monotonic_ns()
                duration = end - start
                duration_f = duration / NANOSECOND

                log_trace(f"render view: {duration} nsec {duration_f:.9f} sec")

                layer_paths.append(out_path)

                print(f"Saved {out_path} (z_cut={z_cut:.4f})")

            if len(layer_paths) > 1:
                sheet_path = out_dir / f"layer_{layer:04d}_contact_sheet.png"
                make_contact_sheet(layer_paths, sheet_path)
                print(f"Saved {sheet_path}")
    except Exception as err:
        print(f"failed to create output images for stl file")

        traceback.print_exception(err)
    finally:
        del renderer

if __name__ == "__main__":
    main()
