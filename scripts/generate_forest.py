"""
Genere Forest.usda : la scene principale composee uniquement de references
vers les assets de usda/assets/.

Aucun mesh n'est inline dans Forest.usda : chaque instance est un Xform avec
prepend references = @./assets/X.usda@</X> + xformOp locaux (translate,
rotateY, rotateZ, scale). Quelques instances incluent des overrides de
materiau pour demontrer la mecanique.

Composition spatiale :
  - Zone_Dense    : foret fermee a gauche, dominee par pins et chenes
                    + 1 chene "Patriarche" geant comme point focal
                    + 3 jeunes pousses pres du chemin
  - Zone_Clearing : ouverture lumineuse au centre
                    + parterres de fleurs (clusters)
                    + fairy ring de 8 champignons
                    + 4 chenes "automne" en peripherie (overrides couleur)
                    + 1 nid d'oiseau perche sur un arbre
  - Zone_Rocky    : zone rocailleuse a droite
                    + cairn (cercle de 6 rochers empiles)
                    + hollow log (tronc tombe entoure de mousses et champignons)
                    + 3 arbres morts cluster
                    + bouleaux dispersees
  - Path          : chemin sinusoidal traversant les 3 zones
                    + 16 petits cailloux jalonnent le tracé
                    + zone d'exclusion 1.5m autour du chemin (pas d'arbres)

Anti-chevauchement : rejection sampling avec distance min par categorie.
Tilt organique : rotateZ aleatoire +/-3 deg sur arbres et buissons.

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
ASSETS_REL = "./assets"

random.seed(2026)  # reproductible


# ============================== Path tracing ================================

def path_z(x):
    """Trace sinusoidal du chemin. Pour un x dans [-18, 18], retourne z."""
    t = (x + 18.0) / 36.0  # t ∈ [0, 1]
    return math.sin(t * math.pi * 1.5) * 4.0


def dist_to_path(x, z, samples=80):
    """Distance approximative d'un point (x,z) au trace du chemin."""
    best = float("inf")
    for i in range(samples + 1):
        px = -18.0 + 36.0 * (i / samples)
        pz = path_z(px)
        d = math.hypot(x - px, z - pz)
        if d < best:
            best = d
    return best


# ========================= Anti-overlap sampler =============================

class Sampler:
    """Rejection sampler avec distance min."""
    def __init__(self):
        self.placed = []  # (x, z, exclusion_radius)

    def try_place(self, x, z, exclusion):
        for px, pz, pr in self.placed:
            if math.hypot(x - px, z - pz) < max(exclusion, pr):
                return False
        self.placed.append((x, z, exclusion))
        return True

    def sample(self, xmin, xmax, zmin, zmax, exclusion,
               path_exclusion=0.0, max_tries=80):
        for _ in range(max_tries):
            x = random.uniform(xmin, xmax)
            z = random.uniform(zmin, zmax)
            if path_exclusion > 0 and dist_to_path(x, z) < path_exclusion:
                continue
            if self.try_place(x, z, exclusion):
                return (x, 0.0, z)
        return None  # echec : zone trop dense


# ========================== Instance helpers ================================

def add_instance(stage, parent_path, name, asset_file, asset_prim,
                 translate, rotate_y=0.0, rotate_z=0.0,
                 scale=1.0, custom_data=None,
                 override_foliage_color=None,
                 override_bush_color=None):
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
    if abs(rotate_z) > 1e-6:
        xform.AddRotateZOp().Set(rotate_z)
    if abs(scale - 1.0) > 1e-6:
        xform.AddScaleOp().Set(Gf.Vec3f(scale, scale, scale))

    if custom_data:
        for k, v in custom_data.items():
            prim.SetCustomDataByKey(k, v)

    if override_foliage_color is not None:
        spec = stage.OverridePrim(f"{prim_path}/Materials/Mat_Foliage/Surface")
        attr = spec.CreateAttribute("inputs:diffuseColor", Sdf.ValueTypeNames.Color3f)
        attr.Set(Gf.Vec3f(*override_foliage_color))

    if override_bush_color is not None:
        spec = stage.OverridePrim(f"{prim_path}/Materials/Mat_Bush/Surface")
        attr = spec.CreateAttribute("inputs:diffuseColor", Sdf.ValueTypeNames.Color3f)
        attr.Set(Gf.Vec3f(*override_bush_color))


