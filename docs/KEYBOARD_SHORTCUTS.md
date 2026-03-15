# Keyboard Shortcuts — ESP32OS Designer

> Also available in-app via **F1** (Help overlay).

## Selection & Navigation

| Key | Action |
|-----|--------|
| LMB | Select / drag widget |
| Shift+click | Range select |
| Ctrl+click | Toggle selection |
| Alt+drag | Clone and drag |
| Box-select on empty | Rubber-band selection |
| Double-click | Edit widget text |
| Right-click | Context menu |
| Esc | Deselect (quit if empty) |
| N / P | Next / prev widget |
| Home / End | First / last widget |
| Shift+N / Shift+P | Extend selection next / prev |
| Ctrl+A | Select all |
| Ctrl+I | Invert selection |
| Ctrl+B | Select same color |
| Ctrl+J | Go to widget |
| Ctrl+K | Select children |
| Ctrl+H | Select parent panel |
| Ctrl+F3 | Select same type |
| Ctrl+Shift+A | Select same type (alt) |
| Ctrl+Shift+B | Select bordered |
| Ctrl+Shift+P | Select panels |
| Ctrl+Shift+U | Select overlapping |
| Shift+L | Select locked |
| Shift+O | Select overflow |
| Shift+S | Select by style |
| Shift+Y | Select hidden |
| Shift+U | Select z-layer |
| / | Search widgets |

## Movement & Sizing

| Key | Action |
|-----|--------|
| Arrows | Nudge selected |
| Ctrl+Arrow | 1 px precise nudge |
| Shift+Arrow | 4× nudge |
| H | Set size (W×H) |
| Shift+H | Set position (X,Y) |
| Shift+W | Full width |
| Shift+F | Full height |
| Shift+X | Swap W/H |
| Ctrl+U | Same size as first |
| Ctrl+Shift+M | Move to origin |
| Ctrl+Shift+N | Compact to origin |
| Ctrl+Shift+J | Snap pos+size to grid |
| Ctrl+Alt+S | Shrink-wrap |

## Clipboard & History

| Key | Action |
|-----|--------|
| Ctrl+C | Copy |
| Ctrl+X | Cut |
| Ctrl+V | Paste |
| Ctrl+P | Paste in place |
| Ctrl+D | Duplicate |
| Shift+D | Array duplicate |
| Shift+, | Duplicate below |
| Shift+. | Duplicate right |
| Del | Delete |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| Ctrl+Y | Redo (alt) |

## Widget Properties

