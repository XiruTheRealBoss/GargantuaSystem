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

## 2026-10-17 — Atmosferas (Scatterer + EVE), pedido do usuário: "parecem stock", Miller "parece Urano"
- CORREÇÃO: o EVE instalado é o EVE Redux 1.11.7.2 (CKAN), não o volumétrico. O zip do blackrack (Atmosphere.dll de 150 KB) é outro build. O "acesso negado" ao instalar era o KSP aberto travando as DLLs, não permissão (o usuário tem controle total). Backups: ksp-eve, ksp-boulderco.
- Scatterer: **Scatterer_atmosphere/Scatterer_ocean precisam ser nós raiz próprios.** `@Scatterer_atmosphere:FOR[...]` casa com o nó de CADA arquivo de config (7 cópias). Já o planetsList precisa ser patch (`@Scatterer_planetsList`).
- `sunsUseIntensityCurves = True` usa a intensidade da luz scaled da estrela principal. Mudado para False em todos.
- **Oceano do Scatterer em Miller deixa a cena inteira preta** (céu e água), mesmo com o Gargantua como sol. Desligado (hasOcean = False). O oceano stock foi tingido de cinza-esverdeado (Material color/colorFromSpace, fog, AerialRampKerbin2).
- Nuvens EVE (`tools/gen_clouds.py`): Miller ~72% encoberto (o "Urano liso" virou um mundo de nuvens, como a foto 5 do filme), Mann lâminas "congeladas" ~11%, Edmunds cúmulos ~10%.
- Resultado verificado: Miller com céu branco encoberto e água escura (filme, foto 3); Mann com céu frio azul-acinzentado e gelo branco; Edmunds com horizonte de deserto.
- Disco de acreção movido para PluginData (o KSP não carrega 16 MB à toa no GameDatabase).

## 2026-10-17 — Nuvens volumétricas (EVE 2.3.3 raymarched, instalado pelo usuário) + oceano Scatterer
- Black screen anterior: **não era o oceano**. Eram duas coisas: (1) a nave afundada a −2 m deixava a câmera embaixo d'água; (2) a Onda E (lon −103) e a Onda G (−36) estão no **lado noturno** de Miller, que é fixo por causa da maré travada. O lado iluminado fica em ~+5° a +60° de longitude. Testar sempre nessa faixa.
- Oceano do Scatterer religado em Miller: AMP 1, vento 8, água cinza-esverdeada, modo subaquático claro (transparencyDepth 30, darknessDepth 600). Ondas reais com reflexo verificadas.
- Nuvens volumétricas: `Configs/Compat/EVE/VolumetricClouds.cfg` com `:NEEDS[StockVolumetricClouds]`. As 2D ficam como fallback `:NEEDS[EnvironmentalVisualEnhancements,!StockVolumetricClouds]`. Cobertura em `PluginData/EVE/*_coverage.png` (canal R, AlphaMap). sdfMap é opcional. Reaproveita detail1/uvnoise1 do StockVolumetricClouds.
- Teto de Miller: densidade 0.08 em 1100 m deixava a superfície quase noite. Ficou 0.025 em 1700–2300 m.
- Onda gigante (+48,6°) vista da Onda G (+49,8°, ~11 km na frente da face): parede cinza-azulada sumindo na névoa (docs/screenshots/miller_giant_wave.png).
- Atenção: BoulderCo (configs 2D antigos do EVE) continua instalado junto com o StockVolumetricClouds. O readme do blackrack manda remover. Backup em ksp-boulderco.
- Não verificado no jogo: as camadas volumétricas de Mann e Edmunds (sem erro no log).

## 2026-10-17 — Fase 4: wormhole, settings e compatibilidade
- Wormholes (`Configs/Wormholes/`): GargSysWormholeA (Jool, 6E8 m; Sarnus com OPM; Saturno com RSS/KSRSS) ↔ GargSysWormholeB (Gargantua, 1.5E11 m). Nó `Wormhole{}` do KEX (partner, influenceAltitude 35 km, jumpMaxAltitude 30 km). Superfície afundada (VertexHeightMap offset −9000) para a nave nunca bater. Visual via Singularity (`wormholeTarget`).
  - **Verificado:** nave em órbita de 20 km da boca A → log "Jumping to GargSysWormholeB" 1 s após carregar; um único salto (sem ping-pong); Gargantua visível do outro lado. SOIs: A 3,9 Mm, B 7,0 Mm.
  - Atenção: a nave sai a 20 km da boca B, ainda dentro de jumpMaxAltitude. Não voltou sozinha, mas o README deve mandar sair da zona antes de salvar.
