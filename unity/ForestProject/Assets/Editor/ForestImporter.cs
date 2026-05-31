using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace TP3Forest
{
    public static class ForestImporter
    {
        private const string UsdAssetPath = "Assets/USD/Forest.usda";
        private const string OutputScenePath = "Assets/Scenes/Forest.unity";

[MenuItem("Tools/Forest/Import Forest.usda")]
        public static void ImportForest()
        {
            string absUsd = Path.GetFullPath(UsdAssetPath);
            if (!File.Exists(absUsd))
            {
                Debug.LogError("[Forest] Introuvable: " + absUsd);
                return;
            }

            System.Type importHelpersType = null;
            System.Type sceneImportOptionsType = null;
            System.Type usdAssetType = null;
            foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies())
            {
                if (importHelpersType == null) importHelpersType = asm.GetType("Unity.Formats.USD.ImportHelpers");
                if (sceneImportOptionsType == null) sceneImportOptionsType = asm.GetType("Unity.Formats.USD.SceneImportOptions");
                if (usdAssetType == null) usdAssetType = asm.GetType("Unity.Formats.USD.UsdAsset");
            }
            if (importHelpersType == null || sceneImportOptionsType == null)
            {
                Debug.LogError("[Forest] Package USD non charge.");
                return;
            }

            var newScene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

            try
            {
                var initForOpen = importHelpersType.GetMethod("InitForOpen", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                var initParams = initForOpen.GetParameters();
                object[] initArgs = new object[initParams.Length];
                initArgs[0] = absUsd;
                object scene = initForOpen.Invoke(null, initArgs);
                if (scene == null) { Debug.LogError("[Forest] Scene null"); return; }

                object importOptions = System.Activator.CreateInstance(sceneImportOptionsType);

                System.Reflection.MethodInfo importMethod = null;
                foreach (var m in importHelpersType.GetMethods(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
                {
                    if (m.Name == "ImportSceneAsGameObject") { importMethod = m; break; }
                }
                var importParams = importMethod.GetParameters();
                object[] args = new object[importParams.Length];
                args[0] = scene;
                args[1] = null;
                args[2] = importOptions;
                if (importParams.Length >= 4) args[3] = true;

                GameObject root = importMethod.Invoke(null, args) as GameObject;
                if (root == null) { Debug.LogError("[Forest] Root null"); return; }
                root.name = "Forest";
                Debug.Log("[Forest] Root cree. Children avant Reload: " + root.transform.childCount);

                var closeMethod = scene.GetType().GetMethod("Close");
                if (closeMethod != null) closeMethod.Invoke(scene, null);

                // Reload du UsdAsset pour expanser la hierarchie
                if (usdAssetType != null)
                {
                    var comp = root.GetComponent(usdAssetType);
                    if (comp != null)
                    {
                        var reload = usdAssetType.GetMethod("Reload");
                        if (reload != null)
                        {
                            var rp = reload.GetParameters();
                            object[] rargs = new object[rp.Length];
                            if (rp.Length >= 1) rargs[0] = true;  // forceRebuild
                            reload.Invoke(comp, rargs);
                            Debug.Log("[Forest] Reload OK. Children apres: " + root.transform.childCount);
                        }
                        else
                        {
                            Debug.LogWarning("[Forest] UsdAsset.Reload introuvable");
                        }
                    }
                }
            }
            catch (System.Reflection.TargetInvocationException tie)
            {
                System.Exception inner = tie.InnerException;
                while (inner != null) { Debug.LogError("[Forest] INNER: " + inner.GetType().Name + ": " + inner.Message); inner = inner.InnerException; }
            }
            catch (System.Exception e)
            {
                Debug.LogError("[Forest] " + e.GetType().Name + ": " + e.Message);
            }

            var lightGO = new GameObject("Sun");
            var lt = lightGO.AddComponent<Light>();
            lt.type = LightType.Directional;
            lt.intensity = 1.1f;
            lt.color = new Color(1.0f, 0.96f, 0.88f);
            lightGO.transform.rotation = Quaternion.Euler(45f, 35f, 0f);

            var cam = Camera.main;
            if (cam != null)
            {
                cam.transform.position = new Vector3(0f, 18f, -28f);
                cam.transform.rotation = Quaternion.Euler(25f, 0f, 0f);
                cam.farClipPlane = 200f;
                cam.backgroundColor = new Color(0.62f, 0.78f, 0.88f);
            }

            string scenesDir = Path.Combine(Application.dataPath, "Scenes");
            if (!Directory.Exists(scenesDir)) Directory.CreateDirectory(scenesDir);
            EditorSceneManager.SaveScene(newScene, OutputScenePath);
            Debug.Log("[Forest] Scene sauvee: " + OutputScenePath);
        }
    }
}
