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
  - tracking station carregou sem tela preta. Foco em Gargantua: disco + lente + anel de fótons renderizados (print v1 removido; substituído pelo v2 abaixo). Nenhum erro do Singularity.
- Pendências visuais (fase 3/5): as faixas do disco estão regulares demais e o disco está largo e escuro comparado ao filme. Ajustar `gen_textures.py` e testar de novo.
- Não testado ainda: DistanceFactor ≠ 1, voo real até o SOI.

## 2026-10-16 — Disco de acreção v2 (pedido do usuário: "parece anelzinho", mais brilho)
- Causa das faixas regulares: o termo `sin(v*140)` no gerador antigo.
- Novo gerador: ruído espectral via FFT (tileável), anisotrópico ao longo de u (estrias que seguem a órbita), 3 camadas (estrias, filamentos, aglomerados) + cisalhamento por linha (rotação diferencial, `np.roll` mantém o tile) + faixas de poeira escura + borda externa irregular. Paleta: branco-quente → dourado → laranja → marrom.
- Brilho: o shader faz rgb*alpha com teto 1. Subi rgb e alpha no disco interno (lum. média do 1/5 interno: 160 → 198 de 255).
- Textura 4096x1024 PNG. Recarrega trocando de cena (o Singularity relê o arquivo no Init), sem reiniciar o jogo.
- Verificado na tracking station: vista de cima e de lado com o arco da lente (docs/screenshots/disk_v2_*.png).
- Automação: o teclado só chega ao KSP depois de um clique no jogo. A câmera do mapa só gira com `rel` (movimento relativo) segurando o botão direito. O botão vermelho no canto superior direito da tracking station volta ao Space Center.

## 2026-10-16 — Fase 3 (planetas) — descobertas
- Gargantua passou a 1e30 kg (decisão do usuário: ~44 km/s do wormhole até Miller).
- Corpos: Miller (idx 18), GargantuaNeutronStar (19), Mann (20), Pantagruel (21), Edmunds (22). SOIs: Miller 14,5 Mm, Mann 68 Mm, Edmunds 83 Mm, Pantagruel 99 Gm, estrela de nêutrons 7,9 Gm.
- **Saves: o Kopernicus resolve a órbita pelo `IDENT` (= identifier do corpo), não pelo `REF`.** Os identifiers `GargantuaSystem/<Corpo>` nunca podem mudar entre versões, senão as naves dos jogadores mudam de corpo.
- **Template Kerbin + removeAllPQSMods** tira também: PQSMod_AerialPerspectiveMaterial (sem ele o PQS renderiza branco/preto em voo), PQSMod_OceanFX (água sem textura animada) e PQSMod_TextureAtlas. Os dois primeiros foram readicionados.
- **No 1.12 o material do PQS de Kerbin é TriplanarAtlas**, que lê a cor de vértice como peso de blend. Com VertexColorMap é preciso usar `materialType = AtmosphericTriplanarZoomRotation`.
- Texturas BUILTIN do KSP usadas no detalhe: Eeloo (Mann), laytheSand/Duna Floor/dresHigh (Edmunds), sea-water1..8 + quiet (Miller). Os nomes vieram de configs públicas de outros packs (são assets do próprio jogo).
- **Mapeamento lon → u (atributos/height do KSP): u = 1 − ((lon − 90°) mod 360)/360** (eixo espelhado). As ondas de Miller estão em lon = 90 − u·360 (onda 2 ≈ −104°). Verificado: nave em lon −103 vê a onda.
- O planejador de manobras do KSP 1.12 lança ArgumentOutOfRange em sistemas com várias estrelas (TransferTypeSimple.SetupCBNames). É bug do jogo, já relatado pelo Kcalbeloh. Vai para o README.
- Testes: save separado `saves/gargantua_test` (cópia do padrão) com naves editadas no persistent.sfs: Teste Miller/Mann/Edmunds em órbita, Onda A–E em Miller, Solo Mann/Edmunds.
- Automação: `tools/ksp_test_flight.sh` (o menu engole cliques nos primeiros ~10 s; Esc só funciona depois de um clique no jogo; a câmera gira com `rel` + botão direito).
- Realismo (pedido do usuário): referências do filme. Mann = geleira Svínafellsjökull (gelo cinza-esbranquiçado enrugado, fendas, cinza vulcânica, céu encoberto). Edmunds = planície rochosa com matacões e cordilheiras (cena final). Miller = água rasa cinza-esverdeada (Máfabót).
  - Mann: dobras ridged (~60 km) + montículos (~15 km) + platôs + fendas Worley (~12 km) + faixas de cinza. Céu via `AtmosphereFromGround.waveLength = 0.62,0.61,0.60` (o template Duna deixava vermelho).
  - Edmunds: cordilheiras ridged em faixas + morros ridged (~30 km, 900 m) + salinas + dunas pequenas + cânions raros. Biomas renomeados (RockyPlains/Mountains/SaltFlats/DuneFields/Canyons).
  - Miller: OceanFX readicionado com sea-water1..8 (água animada), oceanOpacity 0.55 (mar raso), céu cinza-azulado.
  - Verificado no jogo com naves pousadas (altura calculada do heightmap com o mapeamento espelhado de longitude).
- Pendente: encostas de Edmunds ainda suaves de perto (resolução 4096 = ~0,46 km/px). Opções: heightmap 8k ou patch Parallax/scatter de rochas (fase 4).
