# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
"""Gera os mapas procedurais dos planetas (altura, cor, normais, biomas).

Uso: uv run tools/gen_planets.py [miller|mann|edmunds ...]
Saída: GameData/GargantuaSystem/PluginData/<Planeta>/
Todos os mapas são equiretangulares (2:1) amostrados em 3D na esfera, sem costura na longitude e sem
distorção nos polos. As cores dos biomas são conferidas contra os .cfg dos corpos no fim.
"""
import re
import zlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent / "GameData" / "GargantuaSystem"
OUT = ROOT / "PluginData"
CFG = ROOT / "Configs" / "Bodies"
CHUNK = 256  # rows per chunk: keeps 8k maps under ~1 GB of temporaries


# ---------------------------------------------------------------- noise on the sphere
def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFFFF).astype(np.float32) / 0xFFFFFF


_GRADS = np.array([[1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0], [1, 0, 1], [-1, 0, 1],
                   [1, 0, -1], [-1, 0, -1], [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1]], np.float32)


def _rotation(seed):
    """Fixed random rotation per octave/seed: hides the axis-aligned lattice of the noise."""
    q, _ = np.linalg.qr(np.random.default_rng(seed).normal(size=(3, 3)))
    return q.astype(np.float32)


def value_noise(p, seed):
    """3D gradient (Perlin) noise remapped to 0..1. p: (..., 3) float."""
    p = p @ _rotation(seed)
    pi = np.floor(p).astype(np.int64)
    f = (p - pi).astype(np.float32)
    u = f * f * f * (f * (f * 6 - 15) + 10)  # quintic fade: no grid creases
    x, y, z = pi[..., 0], pi[..., 1], pi[..., 2]

    def corner(a, b, d):
        g = _GRADS[(_hash(x + a, y + b, z + d, seed) * 12).astype(np.int64) % 12]
        return g[..., 0] * (f[..., 0] - a) + g[..., 1] * (f[..., 1] - b) + g[..., 2] * (f[..., 2] - d)

    ux, uy, uz = u[..., 0], u[..., 1], u[..., 2]
    x00 = corner(0, 0, 0) + (corner(1, 0, 0) - corner(0, 0, 0)) * ux
    x10 = corner(0, 1, 0) + (corner(1, 1, 0) - corner(0, 1, 0)) * ux
    x01 = corner(0, 0, 1) + (corner(1, 0, 1) - corner(0, 0, 1)) * ux
    x11 = corner(0, 1, 1) + (corner(1, 1, 1) - corner(0, 1, 1)) * ux
    n = (x00 + (x10 - x00) * uy) * (1 - uz) + (x01 + (x11 - x01) * uy) * uz
    return np.clip(n * 0.75 + 0.5, 0, 1)


def fbm(p, freq, octaves, seed, gain=0.5):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total = total + amp * value_noise(p * freq * 2**o, seed + o)
        norm += amp
        amp *= gain
    return total / norm


