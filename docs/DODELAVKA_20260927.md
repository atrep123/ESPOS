# Dodělávka ESPOS — 27. 9. 2026

Rozsah: `C:\Users\atrep\Documents\kimi\workspace\research\ESPOS`.
Přečteny `AGENTS.md`, `src/AGENTS.md`, pravidla sousedního `tabos-core/AGENTS.md`
a celá inventura `tabos-core/docs/INVENTURA_20260927.md`.
Při převzetí zde bylo 9 změněných sledovaných a 2 nové soubory.
Původní smíšený WIP je zachován; nebyl proveden commit, push, checkout ani reset.

## Výsledek a opravy

GPIO WIP kontroluje pin a logickou úroveň před generováním C, odmítá
řetězce, desetinná čísla, bool a neplatný rozsah. Firmware kontroluje
znaménko/rozsah a platnost pinu podle IDF před bitovým posunem; při selhání
`gpio_config` nepokračuje na zápis. Validace je povinná v PlatformIO
i přímé CMake cestě a při vypnutém exportu musí existující C/H odpovídat
ověřenému návrhu. Tyto změny jsou převzatý WIP, nikoli všechny nově napsané
v této dodělávce.

Nové funkční změny této dodělávky:

- `scripts/pio_generate_ui_design.py`: relativní `ESP32OS_UI_JSON` se nyní
  vyhodnocuje vůči `PROJECT_DIR`, i když volající pracuje v jiné složce.
- `tests/test_gpio_security.py`: 13 nových regresí pro GPIO úrovně,
  kladné hranice rozsahu, relativní cestu a odmítnutí neplatného návrhu
  při `ESP32OS_PIO_UI_EXPORT=0` i `ESP32OS_UI_VALIDATE=0`; původní C zůstává
  při odmítnutí beze změny.
- `tools/validate_design.py`, pravidlo 123: dotýkající se cizí widgety
  se společným pásem mají nyní nález pro nulovou mezeru. Překryv, pouhý
  dotek rohu, diagonální mezera a vlastní skupina nejsou tento nález.
- `tools/validate_design.py`, pravidlo 147: svislá čára procházející
  inkoustem neztratí nález prodloužením nad/pod text. Pouhý dotek horní
  nebo dolní hrany nadále nehlásí přeškrtnutí.
- Tři strict xfail značky skutečných vad v
  `tests/test_hranice_starych_pravidel.py` a
  `tests/test_validate_rules_147_svisle.py` nahrazeny běžnými regresními
  testy po opravě produkčního validátoru. Test dokládající staré chybné
  chování nyní vyžaduje správné chování, doplněny negativní geometrické třídy.
- Ruff mechanicky naformátoval 25 souborů v ESPOS, které neprocházely
  předepsanou formátovací branou. Původní JSON fixture a její rozpracovaná
  obsahová změna nebyly přepisovány.

Navazující opravy podle požadavku na uzavření místních bran:

- `tools/validate_design.py`: `_is_int` má skutečný návratový typ
  `TypeGuard[int]` (nadále odmítá bool), souřadnice se ověřují jednotlivě
  a neplatné rozměry nezmizí normalizací. Lokální hodnoty timer/max_lines
  se po ověření používají jako int; proměnná regex match má samostatné jméno.
  Profil s `font_chars=None` znamená neomezenou sadu znaků, nikoli pád;
  kontrola vejití textu zůstává aktivní.
- `ui_designer.py`: malý typovaný `_widget_size` řeší Optional rozměry
  na místech aritmetiky; nenahrazuje záporné/nulové rozměry kladnými.
  Distribuce počítá průběžnou pozici jako float, takže neztrácí zlomkový krok.
- `ui_cli.py`: odlišná jména pro rozdílné typy ve větvích CLI;
  `board_registry.py`: explicitní kontrola přítomnosti display.
  V `ui_models.py`, `ui_designer.py`, `board_registry.py` a
  `ui_template_manager.py` odstraněny pouze nepotřebné existující ignore.
  Mypy konfigurace, globální ignore ani exclude se neměnily;
  nepřibyly nové type-ignore ani obcházení pomocí Any/cast.
- `tests/test_type_boundaries.py`: 7 behaviorálních regresí pro normalizaci
  modelu/resizing, odmítnutí skutečně neplatných JSON rozměrů a profil
  bez omezené sady znaků se zachovanou kontrolou přetečení textu.
