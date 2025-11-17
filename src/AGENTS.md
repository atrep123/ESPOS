# ESP32OS – Agent Guide (C / firmware část)

Tento soubor platí pro všechny soubory v `src/` (firmware, služby, drivery).

## Struktura C kódu

- `src/main.c` – vstupní bod `app_main`, konfigurace, start služeb.
- `src/display/*` – drivery displeje (`ssd1363` atd.).
- `src/kernel/*` – `msgbus`, `timers`, základní OS vrstvička.
- `src/services/*` – logické služby:
  - `input` – čtení tlačítek / vstupu,
  - `rpc` – RPC zvenku,
  - `store` – persistovaná konfigurace,
  - `metrics` – metriky,
  - `ui` – UI stav, render.
- `src/ui_*.c` – demo / design / render helpery.

Při změnách se vždy podívej, zda už pro daný problém neexistuje služba nebo helper (např. neimplementuj vlastní bus, časovače, ukládání konfigurace).

## Styl kódu

- Používej C styl konzistentní s existujícím kódem:
  - 4 mezery pro odsazení, žádné tabulátory.
  - Deklarace nahoře ve funkci, žádné extravagance nad rámec toho, co už repo používá.
  - `static` pro funkce/změnné, které nemají být veřejné.
  - `const` tam, kde data neměníš.
- Přidávej include jen tam, kde jsou opravdu potřeba; preferuj lokální hlavičky (`"..."`) před globálními (`<...>`) pro projektové soubory.

## Veřejné API a hlavičky

- Hlavičky v `src/services/*/*.h` a `src/display/*.h` ber jako public API pro zbytek firmware.
- Při změně signatur:
  - nejdřív zkontroluj všechny volající (`rg`/`grep`),
  - udrž konzistenci mezi `.c` a `.h` (prototypy, typy).
- Nenarušuj existující `app_main` flow v `src/main.c` (start služeb, demo) bez dobrého důvodu – raději přidej nový hook nebo callback.

## Testy a simulátor

- Pokud měníš UI core / render:
  - `src/services/ui/ui_core.c` / `.h`,
  - `src/services/ui/renderer.c`,
  - případně `src/ui_render*.c`,
  tak zvaž, zda je potřeba upravit i:
  - testy v `test/test_ui_core` nebo `test/test_ui_render_swbuf`,
  - simulační kód v `sim/main.c` (ASCII simulátor přes `ui_core`).
- Udržuj kompatibilitu s Python simulátorem tam, kde se sdílí protokol (např. RPC metody).

## Bezpečnost a robustnost

- Vždy kontroluj návratové kódy ESP-IDF/driver funkcí (`esp_err_t`) a loguj chyby přes `ESP_LOGE/W/I`.
- Vyhýbej se dynamické alokaci v horkých cestách; pokud je potřeba, jasně dokumentuj životnost.
- Nezapomínej na hranice polí a maximální délky řetězců.

## Jak dělat změny

- Před větší úpravou:
  - projdi `IMPLEMENTATION_SUMMARY.md` a `FILE_INDEX.md` (kvůli kontextu),
  - zvaž, jestli nepotřebuješ jen rozšířit existující službu místo nové.
- Při přidávání nové služby:
  - vytvoř `src/services/<name>/<name>.c/.h`,
  - zaregistruj inicializaci v `src/main.c` (podobně jako `metrics_start`, `rpc_start`),
  - dbej na konzistentní log tag (`TAG`).