def ridged(p, freq, octaves, seed):
    """Sharp ridge lines (ice pressure ridges, crests): 1 at the ridge, falling off fast."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        n = 1 - np.abs(2 * value_noise(p * freq * 2**o, seed + 31 * o) - 1)
        total = total + amp * n * n
        norm += amp
        amp *= 0.5
    return total / norm


def warp(p, amount, freq, seed):
    """Domain warping: bends straight noise features into organic, flowing shapes."""
    d = np.stack([fbm(p, freq, 3, seed + 7 * i) - 0.5 for i in range(3)], axis=-1)
    return p + amount * d


def worley_edges(p, freq, seed):
    """Cellular noise F2 - F1: ~0 on the borders between cells -> polygonal crack / canyon networks."""
    q = p * freq
    cell = np.floor(q).astype(np.int64)
    f1 = np.full(q.shape[:-1], 9.0, np.float32)
    f2 = np.full(q.shape[:-1], 9.0, np.float32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = cell + np.array([dx, dy, dz])
                fp = np.stack([_hash(c[..., 0], c[..., 1], c[..., 2], seed + 101 * k) for k in range(3)], -1)
                dist = np.linalg.norm(c + fp - q, axis=-1).astype(np.float32)
                f2 = np.where(dist < f1, f1, np.minimum(f2, dist))
                f1 = np.minimum(f1, dist)
    return f2 - f1


def sphere_grid(w, h, r0, r1):
    """Rows r0..r1 of an equirectangular grid: (lat, lon, xyz)."""
    lat = (0.5 - (np.arange(r0, r1) + 0.5) / h) * np.pi
    lon = ((np.arange(w) + 0.5) / w) * 2 * np.pi - np.pi
    lat, lon = np.meshgrid(lat, lon, indexing="ij")
    cl = np.cos(lat)
    xyz = np.stack([cl * np.cos(lon), np.sin(lat), cl * np.sin(lon)], axis=-1).astype(np.float32)
    return lat.astype(np.float32), lon.astype(np.float32), xyz


def render(w, h, fn):
    """Calls fn(lat, lon, xyz) chunk by chunk and stacks the results along rows."""
    parts = [fn(*sphere_grid(w, h, r, min(r + CHUNK, h))) for r in range(0, h, CHUNK)]
    if isinstance(parts[0], tuple):
        return tuple(np.concatenate(k, axis=0) for k in zip(*parts))
    return np.concatenate(parts, axis=0)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def ramp(x, stops, colors):
    colors = np.asarray(colors, dtype=np.float32)
    return np.stack([np.interp(x, stops, colors[:, c]) for c in range(colors.shape[1])], axis=-1)


# ---------------------------------------------------------------- outputs
def save_gray(path, a):
    Image.fromarray((np.clip(a, 0, 1) * 255).round().astype(np.uint8), "L").save(path)


def save_rgb(path, rgb, alpha=None):
    a = np.clip(rgb, 0, 1)
    if alpha is not None:
        a = np.concatenate([a, np.clip(alpha, 0, 1)[..., None]], axis=-1)
    Image.fromarray((a * 255).round().astype(np.uint8), "RGBA" if alpha is not None else "RGB").save(path)


def normal_map(height_m, radius_m, strength=1.0):
    """Tangent-space normals for the scaled body, from a height field in metres.

    Written as R = x, G = y, B = z, A = x so Unity's UnpackNormal reads it both as RGB and as DXT5nm (AG).
    """
    h, w = height_m.shape
    lat = (0.5 - (np.arange(h) + 0.5) / h) * np.pi
    dx = 2 * np.pi * radius_m * np.maximum(np.cos(lat), 0.05)[:, None] / w
    dy = np.pi * radius_m / h
    gx = (np.roll(height_m, -1, axis=1) - np.roll(height_m, 1, axis=1)) / (2 * dx)
    gy = (np.vstack([height_m[:1], height_m[:-1]]) - np.vstack([height_m[1:], height_m[-1:]])) / (2 * dy)
    n = np.stack([-gx * strength, -gy * strength, np.ones_like(gx)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    enc = n * 0.5 + 0.5
    return np.concatenate([enc, enc[..., :1]], axis=-1)


def biome_map(index, palette):
    """index: int array of biome ids -> RGB image with exact (unfiltered) colours."""
    rgb = np.array([_hex(c) for c in palette.values()], dtype=np.uint8)
    return Image.fromarray(rgb[index], "RGB")


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def downsample(a, factor):
    h, w = a.shape[:2]
    return a.reshape(h // factor, factor, w // factor, factor, *a.shape[2:]).mean(axis=(1, 3))


def check_seamless(a, name):
    wrap = np.abs(a[:, 0].astype(float) - a[:, -1].astype(float)).mean()
    step = np.abs(np.diff(a.astype(float), axis=1)).mean()
    assert wrap <= 4 * step + 1e-6, f"{name}: seam at longitude 180 (wrap {wrap:.3f} vs step {step:.3f})"


def check_biomes_in_cfg(body, palette):
    """Every biome colour written to the map must be declared in the body's .cfg (or the biome is lost)."""
    text = (CFG / f"{body}.cfg").read_text(encoding="utf-8")
    declared = {m.lower() for m in re.findall(r"color\s*=\s*(#[0-9A-Fa-f]{6})", text)}
    missing = {n: c for n, c in palette.items() if c.lower() not in declared}
    assert not missing, f"{body}: biome colours missing from {body}.cfg: {missing}"


# ---------------------------------------------------------------- Miller
MILLER_R = 650_000
MILLER_WAVE_H = 1200.0  # ~4000 ft in the film; kept in metres (creative liberty on the scale)
MILLER_HEIGHT = dict(offset=-3.0, deformity=1260.0)  # floor = -3 m (knee-deep), crest ~ +1250 m
MILLER_BIOMES = {
    "Shallows": "#2E6F8E",
    "WaveSlopes": "#4FA3C7",
    "WaveCrests": "#E8F4F8",
    "PolarShallows": "#1B3A4B",
}


