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


def save_height16(path, a):
    """16-bit height for KopernicusExpansion's VertexHeightMap16: value = (G << 8 | B) / 65535.

    8-bit maps gave ~24 m steps on Mann/Edmunds (and land strips in Miller's 3 m deep sea).
    """
    v = (np.clip(a, 0, 1) * 65535).round().astype(np.uint16)
    rgb = np.stack([np.zeros_like(v), v >> 8, v & 0xFF], axis=-1).astype(np.uint8)
    Image.fromarray(rgb, "RGB").save(path)
    back = (rgb[..., 1].astype(np.uint32) << 8 | rgb[..., 2]) / 65535
    assert np.abs(back - np.clip(a, 0, 1)).max() < 1 / 65535, "16-bit height encoding broken"


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
# The giant waves are NOT terrain any more: they move, so the plugin (src/GargantuaWaves) draws them.
# Terrain is just the shallow sea floor (VertexHeightOffset in Miller.cfg); this makes the sea colour and biomes.
MILLER_BIOMES = {
    "Shallows": "#2E6F8E",
    "PolarShallows": "#1B3A4B",
}


def make_miller(out):
    W, H = 4096, 2048
    streak = render(W, H, lambda la, lo, xyz: fbm(xyz * np.float32([1, 4, 1]), 12.0, 4, 300))
    # film: dark grey-green water, almost no blue
    rgb = np.float32([0.14, 0.19, 0.20]) * (0.92 + 0.16 * streak)[..., None]
    check_seamless(streak, "Miller colour")
    save_rgb(out / "Miller_color.png", rgb, np.full(streak.shape, 1.0, np.float32))  # alpha = gloss: shiny sea
    lat = (0.5 - (np.arange(H) + 0.5) / H)[:, None] * np.pi * np.ones((1, W))
    idx = (np.abs(lat) > np.radians(72)).astype(np.uint8)
    biome_map(downsample_idx(idx, 4), MILLER_BIOMES).save(out / "Miller_biomes.png")
    check_biomes_in_cfg("Miller", MILLER_BIOMES)
    return "sea colour and biomes"