- `requirements-dev.txt` už obsahuje `pytest-cov>=4.1.0,<6` i
  `coverage[toml]>=7.3.0,<8`; nebyla přidána duplicitní deklarace.
  Chybějící lokální balíčky byly instalovány v těchto mezích:
  pytest-cov 5.0.0 a coverage 7.16.1.
  Pro samostatnou existující CI benchmark bránu doplněn také lokálně
  chybějící, již deklarovaný pytest-benchmark 5.3.0 (py-cpuinfo2 10.1.1).
- `pyproject.toml`: coverage source vyžaduje názvy modulů, nikoli
  názvy souborů s `.py`. Opraveno všech sedm existujících položek;
  nyní se model/designer/utils skutečně měří. Práh 80 %, branch coverage
  ani seznam výjimek se neměnily. První běh s chybně vynechanými moduly
  (87.91 %) není používán jako finální důkaz pokrytí.

`src/ui_design.c` a `src/ui_design.h` nebyly ručně editovány a nemají Git diff.
Návrh `main_scene.json` zůstal nezměněn.

## Aktuální místní ověření

Host: Windows, Python 3.12.10, PlatformIO Core 6.1.19. Python testy běžely
se `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`,
`PYTHONIOENCODING=utf-8`, nejvýše dvěma pytest workery.

| Příkaz / sada | Výsledek |
|---|---|
| Finální plná CI pytest sada s coverage po doručení kit scén (příkaz níže) | **8722 passed, 0 skipped**, 2 varování, 119.12 s, exit 0; žádný xfail; **88.59 %** line+branch coverage, práh 80 % splněn |
| Paletová sada nad 42 dodanými scénami: `python -m pytest -q -rs tests/test_paleta_jeden_zdroj.py` | **18 passed**, 0.61 s, exit 0 |
| Následný workflow kontrakt: `python -m pytest -q --tb=short tests/test_supply_chain_guard.py` | **35 passed**, 0.32 s, exit 0; obsahuje nový přesný branch kontrakt |
| `python -m pytest -q --tb=short tests/test_type_boundaries.py` | **7 passed**, 0.23 s |
| `python -m pytest tests/test_benchmarks.py --benchmark-only --benchmark-json=output/dodelavka_20260927_benchmarks.json -q` | **15 passed**, skutečný pytest-benchmark plugin, 11.16 s, exit 0 |
| GPIO + PlatformIO hook: `python -m pytest -q --tb=short tests/test_gpio_security.py tests/test_pio_generate.py` | **64 passed**, 2.02 s |
| Pravidla 123/147 + sousední hranice + mutační regrese: `python -m pytest -q --tb=short tests/test_hranice_starych_pravidel.py tests/test_validate_rules_147_svisle.py tests/test_validate_rules_144_147.py tests/test_mutace_pravidel.py` | **165 passed**, 4.91 s |
| `python -m platformio test -e native` | **1147 succeeded**, všech 31 sad passed, Unity 2.6.1, 70.998 s, exit 0 |
| Přesný povinný CI mypy příkaz uvedený níže | **0 chyb**, exit 0, bez follow-imports=silent |
| `python -m mypy --ignore-missing-imports --no-error-summary ui_designer.py ui_models.py ui_template_manager.py` | **0 chyb**, exit 0 i bez advisory `|| true` |
| `python -m ruff check .` | All checks passed, exit 0 |
| `python -m ruff format --check .` | 309 files already formatted, exit 0 |
| `python scripts/check_codegen_freshness.py` | C/H odpovídají aktuálnímu návrhu, exit 0 |
| `python tools/validate_design.py main_scene.json --strict-critical` | exit 0, **82 WARN**, žádný ERROR |
| `python tools/audit_designs.py --root .` | všech 7 nalezených návrhů OK, exit 0 |
| `python tools/check_supply_chain.py` | supply-chain guardrails OK, exit 0 |
| `git diff --check` | exit 0 |

Finální JUnit `output/dodelavka_20260927_final_pytest.xml` obsahuje 8722 případů,
0 failures, 0 errors, 0 skipped. `output/` je lokální ignorovaný výstup.
Validátorový log: `output/dodelavka_20260927_design.log`.

Finální coverage příkaz (přesná CI brána doplněná o místní JUnit):

```powershell
python -m pytest -q --tb=short --ignore=output -n 2 --maxprocesses 2 --cov --cov-report=term-missing:skip-covered --cov-report=html:htmlcov --cov-fail-under=80 --junitxml=output/dodelavka_20260927_final_pytest.xml
```

