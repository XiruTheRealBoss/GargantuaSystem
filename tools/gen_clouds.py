# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
"""Gera as texturas de nuvens do EVE (equiretangulares, sem costura) e a textura de detalhe.

Uso: uv run tools/gen_clouds.py
Saída: GameData/GargantuaSystem/Textures/EVE/  (fora do PluginData: o EVE lê pelo GameDatabase)
RGB = brilho da nuvem, A = cobertura. A cor final vem do _Color de cada camada no .cfg.
"""
from pathlib import Path

import numpy as np

from gen_planets import check_seamless, fbm, render, ridged, save_gray, save_rgb, smoothstep, warp

OUT = Path(__file__).resolve().parent.parent / "GameData" / "GargantuaSystem" / "Textures" / "EVE"


def miller(lat, lon, xyz):
    # Film: a heavy, almost unbroken grey overcast with a few darker, thicker bands and rare breaks.
    p = warp(xyz, 0.5, 2.0, 201)
    base = fbm(p, 3.0, 6, 202)
    cover = smoothstep(0.28, 0.48, base)
    thick = fbm(warp(xyz * np.float32([1, 3, 1]), 0.3, 3.0, 203), 6.0, 5, 204)
    return np.clip(0.82 + 0.18 * thick, 0, 1), np.clip(cover * (0.85 + 0.15 * thick), 0, 1)


def mann(lat, lon, xyz):
    # "Frozen clouds": long thin sheets stretched along the wind, about a third of the sky.
    streaks = ridged(warp(xyz * np.float32([1, 4, 1]), 0.25, 2.0, 211), 4.0, 5, 212)
    patches = smoothstep(0.45, 0.65, fbm(warp(xyz, 0.4, 1.5, 213), 2.0, 4, 214))
    cover = smoothstep(0.35, 0.75, streaks) * patches
    return np.full(lat.shape, 0.95, np.float32), np.clip(cover * 0.85, 0, 1)


def edmunds(lat, lon, xyz):
    # Sparse fair-weather cumulus, a quarter of the sky at most.
    n = fbm(warp(xyz, 0.3, 4.0, 221), 10.0, 6, 222)
    cover = smoothstep(0.60, 0.72, n)
    return np.full(lat.shape, 0.97, np.float32), cover


LAYERS = {"Miller_clouds": (miller, 4096), "Mann_clouds": (mann, 2048), "Edmunds_clouds": (edmunds, 2048)}


def detail(n=512):
    """Tiling detail noise for close-up cloud texture (FFT noise wraps in both axes)."""
    rng = np.random.default_rng(230)
    f = np.fft.fftfreq(n)
    k = np.sqrt(f[None, :] ** 2 + f[:, None] ** 2)
    amp = np.where(k > 0, 1 / np.maximum(k, 1e-6) ** 1.3, 0)
    d = np.fft.ifft2(amp * np.exp(2j * np.pi * rng.random((n, n)))).real
    return (d - d.min()) / (d.max() - d.min())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (fn, w) in LAYERS.items():
        bright, cover = render(w, w // 2, fn)
        check_seamless(cover, name)
        rgb = np.repeat(bright[..., None], 3, axis=-1)
        save_rgb(OUT / f"{name}.png", rgb, cover)
        print(f"{name}: cobertura média {cover.mean():.0%}")
    d = detail()
    check_seamless(d, "cloud detail")
    save_gray(OUT / "cloud_detail.png", d)
    print("cloud_detail ok")


if __name__ == "__main__":
    main()
