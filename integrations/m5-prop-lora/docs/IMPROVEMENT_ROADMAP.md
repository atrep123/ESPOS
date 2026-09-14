# M5 Prop LoRa Controller — Roadmapa vylepšení (v2, po recenzi sněmu)

> **v2** = původní syntéza ~18 model-běhů **+ druhé kolo: 5 nezávislých recenzentů**
> (Codex/gpt-5.5, Gemini, Copilot-Sonnet-4.6, Copilot-GPT-5.5, Opus) roadmapu
> kriticky přečetlo a **4 z 5 ověřily tvrzení přímo proti firmwaru**. Tato verze
> zapracovává jejich nálezy — včetně oprav faktických chyb a přeřazení priorit.
>
> U každého bodu: **Co · Proč · Náročnost · Riziko**. „Shoda" už **není** hlavní
> metrika (viz proč níže). Kontext systému: `M5_PROP_CONTROLLER.md`.

---

## STAV IMPLEMENTACE

- **Sprint A / A1 — HOTOVO + HW-OVĚŘENO (2026-05-24):** receiver-side ARM autorita
  (`Arm` rámec typ 9), Preview už NEARMUJE, FIRE bez ARM odmítnut, STOP latchuje,
  ARM TTL 30 s. Build din-rx+dial-tx OK, protokol-testy 51/51. **HW test (alternující
  self-test, dekódované ACK z přijímače na COM7): armed FIRE → `FIRE`, unarmed FIRE →
  `NOT_ARMED`, dokonalá alternace na 8 výstřelech.** Gate prokazatelně blokuje
  neodjištěný odpal na reálném železe.
- **Sprint A / A2a — HOTOVO + HW-OVĚŘENO (2026-05-24):** link-loss watchdog —
  Dial posílá ARM-heartbeat á 5 s (dual-band, 1 kopie, ~0.86 % LoRa duty), přijímač
  TTL 12 s se obnovuje; ztráta heartbeatu → SAFE ≤12 s; **běžící efekt dobíhá**
  (nezávisí na `_armed`). **HW test (COM8): ARM frames á ~5 s, sustained past 12 s
  TTL** → přijímač zůstává armed dokud link žije.
- **Bonus fix (objeveno při A2a testu):** boot-garbage na UART k modemu se hromadil
  v jeho line-bufferu a korumpoval PRVNÍ příkaz po bootu (`ERR BAD_COMMAND` → Dial
  se odjistil). Opraveno: Dial flushuje modem line-buffer (`\n`) v `_uart_init`.
  Zlepšuje spolehlivost prvního ARM/FIRE po bootu pro **celý** systém.
- **Sprint A / A2b — HOTOVO + HW-OVĚŘENO (2026-05-24):** STOP bypass v modemu —
  STOP nikdy nedostane `ERR BUSY` (priority insert + evikce nejstaršího při plné
  frontě) a nikdy není duty-skipnutý (vždy LoRa i ESP-NOW). Modem-side flush Serial1
  RX při bootu. Build modemu (framework ping-pong) OK, oba modemy flashnuté
  (COM7/COM8). **HW test (COM7): STOP ack od přijímače, arm+fire dál relayuje, první
  reálný příkaz po bootu čistý.**
- **Sprint A / 0.5 — 32-bit epocha HOTOVO + HW-OVĚŘENO (2026-05-24):** sněm
  (Codex impl + Opus + Gemini review) → oba revieweři „neflashovat as-is". Zvoleno
  **Option A: per-boot RANDOM 32-bit epocha** (horních 32 b nonce), `!=` sémantika
  (žádný monotónní čítač → žádné riziko zacihlení), **per-shot lastSeq** (revert
  high-water — replay-safe), **protokol v1→v2** (koordinovaný flash 4 zařízení; starý
  v1 fleet selže bezpečně = dropnut, ne tiše). **HW test (COM8): dva různé epochy
  napříč rebooty (0x02734af3 → 0x115df824), v2 na všech rámcích+ACK, FIRE potvrzen
  v obou bootech** → 1/256 kolize odstraněna (~1/4 mld). Build+flash všech 4 OK.
