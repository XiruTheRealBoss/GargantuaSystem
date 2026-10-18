using System;
using UnityEngine;

namespace GargantuaSystem
{
    /// <summary>
    /// Miller's giant tidal waves that sweep the planet.
    /// Kopernicus does not animate terrain (rebuilding the PQS takes seconds), so each wave is its own mesh,
    /// attached to Miller's PQS and rotating around the planet's axis. The position comes from universal time:
    /// timewarp, save/load and different scenes always see the same wave in the same place.
    /// Analytic interaction (no collider): a vessel below the wave surface floats and is carried along,
    /// like in the film. A moving MeshCollider does not work here: without a Rigidbody it does not wake resting vessels (the wave
    /// passed through them), and with a Rigidbody KSP's floating origin detaches the mesh from the planet.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.Flight, false)]
    public class MillerWaves : MonoBehaviour
    {
        const string BodyName = "Miller";
        const int WaveCount = 5;
        const double CrestHeight = 1200;   // m (the film says ~4000 ft); creative liberty on the scale
        const double Speed = 100;          // m/s at the equator: a wave passes each point every ~2.3 h
        const double WarnDistance = 33000; // m: a crest at this distance triggers the warning (warp stops earlier)
        const double FaceWidth = 2600;     // m: steep front face
        const double BackWidth = 14000;    // m: back slope scale (gaussian)
        const double BackLength = 40000;   // m: where the back slope is already ~0 m
        const double MaxLat = 72;          // degrees: the waves die out before the poles
        const double LatStep = 0.1;        // degrees along the crest (~1.1 km on Miller)

        CelestialBody body;
        Transform pqs;
        Vector3 polarAxis;                 // north axis in PQS local coordinates
        float rotationSign;                // + or -, so the rotation moves east (wave front leading)
        Transform[] waves;
        double angularSpeed;               // degrees/s
        double lastWarnUT = double.MinValue;

