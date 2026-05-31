using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace TP3Forest
{
    public static class ForestMaterialize
    {
        // Map keyword (testé en lowercase contre name + parent name) → couleur HDR-safe (sRGB).
        // Ordre = priorité (premier match gagne).
        private static readonly (string keyword, Color color, float rough, float metal)[] Palette = new (string, Color, float, float)[]
        {
            ("autumnoak/foliage", new Color(0.88f, 0.45f, 0.08f), 0.75f, 0f),
            ("autumnoak/crown",   new Color(0.88f, 0.45f, 0.08f), 0.75f, 0f),
            ("autumnoak",         new Color(0.88f, 0.45f, 0.08f), 0.75f, 0f),
            ("patriarch/foliage", new Color(0.18f, 0.36f, 0.12f), 0.80f, 0f),
            ("patriarch/crown",   new Color(0.18f, 0.36f, 0.12f), 0.80f, 0f),
            ("birch/trunk",       new Color(0.92f, 0.90f, 0.85f), 0.85f, 0f),
            ("birch/foliage",     new Color(0.45f, 0.62f, 0.28f), 0.80f, 0f),
            ("pine/trunk",        new Color(0.32f, 0.20f, 0.12f), 0.85f, 0f),
            ("pine/foliage",      new Color(0.10f, 0.32f, 0.14f), 0.80f, 0f),
            ("oak/trunk",         new Color(0.35f, 0.22f, 0.13f), 0.85f, 0f),
            ("oak/crown",         new Color(0.22f, 0.42f, 0.18f), 0.75f, 0f),
            ("sapling/foliage",   new Color(0.20f, 0.50f, 0.20f), 0.80f, 0f),
            ("sapling/trunk",     new Color(0.30f, 0.20f, 0.12f), 0.85f, 0f),
            ("deadtree",          new Color(0.42f, 0.36f, 0.28f), 0.95f, 0f),
            ("branch",            new Color(0.42f, 0.36f, 0.28f), 0.95f, 0f),
            ("fallenlog/log",     new Color(0.28f, 0.18f, 0.10f), 0.90f, 0f),
            ("hollowlog",         new Color(0.28f, 0.18f, 0.10f), 0.90f, 0f),
            ("bush/lobe",         new Color(0.18f, 0.38f, 0.16f), 0.80f, 0f),
            ("bush",              new Color(0.18f, 0.38f, 0.16f), 0.80f, 0f),
            ("fern/blade",        new Color(0.20f, 0.50f, 0.20f), 0.75f, 0f),
            ("fern",              new Color(0.20f, 0.50f, 0.20f), 0.75f, 0f),
            ("moss/patch",        new Color(0.22f, 0.45f, 0.18f), 0.95f, 0f),
            ("moss",              new Color(0.22f, 0.45f, 0.18f), 0.95f, 0f),
            ("flower/petals",     new Color(0.92f, 0.28f, 0.35f), 0.55f, 0f),
            ("flower/center",     new Color(1.00f, 0.85f, 0.20f), 0.60f, 0f),
            ("flower/stem",       new Color(0.25f, 0.45f, 0.20f), 0.85f, 0f),
            ("flower",            new Color(0.92f, 0.28f, 0.35f), 0.55f, 0f),
            ("mushroom/cap",      new Color(0.85f, 0.18f, 0.12f), 0.45f, 0f),
            ("mushroom/spot",     new Color(0.98f, 0.96f, 0.92f), 0.50f, 0f),
            ("mushroom/stem",     new Color(0.95f, 0.92f, 0.85f), 0.50f, 0f),
            ("mushroom",          new Color(0.85f, 0.18f, 0.12f), 0.45f, 0f),
            ("birdnest/egg",      new Color(0.95f, 0.93f, 0.85f), 0.40f, 0f),
            ("birdnest/ring",     new Color(0.35f, 0.22f, 0.10f), 0.90f, 0f),
            ("birdnest",          new Color(0.35f, 0.22f, 0.10f), 0.90f, 0f),
            ("cairn",             new Color(0.55f, 0.52f, 0.48f), 0.95f, 0f),
            ("rockbig",           new Color(0.45f, 0.43f, 0.40f), 0.95f, 0f),
            ("rocksmall",         new Color(0.55f, 0.52f, 0.48f), 0.95f, 0f),
            ("stone",             new Color(0.55f, 0.52f, 0.48f), 0.95f, 0f),
            ("ground/surface",    new Color(0.34f, 0.28f, 0.18f), 0.95f, 0f),
            ("ground",            new Color(0.34f, 0.28f, 0.18f), 0.95f, 0f),
            ("trunk",             new Color(0.32f, 0.20f, 0.12f), 0.85f, 0f),
            ("foliage",           new Color(0.18f, 0.40f, 0.15f), 0.80f, 0f),
            ("crown",             new Color(0.22f, 0.42f, 0.18f), 0.75f, 0f),
            ("lobe",              new Color(0.18f, 0.38f, 0.16f), 0.80f, 0f),
        };

        private const string MaterialsFolder = "Assets/Materials/ForestGenerated";

        [MenuItem("Tools/Forest/Materialize")]
        public static void Materialize()
        {
            if (!AssetDatabase.IsValidFolder("Assets/Materials"))
                AssetDatabase.CreateFolder("Assets", "Materials");
            if (!AssetDatabase.IsValidFolder(MaterialsFolder))
                AssetDatabase.CreateFolder("Assets/Materials", "ForestGenerated");

            // Shader URP/Lit
            Shader urpLit = Shader.Find("Universal Render Pipeline/Lit");
            if (urpLit == null) urpLit = Shader.Find("URP/Lit");
            if (urpLit == null) urpLit = Shader.Find("Standard");
            if (urpLit == null) { Debug.LogError("[Materialize] Aucun shader URP/Lit ou Standard trouve"); return; }

            var cache = new Dictionary<string, Material>();
            int painted = 0;
            int skipped = 0;

            var renderers = Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None);
            foreach (var r in renderers)
            {
                if (r == null) continue;
                string path = GetPathLower(r.transform);
                var (color, rough, metal, key) = Resolve(path);
                if (key == null) { skipped++; continue; }

                if (!cache.TryGetValue(key, out var mat))
                {
                    mat = new Material(urpLit) { name = "Mat_" + key.Replace("/", "_") };
                    SetColor(mat, color);
                    SetFloat(mat, "_Smoothness", 1f - rough);
                    SetFloat(mat, "_Metallic", metal);
                    string assetPath = $"{MaterialsFolder}/{mat.name}.mat";
                    AssetDatabase.CreateAsset(mat, assetPath);
                    cache[key] = mat;
                }
                r.sharedMaterial = mat;
                painted++;
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"[Materialize] Painted {painted} renderers, skipped {skipped}, materials cached: {cache.Count}");
        }

        private static (Color, float, float, string) Resolve(string lowerPath)
        {
            foreach (var (kw, col, rough, metal) in Palette)
            {
                if (lowerPath.Contains(kw)) return (col, rough, metal, kw);
            }
            return (Color.gray, 0.9f, 0f, null);
        }

        private static string GetPathLower(Transform t)
        {
            var parts = new List<string>();
            for (var cur = t; cur != null; cur = cur.parent) parts.Insert(0, cur.name);
            return string.Join("/", parts).ToLowerInvariant();
        }

        private static void SetColor(Material m, Color c)
        {
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
            if (m.HasProperty("_Color")) m.SetColor("_Color", c);
        }

        private static void SetFloat(Material m, string prop, float v)
        {
            if (m.HasProperty(prop)) m.SetFloat(prop, v);
        }
    }
}
