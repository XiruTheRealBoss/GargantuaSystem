# MODLOG — Gargantua System

## 2026-10-16 — Fase 1
- KSP 1.12.5 (build 03190): `C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program`. CKAN gerencia 132 mods.
- Instalados: Kopernicus release-247 (o último é o 251), Singularity 0.994, MM 4.2.3, Harmony 2.2.1, KopernicusExpansionContinueder Beta9.1.1, Scatterer 0.0878, EVE 1.11.7.2, ParallaxContinued 1.0.2, Firefly 1.0.6.
- Sem Python no sistema. Usar `uv run --no-project python ...`.
- Rota: dados/config apenas (Kopernicus + Singularity + KopernicusExpansion + MM). Sem plugin C#.
- Kcalbeloh é CC-BY-NC-ND-4.0: estudar padrões, não copiar arquivos nem texturas.
- Decisões e fontes: ver PLAN.md.
- Backup antes do 1º teste no jogo: `um backup create "<KSP>/saves" --name ksp-saves`.
- Próximo passo: fase 2 (Gargantua + Singularity + settings).

## 2026-10-16 — Fase 2 (Gargantua + Singularity + settings)
- Backups (`um backup`): `~/.universal-modder/backups/ksp-saves/20261016-195033.zip` (272 arquivos), `ksp-kopernicus-config/…`, `ksp-settings.cfg.bak`.
  Para restaurar: `um backup restore ksp-saves`.
- Instalação de dev: junction `KSP/GameData/GargantuaSystem` → `GargantuaSystem/GameData/GargantuaSystem` (para remover: `rmdir` na junction).
- Singularity (lido do código-fonte): raio visual do horizonte = sqrt(gravity)*5 em scaled space (×6000 → metros). Raios do disco em metros (/6000 internamente). Com `useRadialTextureMapping`, u = ângulo e v = 0 na borda interna → 1 na externa. A textura é achada por `GameData/<path>` com extensão. O objeto é ligado ao transform scaled de nome = `name` do corpo. Lê todos os root nodes `Singularity`, mas só o primeiro `Singularity_config`.
- Teste no jogo (KSP 1.12.5, Kopernicus 247, Singularity 0.994):
  - menu principal OK. Kopernicus: "Loaded Body: Gargantua", SOI = 1.5E13, sem erros no log do corpo.
  - save "padrão" (2 voos, ano 9) carregou no Space Center. Os erros `Cannot find a Module 'PrincipiaPluginAdapter'` etc. vêm de mods antigos do save, não do Gargantua.
  - tracking station carregou sem tela preta. Foco em Gargantua: disco + lente + anel de fótons renderizados (docs/screenshots/phase2_tracking_station.png). Nenhum erro do Singularity.
- Pendências visuais (fase 3/5): as faixas do disco estão regulares demais e o disco está largo e escuro comparado ao filme. Ajustar `gen_textures.py` e testar de novo.
- Não testado ainda: DistanceFactor ≠ 1, voo real até o SOI.