- **Sprint A / 4.x — host testy + FMEA HOTOVO (2026-08-06, sw část):**
  multiplatformní runner `tools/run_host_tests.py` (Linux/Windows; PS1 zůstává
  jako Windows wrapper), host C++ testy safety_logic/palette/led_payload **nově
  v CI** (job Firmware), deterministický **fuzz parseru rámců**
  (`tests/test_protocol_fuzz.py`: 5000 náhodných blobů + mutace každého bytu +
  trunkace — nic nesmí projít MAC gatem) a python safety subset (protocol +
  roundtrip + link sim) **nově v CI** (job Python). **12-řádková FMEA:**
  `docs/FMEA.md` — otevřená rizika S≥3: zero-state check GO (5.2), HW watchdog +
  boot-safe GPIO (0.4), klíče/pairing (Sprint B 1.1). Retire
  `test_project_sources.py` zatím neprovedeno (rozhodnutí vlastníka).
- **Zbývá ze Sprintu A:** HW watchdog + boot-safe GPIO (0.4 — návrh sněmu hotový:
  GPIO13 idle-high root-fix first, pak Task WDT 4-5s; vyžaduje board-level práci).
- **Pozn. build stav:** framework `framework-arduinoespressif32` je teď v
  **pioarduino** verzi (modem-buildable). Rebuild din-rx vyžaduje swap zpět na
  official (smazat + refetch) — viz build gotchas. Aktuální din-rx binárka (A2,
  12 s TTL) je nasazená, takže žádná akce není nutná teď.

---

## 0. HISTORICKÝ STAV PO RECENZI — Sprint A už hlavní ARM gate zavřel

Historický sněm při čtení kódu (`prop_rx.cpp`, `c6l-modem/main.cpp`,
`app_prop_tx.cpp`) **jednomyslně (5/5) potvrdil, že ARM gate tehdy nebyl
vynucený v kódu**. Sprint A tento hlavní nález zavřel: receiver má samostatný
ARM rámec, FIRE bez čerstvého ARM vrací `NOT_ARMED` a ARM TTL je aktuálně 12 s.
Níže zůstává původní evidence kvůli auditní stopě:

- **`prop_rx.cpp:1246` — `startFire()` se volá BEZPODMÍNEČNĚ** po každém platném
  Fire rámci. **Žádná kontrola `_armed`.** → přehraný/přeposlaný/cizí (se znalostí
  klíče) Fire rámec odpálí okamžitě.
- **`prop_rx.cpp:1226` — `_armed = true` nastaví KTERÝKOLI Preview rámec.** Náhled
  (config/test povel) tedy „odjišťuje". `_armed` se navíc používá jen pro UI
  (barva/label), ne jako brána FIRE.
- **`prop_rx.cpp:1256` — STOP** jen nastaví `_armed=false` + `stopOutput()` —
  **nic nelatchuje** (`ABORT_LATCHED` neexistuje).
- **`_modemLastSeenMs` se nastaví, ale nikde nevyhodnocuje** — **link-loss watchdog
  neexistuje**, fail-safe při ztrátě spoje fakticky chybí.
- **STOP může tiše zmizet:** TX fronta modemu `TX_QUEUE_DEPTH=4`; při zaplnění
  vrací `ERR BUSY` a STOP se ztratí. Nouzové zastavení je tak single-point-of-failure.
- **Duty-cycle compliance je iluzorní:** `DUTY_BUCKET_CAP_MS=36000` = **10×**
  hodinový budget (3600 ms) → dovolí nárazově ~1800 LoRa rámců, než začne škrtit;
  navíc `LORA_AIRTIME_MS_EST=20 ms` je **2–4× pod realitou** (skutečně ~43 ms pro
  ~45 B FIRE, ~82 ms pro 96 B rámec). Reálné překročení EU868 1 % limitu může být
  řádové.
- **Sdílený statický HMAC klíč** je identický ve všech 3 binárkách a modem se
  ESP-NOW peer **učí jen z hlavičky bez HMAC validace** → kdokoli s firmwarem umí
  generovat platné FIRE.

⇒ **Tvrzení „bezpečnost je kritická a HW-ověřená" platí pro KOMUNIKACI, ne pro
LOGIKU ODPALU.** První commit roadmapy musí tyto díry zavřít, ne přidávat funkce.

---

## TL;DR — revidované pořadí (po recenzi)

1. **`if (!_armed) return;` do Fire handleru** (`prop_rx.cpp:1232`) — **HNED, první
   commit.** Testovatelné na bench za 10 min, nulový jiný dopad. *(jednohlasně
   označeno jako nejdůležitější bod)*
