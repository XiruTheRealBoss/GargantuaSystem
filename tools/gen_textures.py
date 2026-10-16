# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
"""Gera as texturas procedurais do Gargantua System.

Uso: uv run tools/gen_textures.py
Saída: GameData/GargantuaSystem/Textures/
"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "GameData" / "GargantuaSystem" / "Textures"
SEED = 1014  # fixed seed so builds are reproducible


def periodic_noise(rng, w, h, octaves=5):
    """Fractal noise that tiles horizontally (u = disk angle must wrap)."""
    out = np.zeros((h, w))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cw, ch = 4 * 2**o, 2 + 2**o
        grid = rng.random((ch + 1, cw))
        grid = np.concatenate([grid, grid[:, :1]], axis=1)  # wrap column -> seamless in u
        ys = np.linspace(0, ch, h)
        xs = np.linspace(0, cw, w, endpoint=False)
        y0, x0 = np.floor(ys).astype(int).clip(0, ch - 1), np.floor(xs).astype(int)
        fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        a, b = grid[y0][:, x0], grid[y0][:, x0 + 1]
        c, d = grid[y0 + 1][:, x0], grid[y0 + 1][:, x0 + 1]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
        total += amp
        amp *= 0.55
    return out / total


def accretion_disk(w=2048, h=512):
    """Radial-mapped disk (Singularity useRadialTextureMapping = True).

    u = angle (wraps), v = 0 at the inner edge -> 1 at the outer edge.
    Unity's LoadImage puts PNG row 0 at v = 1, so the inner edge is the bottom row.
    Look: thin, pale yellow-white disk like the film (no Doppler beaming), creative liberty on detail.
    """
    rng = np.random.default_rng(SEED)
    v = np.linspace(1, 0, h)[:, None]  # image top = outer edge
    streaks = periodic_noise(rng, w, h, 6)
    # thin concentric lanes: noise stretched along the angle
    lanes = 0.5 + 0.5 * np.sin(v * 140 + 6 * periodic_noise(rng, w, h, 3))
    heat = np.clip((1 - v) ** 1.6, 0, 1)  # hottest at the inner edge
    inner_fade = np.clip(v / 0.03, 0, 1)
    outer_fade = np.clip((1 - v) / 0.35, 0, 1) ** 1.5
    brightness = (0.35 + 0.65 * heat) * (0.55 + 0.3 * streaks + 0.15 * lanes)
    alpha = np.clip(inner_fade * outer_fade * (0.6 + 0.4 * streaks), 0, 1)
    hot, warm = np.array([1.0, 0.96, 0.86]), np.array([1.0, 0.62, 0.30])
    color = warm + (hot - warm) * heat[..., None]
    rgb = np.clip(color * brightness[..., None], 0, 1)
    rgba = np.concatenate([rgb, alpha[..., None]], axis=2)
    return (rgba * 255).round().astype(np.uint8)


def solid(rgba, size=8):
    return np.full((size, size, 4), rgba, dtype=np.uint8)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    disk = accretion_disk()
    # self-check: seamless in u, inner edge brighter than outer edge, transparent at the outer rim
    assert disk.shape == (512, 2048, 4)
    assert np.abs(disk[:, 0].astype(int) - disk[:, -1].astype(int)).mean() < 12, "disk not seamless in u"
    assert disk[-20:, :, :3].mean() > disk[:20, :, :3].mean(), "inner edge should be brighter"
    assert disk[0, :, 3].max() == 0, "outer rim should be fully transparent"
    Image.fromarray(disk, "RGBA").save(OUT / "AccretionDisk.png")
    Image.fromarray(solid((0, 0, 0, 255)), "RGBA").save(OUT / "Black.png")
    print("ok:", *sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
