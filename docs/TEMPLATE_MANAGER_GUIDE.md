# Template Manager Guide

The Template Manager allows you to save and reuse custom widget combinations in ESP32OS UI Designer.

## Overview

Templates are pre-configured widget groups that you can save and load across different projects. This feature is perfect for:

- Reusing common UI patterns (e.g., navigation bars, forms, dialogs)
- Sharing component configurations between projects
- Building a library of custom UI elements
- Speeding up repetitive design tasks

## Opening Template Manager

1. **Via Palette**: Click the **📑 Templates** button in the left palette
2. **Keyboard**: No dedicated shortcut yet (use mouse)

## Creating Templates

### Step-by-Step

1. **Select widgets** in the canvas:
   - Click individual widgets
   - Or use `Ctrl+A` to select all
   - Or drag-select multiple widgets

2. **Open Template Manager**: Click **📑 Templates**

3. **Save**: Click **💾 Save Selection as Template**

4. **Enter details**:
   - **Name**: Give your template a descriptive name
   - **Description**: Optional description of what the template does

5. **Done!** Template is saved to the `templates/` directory

### Example Template

```text
Name: Login Form
Description: Standard login form with username, password, and submit button
Widgets: 
  - 2 Labels (Username, Password)
  - 2 Input fields
  - 1 Submit button
```

## Using Templates

### Loading a Template

1. Open Template Manager (**📑 Templates**)
2. Browse available templates
3. Click **➕ Add to Canvas** on desired template
4. Widgets appear on canvas (selected automatically)
5. Move/edit widgets as needed

### Template Actions

| Button | Action |
|--------|--------|
| **➕ Add to Canvas** | Load template widgets into current scene |
| **👁️ Preview** | View template info and widget list |
| **🗑️ Delete** | Remove template permanently |
| **🔄 Refresh** | Reload template list |

## Template File Format

Templates are stored as JSON files in the `templates/` directory:

```json
{
  "name": "My Template",
  "description": "Custom component template",
  "widgets": [
    {
      "type": "button",
      "x": 10,
      "y": 10,
      "width": 50,
      "height": 20,
      "text": "Click Me",
      "visible": true,
      "border": true,
      "checked": false,
      "value": 0
    }
  ]
}
```

### Supported Widget Properties

- `type`: Widget type (button, label, box, etc.)
- `x`, `y`: Position coordinates
- `width`, `height`: Dimensions
- `text`: Display text
- `visible`: Visibility flag
- `border`: Border enabled/disabled
- `checked`: Checkbox state (for checkboxes)
- `value`: Progress value (for progress bars/gauges)

## Managing Templates

### Template Directory

All templates are saved in: `templates/`

### Filename Convention

Template names are automatically sanitized:

- Spaces → underscores
- Lowercase
- `.json` extension

Example: "My Cool Template" → `my_cool_template.json`

### Manual Editing

You can manually edit template JSON files with any text editor:

1. Navigate to `templates/` directory
2. Open `.json` file
3. Edit widget properties
4. Save file
5. Click **🔄 Refresh** in Template Manager

### Sharing Templates

Templates are portable JSON files:

- Copy `.json` files between projects
- Share via email/chat
- Version control with Git
- Bundle multiple templates in a folder

## Use Cases

### 1. Navigation Bar Template

Create once, reuse everywhere:

```text
Widgets: Logo, 4 menu buttons, search box
```

### 2. Dialog Box Template

Standard dialog layout:

```text
Widgets: Title label, message label, OK/Cancel buttons
```

### 3. Dashboard Card Template

Reusable metric display:

```text
Widgets: Stat card, progress bar, status indicator
```

### 4. Form Template

Complete input form:

```text
Widgets: Multiple labels, input fields, submit button
```

## Tips & Tricks

### Organizing Templates

- Use descriptive names: "NavBar_Dark_Theme" instead of "Template1"
- Add detailed descriptions for complex templates
- Group related templates with prefixes: "Form_Login", "Form_Register"

### Template Design

- **Keep it modular**: Small, focused templates are easier to reuse
- **Relative positioning**: Position widgets relative to each other
- **Standard sizes**: Use common dimensions for consistency
- **Test first**: Verify layout before saving as template

### Workflow Integration

1. **Design → Template → Reuse**:
   - Design component once
   - Save as template
   - Reuse across projects

2. **Template Library**:
   - Build collection of templates over time
   - Categorize by type (Navigation, Forms, Cards, etc.)
   - Document usage in descriptions

3. **Team Sharing**:
   - Share `templates/` folder with team
   - Use version control for template library
   - Establish naming conventions

## Keyboard Shortcuts

While using Template Manager:

- `Esc`: Close Template Manager window
- `Ctrl+S`: Quick save selection (when Template Manager is open)

## Troubleshooting

### Template not loading?

- Check template JSON syntax (use JSON validator)
- Ensure all required widget properties are present
- Verify file is in `templates/` directory

### Templates disappear?

- Check `templates/` directory exists
- Click **🔄 Refresh** to reload list
- Verify file permissions

### Widget positions wrong?

- Widgets load at saved coordinates
- Move/adjust after loading
- Re-save template with corrected positions

---

**Pro Tip**: Combine templates with keyboard shortcuts (Ctrl+1-9) for ultra-fast UI design!
