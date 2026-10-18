using System;
using System.Collections.Generic;
using UnityEngine;

namespace GargantuaSystem
{
    /// <summary>
    /// Pulsar jets of the neutron star, which Kopernicus cannot do: thin beam + sheath facing the camera and
    /// a halo, spinning like a lighthouse. KSP's own additive particle shader (no asset bundle, no Unity).
    /// </summary>
    [KSPAddon(KSPAddon.Startup.AllGameScenes, false)]
    public class ScaledEffects : MonoBehaviour
    {
        const string StarName = "GargantuaNeutronStar";
        // Plain scaled-space objects. The pulsar is outside Gargantua's lens sphere (Singularity.cfg):
        // inside it Singularity repaints the screen and transparent effects become "background" (vanish). Seen through
        // the sphere, behind Gargantua, the jets vanish; acceptable.
        const int ScaledLayer = 10;

        // Jets (real metres; scaled space divides by ScaledSpace.ScaleFactor). Look inspired by Cosmic Serenity's
        // Anubis: very bright point with a halo, needle-thin beam, wide faint sheath with dust.
        const double JetLength = 3.0E9;
        const double CoreWidth = 3.0E8;     // beam width at the tip
        const double SheathWidth = 1.2E9;   // sheath width at the tip
        const double GlowSize = 1.2E9;     // halo diameter around the star
        const float JetTilt = 25;           // degrees between the magnetic axis (jets) and the spin axis
        const double SpinPeriod = 30;       // s, same as the body rotation (NeutronStar.cfg); 5 s looked like a spinning PNG
        const float FlowSpeed = 0.12f;      // filament texture repeats per second (flows outwards)

        CelestialBody star;
        Transform jets, glow;
        Material flowMat;

        void Start()
        {
            var scene = HighLogic.LoadedScene;
            if (scene != GameScenes.FLIGHT && scene != GameScenes.TRACKSTATION && scene != GameScenes.SPACECENTER) { Destroy(this); return; }
            Shader shader = Shader.Find("KSP/Particles/Additive") ?? Shader.Find("Particles/Additive") ?? Shader.Find("Legacy Shaders/Particles/Additive");
            if (shader == null) { Debug.LogError("[GargantuaSystem] ScaledEffects: additive shader not found"); Destroy(this); return; }

            star = FlightGlobals.GetBodyByName(StarName);
            if (star != null && star.scaledBody != null)
            {
                jets = BuildJets(shader);
                glow = BuildGlow(shader);
                BuildFlow(shader).SetParent(jets, false);
            }

            Debug.Log("[GargantuaSystem] ScaledEffects: shader " + shader.name + ", jets " + (jets != null));
        }

        void LateUpdate()
        {
            double t = Planetarium.GetUniversalTime();
            Camera cam = ScaledCamera.Instance != null ? ScaledCamera.Instance.cam : null;
            if (jets != null && cam != null)
            {
                Vector3 spin = ((Vector3)star.RotationAxis).normalized;
                Vector3 pos = star.scaledBody.transform.position;
                // tilted magnetic axis, spinning around the rotation axis (lighthouse)
                Vector3 perp = Vector3.Cross(spin, Mathf.Abs(spin.x) < 0.9f ? Vector3.right : Vector3.forward).normalized;
                Vector3 axis = Quaternion.AngleAxis((float)(360 * (t % SpinPeriod) / SpinPeriod), spin)
                    * (Quaternion.AngleAxis(JetTilt, perp) * spin);
                // the strip turns around its own axis to always face the camera
                Vector3 toCam = cam.transform.position - pos;
                Vector3 face = toCam - Vector3.Dot(toCam, axis) * axis;
                if (face.sqrMagnitude < 1e-6f) face = perp;
                jets.position = pos;
                jets.rotation = Quaternion.LookRotation(face.normalized, axis);
                glow.position = pos;
                glow.rotation = cam.transform.rotation;
                // real time, not UT: in timewarp the filaments would become a blur
                flowMat.mainTextureOffset = new Vector2(0, -(Time.time * FlowSpeed % 1f));
#if GARGSYS_DEBUG
                // screen position for test scripts to aim the camera (build: -p:DefineConstants=GARGSYS_DEBUG)
                if (Time.frameCount % 600 == 0) Debug.Log("[GargantuaSystem] ScaledEffects debug: viewport " + cam.WorldToViewportPoint(pos));
#endif
            }
        }

        void OnDestroy()
        {
            if (jets != null) Destroy(jets.gameObject);
            if (glow != null) Destroy(glow.gameObject);
        }

        static Transform NewObject(string name, Mesh mesh, Material mat)
        {
            var go = new GameObject(name) { layer = ScaledLayer };
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
            return go.transform;
        }

