# TP3 - Composition d'une forêt structurée avec OpenUSD

ST2SNE, Efrei Paris 2025-2026 — Anil BRAUN.

Scène de forêt construite intégralement avec des références OpenUSD vers des assets externes.

## Structure du dépôt

```
forest-openusd-tp3/
├── usda/
│   ├── Forest.usda            ← scène principale (références uniquement)
│   └── assets/                ← assets .usda sources (un par type d'objet)
│       ├── TreePine.usda
│       ├── TreeOak.usda
│       ├── TreeBirch.usda
│       ├── RockBig.usda
│       ├── RockSmall.usda
│       ├── Bush.usda
│       ├── Fern.usda
│       ├── Flower.usda
│       ├── FallenLog.usda
│       ├── Moss.usda
│       ├── BirdNest.usda
│       └── Ground.usda
├── scripts/
│   ├── generate_assets.py     ← génère les assets sources
│   └── generate_forest.py     ← génère Forest.usda avec références
└── unity/
    └── ForestProject/         ← projet Unity (scène Forest.unity)
```

## Reproduire la génération

```bash
pip install usd-core
python scripts/generate_assets.py
python scripts/generate_forest.py
```

## Visualiser la scène

- **usdview** (Pixar OpenUSD) : `usdview usda/Forest.usda`
- **Unity** : ouvrir `unity/ForestProject/` sous Unity 6.x, scène `Assets/Scenes/Forest.unity`
- **VS Code** : extension *USD Language Support*

## Scène

3 zones paysagères :
- **Zone Dense** : forêt fermée, dominée par les pins et les chênes
- **Zone Clairière** : ouverture lumineuse, herbe haute, fleurs, nid d'oiseau
- **Zone Rocheuse** : rochers, troncs tombés, mousses, bouleaux dispersés

Biodiversité : 3 types d'arbres, 2 types de rochers, 3 strates de végétation basse, 2 éléments de sol, 1 indice de vie animale.

Toutes les instances de la scène utilisent `prepend references = @asset.usda@</PrimRoot>` ; aucun mesh n'est dupliqué dans `Forest.usda`.
