using System;
using System.Collections;
using System.Reflection;
using UnityEngine;

namespace GargantuaSystem
{
    /// <summary>
    /// Inside a Singularity lens sphere the sky is drawn from a galaxy cubemap snapshot. Singularity creates it with
    /// mipmaps, and the lensing bends the sample directions so much that the GPU reads the blurry low mips: stars and
    /// the Milky Way smear into a flat haze and the sphere shows as a "bubble" around Gargantua.
    /// This gives every Singularity material a copy of the snapshot without mipmaps (full-resolution only).
    /// Singularity is found by reflection, so this does nothing when it is not installed.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.AllGameScenes, false)]
    public class LensSkyFix : MonoBehaviour
    {
        static readonly int CubeMapId = Shader.PropertyToID("CubeMap");

        object singularity;
        FieldInfo cubemapField, loadedField, materialField;
        Cubemap sharp;
        float giveUpAt;

        void Start()
        {
            Type t = Type.GetType("Singularity.Singularity, Singularity");
            Type o = Type.GetType("Singularity.SingularityObject, Singularity");
            PropertyInfo inst = t?.GetProperty("Instance", BindingFlags.Public | BindingFlags.Static);
            cubemapField = t?.GetField("galaxyCubemap", BindingFlags.Public | BindingFlags.Instance);
            loadedField = t?.GetField("loadedObjects", BindingFlags.Public | BindingFlags.Instance);
            materialField = o?.GetField("singularityMaterial", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance);
            singularity = inst?.GetValue(null, null);
            if (singularity == null || cubemapField == null || loadedField == null || materialField == null) { Destroy(this); return; }
            giveUpAt = Time.realtimeSinceStartup + 120;
        }

        // Singularity creates the snapshot and its materials a few frames after the scene loads: poll until both exist.
        void Update()
        {
            if (Time.realtimeSinceStartup > giveUpAt) { enabled = false; return; }
            var src = cubemapField.GetValue(singularity) as Cubemap;
            if (src == null) return;
            int bound = 0;
            foreach (object so in (loadedField.GetValue(singularity) as IEnumerable) ?? new object[0])
            {
                var mat = materialField.GetValue(so) as Material;
                if (mat == null || mat.GetTexture(CubeMapId) != src) continue;
                if (sharp == null)
                {
                    sharp = new Cubemap(src.width, src.format, false) { filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp };
                    for (int face = 0; face < 6; face++) Graphics.CopyTexture(src, face, 0, sharp, face, 0);
                }
                mat.SetTexture(CubeMapId, sharp);
                bound++;
            }
            if (bound > 0)
            {
                Debug.Log("[GargantuaSystem] LensSkyFix: " + bound + " Singularity material(s) now use a " + src.width + "px sky without mipmaps");
                enabled = false;
            }
        }

        void OnDestroy()
        {
            if (sharp != null) Destroy(sharp);
        }
    }
}
