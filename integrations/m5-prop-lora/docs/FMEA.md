# FMEA — analýza poruchových režimů odpalového řetězce (roadmapa 4.2)

Formální FMEA pro řetězec Dial (TX) → C6L modem → DinMeter (RX) → efekt.
Scénáře vycházejí ze seznamu odsouhlaseného sněmem (roadmapa 4.2) + z nálezů
Sprintu A. Sloupec **Mitigace** odkazuje na místo v kódu, které chování
vynucuje; sloupec **Zbytkové riziko** říká, co scénář stále dokáže, a na kterou
položku roadmapy se váže.

Závažnost (S): 1 = kosmetická … 5 = nechtěný odpal / neschopnost zastavit.
Hodnota v tabulce je **po** započtení současných mitigací.

| # | Scénář (porucha) | Následek bez mitigace | Současná mitigace (kód) | Zbytkové riziko / follow-up | S |
|---|---|---|---|---|---|
| 1 | Zaseknuté/držené GO tlačítko při bootu či brownout-recovery Dialu | Okamžitý FIRE po naběhnutí, pokud je přijímač ARMED | FIRE bez čerstvého ARM přijímač odmítne (`safety_logic.h` `FireAuthority::fireAllowed`); ARM TTL 12 s okno omezuje | **Zero-state check chybí** — v ARMED okně stuck button odpálí. Roadmapa 5.2: nezapnout ARMED, dokud tlačítko není ověřeně uvolněné | 4 |
| 2 | Ztráta rádiového spoje v ARMED (odchod z dosahu, vybitá baterie Dialu) | Přijímač zůstane trvale odjištěný | ARM-heartbeat á 5 s z Dialu, TTL 12 s na přijímači → SAFE ≤ 12 s; běžící efekt lokálně dobíhá (A2a, HW-ověřeno) | Okno až 12 s; přijatelné pro světelné efekty, pro ostré pyro zvážit kratší TTL / HW interlock (3.0) | 2 |
| 3 | Přehraný (replay) FIRE rámec — záznam a pozdější přeposlání | Opakovaný odpal bez povelu | Per-shot `armSeq` (`fireAllowedForFrame`: seq > armSeq), FIRE je one-shot (`onFireConsumed`), sliding replay-okno (`ReplayFilter`), HMAC autentizace rámce | Uzavřeno pro daný klíč; sdílený statický klíč viz ř. 10 | 1 |
| 4 | STOP se ztratí — plná TX fronta modemu / duty-cycle škrcení | Nouzové zastavení nedoručeno | STOP bypass v modemu: priority-insert + evikce nejstaršího, vždy LoRa i ESP-NOW, nikdy duty-skip (A2b, HW-ověřeno) | Jediný zbylý kanál ztráty je čisté rušení éteru (ř. 11) | 2 |
| 5 | Zpožděný/zatoulaný FIRE dorazí až po STOP | Odpal po nouzovém zastavení | STOP latchuje lockout + sekvenční plot `lockoutSeq`; ARM se seq ≤ plotu jej nezruší (`onStopFrame`, `onArmFrame`) | Uzavřeno; kryto host testy (`test_safety_logic.cpp`) | 1 |
| 6 | Preview/konfigurační rámec „odjistí" přijímač | Náhled efektu otevře cestu k odpalu | Preview NIKDY nearmuje — ARM jen samostatným rámcem typu 9 (Sprint A 0.1, HW-ověřeno) | Uzavřeno | 1 |
| 7 | Brownout/reboot smyčka přijímače | Přijímač nabíhá v neznámém stavu | ARM se NEpersistuje (NVS drží jen paletu/efekt config) → boot vždy SAFE; fail-safe `esp_restart()` vrací do KLID (`prop_rx.cpp:3201`) | HW watchdog + boot-safe GPIO13 (roadmapa 0.4) stále otevřené — výstupní pin při bootu musí být garantovaně idle | 3 |
| 8 | Vymazaná NVS / přeflashovaný Dial | Přijímač trvale odmítá „starý" čítač → mrtvý ovladač, nebo naopak replay | Per-boot NÁHODNÁ 32bit epocha, `!=` sémantika (žádné monotónní pořadí → nelze zacihlit), reset replay-okna na novou epochu (`epochIsNewSession`, `ReplayFilter::resetForNewSession`) | Uzavřeno (0.5, HW-ověřeno: dvě epochy napříč rebooty) | 1 |
| 9 | FW rollback / smíšený fleet (v1 + v2 protokol) | Tichá misinterpretace rámců | Verze v hlavičce: v2 přijímač v1 rámce **dropne** (`prop_protocol.h:198`) — selže bezpečně, ne tiše | Vyžaduje koordinovaný flash všech 4 zařízení; `FW_VERSION` v telemetrii (4.3) zatím chybí | 2 |
| 10 | Záměna přijímače / špatný cíl (dva propy na place) | Odpal jiného propu, než operátor vidí | Route gate: key id + source + destination musí sedět (`routeValid`); 1:1 adresace | **Sdílený statický HMAC klíč ve všech binárkách** — kdokoli s firmwarem umí platný FIRE. Sprint B 1.1 (pairing, per-show klíč) je hlavní otevřená položka. Prop-map/rozblikání (5.3) proti lidské záměně | 4 |
| 11 | Rušení/jamming pásma v ARMED | Nelze doručit STOP ani heartbeat | Dual-band (LoRa + ESP-NOW) pro STOP i heartbeat; výpadek heartbeatu → SAFE ≤ 12 s; běžící efekt dobíhá lokálně (krátký, ohraničený) | Jamming = nedoručitelný STOP během dobíhajícího efektu; efekty musí být časově ohraničené; pro pyro HW interlock (3.0) | 3 |
| 12 | Zaseknutý UART / boot-garbage mezi Dialem a modemem | Zkorumpovaný první povel po bootu (historicky: `ERR BAD_COMMAND` → tiché odjištění) | Dial flushuje line-buffer modemu v `_uart_init`; modem flushuje Serial1 RX při bootu (bonus fix A2a/A2b, HW-ověřeno) | Stuck UART uprostřed show detekuje až radio-watchdog (Sprint B 1.2); do té doby kryje ARM TTL | 2 |

## Poznámky k metodě

- **Ověřitelnost:** řádky 2–6, 8, 12 jsou kryté host testy
  (`firmware/tests/test_safety_logic.cpp`, `tests/test_protocol*.py`,
  `tests/test_sim_link_safety.py`) a HW testy Sprintu A zaznamenanými
  v `IMPROVEMENT_ROADMAP.md` (sekce STAV IMPLEMENTACE).
- **Hlavní otevřená rizika** (S ≥ 3): ř. 1 (zero-state check GO), ř. 7
  (HW watchdog + boot-safe GPIO), ř. 10 (klíče/pairing), ř. 11 (jamming —
  řešitelné jen ohraničením efektů + HW interlockem).
- Tabulku aktualizovat při každé změně protokolu nebo stavového stroje
  odpalu; nový řádek = nový host test, kde to jde.
