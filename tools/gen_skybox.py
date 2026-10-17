# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
"""Gera a skybox (cubemap de 6 faces) usada com a SigmaReplacements-SkyBox (opcional).

Uso: uv run tools/gen_skybox.py
Saída: GameData/GargantuaSystem/Textures/Skybox/Gargantua_<Face>.png e Black_<Face>.png
Estrelas e faixa galáctica são calculadas pela DIREÇÃO 3D de cada pixel, então as faces se encaixam
sem costura independentemente da resolução.
"""
from pathlib import Path

import numpy as np
from PIL import Image

from gen_planets import fbm, warp

OUT = Path(__file__).resolve().parent.parent / "GameData" / "GargantuaSystem" / "Textures" / "Skybox"
N = 2048
# Unity cubemap face basis: direction = forward + u * right + v * up  (u, v in -1..1, v up)
FACES = {
    "PositiveX": (np.array([1, 0, 0]), np.array([0, 0, -1]), np.array([0, 1, 0])),
    "NegativeX": (np.array([-1, 0, 0]), np.array([0, 0, 1]), np.array([0, 1, 0])),
    "PositiveY": (np.array([0, 1, 0]), np.array([1, 0, 0]), np.array([0, 0, -1])),
    "NegativeY": (np.array([0, -1, 0]), np.array([1, 0, 0]), np.array([0, 0, 1])),
    "PositiveZ": (np.array([0, 0, 1]), np.array([1, 0, 0]), np.array([0, 1, 0])),
    "NegativeZ": (np.array([0, 0, -1]), np.array([-1, 0, 0]), np.array([0, 1, 0])),
}
GALACTIC_NORMAL = np.array([0.35, 0.80, 0.48]) / np.linalg.norm([0.35, 0.80, 0.48])


def _hash3(c, seed):
    h = (c[..., 0] * 73856093) ^ (c[..., 1] * 19349663) ^ (c[..., 2] * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFFFF).astype(np.float32) / 0xFFFFFF


def stars(d, scale, density, seed, size):
    """Point stars: one candidate per 3D cell, kept with probability `density`."""
    q = d * scale
    # floor(q - 0.5) + {0,1} covers every star within 0.5 cell of the pixel (stars are <= 0.25 cell wide)
    cell = np.floor(q - 0.5).astype(np.int64)
    out = np.zeros(d.shape[:-1], np.float32)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                c = cell + np.array([dx, dy, dz])
                pos = c + np.stack([_hash3(c, seed + k) for k in range(3)], -1)
                keep = _hash3(c, seed + 7) < density
                mag = _hash3(c, seed + 9) ** 6  # few bright stars, many faint
                dist = np.linalg.norm(pos - q, axis=-1)
                out += keep * mag * np.exp(-(dist / size) ** 2)
    return out


def face(fwd, right, up):
    v, u = np.mgrid[1:-1:N * 1j, -1:1:N * 1j]
    d = fwd + u[..., None] * right + v[..., None] * up
    d = (d / np.linalg.norm(d, axis=-1, keepdims=True)).astype(np.float32)
    b = d @ GALACTIC_NORMAL  # 0 on the galactic plane
    band = np.exp(-(b / 0.18) ** 2)
    glow = band * (0.4 + 0.6 * fbm(warp(d, 0.3, 2.0, 301), 4.0, 6, 302))
    dust = band * np.clip((fbm(warp(d, 0.2, 3.0, 303), 9.0, 5, 304) - 0.45) / 0.25, 0, 1)
    milky = np.clip(glow * (1 - 0.85 * dust), 0, 1)
    s = stars(d, 900, 0.08, 11, 0.25) * (1 + 3 * band) + stars(d, 250, 0.05, 12, 0.2) * 2.5
    warm = np.array([1.0, 0.86, 0.70], np.float32)
    cool = np.array([0.78, 0.86, 1.0], np.float32)
    color = 0.035 * milky[..., None] * warm + np.clip(s, 0, 1.5)[..., None] * np.where(
        (_hash3(np.floor(d * 900).astype(np.int64), 13) > 0.5)[..., None], warm, cool)
    return np.clip(color, 0, 1)


def main():
    check_edges()  # cheap: fail before the slow render
    OUT.mkdir(parents=True, exist_ok=True)
    for name, basis in FACES.items():
        img = face(*basis)
        Image.fromarray((img * 255).round().astype(np.uint8), "RGB").save(OUT / f"Gargantua_{name}.png")
        Image.fromarray(np.zeros((8, 8, 3), np.uint8), "RGB").save(OUT / f"Black_{name}.png")
        print(name, f"brilho médio {img.mean():.4f}", flush=True)
    check_edges()


def check_edges():
    """Pixel-exact seam check: each face edge must point at the same 3D directions as its neighbour's edge
    (a rotated or mirrored face fails here; comparing average brightness did not)."""
    v = np.linspace(1, -1, 64)[:, None]

    def edge(face, u):
        fwd, right, up = FACES[face]
        d = fwd + u * right + v * up
        return d / np.linalg.norm(d, axis=-1, keepdims=True)

    ring = ["PositiveX", "NegativeZ", "NegativeX", "PositiveZ"]  # going right around the horizon
    for a, b in zip(ring, ring[1:] + ring[:1]):
        assert np.allclose(edge(a, 1), edge(b, -1)), f"seam {a}/{b} does not line up"

if __name__ == "__main__":
    main()