def rand_tilt():
    """Tilt organique +/- 3 deg sur Z."""
    return random.uniform(-3.0, 3.0)


def rand_scale(base, jitter):
    return base * (1.0 - jitter + 2 * jitter * random.random())


# ============================== Build =======================================

def main():
    print(f"Generating {os.path.relpath(OUT_PATH, ROOT)}")
    stage = Usd.Stage.CreateNew(OUT_PATH)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    stage.GetRootLayer().documentation = (
        "TP3 ST2SNE - Scene de foret structuree avec references OpenUSD. "
        "Auteur: Anil BRAUN. 3 zones (Dense / Clairiere / Rocheuse) reliees "
        "par un chemin sinusoidal. Points d'interet scenarises : patriarche, "
        "cairn, hollow log, fairy ring, bird nest perche. Composition par "
        "references, jamais par duplication ; overrides de couleur sur "
        "feuillages et buissons fleuris."
    )

    forest = UsdGeom.Xform.Define(stage, "/Forest")
    stage.SetDefaultPrim(forest.GetPrim())

    # Sol commun
    add_instance(stage, "/Forest", "Ground", "Ground.usda", "Ground",
                 translate=(0, 0, 0))

    sampler = Sampler()

    # ============================ Path ======================================
    UsdGeom.Xform.Define(stage, "/Forest/Path")
    # Cailloux le long du tracé (16 pierres)
    for i in range(16):
        x = -17.0 + 34.0 * (i / 15.0)
        z = path_z(x) + random.uniform(-0.25, 0.25)
        add_instance(stage, "/Forest/Path", f"Stone_{i:02d}",
                     "RockSmall.usda", "RockSmall",
                     translate=(x, 0, z),
                     rotate_y=random.uniform(0, 360),
                     scale=rand_scale(0.55, 0.3),
                     custom_data={"role": "path_marker"})
        sampler.placed.append((x, z, 0.4))

    # ============================ Zone Dense ================================
    UsdGeom.Xform.Define(stage, "/Forest/Zone_Dense")

    # Patriarche : chene geant central
    px, pz = -12.5, -1.0
    add_instance(stage, "/Forest/Zone_Dense", "Patriarch_Oak",
                 "TreeOak.usda", "TreeOak",
                 translate=(px, 0, pz),
                 rotate_y=random.uniform(0, 360),
                 rotate_z=rand_tilt(),
                 scale=1.85,
                 custom_data={"role": "patriarch", "age": "ancient"})
    sampler.placed.append((px, pz, 3.5))

    # 16 pins
    for i in range(16):
        pos = sampler.sample(-19, -3, -12, 12, exclusion=2.4, path_exclusion=1.8)
        if pos is None:
            break
        add_instance(stage, "/Forest/Zone_Dense", f"Pine_{i:02d}",
                     "TreePine.usda", "TreePine",
                     translate=pos, rotate_y=random.uniform(0, 360),
                     rotate_z=rand_tilt(),
                     scale=rand_scale(1.0, 0.25),
                     custom_data={"species": "pine", "zone": "dense"})

    # 9 chenes
    for i in range(9):
        pos = sampler.sample(-19, -3, -12, 12, exclusion=2.6, path_exclusion=1.8)
        if pos is None:
            break
        add_instance(stage, "/Forest/Zone_Dense", f"Oak_{i:02d}",
                     "TreeOak.usda", "TreeOak",
                     translate=pos, rotate_y=random.uniform(0, 360),
                     rotate_z=rand_tilt(),
                     scale=rand_scale(1.0, 0.2),
                     custom_data={"species": "oak", "zone": "dense"})

    # 3 jeunes pousses pres du chemin
    for i in range(3):
        pos = sampler.sample(-15, -5, -8, 8, exclusion=1.0, path_exclusion=0.8)
        if pos is None:
            continue
        asset = random.choice([("TreePine.usda", "TreePine"), ("TreeOak.usda", "TreeOak")])
        add_instance(stage, "/Forest/Zone_Dense", f"Sapling_{i:02d}",
                     asset[0], asset[1],
                     translate=pos, rotate_y=random.uniform(0, 360),
                     rotate_z=rand_tilt(),
                     scale=rand_scale(0.45, 0.15),
                     custom_data={"age": "young"})

    # 6 buissons (dont 2 fleuris via override)
    for i in range(6):
        pos = sampler.sample(-19, -3, -12, 12, exclusion=1.2, path_exclusion=1.2)
        if pos is None:
            break
        bush_color = None
        if i == 1:
            bush_color = (0.65, 0.30, 0.55)  # rose
        elif i == 4:
            bush_color = (0.85, 0.85, 0.80)  # blanc creme
        add_instance(stage, "/Forest/Zone_Dense", f"Bush_{i:02d}",
                     "Bush.usda", "Bush",
                     translate=pos, rotate_y=random.uniform(0, 360),
                     scale=rand_scale(1.0, 0.3),
                     override_bush_color=bush_color,
                     custom_data={"flowering": bool(bush_color)})

    # 5 fougeres
    for i in range(5):
        pos = sampler.sample(-19, -3, -12, 12, exclusion=0.7, path_exclusion=1.0)
        if pos is None:
            break
        add_instance(stage, "/Forest/Zone_Dense", f"Fern_{i:02d}",
                     "Fern.usda", "Fern",
                     translate=pos, rotate_y=random.uniform(0, 360),
                     scale=rand_scale(1.0, 0.25))

    # 5 patchs de mousse
    for i in range(5):
        pos = sampler.sample(-19, -3, -12, 12, exclusion=0.6, path_exclusion=0.8)
        if pos is None:
            break
        add_instance(stage, "/Forest/Zone_Dense", f"Moss_{i:02d}",
                     "Moss.usda", "Moss",
                     translate=pos, rotate_y=random.uniform(0, 360),
                     scale=rand_scale(1.0, 0.4))

    # ============================ Zone Clearing =============================
    UsdGeom.Xform.Define(stage, "/Forest/Zone_Clearing")

    # 4 arbres en peripherie de la clairiere
    perimeter = [(-2.5, 0, -6.5), (-2.5, 0, 6.5),
                 (8.5, 0, -6.0), (8.5, 0, 6.0)]
    for i, (x, y, z) in enumerate(perimeter):
        x += random.uniform(-0.4, 0.4)
        z += random.uniform(-0.4, 0.4)
        asset = ("TreeOak.usda", "TreeOak") if i % 2 == 0 else ("TreeBirch.usda", "TreeBirch")
        add_instance(stage, "/Forest/Zone_Clearing", f"PerimeterTree_{i:02d}",
                     asset[0], asset[1],
                     translate=(x, y, z), rotate_y=random.uniform(0, 360),
                     rotate_z=rand_tilt(),
                     scale=rand_scale(1.1, 0.15))
        sampler.placed.append((x, z, 2.0))

    # 4 chenes "automne" - overrides de couleur
    autumn_palette = [(0.85, 0.45, 0.10), (0.92, 0.55, 0.05),
                      (0.78, 0.32, 0.08), (0.90, 0.65, 0.15)]
    autumn_positions = [(3.0, -3.5), (5.5, -1.0), (1.5, 2.5), (6.5, 3.0)]
    for i, (color, (x, z)) in enumerate(zip(autumn_palette, autumn_positions)):
        if not sampler.try_place(x, z, 1.8):
            continue
        add_instance(stage, "/Forest/Zone_Clearing", f"AutumnOak_{i:02d}",
                     "TreeOak.usda", "TreeOak",
                     translate=(x, 0, z),
                     rotate_y=random.uniform(0, 360),
                     rotate_z=rand_tilt(),
                     scale=rand_scale(0.95, 0.15),
                     override_foliage_color=color,
                     custom_data={"variant": "autumn"})

    # 3 parterres de fleurs (clusters de 5-7)
    bed_centers = [(2.0, 4.5), (6.0, -2.5), (3.5, 0.5)]
    for b, (cx, cz) in enumerate(bed_centers):
        n_flowers = random.randint(5, 7)
        for i in range(n_flowers):
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0.15, 0.85)
            x = cx + r * math.cos(angle)
            z = cz + r * math.sin(angle)
            add_instance(stage, "/Forest/Zone_Clearing",
                         f"Flower_bed{b}_{i:02d}",
                         "Flower.usda", "Flower",
                         translate=(x, 0, z),
                         rotate_y=random.uniform(0, 360),
                         scale=rand_scale(1.0, 0.3),
                         custom_data={"bed": b})

    # 6 fougeres dispersees
    for i in range(6):
        pos = sampler.sample(-1, 8, -6, 6, exclusion=0.6, path_exclusion=0.8)
        if pos is None:
            break
        add_instance(stage, "/Forest/Zone_Clearing", f"Fern_{i:02d}",
                     "Fern.usda", "Fern",
                     translate=pos, rotate_y=random.uniform(0, 360),
                     scale=rand_scale(0.95, 0.3))

    # Fairy ring : 8 champignons en cercle (rayon 1.1)
    fairy_cx, fairy_cz = 3.5, -4.5
    for i in range(8):
        ang = 2 * math.pi * i / 8
        x = fairy_cx + 1.1 * math.cos(ang)
        z = fairy_cz + 1.1 * math.sin(ang)
        add_instance(stage, "/Forest/Zone_Clearing", f"FairyRing_Mushroom_{i:02d}",
                     "Mushroom.usda", "Mushroom",
                     translate=(x, 0, z),
                     rotate_y=random.uniform(0, 360),
                     scale=rand_scale(1.0, 0.2),
                     custom_data={"role": "fairy_ring"})

    # 1 nid d'oiseau perche sur l'arbre periphery_01 (chene)
    add_instance(stage, "/Forest/Zone_Clearing", "BirdNest_perched",
                 "BirdNest.usda", "BirdNest",
                 translate=(-2.5 + 0.4, 2.8, 6.5),
                 rotate_y=20,
                 custom_data={"wildlife": "nest", "perched_on": "PerimeterTree_01"})

    # ============================ Zone Rocky ================================
    UsdGeom.Xform.Define(stage, "/Forest/Zone_Rocky")

    # 3 arbres morts clusterisés (drame visuel) - PLACES EN PREMIER (forced)
    dead_cluster = [(15.0, -8.0), (16.2, -7.2), (14.5, -7.0)]
    for i, (x, z) in enumerate(dead_cluster):
        add_instance(stage, "/Forest/Zone_Rocky", f"DeadTree_{i:02d}",
                     "DeadTree.usda", "DeadTree",
                     translate=(x, 0, z),
                     rotate_y=random.uniform(0, 360),
                     rotate_z=random.uniform(-8, 8),
                     scale=rand_scale(1.0, 0.2),
                     custom_data={"role": "dead_cluster"})
        sampler.placed.append((x, z, 1.6))

    # 5 bouleaux dispersées (apres dead cluster)
    for i in range(5):
        pos = sampler.sample(9, 19, -12, 12, exclusion=2.5, path_exclusion=1.8)
        if pos is None:
            break
        override = None
        if i in (1, 3):
            override = (0.25, 0.40, 0.18)  # feuillage plus sombre
        add_instance(stage, "/Forest/Zone_Rocky", f"Birch_{i:02d}",
                     "TreeBirch.usda", "TreeBirch",
                     translate=pos, rotate_y=random.uniform(0, 360),
                     rotate_z=rand_tilt(),
                     scale=rand_scale(1.0, 0.2),
                     override_foliage_color=override,
                     custom_data={"variant": "dark" if override else "standard"})

    # Cairn : cercle de 6 RockSmall empilés (point focal)
    cairn_cx, cairn_cz = 14.0, 4.0
    cairn_pattern = [
        (cairn_cx, 0.0, cairn_cz, 1.4),       # base centre
        (cairn_cx + 0.6, 0.0, cairn_cz + 0.3, 1.0),
        (cairn_cx - 0.5, 0.0, cairn_cz + 0.4, 1.1),
        (cairn_cx + 0.1, 0.0, cairn_cz - 0.5, 1.0),
        (cairn_cx + 0.2, 0.55, cairn_cz + 0.1, 0.9),  # niveau 2
        (cairn_cx - 0.1, 1.05, cairn_cz + 0.05, 0.75),  # sommet
    ]
    for i, (x, y, z, s) in enumerate(cairn_pattern):
        add_instance(stage, "/Forest/Zone_Rocky", f"Cairn_Stone_{i:02d}",
                     "RockSmall.usda", "RockSmall",
                     translate=(x, y, z),
                     rotate_y=random.uniform(0, 360),
                     scale=s,
                     custom_data={"role": "cairn"})
    sampler.placed.append((cairn_cx, cairn_cz, 1.8))

    # Hollow log : tronc tombe + 3 mousses + 4 champignons + 1 fern
    hl_cx, hl_cz = 12.5, -3.0
    add_instance(stage, "/Forest/Zone_Rocky", "HollowLog",
                 "FallenLog.usda", "FallenLog",
                 translate=(hl_cx, 0, hl_cz),
                 rotate_y=35,
                 scale=1.1,
                 custom_data={"role": "hollow_log"})
    for i in range(3):
        x = hl_cx + random.uniform(-1.0, 1.5)
        z = hl_cz + random.uniform(-0.8, 0.8)
        add_instance(stage, "/Forest/Zone_Rocky", f"HollowLog_Moss_{i:02d}",
                     "Moss.usda", "Moss",
                     translate=(x, 0, z),
                     rotate_y=random.uniform(0, 360),
                     scale=rand_scale(1.0, 0.3))
    for i in range(4):
        x = hl_cx + random.uniform(-1.2, 1.2)
        z = hl_cz + random.uniform(-0.6, 0.6)
        add_instance(stage, "/Forest/Zone_Rocky", f"HollowLog_Mushroom_{i:02d}",
                     "Mushroom.usda", "Mushroom",
                     translate=(x, 0, z),
                     rotate_y=random.uniform(0, 360),
                     scale=rand_scale(1.1, 0.2))
    add_instance(stage, "/Forest/Zone_Rocky", "HollowLog_Fern",
                 "Fern.usda", "Fern",
                 translate=(hl_cx + 1.4, 0, hl_cz - 0.4),
                 rotate_y=random.uniform(0, 360),
                 scale=1.1)
    sampler.placed.append((hl_cx, hl_cz, 2.5))

    # 4 grands rochers disperses
    for i in range(4):
        pos = sampler.sample(9, 19, -12, 12, exclusion=1.5, path_exclusion=1.5)
        if pos is None:
            break
        # quelques rochers semi-enfouis (y negatif leger)
        y = -0.2 if i % 2 == 0 else 0.0
        add_instance(stage, "/Forest/Zone_Rocky", f"RockBig_{i:02d}",
                     "RockBig.usda", "RockBig",
                     translate=(pos[0], y, pos[2]),
                     rotate_y=random.uniform(0, 360),
                     scale=rand_scale(1.0, 0.4))

    # 6 petits rochers
    for i in range(6):
        pos = sampler.sample(9, 19, -12, 12, exclusion=0.7, path_exclusion=1.0)
        if pos is None:
            break
        add_instance(stage, "/Forest/Zone_Rocky", f"RockSmall_{i:02d}",
                     "RockSmall.usda", "RockSmall",
                     translate=pos, rotate_y=random.uniform(0, 360),
                     scale=rand_scale(1.0, 0.5))

    # 3 fougeres
    for i in range(3):
        pos = sampler.sample(9, 19, -12, 12, exclusion=0.6, path_exclusion=0.9)
        if pos is None:
            break
        add_instance(stage, "/Forest/Zone_Rocky", f"Fern_{i:02d}",
                     "Fern.usda", "Fern",
                     translate=pos, rotate_y=random.uniform(0, 360),
                     scale=rand_scale(0.9, 0.25))

    # ============================ Save ======================================
    stage.GetRootLayer().Save()
    n_instances = sum(1 for p in stage.Traverse()
                      if p.HasAuthoredReferences())
    print(f"  Forest.usda : {n_instances} instances (toutes par reference)")
    print(f"  Sortie : {os.path.relpath(OUT_PATH, ROOT)}")


if __name__ == "__main__":
    main()
