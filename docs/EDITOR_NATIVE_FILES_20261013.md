# Souborové operace a ruční obnova C++ editoru

## Chování

ESPOS desktop používá jeden `ProjectDocument` pro zdroj i projekci uzlů.
Produkční Open, Save a Save As mají pevný WebView2 native kanál; instalovaná route
není důkazem, že aktuální native dokument získal admission. Neexistuje HTTP,
generický Tauri invoke, uživatelský path ani readiness flag jako náhradní oprávnění.
Native registry zůstává jediným vlastníkem grantů a filesystem rozhodnutí.

- Open chrání rozpracovaný pohled a následně zvlášť neuložený zdroj. Rozhodnutí
  se neobnovuje pro jiný požadavek. Editace včetně edit → undo během chooseru
  nebo potvrzení znemožní použití starého rozhodnutí.
- Save zapíše zachycené bajty. Novější editace zůstává neuložená; potvrzená
  native verze patří jen správnému dokumentu a jeho inkarnaci.
- Save As funguje pro nový koncept i již otevřený soubor. Nový native grant se
  přijme až po ověřeném Written. Předchozí grant se uvolní až po přijetí nového
  dokumentu týmž vlastníkem, nikoli podle GUI popisku nebo writer-only receipt.
- Externí konflikt vyžaduje samostatné rozhodnutí Stop / Overwrite with actual
  backup. Zobrazený hash není compare-and-swap oprávnění.
- Nejasná odpověď uchová přesný zachycený požadavek a blokuje další zápis.
  Výslovná kontrola stejné operace nezahajuje další begin/confirmation. Stále
  Reserved se zastaví pouze přes stejný native request; samotné Cancel není
  potvrzení not-started. Nejasný cleanup má svůj původní Release ticket.

Po restartu uživatel porovná **aktuální soubor / zachycený nový obsah / skutečnou
externí zálohu**. Výběr vytvoří nový **neuložený koncept** ve stejném vlastníkovi.
Nejde o zápis do původního souboru, automatické obnovení, smazání zálohy ani
vyřešení journalu. Chybějící soubor se nezaměňuje za prázdné bajty. Ověřují se
všechny tři verze, i když uživatel vybere pouze jednu.

Obnova aktuálního zápisu se rozlišuje podle skutečného retained owner ticketu
`saveRecoveryKind`, nikoli podle dostupnosti operation ID nebo toho, zda šlo
původně o nový koncept. To zahrnuje ztrátu odpovědi Save As před rezervací.

## Ověření a hranice

Souborové testy používají explicitní TEST_ONLY wire/adapter fixtures. Ověřují
produkční klient, koordinátor, vlastníka, lifecycle ledger a skutečný Svelte
compiler, ale nejsou důkazem FileOpenDialog, COM eventů nebo zápisu z živé GUI.
`pretest:persistence` kontroluje přítomnost všech deseti explicitních testovacích
souborů: Node jinak může chybějící literal test path tiše přeskočit.

Místní úplná C++ sada zahrnuje také skutečný Python parser a SDK katalog. Samostatné
SDK komponentové testy používají aktuální místní SDK a již existující `liblvgl.a`,
nepřekládají celý simulátor ani nespouštějí jeho GUI.

Pro Windows vzniká oddělený onedir `espos_codegraph_backend`; nesmí nahradit
legacy scene sidecar. Jeho zmrazení a CLI ověření popisuje
[DESKTOP_BACKEND_BUNDLE.md](DESKTOP_BACKEND_BUNDLE.md). Backend parser zatím není
připojený jako produkční editorový parser. Tauri bundle, kompletní offline
WebView2 installer/ZIP a živé GUI zůstávají samostatné nedokončené brány.

ESPOS a espos-tauri zůstávají oddělené repozitáře. Přesný native backend pin se
nemění kvůli frontend-only změnám. Rozpracované MCP/sidecar/firmware změny mimo
tento souborový a parserový slice se nepovažují za dokončené vydání. Celý cíl
ESPOS/TabOS, simulátory, hardware a dvou-Tab5 systém nadále zůstává aktivní.

## Pozorované výsledky tohoto kroku

- Finální lokální `test:codegraph:all`: **504 passed / 0 failed / 0 skipped**.
  Souborová sada s úplným inventářem: **281/0/0**, samostatná recovery **59/0/0**.
  Typy mají 0 errors / 0 warnings; Vite frontend build a tři compile-test regrese
  prošly. Editorový commit je `b3bb687e16f8f8a8b9135a87a081692816caf309`.
- Kanonický parser, entry, frozen checker a supply-chain regrese mají lokálně
  **302/0/0**; tři SDK/LVGL komponenty se skutečně provedly, nebyly přeskočené.
  Po doplnění coverage regrese má stejný scoped běh **303/0/0**, branch pokrytí
  těchto čtyř parserových modulů **88,92 %**, nezměněný požadavek 80 % splněn.
- Lokální onedir backend byl nezávisle ověřen sedmi CLI výměnami, všemi s
  přirozeným koncem. Dva kontrolní chybové vstupy správně vracejí exit 2, nejde
  o selhání celé kontroly. Ostatních pět vrací 0 a všechny stderr jsou prázdné.
- [Windows backend CI 38456787151](https://github.com/atrep123/ESPOS/actions/runs/38456787151)
  na přesném `1f625bcd06d026278e4a8802a4c8a1a9b2fcbb03` dokončilo SUCCESS:
  **262 passed / 3 skipped** (bez externího SDK/prebuilt LVGL), skutečný frozen
  backend a jeho sedm kontrol prošly; artifact je komponenta, nikoli release.
- [První celkové CI 38456787142](https://github.com/atrep123/ESPOS/actions/runs/38456787142)
  na tomtéž commitu skončilo FAILURE: Python 3.10 má **9051 passed / 93 skipped**,
  ale slučování coverage selhalo kvůli směsi statement/branch dat. Python 3.12
  byl kvůli matrix fail-fast zrušen, firmware native/nohw job prošel.
  Oprava explicitně předává `--cov-config=pyproject.toml --cov-branch` i pro
  podprocesy s cizím fixture cwd. Nesnižuje práh a nevypíná měření podprocesů.
  Výsledek nového celkového CI je nutné přečíst až po dokončení; lokální scoped
  coverage výsledek není jeho náhradou.
