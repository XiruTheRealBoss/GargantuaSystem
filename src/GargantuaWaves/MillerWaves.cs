using System;
using UnityEngine;

namespace GargantuaSystem
{
    /// <summary>
    /// Ondas de maré gigantes de Miller que varrem o planeta.
    /// O Kopernicus não anima terreno (reconstruir o PQS leva segundos), então cada onda é uma malha própria,
    /// presa ao PQS de Miller e girando em volta do eixo do planeta. A posição vem do tempo universal:
    /// timewarp, save/load e cenas diferentes veem sempre a mesma onda no mesmo lugar.
    /// Interação analítica (sem colisor): a nave que fica abaixo da superfície da onda é erguida e arrastada junto,
    /// como no filme. Um MeshCollider móvel não funciona aqui: sem Rigidbody ele não acorda naves paradas (a onda
    /// atravessava), e com Rigidbody a origem flutuante do KSP descola a malha do planeta.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.Flight, false)]
    public class MillerWaves : MonoBehaviour
    {
        const string BodyName = "Miller";
        const int WaveCount = 5;
        const double CrestHeight = 1200;   // m (o filme fala em ~4000 pés); liberdade criativa na escala
        const double Speed = 100;          // m/s no equador: uma onda passa por cada ponto a cada ~2,3 h
        const double WarnTime = 180;       // s: a onda chegando para a aceleração do tempo e avisa
        const double FaceWidth = 2600;     // m: frente íngreme
        const double BackWidth = 14000;    // m: escala da encosta de trás (gaussiana)
        const double BackLength = 40000;   // m: onde a encosta de trás já está a ~0 m
        const double MaxLat = 72;          // graus: as ondas morrem antes dos polos
        const double LatStep = 0.1;        // graus ao longo da crista (~1,1 km em Miller)

        CelestialBody body;
        Transform pqs;
        Vector3 polarAxis;                 // eixo norte em coordenadas locais do PQS
        float rotationSign;                // + ou −, para a rotação andar para leste (frente da onda na frente)
        Transform[] waves;
        double angularSpeed;               // graus/s
        double lastWarnUT = double.MinValue;

