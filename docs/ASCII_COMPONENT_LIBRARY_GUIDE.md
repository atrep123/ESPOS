# ASCII Component Library Integration Guide

This document describes how to use the ASCII component library in the ESP32OS UI Designer and how to add components to your scenes.

## Overview
- The UI Designer palette now uses the ASCII component library (`ui_components_library_ascii.py`).
- You can browse, filter, and add ASCII components directly to your canvas.
- Each component is compatible with the WidgetConfig ASCII format and can be exported for ESP32 firmware.

## How to Use
1. **Open the UI Designer Preview**
   - Run `ui_designer_preview.py`.
   - The palette window will show all available ASCII components, grouped by category.

2. **Browse and Filter Components**
   - Use the category dropdown to filter by Dialogs, Navigation, Data Display, Controls, or Layouts.
   - Use the search box to find components by name or description.

3. **Add Components to Canvas**
   - Click "➕ Add to Canvas" on any component card.
   - The component's widgets will be added to the current scene.
   - Newly added widgets are automatically selected for further editing.

4. **Export for ESP32**
   - All components use the ASCII WidgetConfig format, ready for export to ESP32 firmware.
   - Use the export function in the UI Designer to generate C code or configuration files.

## Component List
- **Dialogs**: AlertDialog, ConfirmDialog, InputDialog
- **Navigation**: TabBar, VerticalMenu, Breadcrumb
- **Data Display**: StatCard, ProgressCard, StatusIndicator
- **Controls**: ButtonGroup, ToggleSwitch, RadioGroup
- **Layouts**: HeaderFooterLayout, SidebarLayout, GridLayout

## Example: Adding a StatCard
1. Filter by "Data Display" or search "StatCard".
2. Click "➕ Add to Canvas".
3. The StatCard widgets appear in your scene, ready for editing or export.

## Notes
- All palette components are defined in `ui_components_library_ascii.py`.
- You can extend the library by adding new factory functions to this file and updating the palette definition in `ui_designer_preview.py`.
- The integration is designed to be minimal and maintain compatibility with existing UI Designer features.

## Troubleshooting
- If a component does not appear, check that its factory function is correctly imported and listed in the palette definition.
- For export issues, verify that all widgets use the ASCII WidgetConfig format.

---
For further details, see `UI_DESIGNER_GUIDE.md` and the source code in `ui_designer_preview.py` and `ui_components_library_ascii.py`.
