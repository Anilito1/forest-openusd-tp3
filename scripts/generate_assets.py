"""
Genere les assets .usda sources du TP3.

Chaque asset = 1 fichier .usda contenant un prim racine Xform du meme nom,
avec sa geometrie (UsdGeomMesh) et son materiau (UsdPreviewSurface).

Tous les meshes sont produits proceduralement (cone, cylindre, sphere, plan)
pour garantir la portabilite et eviter la dependance a des assets externes.

Usage : python scripts/generate_assets.py
Sortie : usda/assets/*.usda
"""
from __future__ import annotations

import math
import os
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "usda", "assets")
os.makedirs(OUT_DIR, exist_ok=True)


# ----------------------------- Mesh helpers ---------------------------------

def _set_mesh(prim_path, stage, points, face_counts, face_indices, translate=(0, 0, 0)):
    mesh = UsdGeom.Mesh.Define(stage, prim_path)
    mesh.CreatePointsAttr([Gf.Vec3f(*p) for p in points])
    mesh.CreateFaceVertexCountsAttr(face_counts)
    mesh.CreateFaceVertexIndicesAttr(face_indices)
    mesh.CreateSubdivisionSchemeAttr("none")
    if translate != (0, 0, 0):
        mesh.AddTranslateOp().Set(Gf.Vec3d(*translate))
    return mesh


def make_box(stage, path, w, h, d, translate=(0, 0, 0)):
    hx, hy, hz = w / 2, h / 2, d / 2
    pts = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    counts = [4] * 6
    idx = [
        0, 1, 2, 3,  # back
        4, 7, 6, 5,  # front
        0, 4, 5, 1,  # bottom
        2, 6, 7, 3,  # top
        0, 3, 7, 4,  # left
        1, 5, 6, 2,  # right
    ]
    return _set_mesh(path, stage, pts, counts, idx, translate)


def make_cylinder(stage, path, radius, height, segs=16, translate=(0, 0, 0)):
    pts = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        x, z = radius * math.cos(a), radius * math.sin(a)
        pts.append((x, 0, z))
        pts.append((x, height, z))
    bot_center = len(pts); pts.append((0, 0, 0))
    top_center = len(pts); pts.append((0, height, 0))

    counts = []
    idx = []
    for i in range(segs):
        b0 = 2 * i
        b1 = 2 * ((i + 1) % segs)
        t0 = b0 + 1
        t1 = b1 + 1
        counts.append(4)
        idx.extend([b0, b1, t1, t0])
        counts.append(3)
        idx.extend([bot_center, b1, b0])
        counts.append(3)
        idx.extend([top_center, t0, t1])
    return _set_mesh(path, stage, pts, counts, idx, translate)


def make_cone(stage, path, radius, height, segs=16, translate=(0, 0, 0)):
    pts = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        pts.append((radius * math.cos(a), 0, radius * math.sin(a)))
    apex = len(pts); pts.append((0, height, 0))
    base_c = len(pts); pts.append((0, 0, 0))

    counts = []
    idx = []
    for i in range(segs):
        b0 = i
        b1 = (i + 1) % segs
        counts.append(3)
        idx.extend([b0, b1, apex])
        counts.append(3)
        idx.extend([base_c, b1, b0])
    return _set_mesh(path, stage, pts, counts, idx, translate)


def make_sphere(stage, path, radius, lat=10, lon=14, translate=(0, 0, 0)):
    pts = []
    pts.append((0, radius, 0))  # top
    for i in range(1, lat):
        phi = math.pi * i / lat
        y = radius * math.cos(phi)
        r = radius * math.sin(phi)
        for j in range(lon):
            a = 2 * math.pi * j / lon
            pts.append((r * math.cos(a), y, r * math.sin(a)))
    pts.append((0, -radius, 0))  # bottom
    top = 0
    bot = len(pts) - 1

    counts = []
    idx = []
    # top cap
    for j in range(lon):
        a = 1 + j
        b = 1 + (j + 1) % lon
        counts.append(3)
        idx.extend([top, a, b])
    # middle quads
    for i in range(lat - 2):
        row0 = 1 + i * lon
        row1 = 1 + (i + 1) * lon
        for j in range(lon):
            a0 = row0 + j
            a1 = row0 + (j + 1) % lon
            b0 = row1 + j
            b1 = row1 + (j + 1) % lon
            counts.append(4)
            idx.extend([a0, a1, b1, b0])
    # bottom cap
    last_row = 1 + (lat - 2) * lon
    for j in range(lon):
        a = last_row + j
        b = last_row + (j + 1) % lon
        counts.append(3)
        idx.extend([bot, b, a])
    return _set_mesh(path, stage, pts, counts, idx, translate)