        void Start()
        {
            body = FlightGlobals.GetBodyByName(BodyName);
            if (body == null || body.pqsController == null)
            {
                Debug.Log("[GargantuaSystem] MillerWaves: corpo " + BodyName + " não encontrado, ondas desligadas");
                Destroy(this);
                return;
            }
            pqs = body.pqsController.transform;
            angularSpeed = Speed / body.Radius * 180 / Math.PI;
            polarAxis = pqs.InverseTransformDirection((Vector3)(body.GetWorldSurfacePosition(90, 0, 0) - body.position)).normalized;

            // Qual sentido de rotação aumenta a longitude? Testado na hora, sem depender da convenção do KSP.
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
                go.layer = 15; // Local Scenery: as naves colidem como colidem com o terreno
                go.transform.SetParent(pqs, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>().sharedMaterial = material;
                waves[k] = go.transform;
            }
            Debug.Log("[GargantuaSystem] MillerWaves: " + WaveCount + " ondas, " + mesh.vertexCount + " vértices, sinal " + rotationSign
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

        /// Em timewarp a nave fica "em trilhos" e a onda passa sem ninguém ver. Quando uma crista vai chegar,
        /// para a aceleração do tempo e avisa ("isso não é uma montanha").
        void Alarm(Vessel v, double t)
        {
            if (v == null || v.mainBody != body || Math.Abs(v.latitude) > MaxLat || v.altitude > 3 * CrestHeight) return;
            double eta = TimeToNextCrest(v.latitude, v.longitude, t);
            // num passo de física o tempo pode pular mais que WarnTime em warp alto: a janela cresce com o warp
            double window = Math.Max(WarnTime, TimeWarp.CurrentRate * TimeWarp.fixedDeltaTime * 3);
            if (eta > window || t - lastWarnUT < 600) return;
            lastWarnUT = t;
            if (TimeWarp.CurrentRateIndex > 0) TimeWarp.SetRate(0, true);
            double km = eta * Speed * Math.Cos(v.latitude * Math.PI / 180) / 1000;
            ScreenMessages.PostScreenMessage(KSP.Localization.Localizer.Format("#LOC_GargSys_WaveWarning", km.ToString("F0")),
                10f, ScreenMessageStyle.UPPER_CENTER);
        }

        /// Segundos até a próxima crista passar por (lat, lon). As ondas andam para leste a velocidade angular fixa.
        public double TimeToNextCrest(double lat, double lon, double t)
        {
            double latRad = lat * Math.PI / 180;
            double crestOffset = (0.22 * latRad * latRad + 0.04 * Math.Sin(3 * latRad)) * 180 / Math.PI;
            double best = double.MaxValue;
            for (int k = 0; k < WaveCount; k++)
            {
                double crest = k * 360.0 / WaveCount + 23 + angularSpeed * t + crestOffset;
                double ahead = ((lon - crest) % 360 + 360) % 360; // graus que a crista ainda tem que andar até aqui
                best = Math.Min(best, ahead / angularSpeed);
            }
            return best;
        }

        /// Altura da onda (m acima do mar) num ponto, num instante. Mesma fórmula da malha.
        double WaveHeight(double lat, double lon, double t)
        {
            double latRad = lat * Math.PI / 180;
            double metersPerDeg = body.Radius * Math.PI / 180 * Math.Max(Math.Cos(latRad), 0.05);
            double crestOffset = (0.22 * latRad * latRad + 0.04 * Math.Sin(3 * latRad)) * 180 / Math.PI;
            double h = 0;
            for (int k = 0; k < WaveCount; k++)
            {
                double crest = k * 360.0 / WaveCount + 23 + angularSpeed * t + crestOffset;
                double dDeg = ((lon - crest) % 360 + 540) % 360 - 180; // −180..180, positivo = na frente (leste)
                h = Math.Max(h, CrestHeight * Along(latRad) * SmoothStep(MaxLat, 45, Math.Abs(lat)) * Profile(dDeg * metersPerDeg));
            }
            return h;
        }

        /// Ergue e arrasta uma nave que está "dentro" da onda: leva a velocidade para (leste a Speed, para cima
        /// proporcional à profundidade). Aceleração limitada para não virar Kraken.
        void Push(Vessel v, double t)
        {
            double h = WaveHeight(v.latitude, v.longitude, t);
            // h < 2 m = mar aberto: naves boiando ficam a ~−0,1 m e seriam "engolidas" pelo mar parado
            if (h < 2 || v.altitude >= h) return;
            double depth = h - v.altitude;
            Vector3d pos = v.CoMD;
            Vector3d up = (pos - body.position).normalized;
            Vector3d east = (body.GetWorldSurfacePosition(v.latitude, v.longitude + 0.001, v.altitude) - body.GetWorldSurfacePosition(v.latitude, v.longitude, v.altitude)).normalized;
            Vector3d target = east * (Speed * Math.Cos(v.latitude * Math.PI / 180)) + up * Math.Min(depth * 0.5, 60);
            Vector3d acc = (target - v.srf_velocity) * 1.5 + up * FlightGlobals.getGeeForceAtPosition(pos).magnitude;
            if (acc.magnitude > 40) acc = acc.normalized * 40;
            foreach (Part p in v.parts)
                if (p.rb != null) p.rb.AddForce(acc, ForceMode.Acceleration);
        }

        static double Along(double latRad) => 0.75 + 0.15 * Math.Sin(7 * latRad) + 0.10 * Math.Sin(13 * latRad + 1);

        /// Checagem rápida do perfil e da altura (cai no log se alguém mexer na forma e quebrar).
        void SelfCheck()
        {
            bool ok = Math.Abs(Profile(0) - 1) < 1e-9 && Profile(FaceWidth) == 0 && Profile(-BackLength) < 1e-3
                && Profile(FaceWidth / 2) > 0 && Profile(-BackWidth) < Profile(-BackWidth / 2);
            double crestNow = 23 + angularSpeed * Planetarium.GetUniversalTime();
            double hCrest = WaveHeight(0, crestNow, Planetarium.GetUniversalTime());
            ok &= hCrest > 0.6 * CrestHeight && WaveHeight(0, crestNow + 36, Planetarium.GetUniversalTime()) < 1;
            ok &= Math.Abs(TimeToNextCrest(0, crestNow + 1, Planetarium.GetUniversalTime()) - 1 / angularSpeed) < 1;
            if (!ok) Debug.LogError("[GargantuaSystem] MillerWaves: self-check do perfil FALHOU (crista " + hCrest.ToString("F0") + " m)");
        }

        void OnDestroy()
        {
            if (waves == null) return;
            foreach (Transform w in waves)
                if (w != null) Destroy(w.gameObject);
        }

        /// Altura (m) a uma distância d (m) da crista, positiva para a frente (leste). Mesmo perfil das versões estáticas.
        public static double Profile(double d)
        {
            if (d >= 0) return d >= FaceWidth ? 0 : Math.Pow(1 - d / FaceWidth, 1.6);
            return Math.Exp(-(d / BackWidth) * (d / BackWidth));
        }

        // Distâncias do perfil: densas na frente (onde a forma muda rápido), esparsas na encosta de trás
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
                double crest = (0.22 * latRad * latRad + 0.04 * Math.Sin(3 * latRad)) * 180 / Math.PI; // crista curva
                double taper = SmoothStep(MaxLat, 45, Math.Abs(lat));
                double along = Along(latRad);
                double metersPerDeg = R * Math.PI / 180 * Math.Max(Math.Cos(latRad), 0.05);
                for (int j = 0; j < nAcross; j++)
                {
                    double d = Across[j];
                    double h = CrestHeight * along * taper * Profile(d);
                    double lon = crest + d / metersPerDeg;
                    verts[i * nAcross + j] = pqs.InverseTransformPoint(body.GetWorldSurfacePosition(lat, lon, h));
                    // v: 0 = fim da encosta de trás, 0,9 = crista, 1 = pé da frente; u repete a cada ~5 km
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
            // a face precisa olhar para fora do planeta; se o enrolamento saiu ao contrário, inverte
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