Finální log: `output/dodelavka_20260927_final_coverage.log`, HTML: `htmlcov/index.html`.
Pokrytí zahrnuje 21300 statements a 8240 branches produktového kódu.
Dvě varování coverage o časném importu `constants` nejsou potlačena.
Kontrolou skutečných coverage dat (`Coverage.analysis2`) ověřeno, že
`constants.py`, `design_tokens.py` a `event_manager.py` mají všechny
vykonatelné řádky změřené a žádné chybějící; nejde o znovu vynechané moduly.
Finální plná sada již běžela s nainstalovaným pytest-benchmark pluginem;
paralelní coverage běh není samostatná časová benchmark brána.
Samostatná benchmark brána následně prošla se skutečným pluginem:
`output/dodelavka_20260927_benchmarks.log` a
`output/dodelavka_20260927_benchmarks.json` (15 měření).
Benchmarky nemají nakonfigurovanou srovnávací výkonovou hranici;
jejich úspěch neznamená prokázané zrychlení proti baseline.

Počáteční plná sada před novými opravami byla 8696 passed, 1 skipped,
3 xfailed; není to finální stav. Po přidání GPIO regresí mezistav
8709 passed, 1 skipped, 3 xfailed rovněž nenahrazuje finální výsledek výše.

### Mypy a nativní C

Povinný příkaz z CI nyní prochází včetně importovaných modulů:

```powershell
python -m mypy --ignore-missing-imports --no-error-summary tools/ui_codegen.py scripts/pio_generate_ui_design.py design_tokens.py shared_undo_redo.py event_manager.py constants.py
```

Původních 109 chyb je opraveno skutečnými typy a lokálním narrowingem.
Log `output/dodelavka_20260927_mypy.log` je po úspěšném běhu prázdný;
mypy se spouštělo bez `--follow-imports=silent`.

Navazující standardní `python -m platformio test -e native` úspěšně
nainstalovalo předepsanou Unity 2.6.1 a provedlo všech 1147 případů.
Log: `output/dodelavka_20260927_native.log`. Níže zůstává pro dohledatelnost
popsán starší offline běh, nikoli nynější omezení brány.

Běžné `python -m platformio test -e native` se pokusilo instalovat
`throwtheswitch/Unity@^2.6.1`, která v lokální cache nebyla. Běh byl ukončen.
Následující skutečný běh všech stejných C sad použil dostupnou Unity 2.6.0
z IDF. Globální instalace ani `platformio.ini` nebyly upravovány:

```powershell
python -c "import sys; from platformio.test.runners.unity import UnityTestRunner; UnityTestRunner.EXTRA_LIB_DEPS = [r'C:\Users\atrep\.platformio\packages\framework-espidf\components\unity\unity']; from platformio.__main__ import main; sys.argv = ['platformio', 'test', '-e', 'native']; main()"
```

PlatformIO nainstalovalo tuto lokální knihovnu do ignorovaného `.pio`.
Starší výsledek byl host ověření 1147 případů s Unity 2.6.0;
nyní stejná sada prošla i standardním příkazem s Unity 2.6.1.
Nativní `build_src_filter`
nezahrnuje `src/services/logic/logic.c`; GPIO runtime se tím fyzicky
ani nativně nevykonal. Python GPIO testy ověřují návrh, generátor a build gate.

### S3 build

Finální **čistý překlad uspěl**, exit 0, 184.520 s. Vyčištěny byly pouze
regenerovatelné artefakty prostředí `.pio/build/esp32-s3-devkitm-1-nohw`
příkazem `python -m platformio run -e esp32-s3-devkitm-1-nohw -t clean`.
Potom skutečně proběhl `python -m platformio run -e esp32-s3-devkitm-1-nohw -j 2`.
Log `output/dodelavka_20260927_s3.log` obsahuje nový překlad
`src/services/logic/logic.c` i ostatních zdrojů, linkování a vytvoření binárky;
neobsahuje compiler `warning:` ani `error:`.

ESPOS podle vlastního `platformio.ini` používá espressif32 6.12.0,
framework-espidf 3.50500.0 (**IDF 5.5.0**), Xtensa GCC 14.2.0.
Toto není TabOS build ani ověření IDF 5.5.4. Konfigurace nástrojů nebyla
měněna jen kvůli testu.

