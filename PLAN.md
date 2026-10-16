# Gargantua System — Fase 1: pesquisa e plano

Pesquisa feita em 2026-10-16. Tudo abaixo foi conferido na web ou na instalação local. Nada vem de memória.

## 1. Ambiente local (lido da instalação)

- KSP **1.12.5** (build 03190, Steam, pt-br) em `C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program`.
- Gerenciado pelo CKAN (132 mods). Sem anti-cheat. O jogo é single-player e pode receber mods.
- Python não está instalado, mas o `uv 0.12.17` está. Os geradores de textura vão rodar com `uv run`, sem instalar nada no sistema.

## 2. Versões das dependências

| Dependência | Mais recente (fonte, data) | Instalada aqui | Ação |
|---|---|---|---|
| KSP | 1.12.5 (última versão do KSP 1) | 1.12.5 | ok |
| Kopernicus | **release-251** (GitHub Kopernicus/Kopernicus, 2026-10-05) | release-247 | atualizar pelo CKAN (o 251 corrige problemas em sistemas de distância grande) |
| Singularity | **0.994** (SpaceDock 2420 / LGhassen/Singularity, 2026-05-16) | 0.994 | ok |
| ModuleManager | **4.2.3** (sarbian, 2026-09-22) | 4.2.3 | ok |
| Harmony (HarmonyKSP) | **2.2.1.0** (2022-05-15, ainda a última) | 2.2.1.0 | ok; o Kopernicus já depende dele, não declaramos à parte |
| KopernicusExpansion Continued-er | **Beta9.1.1** (VabienArt, SpaceDock 3357, 2023-06-12) | Beta9.1.1 | ok; CKAN id `KopernicusExpansionContinueder`; fornece `KopernicusExpansionContinued-Wormholes` |
| Kcalbeloh (referência) | v1.1.8 (2024-08-31) | não instalado | só para estudo |

Opcionais já instalados aqui: Scatterer v0.0878, EVE 1.11.7.2, Parallax Continued 1.0.2, Firefly 1.0.6, Deferred 1.3.5.
Todos entram apenas por patches com `:NEEDS[...]`.

## 3. Já existe mod de Gargantua para KSP?

**Sim, parcialmente.** Antes de continuar, você precisa decidir:

