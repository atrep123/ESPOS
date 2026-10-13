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