- Settings:
  - `Wormholes = False` → corpos e objetos Singularity não são criados. **Verificado** (sem GargSys no Kopernicus, sem erros; naves em órbita das bocas são apagadas, como esperado).
  - `DistanceFactor = 0` (`KerbolAroundGargantua.cfg`, LAST pass): Sun stock → "Kerbol" a 5E12 m; Gargantua → "Sun" (raiz); todos os corpos que orbitavam o Sun → Kerbol; Kerbin carrega na raiz e vai para o Kerbol via PostSpawnOrbit; Singularity e Scatterer (planetsList e sunflare) renomeados. Identifiers mantidos, então os saves continuam válidos. **Verificado:** raiz Sun:0 com SOI ∞, Kerbol SOI 9,9E11, Kerbin com sma 13.599.840 km em volta do Kerbol, Singularity no "Sun", save carregado.
  - `DisableSkybox` + skybox procedural (`tools/gen_skybox.py`, 6 faces sem costura): só com SigmaReplacements-SkyBox (CKAN; DLL "All Rights Reserved", não empacotada). **Não testado no jogo** (mod não instalado).
- Principia (`Compat/Principia.cfg`, FIRST): força DistanceFactor 0, Wormholes False e skybox preta. Não testado (Principia não instalado).
- RSS/KSRSS (`Compat/RSS_KSRSS.cfg`): proteção contra a limpeza de corpos do RSS (renomeia o nó para DontDeleteMe antes e volta depois), wormhole em Saturno, distância ×10 no RSS. Não testado (RSS não instalado).

## 2026-10-17 — Correções da revisão/auditoria + onda que varre Miller
- Estrela de nêutrons: deixou de ser "estrela" (template Minmus, ScaledVersion Vacuum, sem Light). O StarLightSwitcher do Kopernicus escolhe a estrela mais PRÓXIMA da nave, e ela roubava a luz de Mann e da boca B. Verificado: só Gargantua, Pantagruel e Sun ficam como estrelas, e em Mann a estrela ativa é Gargantua.
- RSS + DF0: Gargantua com ×113 de massa e Kerbol (o Sol) a 5E13 m só nesse modo (SOI do Sol ~1E13 m). Não testado (sem RSS).
- DF0: também renomeia `celestialBodyName = Sun` (planetsList), `Atmo[Sun]` (Scatterer_atmosphere) e `PQS_MANAGER OBJECT body = Sun` para Kerbol (coroa do BetterKerbol). Não testado no jogo.
- Wormhole B agora é `+Body[GargSysWormholeA]` (patch FOR separado, no mesmo arquivo). Verificado: B carregada com a mesma SOI de antes.
- Skybox: o teste agora compara as direções 3D pixel a pixel nas 4 emendas do horizonte (provado que pega uma face espelhada).
- Heightmaps de Mann e Edmunds em 16 bits (`VertexHeightMap16` do KEX: altura = (G<<8|B)/65535), com self-check de codificação no gerador. Verificado: KEX faz o parse sem erro, e o relevo de Mann aparece normal.
- **Onda móvel (plugin `GargantuaWaves.dll`, src/GargantuaWaves, net472, `dotnet build -c Release`)**:
  - 5 malhas (59 mil vértices, uma malha compartilhada) presas ao `pqsController.transform` de Miller e giradas em volta do eixo polar. O ângulo vem de `Planetarium.GetUniversalTime()`. 40 m/s no equador: uma onda por ponto a cada ~5,7 h.
  - **Gotcha 1:** Rigidbody cinemático na malha → a origem flutuante do KSP desloca todo Rigidbody e a malha se descolou do planeta (ficou invisível embaixo do mar). Sem Rigidbody, girando só o Transform, funciona.
  - **Gotcha 2:** MeshCollider movido pelo Transform não acorda naves paradas: a onda atravessava. Trocado por interação analítica (mesma fórmula de altura da malha): nave abaixo da superfície é acelerada para (40 m/s leste, subida ∝ profundidade), com no máximo 40 m/s².
  - **Gotcha 3:** naves boiando ficam a ~−0,1 m → "abaixo da onda" com altura 0 → todas eram arrastadas. Só empurra se a onda tiver ≥ 2 m no ponto.
  - Verificado: a parede chega, a nave fica parada antes (0 m/s) e é varrida quando a onda chega (Flying Low, 40 m/s, subindo) — docs/screenshots/miller_wave_*.png.
  - Terreno de Miller agora é só o fundo raso (VertexHeightOffset −3). Os biomas de onda saíram. O mapa de cor do espaço não tem mais as linhas das ondas.
  - Limitações: dentro da encosta de trás a malha é de um lado só (por baixo não se vê). Naves "packed" (timewarp/distantes) não são empurradas.
  - Teste: as cristas ficam em lon = k·72 + 23 + ω·UT (ω = 40/R rad/s). O lado iluminado de Miller fica em ~+5..+60°. Calcular pela UT do save; SC/TS também fazem o tempo passar.

