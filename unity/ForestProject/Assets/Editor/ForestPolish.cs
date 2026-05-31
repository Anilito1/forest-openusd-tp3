using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace TP3Forest
{
    public static class ForestPolish
    {
        // 3 zones cohérentes avec generate_forest.py
        // (xmin, xmax, zmin, zmax, color, smoothness, name)
        private static readonly (float, float, float, float, Color, float, string)[] Patches = new (float, float, float, float, Color, float, string)[]
        {
            // Fond global d'abord (sous-couche pour eviter les debordements)
            (-30f, 30f, -25f, 25f, new Color(0.28f, 0.24f, 0.15f), 0.05f, "FloorBackground"),
            // Zones spatiales par-dessus (overlap leger pour masquer les jointures)
            (-22f, -1.5f, -16f, 16f, new Color(0.22f, 0.30f, 0.14f), 0.05f, "DenseFloor"),
            (-4f,   10f,  -10f, 10f, new Color(0.42f, 0.55f, 0.22f), 0.10f, "ClearingFloor"),
            ( 7.5f, 22f, -16f,  16f, new Color(0.38f, 0.34f, 0.26f), 0.08f, "RockyFloor"),
        };

        private const string MaterialsFolder = "Assets/Materials/ForestGenerated";

        [MenuItem("Tools/Forest/Polish")]
        public static void Polish()
        {
            EnsureMaterialsFolder();
            HideOriginalGround();
            BuildFloorPatches();
            ConfigureLightingAndSky();
            FrameCamera();

            var scene = EditorSceneManager.GetActiveScene();
            EditorSceneManager.SaveScene(scene);
            Debug.Log("[Polish] Done. Scene sauvegardee.");
        }

        private static void EnsureMaterialsFolder()
        {
            if (!AssetDatabase.IsValidFolder("Assets/Materials"))
                AssetDatabase.CreateFolder("Assets", "Materials");
            if (!AssetDatabase.IsValidFolder(MaterialsFolder))
                AssetDatabase.CreateFolder("Assets/Materials", "ForestGenerated");
        }

        private static void HideOriginalGround()
        {
            // Le sol USD est un plan uni - on le masque, les patches le remplacent
            var groundGo = GameObject.Find("Forest/Forest/Ground");
            if (groundGo != null)
            {
                foreach (var r in groundGo.GetComponentsInChildren<Renderer>())
                    r.enabled = false;
                Debug.Log("[Polish] Ground USD masque.");
            }
        }

        private static void BuildFloorPatches()
        {
            // Supprimer l'ancien container s'il existe
            var oldParent = GameObject.Find("FloorPatches");
            if (oldParent != null) Object.DestroyImmediate(oldParent);

            var parent = new GameObject("FloorPatches");
            Shader urpLit = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");

            int idx = 0;
            foreach (var (xmin, xmax, zmin, zmax, color, smoothness, name) in Patches)
            {
                float w = xmax - xmin;
                float d = zmax - zmin;
                float cx = (xmin + xmax) / 2f;
                float cz = (zmin + zmax) / 2f;
                float y = 0.005f + 0.01f * idx;  // Y croissant pour eviter z-fighting
                idx++;

                var plane = GameObject.CreatePrimitive(PrimitiveType.Plane);
                plane.name = name;
                plane.transform.SetParent(parent.transform, true);
                plane.transform.position = new Vector3(cx, y, cz);
                // Unity Plane = 10x10, donc scale = size/10
                plane.transform.localScale = new Vector3(w / 10f, 1f, d / 10f);

                var matPath = $"{MaterialsFolder}/Mat_Floor_{name}.mat";
                var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
                if (mat == null)
                {
                    mat = new Material(urpLit) { name = $"Mat_Floor_{name}" };
                    AssetDatabase.CreateAsset(mat, matPath);
                }
                if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
                if (mat.HasProperty("_Color")) mat.SetColor("_Color", color);
                if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smoothness);
                if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", 0f);
                plane.GetComponent<Renderer>().sharedMaterial = mat;

                // Pas besoin de collider pour le rendu
                var col = plane.GetComponent<Collider>();
                if (col != null) Object.DestroyImmediate(col);
            }
            Debug.Log($"[Polish] {Patches.Length} patches de sol crees.");
        }

private static void ConfigureLightingAndSky()
        {
            // Fog volumetrique léger
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = 0.012f;
            RenderSettings.fogColor = new Color(0.78f, 0.85f, 0.92f);

            // Ambient
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.65f, 0.78f, 0.92f);
            RenderSettings.ambientEquatorColor = new Color(0.55f, 0.58f, 0.50f);
            RenderSettings.ambientGroundColor = new Color(0.20f, 0.18f, 0.12f);
            RenderSettings.ambientIntensity = 1.2f;

            // Skybox URP procedural (re-config a chaque run)
            string skyPath = $"{MaterialsFolder}/Mat_Skybox.mat";
            Material sky = AssetDatabase.LoadAssetAtPath<Material>(skyPath);
            if (sky == null)
            {
                Shader skyShader = Shader.Find("Skybox/Procedural") ?? Shader.Find("Skybox/Cubemap");
                if (skyShader != null)
                {
                    sky = new Material(skyShader) { name = "Mat_Skybox" };
                    AssetDatabase.CreateAsset(sky, skyPath);
                }
            }
            if (sky != null)
            {
                if (sky.HasProperty("_SunSize")) sky.SetFloat("_SunSize", 0.025f);
                if (sky.HasProperty("_SunSizeConvergence")) sky.SetFloat("_SunSizeConvergence", 5f);
                if (sky.HasProperty("_AtmosphereThickness")) sky.SetFloat("_AtmosphereThickness", 0.6f);
                if (sky.HasProperty("_SkyTint")) sky.SetColor("_SkyTint", new Color(0.50f, 0.70f, 0.95f));
                if (sky.HasProperty("_GroundColor")) sky.SetColor("_GroundColor", new Color(0.28f, 0.24f, 0.18f));
                if (sky.HasProperty("_Exposure")) sky.SetFloat("_Exposure", 0.85f);
                EditorUtility.SetDirty(sky);
                RenderSettings.skybox = sky;
            }

            // Configuration des lumières directionnelles
            foreach (var l in Object.FindObjectsByType<Light>(FindObjectsSortMode.None))
            {
                if (l.type == LightType.Directional)
                {
                    l.intensity = 1.5f;
                    l.color = new Color(1.00f, 0.96f, 0.86f);
                    l.transform.rotation = Quaternion.Euler(48f, 35f, 0f);
                    l.shadows = LightShadows.Soft;
                    l.shadowStrength = 0.7f;
                }
            }
            DynamicGI.UpdateEnvironment();
            Debug.Log("[Polish] Lighting + skybox configures.");
        }

        private static void FrameCamera()
        {
            var cam = Camera.main;
            if (cam == null) return;
            cam.transform.position = new Vector3(0f, 12f, -22f);
            cam.transform.rotation = Quaternion.Euler(18f, 0f, 0f);
            cam.farClipPlane = 250f;
            cam.fieldOfView = 55f;
            cam.clearFlags = CameraClearFlags.Skybox;
            Debug.Log("[Polish] Camera cadree.");
        }
    }
}
