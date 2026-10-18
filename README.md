# Gargantua System

A Kopernicus planet pack for **KSP 1.12.x** inspired by *Interstellar* (2014): the supermassive black hole
Gargantua with a lensed accretion disk, Miller's water world and its giant tidal waves, Mann's frozen planet,
Edmunds' desert world around the star Pantagruel, an unnamed pulsar, and an optional wormhole near Jool.

> **Português:** pack de planetas do filme *Interstellar*. Instalação, dependências e problemas conhecidos estão
> abaixo (em inglês). Resumo: instale pelas dependências listadas, faça backup do save e **desligue o TAA do
> Scatterer** (veja "Known issues").

## Bodies

| Body | What it is | Orbit | Notes |
|---|---|---|---|
| Gargantua | Black hole (Singularity lensing + accretion disk) | Kerbol, 2.0E14 m (`mode = OFF`, hidden orbit line) | Visual horizon ≈ 2.8E9 m, disk 3.6E9–2.2E10 m |
| Miller | Shallow ocean world, tidally locked | Gargantua, 1.0E10 m | 1.3 g. Giant tidal waves sweep the planet (plugin) |
| Mann | Glacier world, thin cold atmosphere | Gargantua, 7.0E10 m | 0.8 g, "frozen clouds" with volumetric EVE |
| Edmunds | Rocky desert with breathable air (oxygen), no ocean | Pantagruel, 1.4E10 m | 0.9 g |
| Pantagruel | Main-sequence star lighting Edmunds | Gargantua, 5.0E11 m | |
| Neutron star | Unnamed pulsar from the film, with jets | Gargantua, 1.0E11 m | Glows but does not light the scene. Lethal heat close in |
| Wormhole A / B | Kerbol side (Jool; Sarnus with OPM; Saturn with RSS/KSRSS) ↔ Gargantua side | | Optional (`Wormholes = True`) |

## Requirements

Required: **Kopernicus**, **ModuleManager**, **Singularity**, **KopernicusExpansion Continued-er** (wormhole
and 16-bit heightmaps). Harmony comes with Kopernicus.

Optional (patched only when installed): Scatterer, EVE (2D clouds, or volumetric clouds with blackrack's
StockVolumetricClouds), Parallax Continued with its stock terrain/scatter textures (rocks on Mann and Edmunds),
SigmaReplacements-SkyBox (custom skybox).

Tested on: KSP 1.12.5, Kopernicus release-247, Singularity 0.994, ModuleManager 4.2.3, KopernicusExpansion
Continued-er Beta9.1.1, Scatterer 0.0878, EVE (raymarched, StockVolumetricClouds V4), Parallax Continued,
Deferred 1.3.5.

## Install

CKAN (when published), or copy `GameData/GargantuaSystem` into your `GameData`. **Back up your save first.**

## Settings

Edit `GameData/GargantuaSystem/GargantuaSystem_Settings.cfg` with the game closed. Changing it mid-save can delete
vessels orbiting bodies that stop existing.

- `Wormholes` (True/False): the Kerbol ↔ Gargantua wormhole.
- `DistanceFactor` (1, 0.1, 10, 100): Kerbol–Gargantua distance. `0` makes Kerbol orbit Gargantua (experimental).
- `DisableSkybox` (True/False): turns off the custom skybox (only exists with SigmaReplacements-SkyBox).

## Compatibility

- **Principia:** forces `DistanceFactor = 0`, no wormholes and a black skybox (Singularity artifacts otherwise).
  *Untested.*
- **RSS / KSRSS:** bodies are protected from RSS cleanup, the wormhole moves to Saturn and distances scale ×10.
  *Untested.*
- **OPM:** the Kerbol-side wormhole moves to Sarnus.
- **KerbalGalaxy 3:** incompatible (it also adds a body named `Gargantua`).

## Known issues

- **Torn or frozen sky near Gargantua:** Scatterer's TAA together with Singularity smears the sky. Set
  `useTemporalAntiAliasing = False` in `GameData/scatterer/config/config.cfg` (SMAA keeps working).
- **Faint circle around Gargantua:** Singularity only draws the black hole inside a sphere (here 5.4E10 m). Inside it
  the sky comes from a galaxy snapshot, so its brightness can differ slightly from the sky outside.
- Pulsar jets disappear when seen *through* that sphere (behind Gargantua).
- Miller's waves only move vessels that are loaded and unpacked. Vessels in time warp or far away are not swept.
  The game drops time warp and warns ("That's not a mountain... it's a wave!") when a crest is 33 km away.
- Miller's night side is very dark.
- After a wormhole jump the vessel exits inside the jump zone of the other mouth: fly out before saving.
- Singularity may crash when switching to a far-away vessel (Singularity #11, with Scatterer), and with Principia
  shows artifacts on one side (Singularity #4).
- Interstellar distances: disable part heating for the long cruise if it misbehaves.

## Creative liberties (vs. the film and real physics)

- **Scale:** Gargantua is 1.0E30 kg (the film's is ≥ 10⁸ solar masses). The real mass makes orbits near the horizon
  relativistic and unplayable. The disk outer radius is limited to 2.2E10 m (Singularity breaks above ~3E10 m).
- No time dilation (1 hour on Miller = 7 years in the film).
- Miller's 1.3 g, the planets' radii, orbits and terrain details are invented to be playable and to look like
  the film. Miller's waves: 1200 m crests at 100 m/s, analytic buoyancy (not a fluid simulation).
- Pantagruel as Edmunds' star and the pulsar's jets/orbit are not from the film.

## Building

- Textures: `uv run tools/gen_textures.py`, `uv run tools/gen_planets.py`, `uv run tools/gen_clouds.py`,
  `uv run tools/gen_skybox.py`.
- Plugin (waves + pulsar jets): `dotnet build -c Release` in `src/GargantuaWaves` (net472; set `-p:KSPDIR=...`).
- Manual test checklist: [docs/TESTING.md](docs/TESTING.md). Development journal: [MODLOG.md](MODLOG.md).

## License

Code and configs: MIT. Textures (all generated by the scripts in `tools/`): CC-BY-4.0. See [LICENSE](LICENSE).
No files from Kcalbeloh, Cosmic Serenity or KerbalGalaxy are included.
