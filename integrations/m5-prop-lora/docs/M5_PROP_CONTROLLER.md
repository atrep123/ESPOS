# M5 Prop LoRa Controller — Systémová dokumentace

> Bezdrátový ovladač RGB-LED „prop" efektů pro divadlo / pyro show.
> Stav: jádro hotové a ověřené na reálném HW (100 % doručení, dual-band, efektový engine, robustnost pro zahlcená místa).
> Poslední aktualizace: 2026-05-24.

---

## 1. Přehled

Operátor na **M5 Dial** (kulatý ovladač) navolí barvy/efekt a odpálí **FIRE**. Povel jde bezdrátově (LoRa 868 MHz **+** ESP-NOW 2.4 GHz současně) přes dvojici **C6 modemů** k **M5 DinMeter** (přijímač), který přehraje světelný efekt na 4 (konfigurovatelně N) RGB LED.

Návrhové priority (pořadí): **spolehlivost doručení → bezpečnost → nízká latence → bohatost efektů**.

---

## 2. Architektura řetězce

```
[M5 Dial]  --UART(115200)-->  [C6 modem A]  ==LoRa 868 + ESP-NOW 2.4==>  [C6 modem B]  --UART-->  [M5 DinMeter]  --WS2812-->  [N×RGB LED]
 ESP32-S3                      ESP32-C6+SX1262                            ESP32-C6+SX1262          ESP32-S3
 GC9A01 240×240               (UART<->RF most)                           (UART<->RF most)         ST7789 240×135
 ESP-IDF + Mooncake                                                                               Arduino + LovyanGFX
 vysílač/ovladač                                                                                  přijímač/přehrávač
```

- **Dial** a **DinMeter** mluví výhradně aplikačním rámcem `prop_protocol`. Nevědí o rádiu — to je čistě věc modemů.
- **Modem** je hloupý UART⇄RF most: dostane `SEND/ACK/FF <hex>` po UARTu → vyšle po obou pásmech; co přijme z rádia → pošle hostu jako `RX <rssi> <snr> <hex>`.
- **Dedup** je na přijímači (DinMeter) — zahodí duplicitní kopie (3× redundance × 2 pásma = až 6 kopií/výstřel).

### COM mapa (vývoj přes USB)
| Port | Zařízení | Platforma | Pozn. |
|---|---|---|---|
| COM6 | M5 Dial | ESP-IDF (idf.py) | nativní USB-JTAG; Serial čitelný |
| COM7 | C6 modem A (Dial-side) | pioarduino (pio) | reportHost na USB i UART |
| COM8 | C6 modem B (DinMeter-side) | pioarduino (pio) | reportHost na USB i UART |
| COM9 | M5 DinMeter | PlatformIO official | **Serial NENÍ na USB** (jen flashing) |

---

## 3. Protokol (`shared/protocol/prop_protocol.h`)

Rámec (HEADER 20 B + payload ≤64 B + MAC 12 B, max 96 B):

| offset | pole | b | význam |
|---|---|---|---|
| 0–1 | magic | 2 | `0x504C` ("PL") |
| 2 | version | 1 | `1` |
| 3 | type | 1 | viz níže |
| 4 | keyId | 1 | id klíče |
| 5 | source | 1 | adresa odesílatele |
| 6 | destination | 1 | adresa cíle |
| 7–10 | sequence | 4 | u32, monotónní; horní bajt nese **epoch** (viz 5.3) |
| 11–18 | nonce | 8 | náhodný (anti-replay) |
| 19 | payloadLen | 1 | délka payloadu |
| 20.. | payload | ≤64 | data |
| konec | MAC | 12 | HMAC-SHA256 zkrácený |

**Typy:** `Ping(1) Status(2) Preview(3) Fire(4) Stop(5) Ack(6) Error(7) PaletteSet(8)`.
**Integrita:** HMAC-SHA256 (sdílený klíč), zkrácený na 12 B, ověřený konstantním časem. (Pozn.: jen autentizace, **ne** šifrování obsahu.)
**LED payload (Preview/Fire):** brightness(1) + 4×RGB(12) = 13 B. **PaletteSet:** rev + fade + 1–8 barev.

---