2. **Reálná ARM autorita:** samostatný `ARM` rámec/typ v protokolu + TTL okno;
   Preview **nikdy** nearmuje; FIRE jen v čerstvém ARM.
3. **Bezpodmínečný latched STOP** s **bypassem** duty-bucketu i TX-fronty (STOP se
   nikdy nesmí ztratit ani být duty-limitován).
4. **Link-loss watchdog** (vyhodnotit `_modemLastSeenMs`) — blokuje **nový** ARM/FIRE
   při ztrátě spoje; už běžící efekt **dobíhá lokálně** (viz 0.3).
5. **Boot-safe GPIO + watchdog**; žádný `ARMED` z NVS.
6. **Klíče/pairing** (povýšeno z „security depth"): zrušit auto-pairing, per-show
   klíč, validace peer přes HMAC.

Vrstvy 0 a 1A jsou **firmware-only**, ověřitelné na COM6–9. HW interlock (3.0) běží
paralelně, je-li cílem ostré pyro.

---

## Vrstva 0 — Bezpečnostní jádro odpalu (PŘEŘAZENO po recenzi)

### 0.1 Reálná ARM/FIRE autorita na přijímači — *nejdřív minimální gate, pak plný stav*
- **Co:** (a) **Okamžitě:** `if(!_armed) return;` ve Fire handleru. (b) **Pak:**
  zavést samostatný **`ARM` typ rámce** v `prop_protocol.h`, stav `SAFE/ARMED/FIRE/
  LOCKOUT` na DinMeteru, ARM s TTL (10–30 s), po vypršení/FIRE/STOP/link-loss návrat
  do `SAFE`. **Preview NESMÍ armovat** (oddělit od `_armed`). Dial UI přestává být
  bezpečnostní hranicí.
- **Proč:** Dnes (ověřeno) přijímač odpálí na jakýkoli platný Fire rámec; Preview
  navíc armuje. Toto je největší reálná díra celého systému.
- **Náročnost:** (a) triviální / (b) nízká–střední. **Riziko:** krátké TTL může
  překážet → konfigurovatelné. Změna protokolu (nový typ) = koordinovaný flash.

### 0.2 Bezpodmínečný latched STOP s bypassem fronty i duty
- **Co:** STOP po obou pásmech, vysoká priorita, **mimo dedup okno** (vlastní
  seq/nonce politika, aby ho dedup nepotlačil), **obchází leaky-bucket i TX-frontu**
  (dedikovaný slot, nikdy `ERR BUSY`). Na přijímači okamžitě zhasne výstup, zruší
  ARM a zůstane `ABORT_LATCHED` do lokálního resetu.
- **Proč:** Nouzové zastavení nesmí být obyčejný paket; dnes (ověřeno) STOP
  nelatchuje a může dostat `ERR BUSY` při plné frontě nebo být duty-skipnut.
- **Náročnost:** nízká–střední. **Riziko:** falešný STOP zastaví show (přijatelnější
  než falešný FIRE). „Mimo dedup" musí být přesně navrženo (recenze: dnes dedup běží
  PŘED kontrolou typu rámce).

### 0.3 Link-loss watchdog — s rozlišením „dobíhající efekt" vs „nový odpal"
- **Co:** Vyhodnocovat `_modemLastSeenMs` (+ heartbeat z Dialu, **jen ESP-NOW**, viz
  1.4 pozn.). Při ztrátě platného spoje >1–2 s: zablokovat **nový** ARM/FIRE a
  pre-trigger glow. **Už spuštěný efekt dobíhá lokálně do svého konce** bez ohledu na
  link (efekt může běžet až ~160 s, `repeat==0` = nekonečno → tvrdý disarm by uťal
  legitimní efekt). Po bootu vždy `SAFE`, LED zhasnuté.
- **Proč:** Rušička / vypnutý vysílač nesmí nechat systém schopný nového odpalu, ale
  nesmí ani uťat běžící legitimní efekt.
- **Náročnost:** nízká. **Riziko:** prahy laditelné; rozlišení „doběh vs nový FIRE"
  je klíčové (recenze to v původní v1 chybělo).

