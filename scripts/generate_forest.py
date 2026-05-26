"""
Genere Forest.usda : la scene principale composee uniquement de references
vers les assets de usda/assets/.

Aucun mesh n'est inline dans Forest.usda : chaque instance est un Xform avec
prepend references = @assets/X.usda@</X> + xformOp locaux (translate, rotateY,
scale). Quelques instances incluent des overrides pour demontrer la mecanique
(ex. chenes d'automne).

3 zones spatiales :
  - Zone_Dense    : foret fermee dominee par pins et chenes
  - Zone_Clearing : ouverture lumineuse, fleurs, fougeres, nid d'oiseau
  - Zone_Rocky    : rochers, troncs tombes, mousses, bouleaux

Usage : python scripts/generate_forest.py
Sortie : usda/Forest.usda
"""
from __future__ import annotations

import math
import os
import random
from pxr import Usd, UsdGeom, Sdf, Gf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "usda", "Forest.usda")
ASSETS_REL = "./assets"  # relatif a Forest.usda

random.seed(42)  # reproductible


def add_instance(stage, parent_path, name, asset_file, asset_prim,
                 translate, rotate_y=0.0, scale=1.0, custom_data=None,
                 override_foliage_color=None):
    """Cree un Xform enfant avec une reference vers un asset externe."""
    prim_path = f"{parent_path}/{name}"
    xform = UsdGeom.Xform.Define(stage, prim_path)
    prim = xform.GetPrim()

    refs = prim.GetReferences()
    refs.AddReference(
        assetPath=f"{ASSETS_REL}/{asset_file}",
        primPath=Sdf.Path(f"/{asset_prim}"),
    )

    xform.AddTranslateOp().Set(Gf.Vec3d(*translate))
    if abs(rotate_y) > 1e-6:
        xform.AddRotateYOp().Set(rotate_y)
    if abs(scale - 1.0) > 1e-6:
        xform.AddScaleOp().Set(Gf.Vec3f(scale, scale, scale))

    if custom_data:
        for k, v in custom_data.items():
            prim.SetCustomDataByKey(k, v)

    if override_foliage_color is not None:
        # over Materials/Mat_Foliage/Surface : diffuseColor
        spec = stage.OverridePrim(f"{prim_path}/Materials/Mat_Foliage/Surface")
        attr = spec.CreateAttribute("inputs:diffuseColor", Sdf.ValueTypeNames.Color3f)
        attr.Set(Gf.Vec3f(*override_foliage_color))


def rand_scale(base=1.0, jitter=0.2):
    return base * (1.0 - jitter + 2 * jitter * random.random())


def rand_rot():
    return random.uniform(0.0, 360.0)


def rand_pos(xmin, xmax, zmin, zmax, y=0.0):
    return (random.uniform(xmin, xmax), y, random.uniform(zmin, zmax))


# --------------------------------- Build ------------------------------------