def make_plane(stage, path, w, d, translate=(0, 0, 0)):
    hx, hz = w / 2, d / 2
    pts = [(-hx, 0, -hz), (hx, 0, -hz), (hx, 0, hz), (-hx, 0, hz)]
    return _set_mesh(path, stage, pts, [4], [0, 1, 2, 3], translate)


# --------------------------- Material helper --------------------------------

def make_material(stage, mat_path, diffuse, roughness=0.7, metallic=0.0):
    mat = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, mat_path + "/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*diffuse))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
    shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def bind(stage, geom_path, mat_path):
    prim = stage.GetPrimAtPath(geom_path)
    mat = UsdShade.Material(stage.GetPrimAtPath(mat_path))
    UsdShade.MaterialBindingAPI(prim).Bind(mat)


# ------------------------------ Builders ------------------------------------

def new_stage(filename, root_name):
    path = os.path.join(OUT_DIR, filename)
    stage = Usd.Stage.CreateNew(path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/" + root_name)
    stage.SetDefaultPrim(root.GetPrim())
    return stage, "/" + root_name, path


def save(stage, path):
    stage.GetRootLayer().Save()
    print(f"  -> {os.path.relpath(path, ROOT)}")


# ----- 1. TreePine -----
def build_tree_pine():
    stage, root, path = new_stage("TreePine.usda", "TreePine")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Trunk", (0.32, 0.20, 0.12), 0.85)
    make_material(stage, root + "/Materials/Mat_Foliage", (0.10, 0.32, 0.14), 0.80)
    make_cylinder(stage, root + "/Trunk", 0.18, 2.0, segs=12)
    bind(stage, root + "/Trunk", root + "/Materials/Mat_Trunk")
    make_cone(stage, root + "/FoliageBottom", 1.10, 1.4, segs=14, translate=(0, 1.6, 0))
    bind(stage, root + "/FoliageBottom", root + "/Materials/Mat_Foliage")
    make_cone(stage, root + "/FoliageMid", 0.85, 1.2, segs=14, translate=(0, 2.6, 0))
    bind(stage, root + "/FoliageMid", root + "/Materials/Mat_Foliage")
    make_cone(stage, root + "/FoliageTop", 0.55, 1.0, segs=14, translate=(0, 3.6, 0))
    bind(stage, root + "/FoliageTop", root + "/Materials/Mat_Foliage")
    save(stage, path)


# ----- 2. TreeOak -----
def build_tree_oak():
    stage, root, path = new_stage("TreeOak.usda", "TreeOak")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Trunk", (0.35, 0.22, 0.13), 0.85)
    make_material(stage, root + "/Materials/Mat_Foliage", (0.22, 0.42, 0.18), 0.75)
    make_cylinder(stage, root + "/Trunk", 0.28, 2.4, segs=14)
    bind(stage, root + "/Trunk", root + "/Materials/Mat_Trunk")
    sphere = make_sphere(stage, root + "/Crown", 1.5, lat=10, lon=16, translate=(0, 3.0, 0))
    sphere.AddScaleOp().Set(Gf.Vec3f(1.2, 0.9, 1.2))
    bind(stage, root + "/Crown", root + "/Materials/Mat_Foliage")
    save(stage, path)


# ----- 3. TreeBirch -----
def build_tree_birch():
    stage, root, path = new_stage("TreeBirch.usda", "TreeBirch")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Trunk", (0.92, 0.90, 0.85), 0.90)
    make_material(stage, root + "/Materials/Mat_Foliage", (0.45, 0.62, 0.28), 0.80)
    make_cylinder(stage, root + "/Trunk", 0.14, 3.2, segs=12)
    bind(stage, root + "/Trunk", root + "/Materials/Mat_Trunk")
    make_cone(stage, root + "/Foliage", 0.95, 1.6, segs=14, translate=(0, 2.8, 0))
    bind(stage, root + "/Foliage", root + "/Materials/Mat_Foliage")
    save(stage, path)


# ----- 4. RockBig -----
def build_rock_big():
    stage, root, path = new_stage("RockBig.usda", "RockBig")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Rock", (0.45, 0.43, 0.40), 0.95)
    s = make_sphere(stage, root + "/Body", 0.9, lat=8, lon=10)
    s.AddScaleOp().Set(Gf.Vec3f(1.4, 0.7, 1.1))
    bind(stage, root + "/Body", root + "/Materials/Mat_Rock")
    save(stage, path)


# ----- 5. RockSmall -----
def build_rock_small():
    stage, root, path = new_stage("RockSmall.usda", "RockSmall")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Rock", (0.55, 0.52, 0.48), 0.95)
    s = make_sphere(stage, root + "/Body", 0.35, lat=8, lon=10)
    s.AddScaleOp().Set(Gf.Vec3f(1.2, 0.8, 1.0))
    bind(stage, root + "/Body", root + "/Materials/Mat_Rock")
    save(stage, path)


# ----- 6. Bush -----
def build_bush():
    stage, root, path = new_stage("Bush.usda", "Bush")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Bush", (0.18, 0.38, 0.16), 0.80)
    for i, off in enumerate([(-0.25, 0.3, 0), (0.25, 0.35, -0.1), (0, 0.5, 0.15)]):
        s = make_sphere(stage, root + f"/Lobe_{i}", 0.45, lat=8, lon=10, translate=off)
        bind(stage, root + f"/Lobe_{i}", root + "/Materials/Mat_Bush")
    save(stage, path)


# ----- 7. Fern -----
def build_fern():
    stage, root, path = new_stage("Fern.usda", "Fern")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Fern", (0.20, 0.50, 0.20), 0.75)
    # 5 fronds arranged radially
    for i in range(5):
        angle = i * (360.0 / 5)
        frond = UsdGeom.Xform.Define(stage, root + f"/Frond_{i}")
        frond.AddRotateYOp().Set(angle)
        make_box(stage, root + f"/Frond_{i}/Blade", 0.05, 0.6, 0.4, translate=(0.0, 0.3, 0.2))
        bind(stage, root + f"/Frond_{i}/Blade", root + "/Materials/Mat_Fern")
    save(stage, path)


# ----- 8. Flower -----
def build_flower():
    stage, root, path = new_stage("Flower.usda", "Flower")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Stem", (0.25, 0.45, 0.20), 0.85)
    make_material(stage, root + "/Materials/Mat_Petal", (0.92, 0.28, 0.35), 0.55)
    make_material(stage, root + "/Materials/Mat_Center", (1.00, 0.85, 0.20), 0.60)
    make_cylinder(stage, root + "/Stem", 0.03, 0.35, segs=8)
    bind(stage, root + "/Stem", root + "/Materials/Mat_Stem")
    make_sphere(stage, root + "/Petals", 0.10, lat=6, lon=10, translate=(0, 0.38, 0))
    bind(stage, root + "/Petals", root + "/Materials/Mat_Petal")
    make_sphere(stage, root + "/Center", 0.04, lat=6, lon=8, translate=(0, 0.40, 0))
    bind(stage, root + "/Center", root + "/Materials/Mat_Center")
    save(stage, path)


# ----- 9. FallenLog -----
def build_fallen_log():
    stage, root, path = new_stage("FallenLog.usda", "FallenLog")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Wood", (0.28, 0.18, 0.10), 0.90)
    log = make_cylinder(stage, root + "/Log", 0.25, 2.5, segs=12)
    log.AddRotateZOp().Set(90.0)  # horizontal
    log.AddTranslateOp().Set(Gf.Vec3d(1.25, 0.25, 0))
    bind(stage, root + "/Log", root + "/Materials/Mat_Wood")
    save(stage, path)


# ----- 10. Moss -----
def build_moss():
    stage, root, path = new_stage("Moss.usda", "Moss")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Moss", (0.22, 0.45, 0.18), 0.95)
    patch = make_sphere(stage, root + "/Patch", 0.45, lat=6, lon=10, translate=(0, 0.04, 0))
    patch.AddScaleOp().Set(Gf.Vec3f(1.4, 0.12, 1.4))
    bind(stage, root + "/Patch", root + "/Materials/Mat_Moss")
    save(stage, path)


# ----- 11. BirdNest -----
def build_bird_nest():
    stage, root, path = new_stage("BirdNest.usda", "BirdNest")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Twigs", (0.35, 0.22, 0.10), 0.90)
    make_material(stage, root + "/Materials/Mat_Egg", (0.95, 0.93, 0.85), 0.40)
    ring = make_sphere(stage, root + "/Ring", 0.30, lat=8, lon=14)
    ring.AddScaleOp().Set(Gf.Vec3f(1.0, 0.35, 1.0))
    bind(stage, root + "/Ring", root + "/Materials/Mat_Twigs")
    for i, off in enumerate([(-0.08, 0.10, 0.04), (0.07, 0.10, -0.05), (0.0, 0.10, 0.10)]):
        make_sphere(stage, root + f"/Egg_{i}", 0.06, lat=6, lon=8, translate=off)
        bind(stage, root + f"/Egg_{i}", root + "/Materials/Mat_Egg")
    save(stage, path)


# ----- 12. DeadTree -----
def build_dead_tree():
    stage, root, path = new_stage("DeadTree.usda", "DeadTree")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_DeadWood", (0.42, 0.36, 0.28), 0.95)
    make_cylinder(stage, root + "/Trunk", 0.20, 2.6, segs=12)
    bind(stage, root + "/Trunk", root + "/Materials/Mat_DeadWood")
    # 3 branches mortes
    for i, (rz, off_y, off_x) in enumerate([(35, 1.6, 0.6), (-30, 1.9, -0.5), (50, 2.2, 0.4)]):
        b = make_cylinder(stage, root + f"/Branch_{i}", 0.05, 0.9, segs=8,
                          translate=(off_x, off_y, 0))
        b.AddRotateZOp().Set(rz)
        bind(stage, root + f"/Branch_{i}", root + "/Materials/Mat_DeadWood")
    save(stage, path)


# ----- 13. Mushroom -----
def build_mushroom():
    stage, root, path = new_stage("Mushroom.usda", "Mushroom")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Stem", (0.95, 0.92, 0.85), 0.50)
    make_material(stage, root + "/Materials/Mat_Cap", (0.85, 0.18, 0.12), 0.45)
    make_material(stage, root + "/Materials/Mat_Spots", (0.98, 0.96, 0.92), 0.50)
    make_cylinder(stage, root + "/Stem", 0.05, 0.18, segs=10)
    bind(stage, root + "/Stem", root + "/Materials/Mat_Stem")
    cap = make_sphere(stage, root + "/Cap", 0.14, lat=8, lon=12, translate=(0, 0.20, 0))
    cap.AddScaleOp().Set(Gf.Vec3f(1.0, 0.65, 1.0))
    bind(stage, root + "/Cap", root + "/Materials/Mat_Cap")
    # 4 points blancs
    for i, off in enumerate([(0.07, 0.24, 0.04), (-0.05, 0.25, 0.06),
                              (0.04, 0.25, -0.07), (-0.08, 0.23, -0.03)]):
        make_sphere(stage, root + f"/Spot_{i}", 0.025, lat=4, lon=6, translate=off)
        bind(stage, root + f"/Spot_{i}", root + "/Materials/Mat_Spots")
    save(stage, path)


# ----- 14. Ground -----
def build_ground():
    stage, root, path = new_stage("Ground.usda", "Ground")
    UsdGeom.Scope.Define(stage, root + "/Materials")
    make_material(stage, root + "/Materials/Mat_Ground", (0.34, 0.28, 0.18), 0.95)
    make_plane(stage, root + "/Surface", 40.0, 40.0)
    bind(stage, root + "/Surface", root + "/Materials/Mat_Ground")
    save(stage, path)


# ------------------------------- Main ---------------------------------------

def main():
    print(f"Generating assets in {OUT_DIR}")
    build_tree_pine()
    build_tree_oak()
    build_tree_birch()
    build_rock_big()
    build_rock_small()
    build_bush()
    build_fern()
    build_flower()
    build_fallen_log()
    build_moss()
    build_bird_nest()
    build_dead_tree()
    build_mushroom()
    build_ground()
    print("Done.")


if __name__ == "__main__":
    main()
