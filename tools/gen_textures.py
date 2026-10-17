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


def spectral_noise(rng, h, w, beta, aniso, kmin=0.0, kmax=0.5):
    """Gaussian noise with a 1/k^beta spectrum, normalised to 0..1.

    Built with an FFT, so it tiles in both axes (u = disk angle must wrap).
    aniso > 1 stretches features along u: long streaks following the orbit instead of blobs.
    """
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    k = np.sqrt((fx * aniso) ** 2 + fy**2)
    amp = np.where((k > kmin) & (k <= kmax), 1.0 / np.maximum(k, 1e-6) ** beta, 0.0)
    phase = rng.random((h, w)) * 2 * np.pi
    field = np.fft.ifft2(amp * np.exp(1j * phase)).real
    field -= field.min()
    return field / field.max()


def shear(img, v, strength):
    """Differential rotation: inner rows are shifted further along u than outer rows.

    np.roll per row keeps the texture seamless in u. Turns straight streaks into tight spiral filaments.
    """
    out = np.empty_like(img)
    w = img.shape[1]
    for row, vv in enumerate(v[:, 0]):
        out[row] = np.roll(img[row], int(strength * w * (1 - vv) ** 2))
    return out


def accretion_disk(w=4096, h=1024):
    """Radial-mapped disk (Singularity useRadialTextureMapping = True).

    u = angle (wraps), v = 0 at the inner edge -> 1 at the outer edge.
    Unity's LoadImage puts PNG row 0 at v = 1, so the inner edge is the bottom row.
    Target look: the film's Gargantua (white-hot inner disk, turbulent orange/brown filaments,
    ragged dusty outer edge, no Doppler beaming). The detail itself is creative liberty.
    The shader outputs rgb * alpha clamped to 1, so "brighter" means rgb and alpha close to 1.
    """
    rng = np.random.default_rng(SEED)
    v = np.linspace(1, 0, h)[:, None]  # image top = outer edge

    # matter: long streaks + finer filaments + large clumps, all following the orbit
    streaks = spectral_noise(rng, h, w, beta=1.6, aniso=10, kmin=0.002)
    filaments = spectral_noise(rng, h, w, beta=1.1, aniso=24, kmin=0.01)
    clumps = spectral_noise(rng, h, w, beta=2.2, aniso=4, kmin=0.001)
    matter = shear(0.45 * streaks + 0.35 * filaments + 0.20 * clumps, v, 0.35)
    matter = (matter - matter.mean()) / matter.std()

    # dust lanes: dark, absorbing, mostly in the cooler outer disk
    dust = shear(spectral_noise(rng, h, w, beta=1.8, aniso=14, kmin=0.003), v, 0.35)
    dust = np.clip((dust - 0.55) / 0.25, 0, 1) * np.clip(v / 0.5, 0.15, 1)

    # temperature: very hot at the inner edge, cooling outwards; matter perturbs it locally
    temp = np.clip((1 - v) ** 0.9 + 0.08 * matter, 0, 1)
    stops = np.array([0.0, 0.25, 0.5, 0.75, 0.9, 1.0])
    palette = np.array([
        [0.30, 0.12, 0.05],  # cold dusty rim, dark brown
        [0.75, 0.36, 0.12],  # orange-brown
        [1.00, 0.62, 0.28],  # orange
        [1.00, 0.86, 0.62],  # pale gold
        [1.00, 0.96, 0.88],  # near white
        [1.00, 1.00, 1.00],  # white hot
    ])
    color = np.stack([np.interp(temp, stops, palette[:, c]) for c in range(3)], axis=-1)

    brightness = (0.8 + 0.35 * temp) * np.clip(1 + 0.18 * matter, 0.45, 1.35) * (1 - 0.65 * dust)
    rgb = np.clip(color * brightness[..., None], 0, 1)

    # opacity: thick and bright inside, ragged dusty outer edge driven by the same matter noise
    inner_edge = np.clip(v / 0.012, 0, 1)
    rim = np.clip((0.88 + 0.10 * matter - v) / 0.2, 0, 1)
    alpha = inner_edge * rim * np.clip(0.95 + 0.12 * matter, 0.65, 1) * (1 - 0.4 * dust)
    alpha[0] = 0  # outermost row fully transparent so the disk never ends in a hard ring
    alpha = np.clip(alpha, 0, 1)

    rgba = np.concatenate([rgb, alpha[..., None]], axis=2)
    return (rgba * 255).round().astype(np.uint8)