- RAM: 84912 / 327680 B, 25.9 %.
- Flash image usage: 375153 / 1048576 B, 35.8 %.
- Binárka: `.pio/build/esp32-s3-devkitm-1-nohw/firmware.bin`, **375664 B**.
- SHA256 binárky:
  `88109C0B0E2B2EF54B630E60170ADB2613A4F9062512014776C3D1C2EB3D278E`.
- SHA256 `sdkconfig.esp32-s3-devkitm-1-nohw` před i po všech buildech:
  `F731DA30DBD5668A0C8474953B27BC3C468B7F475C9B134DFAA2E9E7B70A6B4D`.
  Soubor se nezměnil.

Dva dřívější inkrementální překlady prošly se stejným využitím RAM/flash;
jejich hash není používán jako finální identita čistě přeložené binárky.

Po navazujících typových opravách znovu prošel inkrementální příkaz
`python -m platformio run -e esp32-s3-devkitm-1-nohw -j 2`, exit 0,
4.855 s. Log: `output/dodelavka_20260927_s3_followup.log`.
Tento běh zopakoval validaci a build gate; netvrdí nový čistý překlad C.
SHA256 binárky i sdkconfig zůstaly přesně stejné jako výše.

## Otevřené brány a hranice důkazů

- Dřívější jediný Python skip byl chybějící `_scena_*.json` v existujícím
  sousedním kitu. Během finálního předání jeho vlastník dodal všech 42
  scén; ESPOS consumer již prošel **1 passed**, 0.24 s, bez skip.
  Celý `tests/test_paleta_jeden_zdroj.py` prošel **18 passed**, 0.61 s.
  Kit na `C:\Users\atrep\Documents\kimi\workspace\tabos-ui-kit` byl
  pouze čten. Hashové sidecary `_snimek_*.json` nebyly vydávány za scény;
  ESPOS nevytvářel náhradní data ani sám nespouštěl export do cizího kitu.
  Samotná exportní brána kitu má podle owner artefaktu exit 1, proto
  uzavřený paletový consumer není tvrzení o úplném zeleném kit návrhu.
- Povinná mypy brána i advisory designer brána jsou nyní uzavřené,
  stejně jako místní CI coverage brána. Původních 109 chyb a chybějící
  pytest-cov nejsou nynější blokery.
- Návrh má 82 varování (před opravou pravidla 123 měl 80), včetně dvou
  nově zachycených nulových mezer. To nebrání `--strict-critical`, ale
  neznamená návrh bez připomínek ani vizuální potvrzení.
- Firmware nepoužil flash, COM, síť zařízení ani živý hardware.
  První build/test procesy měly HTTP/HTTPS proxy na nepoužitý loopback
  port 127.0.0.1:9; při pokračování se stáhly pouze výše popsané
  testovací závislosti a Unity 2.6.1, nikoli data z desek/modelových služeb.
  Automatické aktualizační kontroly PlatformIO byly odloženy vysokými
  intervaly v prostředí jednotlivých procesů.
- Neproběhl vzdálený CI, audit závislostí `pip-audit` (lokálně není
  instalován), úplný mutmut běh, Arduino Nano build ani vydání.
  To nejsou zde ověřené brány. Dlouhý modelový běh neproběhl. TabOS IDF 5.5.4,
  jeho sdkconfig, ALWAYSINTERNAL a DSI zůstaly mimo tento pracovní rozsah.

Výsledek uzavírá místní funkční regrese GPIO/build gate, dvě doložené
vady validátoru, skutečné typové chyby a povinné místní Python brány.
Není to tvrzení, že vzdálená CI matice, všechny vizuální návrhy
nebo elektrické vlastnosti zařízení jsou ověřeny.

## Předání před commitem: finální review a CI příkazy

Navazující review prošlo diff GPIO/validátoru/codegenu, obě build cesty,
typové opravy designeru/CLI a regresní testy. V prohlédnutém rozsahu
nenalezen nový blokující correctness nález. Není to úplný bezpečnostní audit.
Kontrolováno, že odmítnutý GPIO návrh nepřepisuje C, vypnutý export
neobchází validaci ani freshness, kontrola pinu předchází bitovému posunu
a `_is_int` nadále odmítá bool. U typových oprav nebyla zrušena validace
neplatných rozměrů ani kontrola přetečení textu.