## 4. Komunikace

### 4.1 Fire-and-forget
FIRE se **nečeká na ACK**. Dial pošle FIRE **3× s jitterem** (~18–40 ms mezi kopiemi). Přijímač provede první platnou kopii, ostatní tiše zahodí (dedup). Best-effort **deferred ACK** (~90–130 ms po přijetí, 1× na výstřel) se vrací jen jako telemetrie „dorazilo".
- Důvod: SF7 má ~6–8 % ztrátu/paket; 3× redundance → <0,1 % selhání doručení, latence = první kopie.
- Deferred (ne okamžitý) ACK: vyhne se half-duplex kolizi s 3× burstem odesílatele.

### 4.2 Dual-band (LoRa 868 + ESP-NOW 2.4)
Každý rámec jde po **obou** pásmech současně. Přijímač dedupuje. Výhoda: pásmová diverzita (když jedno pásmo selže, druhé doručí) + nízká latence ESP-NOW (~jednotky ms) vs dosah LoRa.
- **LoRa:** 868.1 MHz, SF7, BW 250 kHz, CR 4/5, 13 dBm, preamble 8, syncword 0x34.
- **ESP-NOW:** WiFi STA, pevný kanál 1, power-save OFF.
- **Unicast+ACK auto-párování:** modem se naučí MAC protějšku z přijatých platných rámců → posílá **unicast** (HW retry/ACK); broadcast jako fallback do spárování a po 5 s ticha (re-pár).

### 4.3 Anti-replay + epoch (po rebootu)
Dedup = sliding-window 32-bit bitmask nad `sequence` + `lastSeq` v NVS. **Problém:** reboot Dialu (brownout) by resetoval seq → přijímač by nové výstřely zahazoval jako STALE. **Řešení:** Dial při bootu vygeneruje náhodnou **epochu** (horní bajt nonce); přijímač na novou epochu **resetuje dedup okno** → přijme novou session. (Pozn.: epocha 8-bit → 1/256 kolize; kandidát na 16-bit.)