def downsample_idx(idx, f):
    return idx[f // 2::f, f // 2::f]


# ---------------------------------------------------------------- Mann
# Reference: the film shot Mann's planet on the Svinafellsjokull glacier (Iceland): crumpled grey-white ice,
# folded ridges and hummocks, deep crevasses, dark streaks of volcanic ash, under a white overcast sky.
MANN_R = 500_000
MANN_HEIGHT = dict(offset=-800.0, deformity=6000.0)
MANN_BIOMES = {
    "IcePlains": "#DDE8F0",
    "PressureRidges": "#9FB7CC",
    "CrevasseFields": "#4C6680",
    "FrozenHighlands": "#FFFFFF",
    "Poles": "#B8D4E8",
}


def mann_fields(lat, lon, xyz):
    p = warp(xyz, 0.3, 1.5, 11)
    sheet = fbm(p, 1.8, 5, 12)  # broad ice sheet swells (~250 km)
    folds = ridged(warp(xyz, 0.25, 6.0, 13), 8.0, 5, 23)  # folded pressure ridges (~60 km)
    hummocks = ridged(warp(xyz, 0.08, 20.0, 14), 30.0, 4, 24)  # crumpled hummocky ice (~15 km)
    highland = smoothstep(0.55, 0.58, fbm(p, 1.2, 4, 41))  # ice plateaus with steep cliff edges
    field = smoothstep(0.45, 0.55, fbm(p, 2.0, 3, 43))
    cracks = (1 - smoothstep(0.0, 0.05, worley_edges(warp(xyz, 0.04, 10.0, 44), 40.0, 45))) * field
    ash = smoothstep(0.55, 0.80, fbm(warp(xyz * np.float32([1, 5, 1]), 0.2, 4.0, 46), 6.0, 4, 47))
    h = 1200 * sheet + 1800 * folds**2 + 450 * hummocks + 900 * highland - 450 * cracks
    return (h.astype(np.float32), cracks.astype(np.float32), highland.astype(np.float32),
            ash.astype(np.float32), folds.astype(np.float32))


def make_mann(out):
    W, H = 4096, 2048
    h, cracks, highland, ash, folds = render(W, H, mann_fields)
    enc = (h - MANN_HEIGHT["offset"]) / MANN_HEIGHT["deformity"]
    assert 0 <= enc.min() and enc.max() <= 1, f"Mann height out of range {h.min():.0f}..{h.max():.0f} m"
    check_seamless(enc, "Mann height")
    save_height16(out / "Mann_height.png", enc)

    t = (h - h.min()) / (h.max() - h.min())
    # low-saturation glacier greys, brighter on top of ridges; ash bands and crevasses darken it
    ice = ramp(t, [0, 0.3, 0.6, 1.0],
               [[0.70, 0.72, 0.74], [0.84, 0.85, 0.86], [0.92, 0.93, 0.94], [0.98, 0.98, 0.99]])
    ice *= (0.92 + 0.12 * folds)[..., None]
    rgb = ice * (1 - 0.55 * ash[..., None]) + ash[..., None] * 0.55 * np.float32([0.30, 0.30, 0.31])
    rgb = rgb * (1 - 0.8 * cracks[..., None]) + cracks[..., None] * 0.8 * np.float32([0.14, 0.16, 0.18])
    save_rgb(out / "Mann_color.png", rgb, np.full(h.shape, 0.55, np.float32))
    nm = normal_map(downsample(h, 2), MANN_R, 1.5)
    save_rgb(out / "Mann_normal.png", nm[..., :3], nm[..., 3])

    lat = (0.5 - (np.arange(H) + 0.5) / H)[:, None] * np.pi * np.ones((1, W))
    idx = np.zeros(h.shape, np.uint8)
    idx[folds > 0.55] = 1
    idx[cracks > 0.5] = 2
    idx[highland > 0.6] = 3
    idx[np.abs(lat) > np.radians(70)] = 4
    biome_map(downsample_idx(idx, 4), MANN_BIOMES).save(out / "Mann_biomes.png")
    check_biomes_in_cfg("Mann", MANN_BIOMES)
    return f"height {h.min():.0f}..{h.max():.0f} m"


# ---------------------------------------------------------------- Edmunds
# Reference: the film's closing shot of Edmunds: a boulder-strewn grey-tan rocky plain with jagged mountain
# ranges on the horizon (Mojave-like), not a sand sea. Dunes and salt flats are small, local features.
EDMUNDS_R = 600_000
EDMUNDS_HEIGHT = dict(offset=-1200.0, deformity=6500.0)
EDMUNDS_BIOMES = {
    "RockyPlains": "#8C7B66",
    "Mountains": "#4A3E34",
    "SaltFlats": "#F2EEE4",
    "DuneFields": "#E0B070",
    "Canyons": "#3A2418",
}


def edmunds_fields(lat, lon, xyz):
    p = warp(xyz, 0.35, 1.2, 51)
    plains = fbm(p, 1.5, 5, 52)
    belts = smoothstep(0.44, 0.58, fbm(warp(xyz, 0.5, 1.0, 61), 2.0, 3, 62))  # where mountain ranges run
    peaks = ridged(warp(xyz, 0.15, 4.0, 63), 5.0, 6, 64) ** 2.2  # jagged ridgelines
    hills = ridged(warp(xyz, 0.05, 12.0, 65), 16.0, 5, 65)  # rugged ~30 km hills and bluffs everywhere
    basin = smoothstep(0.36, 0.28, plains) * (1 - belts)  # dry lake beds
    dune_mask = smoothstep(0.64, 0.72, fbm(p, 2.5, 3, 66)) * (1 - belts) * (1 - basin)
    # dunes: crests bent by the wind; lon multiplier is an integer so it wraps at 180°
    dunes = 0.5 + 0.5 * np.sin(lon * 700 + lat * 260 + 25 * fbm(xyz, 5.0, 3, 54))
    region = smoothstep(0.62, 0.70, fbm(p, 1.3, 3, 57)) * (1 - dune_mask)
    canyon = (1 - smoothstep(0.0, 0.02, worley_edges(warp(xyz, 0.12, 3.0, 58), 6.0, 59))) * region
    h = (900 * plains + 3600 * peaks * belts + 900 * hills**1.5 + 60 * dunes * dune_mask
         - 700 * canyon - 200 * basin)
    return (h.astype(np.float32), belts.astype(np.float32), peaks.astype(np.float32), canyon.astype(np.float32),
            basin.astype(np.float32), dune_mask.astype(np.float32), dunes.astype(np.float32), hills.astype(np.float32))


def make_edmunds(out):
    W, H = 4096, 2048
    h, belts, peaks, canyon, basin, dune_mask, dunes, hills = render(W, H, edmunds_fields)
    enc = (h - EDMUNDS_HEIGHT["offset"]) / EDMUNDS_HEIGHT["deformity"]
    assert 0 <= enc.min() and enc.max() <= 1, f"Edmunds height out of range {h.min():.0f}..{h.max():.0f} m"
    check_seamless(enc, "Edmunds height")
    save_height16(out / "Edmunds_height.png", enc)

    t = (h - h.min()) / (h.max() - h.min())
    # muted grey-tan gravel plains, darker brown-grey rock in the ranges, pale tops
    rock = ramp(t, [0, 0.3, 0.6, 1.0],
                [[0.42, 0.37, 0.32], [0.56, 0.49, 0.41], [0.50, 0.44, 0.38], [0.70, 0.66, 0.62]])
    rock *= (0.88 + 0.2 * hills)[..., None]
    mountain = (belts * smoothstep(0.15, 0.4, peaks))[..., None]
    rgb = rock * (1 - 0.5 * mountain) + mountain * 0.5 * np.float32([0.34, 0.29, 0.25])
    dune_col = ramp(dunes, [0, 1], [[0.70, 0.58, 0.42], [0.84, 0.72, 0.54]])
    rgb = rgb * (1 - dune_mask[..., None]) + dune_col * dune_mask[..., None]
    rgb = rgb * (1 - basin[..., None]) + basin[..., None] * np.float32([0.86, 0.84, 0.78])
    rgb *= (1 - 0.45 * canyon)[..., None]
    save_rgb(out / "Edmunds_color.png", rgb, np.full(h.shape, 0.2, np.float32))
    nm = normal_map(downsample(h, 2), EDMUNDS_R, 1.5)
    save_rgb(out / "Edmunds_normal.png", nm[..., :3], nm[..., 3])

    idx = np.zeros(h.shape, np.uint8)  # rocky plains by default
    idx[mountain[..., 0] > 0.5] = 1
    idx[basin > 0.5] = 2
    idx[dune_mask > 0.5] = 3
    idx[canyon > 0.5] = 4
    biome_map(downsample_idx(idx, 4), EDMUNDS_BIOMES).save(out / "Edmunds_biomes.png")
    check_biomes_in_cfg("Edmunds", EDMUNDS_BIOMES)
    return f"height {h.min():.0f}..{h.max():.0f} m"


BODIES = {"miller": make_miller, "mann": make_mann, "edmunds": make_edmunds}


def main():
    names = [a.lower() for a in sys.argv[1:]] or list(BODIES)
    for name in names:
        out = OUT / name.capitalize()
        out.mkdir(parents=True, exist_ok=True)
        print(f"{name}: {BODIES[name](out)}", flush=True)


if __name__ == "__main__":
    main()