Předávací cílená sada:
`python -m pytest -q --tb=short -rs tests/test_paleta_jeden_zdroj.py tests/test_gpio_security.py tests/test_type_boundaries.py tests/test_pio_generate.py`
prošla **88 passed, 1 skipped**, 3.51 s, exit 0.
Log: `output/dodelavka_20260927_final_targeted.log`.
Skutečné `_scena_*.json` v kitu při tomto běhu stále chyběly.
Žádný export z Chrome DOM nebyl na straně ESPOS nahrazen fixture nebo
syntetickým JSON. Kit owner má dodat měřené vstupy; ESPOS je pouze čte.

Následně během téhož předání skutečné exporty dorazily. Dřívější skip
výše je historický mezistav, nikoli finální stav. Owner artefakt
`C:\Users\atrep\Documents\kimi\workspace\tabos-ui-kit\navrh-appky\_export_scen_20260927.json`
dokládá příkaz `do_espos.py --zapis-scenu --tridy kapacita` pro 42
artboardů, trvání 44.52 s, `missing=[]`, `protected_changed=[]` a SHA256
84 výstupů (42 scén + jejich meta). Jeho `gate_exit=1` zůstal přiznaný.
Jde o ownerův důkaz běhu; ESPOS sám Chrome DOM export neprováděl.
Read-only ověřeno, že všechny výstupní hashe odpovídají souborům.
Diagnostika `_export_scen_diagnostika_20260927.json` identifikuje tentýž
aktuální ESPOS validátor SHA256
`9318ea1af839606c5db3c93e7b5153cba5efd5a280a5a04f959caec08f278503`.

Lokální inventář consumer inputs s přesnými absolutními cestami,
velikostmi a SHA256: `output/dodelavka_20260927_kit_inputs.json`.
Obsahuje 42 validních JSON scén, všechny mají paletu a soustavu;
žádný hashový drift proti snapshotu nebyl nalezen.
Log paletové sady: `output/dodelavka_20260927_kit_consumer.log`.

Finální Ruff byl dorovnán z 0.15.12 na **0.15.22**, aby splňoval
`ruff>=0.15.16,<0.16` z requirements-dev. Lint i format check prošly
s touto skutečnou verzí: 309 files already formatted. Nebylo potřeba
znovu měnit žádný zdrojový soubor kvůli novému formátovači.

### Dostupné příkazy bez HW

Spouštět v `C:\Users\atrep\Documents\kimi\workspace\research\ESPOS`.
Každý příkaz posuzovat podle vlastního exit kódu; nepřekrývat selhání
předchozího příkazu úspěchem posledního.

```powershell
$env:SDL_VIDEODRIVER='dummy'
$env:SDL_AUDIODRIVER='dummy'
$env:PYTHONIOENCODING='utf-8'
python -m ruff check .
python -m ruff format --check .
python -m mypy --ignore-missing-imports --no-error-summary tools/ui_codegen.py scripts/pio_generate_ui_design.py design_tokens.py shared_undo_redo.py event_manager.py constants.py
python -m mypy --ignore-missing-imports --no-error-summary ui_designer.py ui_models.py ui_template_manager.py
python tools/validate_design.py main_scene.json --strict-critical
python tools/audit_designs.py --root .
python tools/check_supply_chain.py
python scripts/check_codegen_freshness.py
python -m pytest -q --tb=short tests/test_input_handlers.py tests/test_input_handlers_mouse.py tests/test_focus_nav.py tests/test_focus_nav_listmodel.py tests/test_inspector_commit.py tests/test_scene_ops.py
python -m pytest -q --tb=short --ignore=output -n 2 --maxprocesses 2 --cov --cov-report=term-missing:skip-covered --cov-report=html:htmlcov --cov-fail-under=80
python -m pytest tests/test_benchmarks.py --benchmark-only --benchmark-json=output/dodelavka_20260927_benchmarks.json -q
python -m platformio test -e native
python -m platformio run -e esp32-s3-devkitm-1-nohw -j 2
git diff --check
```

Guardrail soubory jsou zahrnuty i v plné sadě. Designer mypy se zde
ověřuje bez CI advisory `|| true`. Native testuje host C, S3 příkaz
pouze překládá. Nepoužívat `-t upload` ani `platformio test` pro board
prostředí: označení nohw není obecné oprávnění k detekci/obsluze zařízení.

Lokální dostupné hlavní testovací závislosti: pytest 9.0.3,
pytest-cov 5.0.0, coverage 7.16.1, pytest-xdist 3.8.0,
pytest-timeout 2.4.0, pytest-benchmark 5.3.0, mypy 1.20.1,
Ruff 0.15.22, PlatformIO 6.1.19 a Unity 2.6.1.

