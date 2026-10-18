# Manual test checklist

Run on a copy of a save. Keep `KSP.log` open: search for `[GargantuaSystem]`, `Exception` and `FALHOU` (plugin self-check).
Status: ✅ verified in game during development · ⬜ not tested yet.

## Loading
- ✅ Game reaches the main menu; no `[GargantuaSystem]` errors; ModuleManager reports no failed patches.
- ✅ An existing save loads; Tracking Station opens; all bodies are listed.

## Bodies
- ✅ Gargantua: black hole + tilted disk, no rays; disk not clipped by the lens sphere (from the pulsar and from Miller orbit).
- ✅ Miller: ocean, clouds, landing/splashdown; wave visible on the day side (lon ≈ +5..+60).
- ✅ Miller wave: warp stops and the warning shows at 33 km; a floating vessel and an EVA Kerbal ride up to the crest and
  come back down with the water (no floating in the air afterwards).
- ⬜ Miller wave with a vessel landed on the shallow sea floor.
- ✅ Mann: terrain detail, Parallax rocks, atmosphere, frozen clouds.
- ✅ Edmunds: terrain, Parallax rocks, atmosphere.
- ✅ Pantagruel lights Edmunds; Gargantua lights Miller and Mann.
- ✅ Neutron star: glows, does not change the lighting of Mann; jets visible in map view.
- ⬜ Jets in the Tracking Station and Space Center scenes.
- ✅ Pulsar at its new orbit (1E11 m): save loads, test vessel stays in orbit of it. SOI (~2.3E10 m) does not reach Mann (7E10 m) by calculation.

## Sky
- ✅ With Scatterer TAA off, no torn/frozen sky in flight and map views near the pulsar and Miller.

## Wormhole (`Wormholes = True`)
- ✅ Orbiting mouth A jumps once to mouth B; Gargantua visible on the other side.
- ✅ `Wormholes = False`: no wormhole bodies, no errors.

## Settings and compatibility
- ✅ `DistanceFactor = 0`: Kerbol orbits Gargantua; save loads.
- ⬜ `DistanceFactor` 0.1 / 10 / 100.
- ⬜ SigmaReplacements-SkyBox skybox and `DisableSkybox`.
- ⬜ Principia, RSS, KSRSS, OPM.