## 2026-10-17 — Visual: Mann/Edmunds, atmosferas, disco, onda mais rápida, pedras (Parallax)
- Mann: mapa de cor 8K em DDS DXT1 (só para o terreno, via VertexColorMap). O PNG 4K continua no scaled. **Gotcha:** o KSP lê DDS de baixo para cima, então o gerador grava a imagem invertida. Conferido: a média de cor no local de pouso bate com o PNG só na versão invertida.
- Mapas de Mann/Edmunds refeitos sem padrões Worley (davam "redes de polígonos"): vales sinuosos, dunas suaves, salinas, mosaico natural de tons.
- Scatterer: atmosferas refeitas a partir dos configs stock (Miller = Laythe, Mann/Edmunds = Kerbin com ajustes). As antigas tinham Mie 3–6× maior e ficavam lavadas. godrayStrength 0 em Miller e Mann (os "raios feios" saindo de Gargantua).
- Disco: volta ao raio externo 2,2E10 m e ganha inclinação de ~27° (normal 0.45,1,0.25). Plano demais em relação às órbitas, ele virava uma faixa fina.
- Onda de Miller: 40 → 100 m/s. Alarme novo: se a nave ativa está em Miller e a próxima crista chega em ≤ 3 min (ou em menos de 3 passos de física do warp atual), o warp para e aparece "Isso não é uma montanha... é uma onda!".
- **Parallax Continued** (`Compat/Parallax.cfg`, opcional, NEEDS dos pacotes stock de texturas/scatters):
  - Terreno: Mann usa as texturas do Eeloo, Edmunds as do Dres. O Parallax multiplica pela cor de vértice, então os mapas de cor do pack continuam valendo.
  - Pedras: as do Dres nos dois planetas. **Verificado em Edmunds:** pedras pequenas a grandes até o horizonte.
  - **Verificado em Mann** (após reiniciar): pedras escuras espalhadas pela geleira (docs/screenshots/parallax_mann.png).
  - **Gotcha:** em Mann, as placas de gelo do Eeloo não apareciam (relevo enrugado demais para o filtro de inclinação, e as poucas placas somem no branco). Trocadas pelas rochas do Dres (detritos de morena) com steepPower 3 (era 8).
  - Subdivisão PQS 6/500 (como Eeloo/Dres stock).
  - Mudanças nos scatters só valem depois de reiniciar o KSP.

## 2026-10-17 — Estrela de nêutrons como pulsar; protótipo de névoa do disco descartado
- Estrela de nêutrons agora é `type = Star` (template Sun), como a Anubis do Cosmic Serenity, mas com `givesOffLight = false`. O StarLightSwitcher do Kopernicus só considera estrelas que emitem luz (KopernicusStar.cs), então ela brilha sem roubar a luz de Mann.
- **Jatos de pulsar** no plugin (`src/GargantuaWaves/ScaledEffects.cs`), com o shader `KSP/Particles/Additive` do próprio KSP:
  - feixe fino + bainha larga com poeira, em faixas que giram em volta do próprio eixo para encarar a câmera;
  - halo virado para a câmera;
  - eixo magnético a 25° do eixo de rotação, girando a cada 5 s (farol, só visual).