### 0.4 Boot-safe GPIO + watchdog
- **Co:** Řídicí/datové GPIO LED do `LOW` co nejdřív v bootu, **před** aplikací. HW/
  Task WDT na všech 3 MCU (~500 ms, krmit i při blokujícím LoRa TX/NVS zápisu).
  Brownout reset zapnutý. **Nikdy** neobnovovat `ARMED` z NVS.
- **Proč:** Reset/zámrz uprostřed show musí skončit vypnutím, ne uvíznutím výstupu.
- **Náročnost:** nízká. **Riziko:** odhalí latentní napájecí problém.

### 0.5 32-bit epocha — *DEMOTED + skutečná oprava NVS wear*
- **Co:** Rozšířit anti-replay epochu (dnes 8-bit v horním bajtu nonce) na 32-bit
  boot/session counter ve **vlastním poli** rámce. **Důležitější:** opravit reálný
  NVS wear — `rememberAcceptedSequence()` (`prop_rx.cpp:1131`) volá
  `putUInt("lastSeq")` **při každém přijatém výstřelu** (desítky–stovky zápisů/show);
  TX ukládá `seq` při každém odeslání. → dávkování / high-water rezervace /
  double-slot CRC. Boot-counter sám (1×/boot, wear-leveled NVS) wear neřeší.
- **Proč:** 1/256 epoch kolize je reálná, ale **slabší riziko** než chybějící ARM
  gate. Recenze: sněm původně přecenil elegantní krypto detail a podcenil díru ve
  fyzické logice odpalu i provozní NVS wear.
- **Náročnost:** nízká (counter) / střední (wear politika). **Riziko:** nové pole
  nonce = breaking change protokolu (offsety parseru ve 3 firmwarech) → koordinovaný flash.

### 0.6 Bezpečnostní event log (ring buffer)
- **Co:** RAM ring + kritické do NVS: ARM/FIRE/STOP, seq, nonce, band, dedup/drop
  důvod, reset reason, brownout, heap-low, queue overflow, pairing změna. Export přes USB.
- **Proč:** Po incidentu musí být jasné, co systém přijal a proč jednal.
- **Náročnost:** nízká–střední. **Riziko:** NVS wear → detail v RAM, jen kritické persistovat.

---

## Vrstva 1 — Autentizace, klíče, spolehlivost (klíče POVÝŠENY)

### 1.1 Klíčový management + zrušení auto-pairingu *(povýšeno z původní 4.1)*
- **Co:** Zrušit defaultní sdílený klíč. Režim **„Pairing"** (hold enkodéru / USB-C)
  → MAC + per-show klíč trvale do NVS; **konec učení peer z libovolného rámce bez
  HMAC**. Volitelně role (`operator-fire`/`technician-config`/`stop-only`). Validovat
  ESP-NOW peer přes HMAC, ne jen hlavičku.
- **Proč:** Dnes (ověřeno) statický klíč ve všech binárkách + auto-pairing = kdokoli
  s firmwarem odpálí. To je **strukturální zranitelnost, ne „hloubka"**.
- **Náročnost:** střední. **Riziko:** ztráta klíče → recovery proces.

### 1.2 Rádiový watchdog / auto-recovery (SX1262 + ESP-NOW)
- **Co:** Stav `OK/Degraded/Resetting/Cooldown`; health-check čte registr SX1262 přes
  SPI + stav ESP-NOW fronty; izolovaný reset periferie bez rebootu.
- **Proč:** **Ověřeno:** `radioReady=false` je dnes prakticky trvalá smrt rádia
  (`enterReceive()`). C6 unicore (WiFi + LoRa IRQ) → reálné riziko tichého záseku.
- **Náročnost:** střední–vyšší. **Riziko:** špatné prahy → falešné resety.

### 1.3 Per-band diagnostika *(ověřit/rozšířit — částečně hotovo)*
- **Co:** HEALTH/ACK počitadla `rx_lora/rx_espnow/dup_lora/dup_espnow/foreign/
  mac_fail/dedup_drop/uart_drop` + UART overflow + free/min heap. Povýšit z debug HUD
  na provozní HEALTH kontrakt (verzované schema).
- **Proč:** „100 % doručeno" maskuje mrtvé pásmo. *(Pozn.: část je už v debug HUD —
  jde o rozšíření, ne implementaci od nuly.)*
- **Náročnost:** nízká–střední. **Riziko:** velikost rámců.