def miller_height(lat, lon, xyz, waves=5):
    """Ocean floor a few metres under the surface plus giant, static tidal waves.

    Each wave is a long crest bent like an arc, steep concave face on the leading (east) side, long gentle
    back on the west side, tapering out before the poles. Waves never overlap: the highest one wins.
    """
    rng = np.random.default_rng(7)
    h = np.zeros(lat.shape, np.float32)
    for k in range(waves):
        lon0 = -np.pi + 2 * np.pi * (k + rng.uniform(0.2, 0.8)) / waves
        crest = lon0 + 0.22 * lat**2 + 0.04 * np.sin(3 * lat + k)
        d = (np.angle(np.exp(1j * (lon - crest)))) * MILLER_R * np.maximum(np.cos(lat), 0.05)
        along = fbm(xyz, 3.0, 4, 100 + k)  # crest height wobbles along the wave
        height = MILLER_WAVE_H * (0.7 + 0.45 * along) * smoothstep(np.radians(72), np.radians(45), np.abs(lat))
        face = np.clip(1 + d / 2600.0, 0, 1) ** 1.6  # d < 0: leading face, ~2.6 km wide
        back = np.exp(-((d / 14000.0) ** 2))  # d > 0: trailing slope, ~14 km
        h = np.maximum(h, height * np.where(d < 0, face, back))
    return h


def make_miller(out):
    W, H = 8192, 4096  # ~0.5 km/px: the wave face is only a few km wide
    height = render(W, H, miller_height)
    floor_m = MILLER_HEIGHT["offset"]
    enc = height / MILLER_HEIGHT["deformity"]  # 0 = ocean floor at offset (-3 m)
    assert enc.max() <= 1.0 and height.max() > 0.8 * MILLER_WAVE_H, f"wave height {height.max():.0f} m"
    check_seamless(enc, "Miller height")
    save_gray(out / "Miller_height.png", enc)

    h4 = downsample(height, 2)  # 4096x2048 for colour, normals and biomes
    lat = (0.5 - (np.arange(h4.shape[0]) + 0.5) / h4.shape[0])[:, None] * np.pi * np.ones((1, h4.shape[1]))
    streak = render(4096, 2048, lambda la, lo, xyz: fbm(xyz * np.float32([1, 4, 1]), 12.0, 4, 300))
    t = np.clip(h4 / MILLER_WAVE_H, 0, 1)
    water = ramp(t, [0, 0.05, 0.45, 0.8, 0.92, 1.0],
                 [[0.16, 0.30, 0.36], [0.20, 0.38, 0.44], [0.30, 0.50, 0.56],
                  [0.48, 0.66, 0.70], [0.80, 0.88, 0.90], [0.96, 0.98, 1.0]])
    water *= (0.92 + 0.16 * streak)[..., None]
    foam = smoothstep(0.85, 0.97, t)[..., None]
    rgb = water * (1 - foam) + foam * np.float32(0.97)
    save_rgb(out / "Miller_color.png", rgb, 1 - 0.6 * t)  # alpha = gloss: shiny sea, rougher wave faces
    nm = normal_map(h4, MILLER_R, 1.0)
    save_rgb(out / "Miller_normal.png", nm[..., :3], nm[..., 3])

    idx = np.zeros(h4.shape, np.uint8)
    idx[h4 > 40] = 1
    idx[h4 > 0.75 * MILLER_WAVE_H] = 2
    idx[(np.abs(lat) > np.radians(72)) & (idx == 0)] = 3
    biome_map(downsample_idx(idx, 4), MILLER_BIOMES).save(out / "Miller_biomes.png")
    check_biomes_in_cfg("Miller", MILLER_BIOMES)
    return f"waves up to {height.max():.0f} m, floor {floor_m} m"