        static Material NewMaterial(Shader shader, Texture tex)
        {
            var m = new Material(shader) { mainTexture = tex };
            m.SetColor("_TintColor", new Color(0.5f, 0.5f, 0.5f, 0.5f)); // neutral: the colour comes from the texture
            return m;
        }

        // ---------- jets ----------

        /// Two strips per jet (wide sheath and thin core), in the local XY plane with the jet axis along +-Y.
        /// LateUpdate turns the object so the plane faces the camera (no "fan" of crossed planes).
        Transform BuildJets(Shader shader)
        {
            float s = ScaledSpace.ScaleFactor;
            float len = (float)(JetLength / s), r0 = (float)(star.Radius / s);
            var verts = new List<Vector3>();
            var uvs = new List<Vector2>();
            var tris = new List<int>();
            // u 0..0.5 = sheath, 0.5..1 = core (the two halves of the same texture)
            AddStrip(verts, uvs, tris, r0, len, (float)(SheathWidth / s), 0f);
            AddStrip(verts, uvs, tris, r0, len * 0.85f, (float)(CoreWidth / s), 0.5f);
            var mesh = new Mesh { name = "GargSys_PulsarJets" };
            mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
            mesh.RecalculateBounds();
            return NewObject("GargSys_PulsarJets", mesh, NewMaterial(shader, JetTexture()));
        }

        /// Trapezoid strip, split into rows with a centre column: with only two triangles the texture suffered
        /// affine distortion and the gaussian ridge followed the diagonal (core and sheath at different angles).
        static void AddStrip(List<Vector3> verts, List<Vector2> uvs, List<int> tris, float r0, float len, float width, float u0)
        {
            const int Rows = 32;
            for (int dir = -1; dir <= 1; dir += 2)
            {
                int v0 = verts.Count;
                for (int i = 0; i <= Rows; i++)
                {
                    float fv = i / (float)Rows, w = width * (0.02f + 0.48f * fv), y = dir * (r0 + len * fv);
                    for (int c = 0; c < 3; c++)
                    {
                        verts.Add(new Vector3((c - 1) * w, y, 0));
                        uvs.Add(new Vector2(u0 + 0.25f * c, fv));
                    }
                }
                for (int i = 0; i < Rows; i++)
                    for (int c = 0; c < 2; c++)
                    {
                        int a = v0 + i * 3 + c, b = a + 3;
                        tris.AddRange(new[] { a, b, a + 1, a + 1, b, b + 1 });
                    }
            }
        }

        /// Left half: sheath (wide faint gaussian + dotted dust, denser towards the tip).
        /// Right half: core (thin hot thread that widens a little and fades at the tip).
        static Texture2D JetTexture()
        {
            const int W = 256, H = 1024, Half = W / 2;
            var tex = new Texture2D(W, H, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Clamp, anisoLevel = 8, filterMode = FilterMode.Trilinear };
            var px = new Color[W * H];
            var rng = new System.Random(4242);
            for (int y = 0; y < H; y++)
            {
                float fv = y / (H - 1f);
                float baseFade = Mathf.Clamp01(fv * 60); // no hard edge at the base
                for (int x = 0; x < W; x++)
                {
                    float u = ((x % Half) / (Half - 1f) - 0.5f) * 2; // -1..1 in each half
                    float b;
                    if (x >= Half)
                    {
                        float sig = 0.10f + 0.25f * fv;
                        b = Mathf.Exp(-u * u / (sig * sig)) * Mathf.Pow(1 - fv, 1.1f) * 2f;
                    }
                    else
                    {
                        float sig = 0.30f + 0.15f * fv;
                        float haze = Mathf.Exp(-u * u / (sig * sig)) * Mathf.Pow(1 - fv, 1.3f) * 1.6f;
                        float dust = rng.NextDouble() < 0.015 + 0.05 * fv
                            ? (float)rng.NextDouble() * 2.4f * fv * (1 - fv) * Mathf.Exp(-u * u / 0.3f) : 0;
                        b = haze + dust;
                    }
                    b = Mathf.Clamp01(b * baseFade);
                    // colour baked into the texture: KSP/Particles/Additive ignores vertex colour
                    Color c = x >= Half ? new Color(0.80f, 0.90f, 1f) : new Color(0.40f, 0.60f, 1f);
                    px[y * W + x] = new Color(c.r * b, c.g * b, c.b * b, b);
                }
            }
            tex.SetPixels(px);
            tex.Apply(true, true);
            return tex;
        }