### 1.4 Pre-flight READY + boot self-check
- **Co:** Dial povolí ARM až po čerstvém `READY` z přijímače (peer OK, configVersion,
  RSSI/SNR obou pásem, duty rezerva, napájení) + boot self-check (UART modem, pairing,
  LoRa init, keyId, LED test 1 px, heap). **+ Aktivní notifikace ztráty spoje na Dialu**
  (výrazná červená/haptika při auto-disarmu), ne až marným FIRE.
- **Proč:** Operátor nesmí zjistit problém až při FIRE.
- **Náročnost:** střední. **Riziko:** self-check nesmí spustit efekt; UI nepřeplnit.
- **Pozn. (heartbeat):** Periodický heartbeat (0.3) **musí jet výhradně ESP-NOW** —
  Dial dnes žádný periodický rámec neposílá, a po LoRa by 2–4 pingy/s = 8–17 % duty
  (8× přes EU868 1 %).

### 1.5 FIRE-mini rámec
- **Co:** Kompaktní autentizovaný FIRE: `effectId/cueId + configVersion + seq + nonce
  + MAC` (~20 B). Plná konfigurace předem (PaletteSet/PRELOAD). Verzovaný typ.
- **Proč:** ~½ airtime → menší duty tlak, menší kolizní okno, nižší latence.
- **Náročnost:** střední. **Riziko:** offsety parseru; nesmí oslabit anti-replay.
  **Nekombinovat s AEAD** (viz 1.7).

### 1.6 Deterministická volba ESP-NOW kanálu (NE boot-sken)
- **Co:** Kanál **fixní v NVS** (menu 1–13); sken jen při explicitní factory-reset
  sekvenci. Neměnit za běhu.