- **Gotchas:**
  - Lente do Singularity na própria estrela (gravity 0.02, como na Anubis): desenhava uma esfera escura enorme com estrias e escondia tudo. Removida.
  - `KSP/Particles/Additive` ignora a cor de vértice. Cor e intensidade vão na textura ou no `_TintColor`.
  - Faixa em trapézio com só 2 triângulos: distorção afim da textura, e o fio e a bainha saíam em ângulos diferentes. Agora são 32 linhas com uma coluna central.
  - **Singularity apaga efeitos transparentes na layer 10:** a esfera da lente de Gargantua tem raio sqrt(gravity)·120 un. = 6,7E10 m, maior que a órbita da pulsar. Dentro dela o shader repinta a tela com a cena recapturada, e o que não escreve profundidade vira fundo. Solução: layer livre (3) e uma câmera própria logo depois da escalada (CopyFrom no OnPreCull, limpando só a profundidade).
  - Limitação: os jatos não somem atrás de planetas.
  - Verificado na vista do mapa a 2,5E9 m da estrela (docs/screenshots/pulsar_jets.png). Não testado no Tracking Station nem na KSC.
- Protótipo de névoa do disco (camadas aditivas acima e abaixo do disco): **descartado**. As camadas viravam faixas listradas, não eram dobradas pela lente e, fora da layer 10, ficavam por cima de tudo. Disco volumétrico de verdade exige shader próprio (asset bundle do Unity 2019.4) e ainda assim não seria dobrado pela lente.
- Observado: com o Singularity, a partir da órbita da pulsar aparecem faixas escuras no disco visto quase de lado, e uma faixa vertical mais escura no céu. Somem sem o Singularity; não vêm destas mudanças.
- Build de teste com `-p:DefineConstants=GARGSYS_DEBUG` loga a posição da pulsar na tela (para mirar a câmera nos testes).

## 2026-10-17 — Correção: céu "congelando" e rachando (câmera extra dos jatos)
- Causa: a câmera dos jatos copiava a câmera escalada com `CopyFrom`, e a escalada roda em **DeferredShading** por causa do mod Deferred. Uma câmera deferred que não limpa a cor (clearFlags Depth) reaproveita a imagem velha na composição de luz, e o céu "congelava" e rachava. A mesma coisa causava a "faixa escura vertical" que eu tinha atribuído ao Singularity.
- Correção:
  - a câmera é forçada a Forward, sem HDR e sem MSAA;
  - quando a câmera escalada não está ativa, a dos jatos não desenha nem limpa nada.
- Tentado e descartado: CommandBuffer na própria câmera escalada (`AfterForwardAlpha` e `AfterEverything`). Os jatos não apareciam em nenhum dos dois.
- Verificado: jatos visíveis no mapa e no voo, girando a câmera e alternando mapa/voo, sem imagem velha nem faixa escura (docs/screenshots/pulsar_map_flight.png). O congelamento relatado não aconteceu na sessão de teste.

## 2026-10-17 — Céu rasgado/congelado: causa é o TAA do Scatterer
- Sintoma (print do usuário): a galáxia aparece rasgada em blocos verticais e borrada, e o céu parece congelado. Isso continuou mesmo **sem** os jatos.
- Causa: o TAA (antialiasing temporal) do Scatterer 0.0878, junto com o Singularity e o Deferred. As naves do sistema ficam dentro da esfera da lente de Gargantua (raio 6,7E10 m), onde o Singularity repinta o céu, e o TAA mistura quadros velhos.
- Correção (na instalação do usuário, fora do mod): `scatterer/config/config.cfg` → `useTemporalAntiAliasing = False`. Backup em `config.cfg.bak_taa`. O SMAA continua ligado. Verificado: vistas de voo limpas (docs/screenshots/sky_taa_off.png).
- Jatos da pulsar removidos (`ScaledEffects.cs`) enquanto eu procurava a causa. A estrela continua azul e brilhante. A versão com jatos está no commit c5b1e95.
- README (fase 5): avisar para desligar o TAA do Scatterer.