### CI kroky připravené, nyní nezapojené / WIP ponechaný

Tyto příkazy již existují v `.github/workflows/ci.yml`; nejsou novou
implementací v tomto předání a nebyly nyní spuštěny:

| Krok | Existující CI příkaz | Místní stav / další závislosti |
|---|---|---|
| Audit dev dependencies | `python -m pip_audit -r requirements-dev.txt --strict --desc --ignore-vuln PYSEC-2026-161` | pip-audit není instalován; deklarováno `pip-audit>=2.10.1,<3`; potřebuje síťový resolver/audit službu; existující cílenou výjimku jsme neměnili |
| Audit MCP dependencies | `python -m pip_audit -r requirements-mcp.txt --strict --desc` | stejný chybějící audit nástroj; auditovat deklarované `mcp>=1.27.2,<2`, ne tvrdit audit lokálního MCP 1.27.1 |
| Mutation testing, advisory | `python -m mutmut run --no-progress`, potom `python -m mutmut results` a `python -m mutmut html` | mutmut není instalován; deklarováno `mutmut>=2.5.0,<3`; úplný běh může být dlouhý, ponechán dle zadání; původní CI používá shell tail a 20min timeout |
| Budoucí Nano nohw build | `python -m platformio run -e arduino_nano_esp32-nohw` | prostředí existuje v platformio.ini, ale tento překlad/toolchain zde není ověřen; WIP nebyl dokončován ani sdkconfig měněn |

Existující CI bootstrap je
`python -m pip install --upgrade "pip>=26.1.2,<27"` a
`python -m pip install -r requirements.txt -r requirements-dev.txt`.
Lokální pip zůstává 25.0.1; nový resolver/bootstrap ani celá čerstvá CI
instalace nebyly ověřeny. Pip-audit a mutmut jsou již v manifestu,
nejsou to chybějící deklarace, pouze nyní nepřipojené lokální nástroje.
MCP je samostatná volitelná vrstva s requirements-mcp.txt; lokální 1.27.1
neodpovídá jeho nynějšímu minimu 1.27.2, proto se její úplné fresh-install
ověření nesmí přičíst k zeleným hlavním Python branám.

### Consumer po doručení měřených scén z kitu

Po skutečném exportu vlastníkem kitu stačí nejprve read-only consumer:

```powershell
python -m pytest -q -rs tests/test_paleta_jeden_zdroj.py::test_zive_sceny_kitu_NESOU_paletu_a_soustavu
```

Příkaz nyní skutečně skončil **1 passed**, nikoli skip. Uzavírá chybějící
consumer test; sám o sobě neprokazuje Chrome DOM měření ani neodstraňuje
vlastní nálezy kitu. Ownerův exportní důkaz je odlišen výše. Plný coverage
běh po doručení scén prošel 8722 passed, bez skip, s 88.59 % pokrytím.
Commit/push zůstává na rodiči po jeho
vlastním posouzení; ESPOS ho neprovedl. Rodič ESPOS zdroje neměnil.

### Push CI pro publikovanou větev

Na výslovný požadavek rodiče přidána pouze přesná větev
`codex/dodelavky-20260927` do `.github/workflows/ci.yml` → `on.push.branches`.
Seznam je nyní `main`, `master`, `codex/dodelavky-20260927`;
`on.pull_request.branches` zůstal `main`, `master` a oprávnění
`contents: read` zůstalo beze změny. Nebyl přidán wildcard, workflow_dispatch,
nová oprávnění ani mutation PR/main. Žádné Git write operace neproběhly.

V `tests/test_supply_chain_guard.py` doplněn trvalý kontrakt pro přesný
push seznam i zachovaný PR seznam. Celý tento soubor prošel 35 passed,
0.32 s; následně prošel supply-chain guard, Ruff lint a format check.
Při místním diagnostickém načtení skutečného YAML pomocí BaseLoader
potvrzeny stejné struktury triggerů a read-only oprávnění.
Trvalý test používá pouze standardní knihovnu, žádná nová YAML dependency
nebyla přidána do manifestu.

Log: `output/dodelavka_20260927_ci_contract.log`. Tato malá workflow/test
změna vznikla až po plné sadě 8722; není předstírána nová plná sada 8723.
Pro změnu triggeru proběhlo přiměřené cílené ověření 35 testů a YAML kontraktu.
Vzdálený GitHub Actions běh nastane až při rodičově push a zde není potvrzen.