- **Proč:** Kanál 1 bývá nejzarušenější; únik na prázdný kanál zvedne 2.4 GHz vrstvu.
  LoRa zůstává záchrana. *(Řeší odložené „kanálová agilita" bezpečně.)*
- **Náročnost:** nízká. **Riziko:** nízké.

### 1.7 Anténa, umístění, link-budget *(jako MĚŘENÍ, ne feature)* + duty-cycle FIX
- **Co:** (a) Externí 868 antény, C6 mimo kov, přijímač výš, krátký koax; **změřit**
  link-budget tabulku a reálný airtime. (b) **Opravit duty-bucket:** `DUTY_BUCKET_CAP`
  na realistickou hodnotu a `LORA_AIRTIME_MS_EST` na měřený airtime (~43/~82 ms);
  STOP/FIRE mimo backoff.
- **Proč:** Největší RF zisk z umístění; současná duty compliance je iluzorní.
- **Náročnost:** nízká. **Riziko:** ERP u ziskové antény.

> **Degradováno / přeformulováno po recenzi (původní v1 body):**
> - **Adaptivní SF za běhu → JEN „fixní profil zvolený před show".** Přijímač
>   poslouchá na fixním SF7; když TX přepne na SF9, přijímač **neslyší nic**, ani
>   povel k přepnutí. Runtime adaptace = rozbití linku.
> - **CAD/LBT → jen pro NEKRITICKÉ rámce (Health/ACK).** CAD detekuje LoRa preambuli
>   kompatibilního profilu, **ne** obecné rušení, a **není** regulační LBT;
>   „částečná EU868 compliance" je zavádějící. Pro FIRE/STOP žádný backoff
>   (CAD@SF7/BW250 ~65 ms = neakceptovatelná latence).
> - **AEAD šifrování → VYŠKRTNUTO** (přesunuto do „zamítnuto", viz níže).

---

## Vrstva 2 — *(zrušena jako samostatná „security depth")*

Klíče/pairing povýšeny do 1.1. **AEAD a RF_DEGRADED-bez-prahů** přesunuty do
„Zamítnuto / odloženo".

---

## Vrstva 3 — HW bezpečnost a napájení (HW interlock POVÝŠEN)

### 3.0 HW interlock pro ostré výstupy *(povýšeno z původní 6.2 — podmínka pyro)*
- **Co:** K ostrému odpalovacímu stupni **nepouštět energii jen přes ESP32 pin** — HW
  safety relay/MOSFET enable, **fyzický klíč/arming plug na přijímači, nezávislý
  E-stop okruh, shunt/bleeder + no-energy default, continuity test bezpečným proudem**.
  Volitelně dead-man vstup blokující výstup bez ohledu na RF.
- **Proč:** SW crash, brownout ani GPIO glitch nesmí aktivovat ostrý výstup — žádný
  FW fail-safe to nezajistí (proražený FET). **Recenze 5/5: nepatří na chvost, je to
  podmínka před jakýmkoli ostrým pyro.**
- **Náročnost:** střední–vysoká. **Riziko:** nutný HW návrh + test.

### 3.1 Dynamický LED proudový rozpočet *(ověřit/rozšířit — částečně hotovo)*
- **Co:** Per-snímek omezit jas dle odběru (`~60 mA × N`). **Pozn.: `budgetedBrightness()`
  v `prop_rx.cpp` už existuje (220 mA) — jde o ověření/zobecnění (konfig. limit dle
  baterie, škálovat s `_activeLeds`), ne implementaci od nuly.**
- **Náročnost:** nízká. **Riziko:** velmi nízké.

### 3.2 Napájecí hardening + RF koexistence + prostředí *(část NOVĚ z recenze)*
- **Co:** Bulk (~1000 µF low-ESR) + decoupling (10–100 µF u C6); UVLO fail-safe +
  ADC napětí; fuel gauge (MAX1704x) do HEALTH; oddělené větve LED/logika; boot-safe
  LED linka (pull-down + sériový R + level shift); zamykatelné konektory + enclosure.
  **NOVĚ:** (a) **měřit koexistenci 868 + 2.4 GHz na jedné C6 desce** — zda ESP-NOW TX
  neshazuje probíhající LoRa RX (desense + proudové špičky). (b) **Teplotní drift TCXO
  SX1262** (venku −10…+40 °C vs BW 250 kHz — drift může vypadnout z pásma).
  (c) **ESD ochrana** WS2812 datové linky / dlouhých vodičů.
- **Proč:** RF už ověřeno; další zdroje selhání jsou napájení, koexistence, teplota, ESD.
- **Náročnost:** nízká (caps/linka) – vysoká (enclosure). **Riziko:** nízké.

---

## Vrstva 4 — Architektura a test *(BĚŽÍ PARALELNĚ s Vrstvou 0, ne po HW)*

### 4.1 Header-only `shared/core` + host unit testy + **fuzzing parseru**
- **Co:** Vytáhnout `classifyReplay`, `waveformLevel`, HSV, duty bucket, frame codec
  do header-only modulů bez Arduino/ESP-IDF. Host testy (Catch2/GTest). **NOVĚ:
  fuzzing parseru rámců** + test, že **STOP projde při zaplněné TX frontě**.
- **Proč:** Nejrizikovější logiku (vč. nové ARM mašiny) testovat na PC za sekundy.
  Recenze: testy patří PŘED/SOUBĚŽNĚ s bezpečnostním sprintem, ne až po pájení.
- **Náročnost:** nízká–střední. **Riziko:** nízké.

### 4.2 Golden vektory + regrese „ACK UNKNOWN" + **hazard/FMEA tabulka**
- **Co:** Uložené vzorové rámce (encode/decode + odmítnutí poškozených); parser test
  staré UART smyčky. **NOVĚ: formální FMEA** — zaseknuté/držené GO tlačítko při
  boot/brownout (zero-state check!), stuck UART, brownout loop, špatný cíl, záměna
  přijímače, vymazaná NVS, FW rollback, rušení v ARMED.
- **Proč:** Chrání draze nalezené chyby; FMEA odhalí díry, které ad-hoc návrh mine.
- **Náročnost:** nízká–střední. **Riziko:** nízké.

### 4.3 Monorepo single-source-of-truth + NVS schema + CI + HIL
- **Co:** `shared/protocol`+`shared/core` do CMake i `lib_extra_dirs`; izolovat PIO
  core dir (vyřešit `framework-arduinoespressif32` ping-pong). NVS schema versioning +
  CRC + migrace (host test). CI: build ×3 + host testy + **size-guard C6** (89 % flash)
  + git SHA/dirty → `FW_VERSION` v telemetrii. Lokální HIL smoke přes COM6–9.
- **Proč:** Drift definic mezi ESP-IDF/Arduino; u pyro znát přesný kód na každém kusu.
  *(Řeší framework ping-pong + mrtvý `ReplayWindow`, viz dole.)*
- **Náročnost:** střední. **Riziko:** přemapování include cest.

---

## Vrstva 5 — Show-control *(DE-SCOPED — až po stabilním bezpečnostním jádru)*

### 5.1 Adresace `dest` + skupiny (1:N)
- **Co:** Trvalé `propId` + bitmask skupin; `dest` důsledně (broadcast/skupina/unicast);
  per-receiver `lastSeq`. *(Řeší „jen 1:1".)*
- **Náročnost:** střední. **Riziko:** chyba adresace u pyro kritická → čitelné UI cíle.

### 5.2 HW „GO" tlačítko / nožní spínač *(se zero-state checkem)*
- **Co:** Fyzický vstup (debounce, izolace) → Fire/posun cue. **Nezapnout ARMED,
  pokud tlačítko není ověřeně uvolněné** (zaseklé/držené při boot/brownout recovery).
- **Náročnost:** velmi nízká. **Riziko:** nízké. *(Řeší „bez externího triggeru".)*

### 5.3 Cue-list sekvencer + PRELOAD/ARM/FIRE + SIM mód + prop-map
- **Co:** Show = seznam cue (target/efekt/trigger); efekty předem nahrané, pak jen
  krátký `ARM cueId`+`FIRE cueId`. **SIM mód:** přehraje cue-list, posílá jen Preview,
  nikdy Fire. **Prop-map:** ping/rozblikání + jméno/skupina (proti záměně). **Jasné
  oddělení SIM/TEST/LIVE.**
- **Proč:** Profi nástroj, menší airtime, opakovatelnost, bezpečné zkoušky.
- **Náročnost:** střední. **Riziko:** ochrana proti odpalu neaktuálního cue; ARM TTL.
  *(Řeší „bez show/sekvencí".)*

> **Odsunuto do estetického/budoucího backlogu (recenze: scope creep mimo
> bezpečnost):** prostorové efekty COMET/SPARKLE; time-sync „deferred fire" (zbytečně
> složité pro 1:1 LED fázi).

---

## Zamítnuto / odloženo (po recenzi)

- **AEAD šifrování (původní 4.2) — ZAMÍTNUTO.** Důvěrnost cue dat je irelevantní (jde
  o blikání LED). GCM/Poly1305 tag (16 B) by na ~20 B FIRE-mini byl ~80 % overhead a
  zkrácení tagu kvůli airtime oslabuje autenticitu pod bezpečný práh. Pro odpal je
  rozhodující autentizace + klíče + role + stavová mašina (1.1, 0.1), ne šifra.
- **DMX512 ingest, WebUI/WiFi AP (původní 5.5/5.6) — ODLOŽENO/MIMO.** WiFi AP +
  HTTP server na safety-critical zařízení = RAM tlak + riziko záseku jádra. Konfig
  přes USB/SD. DMX až po bezpečnostním jádru a 1:N.
- **„Certifikační hranice" jako samostatný bod (původní 6.1) — PŘESUNUTO do hlavičky
  dokumentu** (je to disclaimer/memo, ne úkol): tento řetězec je **necertifikovaný
  řídicí prototyp**; pro ostré pyro řešit EU 2013/29/EU, RED 2014/53/EU, IEC 61508 a
  oddělenou certifikovatelnou odpalovací část (3.0).
- **RF_DEGRADED bez konkrétních prahů, role bez provisioning procesu** — vágní;
  rozpracovat až s daty (1.7 měření).

---

## Proč „mapa shody" (počet hlasů) NENÍ metrika jistoty

Recenze (Opus, Codex) upozornila: všech ~18 model-běhů sdílí trénovací korpus a
dostalo stejný kontext → **hlasují korelovaně** na to, co je v embedded literatuře
*populární* (stavová mašina, watchdog), ne na to, co je pro **tenhle** řetězec
nejnebezpečnější. Důkaz: HW interlock a UVLO dostaly v původní v1 méně „hvězd" než
„adresace dest", přestože interlock je poslední fyzická pojistka u pyro. ⇒ Počet
hlasů používat **jen pro řazení v rámci stejné rizikové třídy, nikdy napříč**.
**Skutečnou jistotu dává code-grounded ověření** — proto v0 sekce cituje řádky kódu.

---

## Revidované sekvenování (sprinty)

- **Sprint A — Zavřít díry v odpalu (firmware, dny):** 0.1a (`if(!_armed)`) → 0.1b
  (ARM rámec+TTL, Preview nearmuje) → 0.2 (latched STOP+bypass) → 0.3 (link-loss
  watchdog) → 0.4 (boot-safe+WDT). **Souběžně 4.1/4.2** (host testy + FMEA).
- **Sprint B — Autentizace + spolehlivost:** 1.1 (pairing/klíče) → 1.2 (radio
  watchdog) → 1.7b (duty FIX) → 1.3 (per-band diag) → 1.4 (READY) → 1.6 (fixní kanál)
  → 1.5 (FIRE-mini) → 0.5 (epocha + NVS wear).
- **Sprint C — HW (před prvním ostrým/bateriovým nasazením):** 3.0 (interlock/E-stop)
  → 3.1 (LED budget ověřit) → 3.2 (caps/UVLO/telemetrie/koexistence/TCXO/ESD). Sem
  reálný range-test a **test v RF-blokovaném prostředí** (atenuátor/klec).
- **Sprint D — Architektura/CI:** 4.3 (monorepo/CI/HIL/NVS schema).
- **Sprint E — Show-control:** 5.1 → 5.2 → 5.3.

---

## Konsolidovaný seznam chybějících rizik (z recenze)

1. Chybějící ARM gate ve Fire handleru *(0.1)* — **#1**.
2. STOP `ERR BUSY` při plné TX frontě / duty-skip *(0.2)*.
3. Link-loss watchdog neexistuje *(0.3)*.
4. Duty cap 10× + airtime estimate 2–4× nízko *(1.7b)*.
5. Statický sdílený klíč + auto-pairing bez HMAC *(1.1)*.
6. 868 + 2.4 GHz koexistence na jedné desce *(3.2a)*.
7. Teplotní drift TCXO vs úzké BW *(3.2b)*.
8. ESD na WS2812 lince *(3.2c)*.
9. Zero-state check zaseklého GO tlačítka *(4.2 / 5.2)*.
10. NVS wear `lastSeq` per-výstřel *(0.5)*.
11. Chybí fuzzing parseru + RF-blokovaný test *(4.1 / Sprint C)*.
12. Preview/config/arm/fire nejsou čistě oddělené *(0.1)*.

---

## Vyřešený flag (mrtvý kód)

`struct ReplayWindow` v `prop_protocol.h:45` (`classify()` jen nad `lastSequence`) je
**mrtvý kód — nikde se nevolá** (ověřeno grepem). Reálná deduplikace běží v
`prop_rx.cpp` přes `_rxWindowBase`/`_rxWindowMask` (skutečné 32-bit okno). Funkční
dopad = žádný, ale je to zavádějící paralelní implementace → cleanup s 4.1/4.3
(single source of truth). Změna hlavičky = koordinovaný flash → naplánovat.

---

## Log recenze sněmu (kdo co přinesl)

- **Opus** (code-grounded): chybějící ARM gate + Preview-armuje + STOP nelatchuje +
  link-loss watchdog neexistuje (řádky); duty cap 10×; STOP `ERR BUSY` SPOF; adaptivní
  SF rozbité; NVS wear `lastSeq`; `budgetedBrightness` už existuje; koexistence/TCXO/
  ESD/fuzzing; „mapa shody" je nápadnost, ne jistota.
- **Copilot-GPT-5.5** (code-grounded): protokol nemá ARM typ; Preview nastavuje
  `_armed`; dedup běží před typem rámce (STOP); CAD ≠ regulační LBT; key mgmt je základ;
  chybí FMEA.
- **Copilot-Sonnet-4.6** (code-grounded): `LORA_AIRTIME_MS_EST=20` je 2–4× nízko
  (reálně ~43/82 ms); CAD@SF7/BW250 ~65 ms; `if(!_armed) return;` jako první commit;
  RF-blokovaný test; testy paralelně se Sprintem A.
- **Codex** (code-grounded): HW interlock + klíče výš; Preview nesmí armovat; CAD
  optimistické; NVS wear; AEAD přeceněné; část bodů už hotová → „ověřit/rozšířit";
  E-stop/shunt/continuity/SIM-TEST-LIVE.
- **Gemini** (text + ověření): heartbeat jen ESP-NOW (16 % duty po LoRa); AEAD vs
  FIRE-mini protiřečí; CAD/LBT jen telemetrie; HW interlock do Sprintu A; vyhodit
  WebUI; zero-state check; aktivní notifikace ztráty spoje na Dialu.