        void Start()
        {
            body = FlightGlobals.GetBodyByName(BodyName);
            if (body == null || body.pqsController == null)
            {
                Debug.Log("[GargantuaSystem] MillerWaves: body " + BodyName + " not found, waves disabled");
                Destroy(this);
                return;
            }
            pqs = body.pqsController.transform;
            angularSpeed = Speed / body.Radius * 180 / Math.PI;
            polarAxis = pqs.InverseTransformDirection((Vector3)(body.GetWorldSurfacePosition(90, 0, 0) - body.position)).normalized;

            // Which rotation direction increases longitude? Tested at runtime, without relying on KSP's convention.
            Vector3 p0 = pqs.InverseTransformPoint(body.GetWorldSurfacePosition(0, 0, 0));
            Vector3 p1 = Quaternion.AngleAxis(1, polarAxis) * p0;
            double lon1 = body.GetLongitude(pqs.TransformPoint(p1));
            rotationSign = Math.Abs(lon1 - 1) < 0.1 ? 1 : -1;

            Mesh mesh = BuildMesh();
            Material material = BuildMaterial();
            waves = new Transform[WaveCount];
            for (int k = 0; k < WaveCount; k++)
            {
                var go = new GameObject("GargSys_MillerWave_" + k);
                go.layer = 15; // Local Scenery: vessels collide as they do with terrain
                go.transform.SetParent(pqs, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>().sharedMaterial = material;
                waves[k] = go.transform;
            }
            Debug.Log("[GargantuaSystem] MillerWaves: " + WaveCount + " waves, " + mesh.vertexCount + " vertices, sign " + rotationSign
                + ", shader " + (material.shader != null ? material.shader.name : "NULL"));
            SelfCheck();
        }

        void FixedUpdate()
        {
            if (waves == null) return;
            bool active = FlightGlobals.currentMainBody == body && !MapView.MapIsEnabled;
            double t = Planetarium.GetUniversalTime();
            for (int k = 0; k < WaveCount; k++)
            {
                Transform w = waves[k];
                if (w.gameObject.activeSelf != active) w.gameObject.SetActive(active);
                if (!active) continue;
                double lon = (k * 360.0 / WaveCount + 23 + angularSpeed * t) % 360;
                w.localPosition = Vector3.zero;
                w.localRotation = Quaternion.AngleAxis(rotationSign * (float)lon, polarAxis);
            }
            if (active)
            {
                foreach (Vessel v in FlightGlobals.VesselsLoaded)
                    if (v.mainBody == body && !v.packed) Push(v, t);
                Alarm(FlightGlobals.ActiveVessel, t);
            }
        }

        /// In timewarp the vessel is "on rails" and the wave passes unseen. When a crest is about to arrive,
        /// stop time acceleration and warn ("that's not a mountain").
        void Alarm(Vessel v, double t)
        {
            if (v == null || v.mainBody != body || Math.Abs(v.latitude) > MaxLat || v.altitude > 3 * CrestHeight) return;
            double eta = TimeToNextCrest(v.latitude, v.longitude, t);
            double groundSpeed = Speed * Math.Cos(v.latitude * Math.PI / 180);
            // in one physics step high warp can skip the whole wave: stop warp earlier, with margin
            if (TimeWarp.CurrentRateIndex > 0 && eta <= Math.Max(WarnDistance / groundSpeed, TimeWarp.CurrentRate * TimeWarp.fixedDeltaTime * 3))
                TimeWarp.SetRate(0, true);
            if (eta * groundSpeed > WarnDistance || t - lastWarnUT < 600) return;
            lastWarnUT = t;
            double km = eta * groundSpeed / 1000;
            ScreenMessages.PostScreenMessage(KSP.Localization.Localizer.Format("#LOC_GargSys_WaveWarning", km.ToString("F0")),
                10f, ScreenMessageStyle.UPPER_CENTER);
        }

        /// Seconds until the next crest passes (lat, lon). The waves move east at a fixed angular speed.
        public double TimeToNextCrest(double lat, double lon, double t)
        {
            double latRad = lat * Math.PI / 180;
            double crestOffset = (0.22 * latRad * latRad + 0.04 * Math.Sin(3 * latRad)) * 180 / Math.PI;
            double best = double.MaxValue;
            for (int k = 0; k < WaveCount; k++)
            {
                double crest = k * 360.0 / WaveCount + 23 + angularSpeed * t + crestOffset;
                double ahead = ((lon - crest) % 360 + 360) % 360; // degrees the crest still has to travel to get here
                best = Math.Min(best, ahead / angularSpeed);
            }
            return best;
        }

        /// Wave height (m above the sea) at a point and time. Same formula as the mesh.
        double WaveHeight(double lat, double lon, double t)
        {
            double latRad = lat * Math.PI / 180;
            double metersPerDeg = body.Radius * Math.PI / 180 * Math.Max(Math.Cos(latRad), 0.05);
            double crestOffset = (0.22 * latRad * latRad + 0.04 * Math.Sin(3 * latRad)) * 180 / Math.PI;
            double h = 0;
            for (int k = 0; k < WaveCount; k++)
            {
                double crest = k * 360.0 / WaveCount + 23 + angularSpeed * t + crestOffset;
                double dDeg = ((lon - crest) % 360 + 540) % 360 - 180; // -180..180, positive = ahead (east)
                h = Math.Max(h, CrestHeight * Along(latRad) * SmoothStep(MaxLat, 45, Math.Abs(lat)) * Profile(dDeg * metersPerDeg));
            }
            return h;
        }

        // "Fake" water (KSP has no fluid): buoyancy proportional to depth + drag towards the water velocity.
        // It used to be a lift (cancelled gravity and pulled at 100 m/s over the whole 40 km back slope):
        // after the crest the vessel kept "floating" up high for a long time.
        const double FloatDepth = 4;       // m submerged at which buoyancy equals gravity
        const double BuoyMax = 3;          // maximum buoyancy, in g (bottom of the wave)
        const double VertDamp = 1.2;       // 1/s: follows the surface rising and falling
        const double HorizDrag = 0.6;      // 1/s: drag towards the water velocity
        const double WaterDepth = 600;     // m, effective: at the crest the water moves ~2/3 of the wave speed (with 150 the vessel surfed the crest forever)

        /// Horizontal water velocity under the wave (shallow water: u = c*eta/(eta+H)). Near the crest almost c,
        /// on the back slope it drops with the height, and the vessel slows down.
        static double WaterSpeed(double h, double groundSpeed) => groundSpeed * h / (h + WaterDepth);

        /// Vessel below the wave surface: upward buoyancy, vertical damping relative to the surface (which rises
        /// and falls with the wave) and horizontal drag towards the water velocity. Below 2 m the stock sea takes over.
        void Push(Vessel v, double t)
        {
            double h = WaveHeight(v.latitude, v.longitude, t);
            // h < 2 m = open sea: floating vessels sit at ~-0.1 m and would be "swallowed" by the calm sea
            if (h < 2 || v.altitude >= h) return;
            double depth = h - v.altitude;
            Vector3d pos = v.CoMD;
            Vector3d up = (pos - body.position).normalized;
            Vector3d east = (body.GetWorldSurfacePosition(v.latitude, v.longitude + 0.001, v.altitude) - body.GetWorldSurfacePosition(v.latitude, v.longitude, v.altitude)).normalized;
            double g = FlightGlobals.getGeeForceAtPosition(pos).magnitude;
            double groundSpeed = Speed * Math.Cos(v.latitude * Math.PI / 180);
            double surfaceRise = WaveHeight(v.latitude, v.longitude, t + 0.5) - WaveHeight(v.latitude, v.longitude, t - 0.5); // m/s
            Vector3d rel = v.srf_velocity - east * WaterSpeed(h, groundSpeed) - up * surfaceRise;
            double relUp = Vector3d.Dot(rel, up);
            Vector3d acc = up * (g * Math.Min(depth / FloatDepth, BuoyMax) - VertDamp * relUp) - (rel - up * relUp) * HorizDrag;
            if (acc.magnitude > 40) acc = acc.normalized * 40;
            foreach (Part p in v.parts)
                if (p.rb != null) p.rb.AddForce(acc, ForceMode.Acceleration);
#if GARGSYS_DEBUG
            if (v.isActiveVessel && Time.frameCount % 100 == 0)
                Debug.Log("[GargantuaSystem] MillerWaves debug: h " + h.ToString("F0") + " alt " + v.altitude.ToString("F0") + " vUp "
                    + v.verticalSpeed.ToString("F1") + " vHor " + v.horizontalSrfSpeed.ToString("F1") + " rise " + surfaceRise.ToString("F1"));
#endif
        }

        static double Along(double latRad) => 0.75 + 0.15 * Math.Sin(7 * latRad) + 0.10 * Math.Sin(13 * latRad + 1);

        /// Quick check of the profile and height (logs an error if someone changes the shape and breaks it).
        void SelfCheck()
        {
            bool ok = Math.Abs(Profile(0) - 1) < 1e-9 && Profile(FaceWidth) == 0 && Profile(-BackLength) < 1e-3
                && Profile(FaceWidth / 2) > 0 && Profile(-BackWidth) < Profile(-BackWidth / 2);
            double crestNow = 23 + angularSpeed * Planetarium.GetUniversalTime();
            double hCrest = WaveHeight(0, crestNow, Planetarium.GetUniversalTime());
            ok &= hCrest > 0.6 * CrestHeight && WaveHeight(0, crestNow + 36, Planetarium.GetUniversalTime()) < 1;
            ok &= Math.Abs(TimeToNextCrest(0, crestNow + 1, Planetarium.GetUniversalTime()) - 1 / angularSpeed) < 1;
            ok &= WaterSpeed(CrestHeight, Speed) > 0.5 * Speed && WaterSpeed(CrestHeight, Speed) < 0.8 * Speed && WaterSpeed(2, Speed) < 0.02 * Speed;
            if (!ok) Debug.LogError("[GargantuaSystem] MillerWaves: profile self-check FAILED (crest " + hCrest.ToString("F0") + " m)");
        }

        void OnDestroy()
        {
            if (waves == null) return;
            foreach (Transform w in waves)
                if (w != null) Destroy(w.gameObject);
        }

        /// Height (m) at a distance d (m) from the crest, positive ahead (east). Same profile as the static versions.
        public static double Profile(double d)
        {
            if (d >= 0) return d >= FaceWidth ? 0 : Math.Pow(1 - d / FaceWidth, 1.6);
            return Math.Exp(-(d / BackWidth) * (d / BackWidth));
        }

        // Profile distances: dense on the front (where the shape changes fast), sparse on the back slope
        static readonly double[] Across = BuildAcross();

        static double[] BuildAcross()
        {
            var a = new System.Collections.Generic.List<double>();
            for (int i = 0; i <= 24; i++) { double x = i / 24.0; a.Add(-BackLength * (1 - x) * (1 - x)); }
            for (int i = 1; i <= 16; i++) a.Add(FaceWidth * i / 16.0);
            return a.ToArray();
        }

        Mesh BuildMesh()
        {
            int nLat = (int)(2 * MaxLat / LatStep) + 1, nAcross = Across.Length;
            var verts = new Vector3[nLat * nAcross];
            var uvs = new Vector2[verts.Length];
            double R = body.Radius;
            for (int i = 0; i < nLat; i++)
            {
                double lat = -MaxLat + i * LatStep, latRad = lat * Math.PI / 180;
                double crest = (0.22 * latRad * latRad + 0.04 * Math.Sin(3 * latRad)) * 180 / Math.PI; // curved crest
                double taper = SmoothStep(MaxLat, 45, Math.Abs(lat));
                double along = Along(latRad);
                double metersPerDeg = R * Math.PI / 180 * Math.Max(Math.Cos(latRad), 0.05);
                for (int j = 0; j < nAcross; j++)
                {
                    double d = Across[j];
                    double h = CrestHeight * along * taper * Profile(d);
                    double lon = crest + d / metersPerDeg;
                    verts[i * nAcross + j] = pqs.InverseTransformPoint(body.GetWorldSurfacePosition(lat, lon, h));
                    // v: 0 = end of the back slope, 0.9 = crest, 1 = foot of the front; u repeats every ~5 km
                    double v = d <= 0 ? 0.9 * (1 + d / BackLength) : 0.9 + 0.1 * d / FaceWidth;
                    uvs[i * nAcross + j] = new Vector2((float)(i * LatStep * Math.PI / 180 * R / 5000), (float)v);
                }
            }
            var tris = new int[(nLat - 1) * (nAcross - 1) * 6];
            int n = 0;
            for (int i = 0; i < nLat - 1; i++)
                for (int j = 0; j < nAcross - 1; j++)
                {
                    int a = i * nAcross + j, b = a + nAcross;
                    tris[n++] = a; tris[n++] = a + 1; tris[n++] = b;
                    tris[n++] = b; tris[n++] = a + 1; tris[n++] = b + 1;
                }
            var mesh = new Mesh { name = "GargSys_MillerWave" };
            mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            mesh.vertices = verts;
            mesh.uv = uvs;
            mesh.triangles = tris;
            // the face must point away from the planet; if the winding came out reversed, flip it
            mesh.RecalculateNormals();
            int mid = (nLat / 2) * nAcross + nAcross / 2;
            if (Vector3.Dot(mesh.normals[mid], verts[mid].normalized) < 0)
            {
                for (int t = 0; t < tris.Length; t += 3) { int s = tris[t + 1]; tris[t + 1] = tris[t + 2]; tris[t + 2] = s; }
                mesh.triangles = tris;
                mesh.RecalculateNormals();
            }
            mesh.RecalculateBounds();
            return mesh;
        }

        static Material BuildMaterial()
        {
            Shader shader = Shader.Find("KSP/Specular") ?? Shader.Find("KSP/Diffuse");
            var m = new Material(shader);
            Texture2D tex = GameDatabase.Instance.GetTexture("GargantuaSystem/Textures/MillerWave", false);
            if (tex != null) { tex.wrapModeU = TextureWrapMode.Repeat; tex.wrapModeV = TextureWrapMode.Clamp; m.mainTexture = tex; }
            m.SetColor("_Color", new Color(0.85f, 0.9f, 0.9f));
            m.SetColor("_SpecColor", new Color(0.6f, 0.65f, 0.65f));
            m.SetFloat("_Shininess", 0.6f);
            return m;
        }

        static double SmoothStep(double e0, double e1, double x)
        {
            double t = Math.Max(0, Math.Min(1, (x - e0) / (e1 - e0)));
            return t * t * (3 - 2 * t);
        }
    }
}