### 4.4 Cesta spolehlivosti (měřeno)
| fáze | doručení | pozn. |
|---|---|---|
| bug (UART „ACK UNKNOWN" smyčka) | ~6 % | smyčka zahltila UART |
| oprava smyčky | 100 % (1 kopie/výstřel) | |
| + tichý DUP-drop | 100 % (3 kopie/výstřel) | redundance efektivní |
| + deferred ACK | 100 % doručení / **98–100 % potvrzení** | |
| + dual-band + unicast | 100 %, obě pásma, ~4–5 kopií/výstřel | Opus-ověřeno |

---

## 5. Robustnost pro RF-zahlcená místa (H1/H2/H3 + deep)
Sněm 3 modelů našel 8 latentních chyb, které se na čistém stole neprojeví. Implementováno + ověřeno:
- **Pre-filtr cizích rámců** v modemu (`hasProtocolHeader` před UARTem) → cizí ESP-NOW/LoRa (syncword 0x34 je generický) se nezahltí → brání recidivě UART bouře.
- **TX-stagger** ESP-NOW vs LoRa ~6 ms → menší proudová špička (brownout na baterii).
- **ESP-NOW RX fronta 32** (z 8) + drop-counter.
- **Duty-cycle leaky-bucket** (EU868 ~1 %): při překročení vynechá redundantní LoRa kopie (ESP-NOW jede dál).
- **Epoch anti-replay** (viz 4.3).
- **HEALTH telemetrie** každé 2 s: `OK HEALTH foreign=.. qdrop=.. rxfree=.. peer=.. dutyskip=..` na DinMeter HUD (+ per-band Rx LoRa/ESP-NOW, reset-reason/brownout).

---

## 6. Efektový engine (DinMeter-local)
Konfigurace je **lokální na DinMeteru** (NVS klíč `eff2`, edituje se enkodérem; Dial posílá jen barvy + FIRE trigger). Editace **live-apply** (co nastavíš, hraje hned — graf, Náhled i FIRE).

**Model výstupu LED:** `RGB(t) = barva(t) · B_tvar(t − delay_i) · intenzita`

- **Jas B(t)** (fáze φ=0..1, 5 tvarů): `SINE` sin²(πφ), `SQUARE` (param=duty 5-95 %), `SAWTOOTH` (param=směr nahoru/dolů), `TRIANGLE`, `EXP_DECAY` (param=ostrost).
- **Barva v čase (paleta):** 1–8 barev, režim `STEP` (tvrdé) / `FADE` (HSV lerp).
- **Per-LED delay** (chase), **intenzita** 10–100 %, **repeat** 1–∞, **pre-trigger glow**.
- **Konfigurovatelný počet LED** (1..30; přebytek natvrdo zhasnut → žádné stray LED).
- **UI menu (enkodér):** PŘED / DOBA / **TVAR** / parametr (DUTY/SMĚR/OSTROST) / OPAK / JAS / LED delays / Náhled.

---

## 7. UI

- **Dial (kulatý):** 12 stavů — PREVIEW/ARM/STOP/PING, ARMED→ODPAL, ODESÍLÁM/WAIT/POTVRZENO, NO ACK, SETUP LED/HUE/JAS. Zelený prstenec = stav, 4 tečky = LED kanály, orb = hodnota/akce.
- **DinMeter (obdélníkový):** živý graf křivky jasu (4 LED posunuté o delay), paleta (segmenty), LED delays, status (KLID/NABITO/PÁLÍ/ULOŽENO), baterie, debug HUD.
- **Simulátor:** `espos/tools/dinmeter_sim.html` (web), `render_dinmeter_native.py` (PNG rendery; `DINMETER_HIRES=1 DINMETER_TILES=1` → hi-res dlaždice).

---

## 8. Build & flash (DŮLEŽITÉ gotchas)

**Sdílený PlatformIO core `C:/piotx`** (POZOR: vždy forward-slash). Dial = ESP-IDF; modem = pioarduino; DinMeter = official espressif32@6.3.1.

> ⚠️ **Framework ping-pong:** modem (pioarduino, core 3.3.8) a DinMeter (official 2.0.9) sdílí balík `framework-arduinoespressif32` se stejným jménem → vzájemně se přepisují. Před buildem toho druhého smaž `C:/piotx/packages/framework-arduinoespressif32` a nech refetch. (Doporučená trvalá oprava: izolovat core dir modemu do `C:/piotx-c6`.)
>
> ⚠️ **Modem (C6/pioarduino) builduj jen z PowerShellu** (ne Bash/MSYS) — `idf_tools.py` odmítá MSYS prostředí → toolchain se nenainstaluje. `$env:MSYSTEM=$null`.

```powershell
# Modem (PowerShell): 
$env:MSYSTEM=$null; $env:PLATFORMIO_CORE_DIR="C:/piotx"; $env:PYTHONIOENCODING="utf-8"
pio.exe run -d <c6l-modem> -e m5stack-c6l                 # build
pio.exe run -d <c6l-modem> -e m5stack-c6l -t upload --upload-port COM7   # flash
```
```bash
# DinMeter (Bash OK): 
PLATFORMIO_CORE_DIR=C:/piotx PYTHONIOENCODING=utf-8 pio.exe run -e esp32-s3-devkitc-1
# flash app-only přes idf-python esptool:
python -m esptool --chip esp32s3 -p COM9 -b 460800 write_flash 0x10000 .pio/build/esp32-s3-devkitc-1/firmware.bin
```
```powershell
# Dial (PowerShell, ESP-IDF):
$env:MSYSTEM=$null; . esp-idf-v5.1.3\export.ps1
idf.py -C <dial-tx> -B C:\m5b\dial-tx -p COM6 flash
```

---

## 9. Testování / měření

- **Self-test:** Dial s `#define SELFTEST_FIRE 1` auto-pálí 50× á 700 ms + tiskne `STAT ff_sent=.. conf=.. ratio=..` po USB (COM6). (V ostrém provozu = 0.)
- **Čtení serial BEZPEČNĚ:** `python tools/read_com.py COM7 10 115200` — vynucuje `dtr=False/rts=False` (jinak DTR/RTS shodí COM7/8/9 do download módu). Filtruj až přes shell pipe, např. `| findstr RX`. **Nikdy** jiný monitor na COM7/8/9.
- **Reset Dialu:** `esptool --chip esp32s3 -p COM6 --before default_reset --after hard_reset run`.
- **Per-band měření:** z COM8 raw rozliš ESP-NOW (`RX 0.0 0.0`) vs LoRa (`RX <snr>`); dekóduj `sequence` z bajtů 7–10 → distinktní výstřely / delivery.
- **Sub-agenti (Opus)** dostávají přísně bezpečný postup a měří autonomně.

---

## 10. Známá omezení / odloženo
- Kanálová agilita ESP-NOW (boot sken rozbil ESP-NOW → odloženo; nutné s LoRa-koordinací kanálu).
- FIRE-mini rámec (menší, kratší airtime) — neimplementováno.
- Prostorové vzory efektu (COMET/SPARKLE/FIRE/RAINBOW) — odloženo (2. dávka).
- Epoch 8-bit (1/256 kolize) → 16-bit.
- Jen 1:1 (jeden přijímač); bez show/sekvencí; bez externího triggeru.
- Baterie netestována (zatím USB). Modem flash 89 % (WiFi stack) — málo místa.
- Sdílený `framework-arduinoespressif32` ping-pong (izolovat core dir).

---

## 11. Návrhy na vylepšení (výzkum sněmu)

Plná syntéza je v **[`IMPROVEMENT_ROADMAP.md`](IMPROVEMENT_ROADMAP.md)** — v2 = ~18
model-běhů **+ druhé kolo 5 recenzentů** (Codex/gpt-5.5, Gemini, Copilot-Sonnet-4.6,
Copilot-GPT-5.5, Opus), z nichž **4 ověřily nálezy přímo proti firmwaru**.

> ✅ **AKTUÁLNÍ STAV PO SPRINT A:** historické zjištění „receiver-side ARM není
> vynucen" je vyřešené: DinMeter přijímá samostatný ARM rámec, FIRE bez čerstvého
> ARM odmítá (`NOT_ARMED`) a ARM má krátkou TTL (aktuálně 12 s). STOP je master-off
> cesta receiveru. Stále otevřené pro dedikovaný safety pass: replay floor přes epoch
> rollback po rebootu, ACK/retry parita UIFlow STOP/FIRE, release klíče mimo zdroj a
> hardwarový interlock pro ostré výstupy.

### 11.1 Bezpečnostní jádro odpalu — dělat PRVNÍ (firmware-only, bench)
1. **`if(!_armed) return;` do Fire handleru** (`prop_rx.cpp:1232`) — první commit,
   bench za 10 min. *(jednohlasně označeno jako nejdůležitější)*
2. **Reálná ARM autorita:** samostatný `ARM` rámec v protokolu + TTL; **Preview
   nikdy nearmuje**; FIRE jen v čerstvém ARM.
3. **Bezpodmínečný latched STOP** s **bypassem** duty-bucketu i TX-fronty (dnes STOP
   nelatchuje a může dostat `ERR BUSY` při plné frontě → tiše se ztratí).
4. **Link-loss watchdog** (vyhodnotit `_modemLastSeenMs`) — blokuje **nový** odpal;
   už běžící efekt **dobíhá lokálně** (efekt může běžet až ~160 s / nekonečno).
5. **Boot-safe GPIO + watchdog**; žádný `ARMED` z NVS. Plus **event log**.
6. **Klíče/pairing povýšeny:** zrušit auto-pairing + statický klíč (kdokoli s
   firmwarem umí dnes generovat platné FIRE). **32-bit epocha demoted** (slabší riziko
   než chybějící ARM; reálný NVS wear je `lastSeq` per-výstřel, ne boot-counter).

### 11.2 Autentizace + spolehlivost a RF
- **Rádiový watchdog / auto-recovery** (ověřeno: `radioReady=false` = trvalá smrt rádia).
- **Per-band diagnostika** (rx_lora/rx_espnow/dup/mac_fail) — „100 %" maskuje mrtvé
  pásmo *(část už v debug HUD → rozšířit, ne dělat od nuly)*.
- **Pre-flight READY** + aktivní notifikace ztráty spoje na Dialu (červená/haptika).
- **FIRE-mini rámec** (~½ airtime) → řeší známé omezení.
- **Deterministická volba ESP-NOW kanálu** (fixní v NVS, ne boot-sken) → řeší omezení.
- **Duty-cycle FIX:** `DUTY_BUCKET_CAP` je dnes 10× budget a `LORA_AIRTIME_MS_EST=20`
  je 2–4× pod realitou (~43/82 ms) → compliance je iluzorní, opravit.
- **Heartbeat jen ESP-NOW** (po LoRa = 8–17 % duty, 8× přes limit).
- ⚠️ **Adaptivní SF za běhu DEGRADOVÁNO** → jen „fixní profil před show" (přijímač na
  fixním SF7 by přepnutý TX neslyšel, ani povel k přepnutí). **CAD/LBT jen pro
  nekritické rámce** (CAD ≠ regulační LBT; @SF7/BW250 ~65 ms = moc pro FIRE).