def downsample_idx(idx, f):
    return idx[f // 2::f, f // 2::f]


# ---------------------------------------------------------------- Mann
MANN_R = 500_000
MANN_HEIGHT = dict(offset=-500.0, deformity=5000.0)
MANN_BIOMES = {
    "IcePlains": "#DDE8F0",
    "PressureRidges": "#9FB7CC",
    "CrevasseFields": "#4C6680",
    "FrozenHighlands": "#FFFFFF",
    "Poles": "#B8D4E8",
}


def mann_fields(lat, lon, xyz):
    p = warp(xyz, 0.35, 1.5, 11)
    base = fbm(p, 2.0, 6, 12)
    ridges = ridged(warp(xyz, 0.2, 3.0, 13), 2.5, 5, 23)
    highland = smoothstep(0.50, 0.65, fbm(p, 1.0, 4, 41))
    # polygonal crack network (ice plates), only inside "crevasse field" regions
    field = smoothstep(0.48, 0.58, fbm(p, 1.6, 3, 43))
    cracks = (1 - smoothstep(0.0, 0.07, worley_edges(warp(xyz, 0.05, 6.0, 44), 14.0, 45))) * field
    h = 900 * base + 2400 * ridges**2.5 * (0.4 + 0.6 * highland) + 1100 * highland - 320 * cracks
    return h.astype(np.float32), cracks.astype(np.float32), highland.astype(np.float32)


def make_mann(out):
    W, H = 4096, 2048
    h, cracks, highland = render(W, H, mann_fields)
    enc = (h - MANN_HEIGHT["offset"]) / MANN_HEIGHT["deformity"]
    assert 0 <= enc.min() and enc.max() <= 1, f"Mann height out of range {h.min():.0f}..{h.max():.0f} m"
    check_seamless(enc, "Mann height")
    save_gray(out / "Mann_height.png", enc)

    t = (h - h.min()) / (h.max() - h.min())
    rgb = ramp(t, [0, 0.3, 0.6, 1.0],
               [[0.62, 0.70, 0.78], [0.80, 0.86, 0.91], [0.90, 0.94, 0.97], [1.0, 1.0, 1.0]])
    rgb = rgb * (1 - 0.55 * cracks[..., None]) + cracks[..., None] * np.float32([0.10, 0.18, 0.28])
    save_rgb(out / "Mann_color.png", rgb, np.full(h.shape, 0.55, np.float32))
    nm = normal_map(downsample(h, 2), MANN_R, 1.5)
    save_rgb(out / "Mann_normal.png", nm[..., :3], nm[..., 3])

    lat = (0.5 - (np.arange(H) + 0.5) / H)[:, None] * np.pi * np.ones((1, W))
    idx = np.zeros(h.shape, np.uint8)
    idx[t > 0.55] = 1
    idx[cracks > 0.5] = 2
    idx[highland > 0.6] = 3
    idx[np.abs(lat) > np.radians(70)] = 4
    biome_map(downsample_idx(idx, 4), MANN_BIOMES).save(out / "Mann_biomes.png")
    check_biomes_in_cfg("Mann", MANN_BIOMES)
    return f"height {h.min():.0f}..{h.max():.0f} m"


# ---------------------------------------------------------------- Edmunds
EDMUNDS_R = 600_000
EDMUNDS_HEIGHT = dict(offset=-1200.0, deformity=5000.0)
EDMUNDS_BIOMES = {
    "DuneSeas": "#E0B070",
    "Mesas": "#8A4A2A",
    "SaltFlats": "#F2EEE4",
    "RockyHighlands": "#6B5A4A",
    "Canyons": "#3A2418",
}


def edmunds_fields(lat, lon, xyz):
    p = warp(xyz, 0.4, 1.4, 51)
    base = fbm(p, 1.8, 6, 52)
    sand = smoothstep(0.50, 0.58, fbm(p, 1.1, 4, 53))  # 1 = dune sea (~1/3 of the surface)
    # dunes: parallel crests bent by the wind field; lon multiplier is an integer so it wraps at 180°
    dunes = 0.5 + 0.5 * np.sin(lon * 700 + lat * 260 + 25 * fbm(xyz, 5.0, 3, 54))
    plateau = fbm(warp(xyz, 0.3, 2.0, 55), 2.4, 5, 56)
    mesa_mask = smoothstep(0.56, 0.60, plateau) * (1 - sand)
    mesa = np.floor(plateau * 7) / 7  # terraced steps on the plateaus
    # branching canyon systems: warped cell borders, only in canyon regions and never in the sand
    region = smoothstep(0.50, 0.60, fbm(p, 1.3, 3, 57))
    canyon = (1 - smoothstep(0.0, 0.05, worley_edges(warp(xyz, 0.12, 3.0, 58), 6.0, 59))) * region * (1 - sand)
    salt = smoothstep(0.40, 0.34, base) * (1 - sand) * (1 - mesa_mask)
    h = (1400 * base + 1700 * mesa_mask * mesa + 70 * sand * dunes - 900 * canyon - 200 * salt)
    return (h.astype(np.float32), sand.astype(np.float32), mesa_mask.astype(np.float32),
            canyon.astype(np.float32), salt.astype(np.float32), dunes.astype(np.float32))


def make_edmunds(out):
    W, H = 4096, 2048
    h, sand, mesa, canyon, salt, dunes = render(W, H, edmunds_fields)
    enc = (h - EDMUNDS_HEIGHT["offset"]) / EDMUNDS_HEIGHT["deformity"]
    assert 0 <= enc.min() and enc.max() <= 1, f"Edmunds height out of range {h.min():.0f}..{h.max():.0f} m"
    check_seamless(enc, "Edmunds height")
    save_gray(out / "Edmunds_height.png", enc)

    t = (h - h.min()) / (h.max() - h.min())
    rock = ramp(t, [0, 0.35, 0.7, 1.0],
                [[0.36, 0.22, 0.14], [0.55, 0.36, 0.22], [0.66, 0.46, 0.30], [0.74, 0.60, 0.46]])
    dune_col = ramp(dunes, [0, 1], [[0.80, 0.58, 0.34], [0.93, 0.76, 0.50]])
    rgb = rock * (1 - sand[..., None]) + dune_col * sand[..., None]
    rgb = rgb * (1 - mesa[..., None] * 0.25) + mesa[..., None] * np.float32([0.50, 0.24, 0.13]) * 0.25
    rgb = rgb * (1 - salt[..., None]) + salt[..., None] * np.float32([0.94, 0.92, 0.86])
    rgb *= (1 - 0.45 * canyon)[..., None]
    save_rgb(out / "Edmunds_color.png", rgb, np.full(h.shape, 0.2, np.float32))
    nm = normal_map(downsample(h, 2), EDMUNDS_R, 1.5)
    save_rgb(out / "Edmunds_normal.png", nm[..., :3], nm[..., 3])

    idx = np.full(h.shape, 3, np.uint8)  # rocky highlands by default
    idx[sand > 0.5] = 0
    idx[mesa > 0.5] = 1
    idx[salt > 0.5] = 2
    idx[canyon > 0.5] = 4
    biome_map(downsample_idx(idx, 4), EDMUNDS_BIOMES).save(out / "Edmunds_biomes.png")
    check_biomes_in_cfg("Edmunds", EDMUNDS_BIOMES)
    return f"height {h.min():.0f}..{h.max():.0f} m"


# ---------------------------------------------------------------- PQS detail textures
# The triplanar PQS shader multiplies these tiling textures by the vertex colour (from *_color.png),
# so they are near-white with only fine structure: the colour comes from the planet map.
DETAILS = {
    # body: (stretch along x for streaks, contrast, fog ramp from ground colour to sky colour)
    "Miller": (6.0, 0.10, [[0.30, 0.45, 0.50], [0.55, 0.68, 0.75]]),
    "Mann": (1.5, 0.12, [[0.70, 0.78, 0.86], [0.80, 0.86, 0.95]]),
    "Edmunds": (1.0, 0.22, [[0.70, 0.50, 0.32], [0.86, 0.72, 0.56]]),
}


def tile_noise(rng, n, stretch, beta=1.4):
    """Seamless 2D noise (FFT), 0..1; stretch > 1 makes streaks along x (water, wind)."""
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    k = np.sqrt((fx * stretch) ** 2 + fy**2)
    amp = np.where(k > 0, 1 / np.maximum(k, 1e-6) ** beta, 0)
    f = np.fft.ifft2(amp * np.exp(2j * np.pi * rng.random((n, n)))).real
    return (f - f.min()) / (f.max() - f.min())


def make_details(body, n=1024):
    stretch, contrast, ramp_cols = DETAILS[body]
    rng = np.random.default_rng(zlib.crc32(body.encode()))  # stable seed (hash() is salted per run)
    t = tile_noise(rng, n, stretch)
    tex = np.clip(0.85 + contrast * (t - 0.5) * 2, 0, 1)
    out = OUT / body
    save_gray(out / f"{body}_detail.png", tex)
    h = t * 4.0  # fake height for a gentle tiling bump map
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2
    nrm = np.stack([-gx, -gy, np.ones_like(h)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    enc = nrm * 0.5 + 0.5
    save_rgb(out / f"{body}_detail_nrm.png", enc, enc[..., 0])
    ramp_img = ramp(np.linspace(0, 1, 256), [0, 1], ramp_cols)[None].repeat(4, 0)
    save_rgb(out / f"{body}_fogramp.png", ramp_img)
    check_seamless(tex, f"{body} detail")
    return "detail, normal and fog ramp"


BODIES = {"miller": make_miller, "mann": make_mann, "edmunds": make_edmunds,
          "details": lambda out: "; ".join(f"{b}: {make_details(b)}" for b in DETAILS)}


def main():
    names = [a.lower() for a in sys.argv[1:]] or list(BODIES)
    for b in DETAILS:
        (OUT / b).mkdir(parents=True, exist_ok=True)
    for name in names:
        print(f"{name}: {BODIES[name](OUT / name.capitalize())}", flush=True)


if __name__ == "__main__":
    main()