1. **KerbalGalaxy 3** (Ledvin25, v1.1.5 para KSP 1.12.x, 2022-12-16). É um pack de galáxia inteira que também mexe no sistema Kerbol.
   - Inclui `Gargantua System/` com Gargantua, MillersPlanet, MannsPlanet e um wormhole ligado a Jool.
   - Não está no CKAN e a licença não é declarada (NOASSERTION).
   - Tem a issue aberta [#5](https://github.com/Ledvin25/Kerbal-Galaxy-3/issues/5): o wormhole crasha ao ser atravessado e aparece como esfera cinza.
   - Não tem Edmunds, Pantagruel, settings nem compatibilidade com Principia/RSS.
2. **Kargantua System** (KSP 1.2.2, ~2017): abandonado, não roda no 1.12.

Proposta de diferenciação: mod standalone, só do filme, no CKAN, com wormhole opcional, settings e compatibilidade documentada.

Conflito possível: um corpo chamado `Gargantua` se o KG3 estiver instalado. O README vai declarar a incompatibilidade, e o `.netkan` não pode usar `conflicts` porque o KG3 não está no CKAN.

## 4. Problemas conhecidos e como evitá-los

| Problema | Fonte | Solução no plano |
|---|---|---|
| Tela preta / loading infinito ao abrir save | Kcalbeloh [issue #28](https://github.com/jcyuan06/Kcalbeloh-System/issues/28) (NRE do Kopernicus), [fórum 228184](https://forum.kerbalspaceprogram.com/topic/228184-kcalbeloh-not-loading-when-i-start-the-game/) (save corrompido), [fórum 228812](https://forum.kerbalspaceprogram.com/topic/228812-ksp-doesnt-load-when-i-install-kcalbeloh/) (conflito OPM_Parallax), Kopernicus #491/#554 | Corpo raiz continua o Kerbol. Gargantua orbita o Kerbol com `mode = OFF`, como no Kcalbeloh. Não remover/renomear corpos com save aberto. Exigir Kopernicus ≥ 251 (o release-247 corrigiu "NRE spam with black holes lacking a scaledbody", então manter um ScaledVersion válido). README: backup + `persistent.sfs` de `backups/`. Parallax só via patch `:NEEDS[Parallax]` sem dependência do OPM. |
| Singularity não teleporta | Singularity [#14](https://github.com/LGhassen/Singularity/issues/14) (autor: "only visual effects") | Teleporte via nó `Wormhole {}` do KopernicusExpansion. O Singularity só renderiza (`wormholeTarget`). |
| Disco de acreção quebra se for grande demais (~3e10 m) | Singularity [#3](https://github.com/LGhassen/Singularity/issues/3) | `accretionDiskOuterRadius` < 2.5e10 m. Isso obriga a usar escala Kerbal (ver pergunta 2). |
| Singularity + Principia: artefato num lado do buraco negro | Singularity [#4](https://github.com/LGhassen/Singularity/issues/4) | Com `:NEEDS[Principia]`: skybox preto, wormhole desligado e Kerbol orbitando Gargantua (`DistanceFactor = 0`), como no Kcalbeloh. |
| Crash ao trocar para nave distante | Singularity [#11](https://github.com/LGhassen/Singularity/issues/11) (ligado ao Scatterer #223) | Sem correção upstream. Vai como problema conhecido no README e no checklist. |
| Singularity renderiza de anos-luz de distância e mata FPS | Singularity [#2](https://github.com/LGhassen/Singularity/issues/2) | Um objeto Singularity só para Gargantua e um por boca de wormhole. Resolução de cubemap moderada (2048). |
| Calor e navball estranhos em distância interestelar | Kopernicus BandC.md #3/#4 | README: desligar aquecimento de partes na viagem longa. Distância padrão moderada. |
| Homeworld precisa ser "Kerbin" e orbitar a estrela raiz | Kopernicus BandC.md #2 | Sem HomeSwitch nesta versão. |
| Wormhole do KG3 crasha / aparece como esfera cinza | KG3 #5 | Usar o padrão do Kcalbeloh (Template Minmus, `removeAllPQSMods`, ScaledVersion Vacuum preto, `Wormhole{ partner, influenceAltitude, jumpMaxAltitude }`) e testar ida e volta + save/load nas duas bocas. |

## 5. O que aproveitar do Kcalbeloh (só estrutura)

A licença do Kcalbeloh é **CC-BY-NC-ND-4.0** e proíbe obras derivadas. Por isso não copio arquivos, texturas nem valores. Reaproveito só os padrões de config, que são técnicas comuns do Kopernicus/ModuleManager:

- arquivo de settings `GargantuaSystemSettings { ... }`, injetado em cada root node com `#@GargantuaSystemSettings {}` no `:BEFORE[GargantuaSystem]` e removido no `:FINAL`;
- toggles por `:HAS[@GargantuaSystemSettings:HAS[~Wormholes[?rue]]]`;
- `DistanceFactor` multiplica o `semiMajorAxis` em `:AFTER[Kopernicus]`; o valor 0 faz o Kerbol orbitar Gargantua;
- skybox via SigmaReplacements opcional; com Principia o skybox fica preto.

## 6. Dados científicos (fontes)

| Item | Valor | Fonte | Status |
|---|---|---|---|
| Massa de Gargantua | ≥ 1×10⁸ M☉ ("at least 100 million times the Sun's mass") | Thorne, *The Science of Interstellar* (2014), excerto em space.com; arXiv 1910.00940 | confirmado |
| Spin | a/M ≈ 1 − 10⁻¹⁴ | arXiv 1910.00940, citando Thorne | confirmado |
| Dilatação em Miller | ~60 000× (1 h ≈ 7 anos) | arXiv 1910.00940; arXiv 1503.08305 | confirmado |
| Período orbital de Miller ~1,7 h | só em wiki de fã | não confirmado → marcado como liberdade |
| Gravidade de Miller 130% | não achei fonte primária | não confirmado → liberdade |
| Ondas gigantes em Miller | filme | KSP não faz ondas no oceano → visual (Scatterer) + texto |
| Mann: gelo/nuvens congeladas; Edmunds: deserto rochoso habitável | filme | confirmado como descrição |
| Pantagruel | Fontes conflitam: estrela de sequência principal de Edmunds (fan wiki, sem nome no filme); 2º buraco negro (roteiro de 2008); a estrela de nêutrons do filme não tem nome | ambíguo → pergunta 3 |

Física: perto do horizonte a órbita real exige velocidades relativísticas. Com a massa real, uma órbita Newtoniana logo acima do horizonte dá período de ~150 s e ~0,57c, impossível de jogar. Por isso a escala precisa ser decidida (pergunta 2).

## 7. Arquitetura proposta

```
GameData/GargantuaSystem/
  GargantuaSystem.version          (KSP-AVC)
  GargantuaSystem_Settings.cfg     (Wormholes, DistanceFactor, DisableSkybox)
  Configs/
    Bodies/   Gargantua.cfg, Miller.cfg, Mann.cfg, Edmunds.cfg, Pantagruel.cfg (+ NeutronStar.cfg?)
    Settings/ SettingsInjection.cfg, DistanceFactor.cfg
    Singularity.cfg
    Wormholes/ WH_Kerbol.cfg, WH_Gargantua.cfg   (:NEEDS[KopernicusExpansion])
    Compat/   Principia.cfg, RSS_KSRSS.cfg (SigmaDimensions), Scatterer/, EVE/, Parallax/, Firefly/
    Localization/ en-us.cfg, pt-br.cfg
  Textures/     (.dds gerados)
  PluginData/   biome maps, heightmaps (.png lidos pelo Kopernicus OnDemand)
tools/          geradores Python (uv run): heightmaps, color maps, biomes, disco de acreção, skybox
README.md, LICENSE, CHANGELOG.md, GargantuaSystem.netkan
```

- **Sem plugin C#.** Tudo é config do Kopernicus, Singularity, KopernicusExpansion e ModuleManager.
- **Licença proposta:** MIT para configs e código, CC-BY-4.0 para texturas.
- **netkan:** `depends` = Kopernicus, ModuleManager, Singularity e KopernicusExpansionContinueder. Ainda falta decidir se o wormhole fica como recomendação ou dependência.

## 8. Fases

1. Pesquisa e plano. **Este documento.**
2. Gargantua (corpo invisível, `mode = OFF`, ScaledVersion válido), Singularity com disco de acreção, órbita em volta do Kerbol e settings básicos. Teste: o jogo carrega, a tracking station abre e um save existente carrega.
3. Planetas com texturas procedurais: Miller (oceano, maré travada), Mann (gelo/nuvens), Edmunds e Pantagruel conforme as respostas. Teste: órbita e pouso em cada corpo.
4. Wormhole ativável, DistanceFactor, DisableSkybox, Principia/RSS/KSRSS e patches opcionais.
5. Testes no jogo (log + screenshots), README, CHANGELOG, `.version`, `.netkan` e checklist manual.
6. (Opcional, só com seu OK) plugin C# de dilatação temporal.

## 9. Decisões (respostas do usuário)

Respondidas em 2026-10-16:

1. **Seguir standalone**, apesar do KerbalGalaxy 3. A incompatibilidade com o KG3 vai documentada no README.
2. **Escala Kerbal jogável.** Massa da ordem de 1e31–1e32 kg e disco com raio externo < 2.5e10 m. A massa real (≥ 1e8 M☉) fica citada no README como liberdade criativa.
3. **Pantagruel = estrela de sequência principal** que ilumina Edmunds e orbita Gargantua. A **estrela de nêutrons sem nome do filme** entra como corpo à parte, orbitando Gargantua.
4. **KopernicusExpansion Continued-er é dependência obrigatória** no `.netkan`. Mesmo com `Wormholes = False` o mod continua carregando, porque os nós `Wormhole{}` ficam atrás de `:HAS[...]`.

Ainda em aberto (só na fase 6): o plugin C# de dilatação temporal. Pergunto antes de implementar.