def miller_wave(w=1024, h=256):
    """Texture of the moving giant wave (plugin GargantuaWaves). u = along the crest (repeats ~5 km),
    v = across: 0 = far end of the back slope, 0.9 = crest, 1 = foot of the steep front face.
    Unity puts PNG row 0 at v = 1, so the front face is the TOP of the image."""
    rng = np.random.default_rng(SEED + 1)
    v = np.linspace(1, 0, h)[:, None]
    streaks = spectral_noise(rng, h, w, beta=1.4, aniso=4, kmin=0.002)    # FFT noise wraps: repeats along the crest
    drips = spectral_noise(rng, h, w, beta=1.2, aniso=0.15, kmin=0.004) ** 3  # vertical: foam running down the face
    base = np.array([0.20, 0.27, 0.28]) * (0.85 + 0.3 * streaks[..., None])
    crest = np.exp(-((v - 0.9) / 0.012) ** 2)                 # thin white foam line on the crest
    face_foam = np.clip((v - 0.9) / 0.1, 0, 1) * np.clip(drips * 2.5, 0, 1)
    back_foam = np.clip((v - 0.6) / 0.3, 0, 1) * np.clip((streaks - 0.55) * 3, 0, 1) * 0.5
    foam = np.clip(crest + face_foam + back_foam, 0, 1)[..., None]
    rgb = base * (1 - foam) + 0.92 * foam
    return (np.concatenate([rgb, np.ones((h, w, 1))], axis=2) * 255).round().astype(np.uint8)


def solid(rgba, size=8):
    return np.full((size, size, 4), rgba, dtype=np.uint8)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    disk = accretion_disk()
    # self-check: seamless in u, bright opaque inner disk, transparent outer rim
    h = disk.shape[0]
    assert disk.shape == (1024, 4096, 4)
    lum = disk[..., :3].astype(float).mean(axis=2) * disk[..., 3] / 255
    wrap = np.abs(lum[:, 0] - lum[:, -1]).mean()
    step = np.abs(np.diff(lum, axis=1)).mean()
    assert wrap < 3 * step, f"disk not seamless in u (wrap {wrap:.1f} vs step {step:.1f})"
    inner, outer = lum[-h // 5:].mean(), lum[: h // 5].mean()
    assert inner > 180 and inner > 3 * outer, f"inner disk should dominate ({inner:.0f} vs {outer:.0f})"
    assert disk[0, :, 3].max() == 0, "outer rim should be fully transparent"
    # PluginData: o Singularity lê o arquivo direto, e fora daqui o KSP carregaria 16 MB à toa no GameDatabase
    (OUT.parent / "PluginData").mkdir(exist_ok=True)
    Image.fromarray(disk, "RGBA").save(OUT.parent / "PluginData" / "AccretionDisk.png")
    Image.fromarray(solid((0, 0, 0, 255)), "RGBA").save(OUT / "Black.png")
    Image.fromarray(solid((255, 255, 255, 255)), "RGBA").save(OUT / "White.png")
    wave = miller_wave()
    assert np.abs(wave[:, 0].astype(int) - wave[:, -1].astype(int)).mean() < 12, "wave texture not seamless in u"
    Image.fromarray(wave, "RGBA").save(OUT / "MillerWave.png")
    print(f"ok: inner lum {inner:.0f}, outer lum {outer:.0f};", *sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