### 11.3 HW bezpečnost + napájení (HW interlock POVÝŠEN — podmínka pyro)
- **HW interlock pro ostré výstupy** (energie nesmí jít jen přes ESP32 pin):
  relay/MOSFET enable, **fyzický klíč/arming plug, nezávislý E-stop, shunt/bleeder +
  no-energy default, continuity test**. *(Recenze 5/5: nepatří na chvost.)*
- **Dynamický LED proudový rozpočet** — *pozn.: `budgetedBrightness()` už existuje
  (220 mA) → ověřit/zobecnit.*
- **Bulk + decoupling caps**, **UVLO** + ADC, **fuel gauge** do HEALTH, oddělené větve,
  boot-safe LED linka, konektory/enclosure.
- **NOVĚ z recenze:** koexistence 868+2.4 GHz na jedné desce (desense/proud), teplotní
  drift TCXO (−10…+40 °C vs BW 250 kHz), ESD na WS2812 lince.

### 11.4 Architektura / testovatelnost *(BĚŽÍ PARALELNĚ se Sprintem A)*
- **Header-only `shared/core`** + **host unit testy** + **fuzzing parseru** + test, že
  STOP projde při plné TX frontě; golden vektory + regrese „ACK UNKNOWN".
- **Hazard/FMEA tabulka** (zaseklé GO, stuck UART, brownout loop, špatný cíl, záměna
  přijímače, vymazaná NVS, FW rollback, rušení v ARMED).