| Key | Action |
|-----|--------|
| T | Cycle type |
| S | Cycle style |
| B | Cycle border |
| Q | Cycle color |
| W | Border on/off |
| O | Overflow toggle |
| A | Align |
| Shift+A | Vertical align |
| L | Lock / unlock |
| V | Show / hide |
| R | Rename |
| I | Edit icon |
| E | Smart edit |
| Shift+E | Edit runtime binding |
| Shift+T | Text overflow mode |
| Shift+B | Border width |
| Shift+V | Value range |
| Shift+Q | Swap fg/bg |
| C | Edit foreground color |
| Shift+C | Edit background color |
| \\ | Cycle gray FG (4-bit) |
| Shift+\\ | Cycle gray BG (4-bit) |
| K | Set padding (Px, Py) |
| J | Set margin (Mx, My) |
| Shift+J | Clear margins |
| Shift+K | Clear padding |
| F | Set max_lines |
| U | Set z-index |
| D | Edit data_points |
| Y | Toggle checked |
| +/− | Adjust value |
| Shift+{+/−} | Adjust value ±5 |
| Shift+I | Widget info |
| ` | Toggle widget IDs |
| ~ | Toggle z-index labels |

## Z-Order

| Key | Action |
|-----|--------|
| \[ | Step down |
| \] | Step up |
| Ctrl+\[ | Send to back |
| Ctrl+\] | Bring to front |
| Ctrl+Shift+Up/Dn | Reorder in list |
| Ctrl+Shift+S | Sort by position |
| Ctrl+Shift+0 | Flatten z-index |

## Layout & Alignment

| Key | Action |
|-----|--------|
| ; | Stack vertical |
| ' | Stack horizontal |
| Shift+; | Equalize heights |
| Shift+' | Equalize widths |
| , | Swap positions (2 sel) |
| . | Center in scene |
| F6 | Arrange row |
| F7 | Arrange column |
| Ctrl+F6 | Flow layout |
| Ctrl+F8 | Space evenly H |
| Ctrl+F9 | Space evenly V |
| Ctrl+F7 | Measure gaps |
| Ctrl+Alt+Arrows | Align edges |
| Ctrl+Alt+H | Distribute horizontally |
| Ctrl+Alt+V | Distribute vertically |
| Ctrl+Alt+W / T | Match width / height |
| Ctrl+Alt+C | Center align |
| Ctrl+Alt+G | Grid arrange |
| Ctrl+Alt+E | Equalize gaps |
| Ctrl+Alt+R | Reverse order |
| Ctrl+Alt+F | Flip vertical |
| Ctrl+Alt+N | Normalize sizes |
| Ctrl+Alt+M | Flip horizontal |
| Shift+; | Equalize heights |
| Shift+' | Equalize widths |

## Scenes

| Key | Action |
|-----|--------|
| Ctrl+N | New scene |
| Ctrl+R | Rename scene |
| Ctrl+1–9 | Jump to scene |
| Ctrl+Tab | Next scene |
| Ctrl+Shift+Tab | Prev scene |
| Ctrl+PgUp/PgDn | Switch scene |
| F10 / Shift+F10 | Next / prev scene |
| Ctrl+Shift+D | Duplicate scene |
| Ctrl+Shift+Del | Delete scene |
| Ctrl+Shift+E | Extract selection to scene |
| Ctrl+O | Copy to scene |
| Ctrl+Q | Broadcast to all scenes |
| Ctrl+F10 | Scene overview |
| DblClick tab | Rename scene |
| MidClick tab | Close scene |
| Drag tab | Reorder |
| Wheel on tabs | Scroll tabs |

## Quick-Add Widgets

| Key | Widget |
|-----|--------|
| 1 | Label |
| 2 | Button |
| 3 | Panel |
| 4 | Progressbar |
| 5 | Gauge |
| 6 | Slider |
| 7 | Checkbox |
| 8 | Chart |
| 9 | Icon |
| 0 | Textbox |
| Shift+0 | Radiobutton |

## Composite Templates (Shift+F*)

| Key | Template |
|-----|----------|
| Shift+F1 | Header bar |
| Shift+F2 | Nav row |
| Shift+F3 | Form pair |
| Shift+F4 | Status bar |
| Shift+F5 | Toggle group |
| Shift+F6 | Slider + label |
| Shift+F7 | Gauge panel |
| Shift+F8 | Progress row |
| Shift+F9 | Icon buttons |
| Shift+F11 | Card |
| Shift+F12 | Dashboard 2×2 |
| Ctrl+F12 | Split layout |

## Propagation

| Key | Action |
|-----|--------|
| Ctrl+Alt+P | Propagate style |
| Ctrl+Alt+B | Propagate border |
| Ctrl+Alt+J | Propagate alignment |
| Ctrl+Alt+K | Propagate colors |
| Ctrl+Alt+Q | Propagate value |
| Ctrl+Alt+U | Propagate padding |
| Ctrl+Alt+Y | Propagate margin |
| Ctrl+Alt+Z | Propagate full look |
| Ctrl+Alt+L | Clone text |
| Ctrl+Alt+I | Increment text # |
| Ctrl+Alt+X | Swap content (2 sel) |
| Ctrl+Alt+D | Remove duplicates |
| Ctrl+Alt+A | Name all in scene |
| Ctrl+Shift+C | Copy style |
| Ctrl+Shift+V | Paste style |

## File & Export

| Key | Action |
|-----|--------|
| Ctrl+S | Save JSON |
| Ctrl+L | Load JSON |
| Ctrl+E | Export C header |
| Ctrl+T | Save as template |
| Ctrl+Shift+T | List templates |
| Ctrl+F11 | Export selection as JSON |
| F12 | Screenshot |

## View & Display

| Key | Action |
|-----|--------|
| Ctrl+0 | Reset zoom |
| Ctrl+{+/−} | Zoom in/out |
| Mouse wheel | Zoom |
| F1 | Help / self-check overlay |
| F2 | Input simulation mode |
| F3 | Overflow warnings |
| F4 | Zoom to fit |
| F8 | Toggle enabled state |
| F9 | Clean preview |
| F11 | Fullscreen |
| G | Toggle grid |
| X | Toggle snap |
| Tab | Toggle panels |
| Shift+G | Center guides |
| Ctrl+W | Scene stats |
| Ctrl+/ | Quick reference panel |
| Ctrl+F1 | Type summary |
| Ctrl+F2 | Focus order overlay |
| Ctrl+F4 | Zoom to selection |
| Ctrl+F5 | Find/replace text |
| Ctrl+Alt+O | Outline mode |
| Ctrl+Shift+H | Hide unselected |
| Ctrl+Shift+I | Show all |
| Ctrl+Shift+L | Unlock all |
| Ctrl+Shift+Y | Enable all |
| Ctrl+Shift+X | Remove degenerate |
| Ctrl+Shift+Q | Quick clone |
| Shift+R | Auto-rename |

## Misc

| Key | Action |
|-----|--------|
| Ctrl+M | Snap to grid |
| M | Mirror horizontal |
| Shift+M | Mirror vertical |
