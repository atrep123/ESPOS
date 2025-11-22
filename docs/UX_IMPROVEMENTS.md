# Plán vylepšení UI Designeru (responsivita, UX, export)

Tento dokument slouží jako backlog pro postupné zlepšení hlavní aplikace UI Designer (Python/Tk).

## Responsivita a velikosti
- Aplikovat `responsive_scalars` na padding panelů, velikost handle, mřížku (grid size/nudge), font v status baru a hinty.
- Výchozí zoom přizpůsobit scéně (auto-fit) a ve status baru ukazovat responsive tier (tiny/small/medium/wide).

## Status bar / hinty
- Přidat ikonky a barvy pro režimy (Grid/Snap/Guides/Handles) a výraznější varování výkonu.
- Hinty rozšířit o relevantní klávesové zkratky podle režimu (panning, multi-select, export).

## Selektování a drag UX
- Větší/kontrastnější resize handly s tooltipem (rozměry, směr).
- Box-select: zobrazit počet chycených widgetů + rychlou akci Align/Distribute ve status baru.

## Palety a vkládání
- Quick-insert: ghost náhled dimenzí před vložením.
- Paleta komponent: filtr „recent“ a uložit vlastní výchozí set komponent.

## Export/preview
- Přepínač témat přímo v preview (dark/light/nord/dracula) s okamžitým redraw.
- Export dialog: předvolby pro tokeny (např. high-contrast) a volba „respektovat responsive scale“.

## Dostupnost a kontrast
- High-contrast přepínač v UI Designeru (globální) pro barvy handlů/guides/status baru dle HC tokenů.
- Alternativní kurzor/outline pro lepší viditelnost na tmavém pozadí.

## Dokumentace v UI
- Inline „mini help“ panel s klávesovými zkratkami (F1/F10), včetně responsivního chování a tokenových témat.
- Onboarding tooltip při prvním spuštění: jak zapnout grid/snap a quick-add.

## Nástroje a diagnostika
- Live FPS/render time ve status baru + volitelný „perf overlay“ s bar graphem.
- Tlačítko „profilovat snímek“: jednorázový capture renderu a uložení do reports pro CI parity.