- **Monorepo single-source-of-truth** + NVS schema versioning (řeší framework
  ping-pong i mrtvý `ReplayWindow`); **CI** (build ×3 + size-guard C6 + FW verze) + HIL.

### 11.5 Škálování / show-control *(de-scoped — až po stabilním jádru)*
- **Adresace `dest` + skupiny** (1:N) → řeší „jen 1:1".
- **HW „GO" tlačítko** se zero-state checkem → řeší „bez externího triggeru".
- **Cue-list** + PRELOAD/ARM/FIRE + **SIM mód** + prop-map (SIM/TEST/LIVE oddělení)
  → řeší „bez show/sekvencí".

### 11.6 Zamítnuto / odloženo (po recenzi)
- **AEAD šifrování — ZAMÍTNUTO** (důvěrnost LED-blikání irelevantní; +16 B tag na
  ~20 B FIRE-mini = 80 % overhead; pro odpal rozhoduje autentizace+klíče, ne šifra).
- **DMX512, WebUI/WiFi AP — ODLOŽENO** (WiFi na safety zařízení = riziko; konfig USB/SD).
- **Time-sync deferred-fire, COMET/SPARKLE → estetický/budoucí backlog.**
- **Certifikační hranice** = disclaimer (necertifikovaný prototyp; EU 2013/29, RED
  2014/53, IEC 61508), ne úkol.

> **Revidované pořadí sprintů:** A (zavřít díry v odpalu 11.1 + testy/FMEA 11.4) → B
> (autentizace+spolehlivost 11.2) → C (HW interlock+napájení 11.3, vč. range-testu a
> RF-blokovaného testu) → D (architektura/CI) → E (show-control 11.5). Detaily,
> code-grounded nálezy a log recenze v `IMPROVEMENT_ROADMAP.md`.