## 2026-10-17 — Céu rasgando: causa real é a esfera da lente do Singularity
- Com o TAA desligado, o céu ainda rasgava perto da pulsar (print do usuário): galáxia em faixas verticais, blocos escuros.
- Causa: a esfera da lente de Gargantua (raio = scaleEnclosingMesh·sqrt(gravity)·120 un. = 6,7E10 m com scale 1) engolia a pulsar e chegava quase a Mann. Dentro dela, longe do buraco, o traçado de raios do Singularity rasga o céu. Não tem relação com as mudanças no disco: a esfera depende só de `gravity`, que nunca mudou.
- `scaleEnclosingMesh = 0.6` (4E10 m). Com 0.35 (2,35E10) o céu ficava limpo, mas a esfera cortava a imagem lensada do disco num círculo duro.
- Órbita da pulsar: 3,5E10 m (e 0.1) → 5E10 m (e 0.05), para ficar fora da esfera.
- Verificado: perto da pulsar o céu fica limpo e o disco aparece inteiro (docs/screenshots/sky_lens06_pulsar.png). Em Miller (dentro da esfera), disco ok, sem rasgo; restam linhas finas e fracas perto do plano do disco (sky_lens06_miller.png).
- Efeito colateral: de longe dá para ver a borda da esfera como um círculo em volta de Gargantua (céu um pouco mais escuro dentro, poeira externa do disco cortada).
- Ajuste (usuário: o buraco negro "só aparece dentro de uma bolha" e a borda cortava um pedaço do disco): esfera `0.8` (5,4E10 m) e pulsar a 6,2E10 m (e 0.03), fora dela. Verificado perto da pulsar: disco inteiro, sem corte, céu sem rasgo (docs/screenshots/sky_lens08_pulsar.png).
- Limitação do Singularity, sem opção de config: dentro da esfera o céu vem de uma cópia da galáxia capturada no carregamento, sem o escurecimento dinâmico do KSP. Por isso a esfera pode aparecer como um círculo levemente mais escuro ou mais claro em volta de Gargantua. Vai para o README.

## 2026-10-17 — Jatos da pulsar de volta, sem câmera extra, e com mais qualidade
- Com a pulsar fora da esfera da lente (6,2E10 m), os jatos voltam a ser objetos comuns da layer 10. Sem câmera extra e sem command buffer. Vistos através da esfera, atrás de Gargantua, eles somem (o Singularity repinta lá).
- Usuário: "parece um png de baixa resolução girando". Mudanças:
  - texturas 256×1024 e 256² com filtro trilinear/anisotrópico;
  - camada nova de filamentos (14 fios, brilho pulsando em ondas que repetem sem emenda) que escorre para fora via `mainTextureOffset`, em tempo real (`Time.time`, não UT, para não virar borrão no timewarp). O sumiço nas pontas vem da largura em losango, já que a textura rola;
  - giro de 5 s → 30 s (igual à rotação do corpo).
- Verificado no mapa (docs/screenshots/pulsar_jets_v2.png).
- A pasta `Downloads/Anubis` do usuário só tem `AnubisJets.cfg`; o `Jets.unity3d` fica no pacote principal do Cosmic Serenity ("All Rights Reserved"), então não foi usado.

## 2026-10-17 — Aviso da onda a 50 km (depois 33 km)
- Antes: o aviso disparava pela janela de tempo (≥180 s ou 3 passos de física do warp atual) e, em warp alto, mostrava distâncias enormes.
- Agora: o warp para quando a crista está a ≤50 km do chão ou a até 3 passos de física (o que vier primeiro). A mensagem só aparece com a crista a ≤50 km. `WarnDistance` em MillerWaves.cs (33000 m, pedido do usuário).
- O texto em inglês já existia (`en-us` em Localization.cfg); o KSP escolhe pelo idioma do jogo.
- Não testado no jogo (precisa esperar uma crista com a nave no lado certo de Miller).