        /// Filaments flowing along the beam: a strip (child of the jet, same orientation) with a texture that
        /// repeats along the length and moves via mainTextureOffset. The fade at the ends comes from the width (diamond),
        /// because the texture scrolls and cannot carry the gradient.
        Transform BuildFlow(Shader shader)
        {
            const int Rows = 48, Repeats = 3;
            float s = ScaledSpace.ScaleFactor;
            float len = (float)(JetLength / s) * 0.9f, r0 = (float)(star.Radius / s), width = (float)(SheathWidth / s) * 0.45f;
            var verts = new List<Vector3>();
            var uvs = new List<Vector2>();
            var tris = new List<int>();
            for (int dir = -1; dir <= 1; dir += 2)
            {
                int v0 = verts.Count;
                for (int i = 0; i <= Rows; i++)
                {
                    float fv = i / (float)Rows;
                    float w = width * Mathf.Pow(Mathf.Sin(Mathf.PI * Mathf.Min(1, fv * 1.6f)), 0.8f) * (1 - fv);
                    for (int c = 0; c < 3; c++)
                    {
                        verts.Add(new Vector3((c - 1) * w, dir * (r0 + len * fv), 0));
                        uvs.Add(new Vector2(0.5f * c, fv * Repeats));
                    }
                }
                for (int i = 0; i < Rows; i++)
                    for (int c = 0; c < 2; c++)
                    {
                        int a = v0 + i * 3 + c, b = a + 3;
                        tris.AddRange(new[] { a, b, a + 1, a + 1, b, b + 1 });
                    }
            }
            var mesh = new Mesh { name = "GargSys_PulsarFlow" };
            mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
            mesh.RecalculateBounds();
            flowMat = NewMaterial(shader, FlowTexture());
            return NewObject("GargSys_PulsarFlow", mesh, flowMat);
        }

        /// Thin filaments along v, with brightness varying in integer-frequency waves (repeats seamlessly).
        static Texture2D FlowTexture()
        {
            const int W = 128, H = 512, Strands = 14;
            var rng = new System.Random(77);
            var pos = new float[Strands]; var wid = new float[Strands]; var amp = new float[Strands];
            var f1 = new int[Strands]; var f2 = new int[Strands]; var ph = new float[Strands];
            for (int k = 0; k < Strands; k++)
            {
                pos[k] = (float)(rng.NextDouble() * 1.2 - 0.6); wid[k] = 0.02f + 0.06f * (float)rng.NextDouble();
                amp[k] = 0.4f + 0.6f * (float)rng.NextDouble(); f1[k] = 1 + rng.Next(4); f2[k] = 3 + rng.Next(6);
                ph[k] = (float)(rng.NextDouble() * Mathf.PI * 2);
            }
            var px = new Color[W * H];
            for (int y = 0; y < H; y++)
            {
                float v = y / (float)H * Mathf.PI * 2;
                for (int x = 0; x < W; x++)
                {
                    float u = (x + 0.5f) / W * 2 - 1, b = 0;
                    for (int k = 0; k < Strands; k++)
                    {
                        float pulse = 0.5f + 0.5f * Mathf.Sin(f1[k] * v + ph[k]) * Mathf.Sin(f2[k] * v + 2 * ph[k]);
                        float d = (u - pos[k]) / wid[k];
                        b += amp[k] * pulse * pulse * Mathf.Exp(-d * d);
                    }
                    b = Mathf.Clamp01(b * 0.45f * Mathf.Exp(-u * u * 1.5f));
                    px[y * W + x] = new Color(0.55f * b, 0.75f * b, b, b);
                }
            }
            var tex = new Texture2D(W, H, TextureFormat.RGBA32, true)
                { wrapModeU = TextureWrapMode.Clamp, wrapModeV = TextureWrapMode.Repeat, anisoLevel = 8, filterMode = FilterMode.Trilinear };
            tex.SetPixels(px);
            tex.Apply(true, true);
            return tex;
        }

        /// Halo around the star: camera-facing quad, saturated core and long (~1/r^2) tail.
        Transform BuildGlow(Shader shader)
        {
            float h = (float)(GlowSize / ScaledSpace.ScaleFactor / 2);
            var mesh = new Mesh
            {
                name = "GargSys_PulsarGlow",
                vertices = new[] { new Vector3(-h, -h, 0), new Vector3(h, -h, 0), new Vector3(-h, h, 0), new Vector3(h, h, 0) },
                uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(0, 1), new Vector2(1, 1) },
                triangles = new[] { 0, 2, 1, 1, 2, 3 }
            };
            mesh.RecalculateBounds();
            const int N = 256;
            var tex = new Texture2D(N, N, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Trilinear };
            var px = new Color[N * N];
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float dx = (x + 0.5f) / N * 2 - 1, dy = (y + 0.5f) / N * 2 - 1, r2 = dx * dx + dy * dy;
                    float b = 0.012f / (r2 + 0.012f) * Mathf.Clamp01((1 - Mathf.Sqrt(r2)) / 0.3f);
                    px[y * N + x] = new Color(0.60f * b, 0.75f * b, b, b);
                }
            tex.SetPixels(px);
            tex.Apply(true, true);
            return NewObject("GargSys_PulsarGlow", mesh, NewMaterial(shader, tex));
        }

    }
}