def main():
    print(f"Generating {os.path.relpath(OUT_PATH, ROOT)}")
    stage = Usd.Stage.CreateNew(OUT_PATH)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    stage.GetRootLayer().documentation = (
        "TP3 ST2SNE - Scene de foret structuree avec references OpenUSD. "
        "Auteur: Anil BRAUN. Composition exclusivement par references vers "
        "des assets externes dans ./assets/. Variations locales (translate, "
        "rotateY, scale) sur chaque instance ; overrides ponctuels."
    )

    forest = UsdGeom.Xform.Define(stage, "/Forest")
    stage.SetDefaultPrim(forest.GetPrim())

    # Sol commun
    add_instance(stage, "/Forest", "Ground", "Ground.usda", "Ground",
                 translate=(0, 0, 0))

    # ----------------------------- Zone Dense -------------------------------
    UsdGeom.Xform.Define(stage, "/Forest/Zone_Dense")
    # 18 pins
    for i in range(18):
        pos = rand_pos(-18, -3, -10, 10)
        add_instance(stage, "/Forest/Zone_Dense", f"Pine_{i:02d}",
                     "TreePine.usda", "TreePine",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.25),
                     custom_data={"species": "pine", "zone": "dense"})
    # 10 chenes
    for i in range(10):
        pos = rand_pos(-18, -3, -10, 10)
        add_instance(stage, "/Forest/Zone_Dense", f"Oak_{i:02d}",
                     "TreeOak.usda", "TreeOak",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.2),
                     custom_data={"species": "oak", "zone": "dense"})
    # 6 buissons
    for i in range(6):
        pos = rand_pos(-18, -3, -10, 10)
        add_instance(stage, "/Forest/Zone_Dense", f"Bush_{i:02d}",
                     "Bush.usda", "Bush",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.3))
    # 4 fougeres
    for i in range(4):
        pos = rand_pos(-18, -3, -10, 10)
        add_instance(stage, "/Forest/Zone_Dense", f"Fern_{i:02d}",
                     "Fern.usda", "Fern",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.25))
    # 4 mousses au sol
    for i in range(4):
        pos = rand_pos(-18, -3, -10, 10)
        add_instance(stage, "/Forest/Zone_Dense", f"Moss_{i:02d}",
                     "Moss.usda", "Moss",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.4))

    # ----------------------------- Zone Clairiere ---------------------------
    UsdGeom.Xform.Define(stage, "/Forest/Zone_Clearing")
    # 4 arbres en peripherie (ouverture lumineuse au centre)
    perimeter = [(-2, 0, -6), (-2, 0, 6), (8, 0, -6), (8, 0, 6)]
    for i, (x, y, z) in enumerate(perimeter):
        x += random.uniform(-0.6, 0.6)
        z += random.uniform(-0.6, 0.6)
        asset = "TreeOak.usda" if i % 2 == 0 else "TreeBirch.usda"
        prim_name = "TreeOak" if i % 2 == 0 else "TreeBirch"
        add_instance(stage, "/Forest/Zone_Clearing", f"PerimeterTree_{i:02d}",
                     asset, prim_name,
                     translate=(x, y, z), rotate_y=rand_rot(),
                     scale=rand_scale(1.1, 0.15))
    # 2 chenes "automne" - DEMONSTRATION D'OVERRIDE
    add_instance(stage, "/Forest/Zone_Clearing", "AutumnOak_00",
                 "TreeOak.usda", "TreeOak",
                 translate=(3.5, 0, -2.5), rotate_y=120,
                 scale=1.0,
                 override_foliage_color=(0.85, 0.45, 0.10),
                 custom_data={"variant": "autumn"})
    add_instance(stage, "/Forest/Zone_Clearing", "AutumnOak_01",
                 "TreeOak.usda", "TreeOak",
                 translate=(5.5, 0, 1.0), rotate_y=200,
                 scale=0.9,
                 override_foliage_color=(0.92, 0.55, 0.05),
                 custom_data={"variant": "autumn"})
    # 20 fleurs dispersees
    for i in range(20):
        pos = rand_pos(-1, 7, -5, 5)
        add_instance(stage, "/Forest/Zone_Clearing", f"Flower_{i:02d}",
                     "Flower.usda", "Flower",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.3))
    # 8 fougeres
    for i in range(8):
        pos = rand_pos(-1, 7, -5, 5)
        add_instance(stage, "/Forest/Zone_Clearing", f"Fern_{i:02d}",
                     "Fern.usda", "Fern",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(0.9, 0.3))
    # 1 nid d'oiseau - vie animale (sur un perchoir simule)
    add_instance(stage, "/Forest/Zone_Clearing", "BirdNest_01",
                 "BirdNest.usda", "BirdNest",
                 translate=(3.0, 2.8, 1.5), rotate_y=15,
                 scale=1.0,
                 custom_data={"wildlife": "nest", "zone": "clearing"})

    # ----------------------------- Zone Rocheuse ----------------------------
    UsdGeom.Xform.Define(stage, "/Forest/Zone_Rocky")
    # 6 bouleaux dispersés
    for i in range(6):
        pos = rand_pos(8, 18, -10, 10)
        add_instance(stage, "/Forest/Zone_Rocky", f"Birch_{i:02d}",
                     "TreeBirch.usda", "TreeBirch",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.2))
    # 5 grands rochers
    for i in range(5):
        pos = rand_pos(8, 18, -10, 10)
        add_instance(stage, "/Forest/Zone_Rocky", f"RockBig_{i:02d}",
                     "RockBig.usda", "RockBig",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.4))
    # 8 petits rochers
    for i in range(8):
        pos = rand_pos(8, 18, -10, 10)
        add_instance(stage, "/Forest/Zone_Rocky", f"RockSmall_{i:02d}",
                     "RockSmall.usda", "RockSmall",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.5))
    # 3 troncs tombés
    for i in range(3):
        pos = rand_pos(8, 18, -10, 10)
        add_instance(stage, "/Forest/Zone_Rocky", f"FallenLog_{i:02d}",
                     "FallenLog.usda", "FallenLog",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.0, 0.3))
    # 5 patchs de mousse
    for i in range(5):
        pos = rand_pos(8, 18, -10, 10)
        add_instance(stage, "/Forest/Zone_Rocky", f"Moss_{i:02d}",
                     "Moss.usda", "Moss",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(1.1, 0.3))
    # 3 fougeres
    for i in range(3):
        pos = rand_pos(8, 18, -10, 10)
        add_instance(stage, "/Forest/Zone_Rocky", f"Fern_{i:02d}",
                     "Fern.usda", "Fern",
                     translate=pos, rotate_y=rand_rot(),
                     scale=rand_scale(0.9, 0.25))

    stage.GetRootLayer().Save()
    n_instances = sum(1 for p in stage.Traverse()
                      if p.GetTypeName() == "Xform" and p.HasAuthoredReferences())
    print(f"  Forest.usda : {n_instances} instances (toutes par reference)")
    print(f"  Sortie : {os.path.relpath(OUT_PATH, ROOT)}")


if __name__ == "__main__":
    main()
