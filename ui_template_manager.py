#!/usr/bin/env python3
"""
UI Template Manager for ESP32 UI Designer
Manages scene templates with categories, preview, and import/export
"""

import json
import os
import tempfile
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw, ImageTk

try:
    from ui_designer import UIDesigner, Scene, WidgetConfig, WidgetType
except ImportError:
    # Fallback for when module is imported standalone
    from typing import Any as Scene
    from typing import Any as WidgetConfig
    from typing import Any as WidgetType
    UIDesigner = None


@dataclass
class TemplateMetadata:
    """Metadata for a scene template"""
    name: str
    category: str
    description: str
    author: str = "User"
    tags: List[str] = None
    thumbnail: Optional[str] = None  # Base64 encoded PNG
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class Template:
    """A complete scene template with metadata"""
    
    def __init__(self, metadata: TemplateMetadata, scene: Scene):
        self.metadata = metadata
        self.scene = scene
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize template to dictionary"""
        return {
            "metadata": asdict(self.metadata),
            "scene": self._scene_to_dict(self.scene)
        }
    
    def _scene_to_dict(self, scene: Scene) -> Dict[str, Any]:
        """Convert scene to dictionary"""
        # If scene has _raw_data, use that directly (already in dict format)
        if hasattr(scene, '_raw_data'):
            return scene._raw_data
        if hasattr(scene, 'to_dict'):
            return scene.to_dict()
        # Fallback manual serialization
        return {
            "name": getattr(scene, 'name', 'scene'),
            "widgets": [self._widget_to_dict(w) for w in getattr(scene, 'widgets', [])]
        }
    
    def _widget_to_dict(self, widget: WidgetConfig) -> Dict[str, Any]:
        """Convert widget to dictionary"""
        if hasattr(widget, 'to_dict'):
            return widget.to_dict()
        # Fallback: use __dict__
        return {k: v for k, v in widget.__dict__.items() if not k.startswith('_')}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """Deserialize template from dictionary"""
        metadata = TemplateMetadata(**data['metadata'])
        # Scene reconstruction depends on UIDesigner availability
        scene_data = data['scene']
        # Store as generic object; _raw_data is authoritative
        scene = type('Scene', (), {})()
        scene._raw_data = scene_data
        return cls(metadata, scene)


class TemplateLibrary:
    """Manages collection of templates with categories"""
    
    CATEGORIES = [
        "Layouts",
        "Forms",
        "Dashboards",
        "Dialogs",
        "Navigation",
        "Data Display",
        "Custom"
    ]
    
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            storage_dir = os.path.join(tempfile.gettempdir(), "esp32os_designer", "templates")
            os.makedirs(storage_dir, exist_ok=True)
            storage_path = os.path.join(storage_dir, "templates.json")
        
        self.storage_path = storage_path
        self.templates: List[Template] = []
        self._load_templates()
        self._ensure_default_templates()
    
    def _load_templates(self):
        """Load templates from storage"""
        if not os.path.exists(self.storage_path):
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.templates = [Template.from_dict(t) for t in data.get('templates', [])]
        except Exception as e:
            print(f"Warning: Failed to load templates: {e}")
    
    def _save_templates(self):
        """Save templates to storage"""
        try:
            data = {
                "version": "1.0",
                "templates": [t.to_dict() for t in self.templates]
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving templates: {e}")
    
    def add_template(self, template: Template):
        """Add a new template"""
        self.templates.append(template)
        self._save_templates()
    
    def remove_template(self, template: Template):
        """Remove a template"""
        if template in self.templates:
            self.templates.remove(template)
            self._save_templates()
    
    def get_templates_by_category(self, category: str) -> List[Template]:
        """Get all templates in a category"""
        return [t for t in self.templates if t.metadata.category == category]
    
    def search_templates(self, query: str) -> List[Template]:
        """Search templates by name, description, or tags"""
        query = query.lower()
        results = []
        for t in self.templates:
            if (query in t.metadata.name.lower() or
                query in t.metadata.description.lower() or
                any(query in tag.lower() for tag in t.metadata.tags)):
                results.append(t)
        return results
    
    def _ensure_default_templates(self):
        """Create default templates if library is empty"""
        if self.templates:
            return  # Already have templates
        
        # Create basic default templates
        self._create_default_dashboard()
        self._create_default_form()
        self._create_default_dialog()
        self._save_templates()
    
    def _create_default_dashboard(self):
        """Create a default dashboard template"""
        metadata = TemplateMetadata(
            name="Simple Dashboard",
            category="Dashboards",
            description="Basic dashboard layout with header, stats cards, and content area",
            tags=["dashboard", "stats", "layout"]
        )
        
        # Create mock scene with widgets
        scene = type('Scene', (), {
            'name': 'dashboard',
            'widgets': [],
            '_raw_data': {
                'name': 'dashboard',
                'widgets': [
                    {'type': 'label', 'x': 0, 'y': 0, 'width': 240, 'height': 20, 'text': 'Dashboard', 'border': True},
                    {'type': 'box', 'x': 10, 'y': 30, 'width': 70, 'height': 50, 'border': True},
                    {'type': 'label', 'x': 15, 'y': 35, 'width': 60, 'height': 10, 'text': 'CPU: 45%'},
                    {'type': 'box', 'x': 90, 'y': 30, 'width': 70, 'height': 50, 'border': True},
                    {'type': 'label', 'x': 95, 'y': 35, 'width': 60, 'height': 10, 'text': 'MEM: 60%'},
                    {'type': 'box', 'x': 170, 'y': 30, 'width': 60, 'height': 50, 'border': True},
                    {'type': 'label', 'x': 175, 'y': 35, 'width': 50, 'height': 10, 'text': 'Temp: 42°C'},
                ]
            }
        })()
        
        self.templates.append(Template(metadata, scene))
    
    def _create_default_form(self):
        """Create a default form template"""
        metadata = TemplateMetadata(
            name="Settings Form",
            category="Forms",
            description="Simple settings form with labels and input fields",
            tags=["form", "settings", "input"]
        )
        
        scene = type('Scene', (), {
            'name': 'settings_form',
            'widgets': [],
            '_raw_data': {
                'name': 'settings_form',
                'widgets': [
                    {'type': 'label', 'x': 0, 'y': 0, 'width': 240, 'height': 20, 'text': 'Settings', 'border': True},
                    {'type': 'label', 'x': 10, 'y': 30, 'width': 60, 'height': 10, 'text': 'Username:'},
                    {'type': 'box', 'x': 80, 'y': 28, 'width': 150, 'height': 14, 'border': True},
                    {'type': 'label', 'x': 10, 'y': 50, 'width': 60, 'height': 10, 'text': 'Volume:'},
                    {'type': 'slider', 'x': 80, 'y': 48, 'width': 150, 'height': 8, 'value': 50},
                    {'type': 'checkbox', 'x': 10, 'y': 70, 'width': 100, 'height': 10, 'text': 'Enable WiFi', 'checked': True},
                    {'type': 'button', 'x': 80, 'y': 95, 'width': 60, 'height': 15, 'text': 'Save'},
                ]
            }
        })()
        
        self.templates.append(Template(metadata, scene))
    
    def _create_default_dialog(self):
        """Create a default dialog template"""
        metadata = TemplateMetadata(
            name="Confirmation Dialog",
            category="Dialogs",
            description="Simple confirmation dialog with message and Yes/No buttons",
            tags=["dialog", "confirm", "message"]
        )
        
        scene = type('Scene', (), {
            'name': 'confirm_dialog',
            'widgets': [],
            '_raw_data': {
                'name': 'confirm_dialog',
                'widgets': [
                    {'type': 'panel', 'x': 40, 'y': 30, 'width': 160, 'height': 80, 'border': True, 'text': 'Confirm'},
                    {'type': 'label', 'x': 50, 'y': 50, 'width': 140, 'height': 20, 'text': 'Are you sure?', 'align': 'center'},
                    {'type': 'button', 'x': 60, 'y': 85, 'width': 50, 'height': 15, 'text': 'Yes'},
                    {'type': 'button', 'x': 130, 'y': 85, 'width': 50, 'height': 15, 'text': 'No'},
                ]
            }
        })()
        
        self.templates.append(Template(metadata, scene))


class TemplateManagerWindow:
    """Template Manager GUI window"""
    
    def __init__(self, parent: tk.Tk, designer: Optional[Any] = None):
        self.parent = parent
        self.designer = designer
        self.library = TemplateLibrary()
        self.selected_template: Optional[Template] = None
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Template Manager")
        self.window.geometry("800x600")
        self.window.transient(parent)
        
        self._setup_ui()
        self._refresh_template_list()
    
    def _setup_ui(self):
        """Setup UI components"""
        # Main container
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', lambda e: self._on_search())
        
        ttk.Button(toolbar, text="🔍 Search", command=self._on_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🔄 Refresh", command=self._refresh_template_list).pack(side=tk.LEFT, padx=5)
        
        # Content area (3 columns: categories, templates, preview)
        content = ttk.Frame(main_frame)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Left: Categories
        left_frame = ttk.LabelFrame(content, text="Categories", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        self.category_listbox = tk.Listbox(left_frame, width=20, height=20)
        self.category_listbox.pack(fill=tk.BOTH, expand=True)
        
        for category in TemplateLibrary.CATEGORIES:
            self.category_listbox.insert(tk.END, category)
        
        self.category_listbox.bind('<<ListboxSelect>>', lambda e: self._on_category_select())
        self.category_listbox.select_set(0)
        
        # Middle: Template list
        middle_frame = ttk.LabelFrame(content, text="Templates", padding=5)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Template list with scrollbar
        list_container = ttk.Frame(middle_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.template_listbox = tk.Listbox(list_container, yscrollcommand=scrollbar.set, height=20)
        self.template_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.template_listbox.yview)
        
        self.template_listbox.bind('<<ListboxSelect>>', lambda e: self._on_template_select())
        
        # Template info below list
        info_frame = ttk.Frame(middle_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.info_label = ttk.Label(info_frame, text="Select a template", wraplength=250, justify=tk.LEFT)
        self.info_label.pack(fill=tk.X)
        
        # Right: Preview
        right_frame = ttk.LabelFrame(content, text="Preview", padding=5)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.preview_canvas = tk.Canvas(right_frame, width=240, height=320, bg="#1e1e1e", relief=tk.SUNKEN, borderwidth=2)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bottom: Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="💾 Save Current Scene", command=self._save_current_scene).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📥 Apply Template", command=self._apply_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📤 Export Template", command=self._export_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📂 Import Template", command=self._import_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🗑️ Delete Template", command=self._delete_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _refresh_template_list(self):
        """Refresh the template list based on selected category"""
        self._on_category_select()
    
    def _on_category_select(self):
        """Handle category selection"""
        selection = self.category_listbox.curselection()
        if not selection:
            return
        
        category = self.category_listbox.get(selection[0])
        templates = self.library.get_templates_by_category(category)
        
        # Update template list
        self.template_listbox.delete(0, tk.END)
        for template in templates:
            self.template_listbox.insert(tk.END, template.metadata.name)
        
        # Store templates for reference
        self._current_templates = templates
    
    def _on_template_select(self):
        """Handle template selection"""
        selection = self.template_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        if not hasattr(self, '_current_templates') or idx >= len(self._current_templates):
            return
        
        self.selected_template = self._current_templates[idx]
        
        # Update info
        meta = self.selected_template.metadata
        info_text = f"{meta.name}\n\n{meta.description}\n\nAuthor: {meta.author}"
        if meta.tags:
            info_text += f"\nTags: {', '.join(meta.tags)}"
        self.info_label.config(text=info_text)
        
        # Update preview
        self._render_preview()
    
    def _render_preview(self):
        """Render preview of selected template"""
        if not self.selected_template:
            return
        
        # Create preview image
        width, height = 240, 320
        img = Image.new('RGB', (width, height), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        
        # Get widgets from scene
        scene_data = getattr(self.selected_template.scene, '_raw_data', {})
        widgets = scene_data.get('widgets', [])
        
        # Draw widgets (simplified)
        for widget in widgets:
            self._draw_preview_widget(draw, widget)
        
        # Convert to PhotoImage and display
        self.preview_photo = ImageTk.PhotoImage(img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_photo)
    
    def _draw_preview_widget(self, draw: ImageDraw, widget: Dict[str, Any]):
        """Draw a single widget in preview"""
        x = widget.get('x', 0)
        y = widget.get('y', 0)
        w = widget.get('width', 40)
        h = widget.get('height', 12)
        wtype = widget.get('type', 'box')
        text = widget.get('text', '')
        border = widget.get('border', True)
        
        # Colors
        bg_color = (60, 60, 60)
        fg_color = (200, 200, 200)
        border_color = (100, 150, 255)
        
        # Draw background
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=bg_color)
        
        # Draw border
        if border:
            draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border_color, width=1)
        
        # Draw widget-specific elements
        if wtype == 'button':
            if text:
                draw.text((x + 5, y + 2), text, fill=fg_color)
        elif wtype == 'label':
            if text:
                draw.text((x + 2, y + 2), text, fill=fg_color)
        elif wtype == 'checkbox':
            # Draw checkbox box
            draw.rectangle([x + 2, y + 2, x + 8, y + 8], outline=fg_color, width=1)
            if widget.get('checked'):
                draw.line([(x + 3, y + 5), (x + 7, y + 7)], fill=fg_color, width=1)
            if text:
                draw.text((x + 12, y + 2), text, fill=fg_color)
        elif wtype == 'slider':
            # Draw slider track
            draw.line([(x + 2, y + h // 2), (x + w - 2, y + h // 2)], fill=fg_color, width=1)
            value = widget.get('value', 50)
            handle_x = x + 2 + int((w - 4) * value / 100)
            draw.rectangle([handle_x - 2, y + 2, handle_x + 2, y + h - 2], fill=fg_color)
        elif wtype == 'progressbar':
            value = widget.get('value', 50)
            progress_w = int((w - 4) * value / 100)
            if progress_w > 0:
                draw.rectangle([x + 2, y + 2, x + 2 + progress_w, y + h - 3], fill=fg_color)
        elif wtype == 'panel':
            if text:
                draw.text((x + 4, y + 2), text, fill=fg_color)
    
    def _on_search(self):
        """Handle search input"""
        query = self.search_var.get().strip()
        if not query:
            self._refresh_template_list()
            return
        
        templates = self.library.search_templates(query)
        
        # Update template list
        self.template_listbox.delete(0, tk.END)
        for template in templates:
            self.template_listbox.insert(tk.END, f"{template.metadata.name} ({template.metadata.category})")
        
        self._current_templates = templates
    
    def _save_current_scene(self):
        """Save current scene as template"""
        if not self.designer:
            messagebox.showwarning("No Designer", "No UI Designer instance available")
            return
        
        # Get current scene
        scene = self.designer.scenes.get(self.designer.current_scene)
        if not scene:
            messagebox.showwarning("No Scene", "No active scene to save")
            return
        
        # Show dialog to get template info
        dialog = tk.Toplevel(self.window)
        dialog.title("Save Template")
        dialog.geometry("400x350")
        dialog.transient(self.window)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Template Name:").pack(pady=(10, 0), padx=10, anchor=tk.W)
        name_var = tk.StringVar(value=scene.name)
        ttk.Entry(dialog, textvariable=name_var, width=50).pack(pady=5, padx=10)
        
        ttk.Label(dialog, text="Category:").pack(pady=(10, 0), padx=10, anchor=tk.W)
        category_var = tk.StringVar(value="Custom")
        category_combo = ttk.Combobox(dialog, textvariable=category_var, values=TemplateLibrary.CATEGORIES, width=47)
        category_combo.pack(pady=5, padx=10)
        
        ttk.Label(dialog, text="Description:").pack(pady=(10, 0), padx=10, anchor=tk.W)
        desc_text = tk.Text(dialog, width=50, height=5)
        desc_text.pack(pady=5, padx=10)
        
        ttk.Label(dialog, text="Tags (comma-separated):").pack(pady=(10, 0), padx=10, anchor=tk.W)
        tags_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=tags_var, width=50).pack(pady=5, padx=10)
        
        ttk.Label(dialog, text="Author:").pack(pady=(10, 0), padx=10, anchor=tk.W)
        author_var = tk.StringVar(value="User")
        ttk.Entry(dialog, textvariable=author_var, width=50).pack(pady=5, padx=10)
        
        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Invalid Name", "Please enter a template name")
                return
            
            category = category_var.get()
            description = desc_text.get("1.0", tk.END).strip()
            tags = [t.strip() for t in tags_var.get().split(',') if t.strip()]
            author = author_var.get().strip() or "User"
            
            metadata = TemplateMetadata(
                name=name,
                category=category,
                description=description,
                author=author,
                tags=tags
            )
            
            template = Template(metadata, scene)
            self.library.add_template(template)
            
            messagebox.showinfo("Success", f"Template '{name}' saved successfully!")
            dialog.destroy()
            self._refresh_template_list()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _apply_template(self):
        """Apply selected template to designer"""
        if not self.selected_template:
            messagebox.showwarning("No Selection", "Please select a template to apply")
            return
        
        if not self.designer:
            messagebox.showwarning("No Designer", "No UI Designer instance available")
            return
        
        # Confirm overwrite
        if not messagebox.askyesno("Confirm", "This will replace the current scene. Continue?"):
            return
        
        # Apply template
        scene_data = getattr(self.selected_template.scene, '_raw_data', {})
        scene_name = scene_data.get('name', 'imported_scene')
        
        # Create new scene
        self.designer.create_scene(scene_name)
        scene = self.designer.scenes.get(scene_name)
        
        # Add widgets
        for widget_data in scene_data.get('widgets', []):
            wtype_str = widget_data.get('type', 'label')
            # Map string to WidgetType enum
            wtype_map = {
                'label': WidgetType.LABEL,
                'button': WidgetType.BUTTON,
                'box': WidgetType.BOX if hasattr(WidgetType, 'BOX') else WidgetType.PANEL,
                'panel': WidgetType.PANEL,
                'checkbox': WidgetType.CHECKBOX,
                'slider': WidgetType.SLIDER,
                'progressbar': WidgetType.PROGRESSBAR,
                'gauge': WidgetType.GAUGE,
            }
            wtype = wtype_map.get(wtype_str, WidgetType.LABEL)
            
            # Extract properties
            props = {k: v for k, v in widget_data.items() if k not in ['type', 'x', 'y', 'width', 'height']}
            
            self.designer.add_widget(
                wtype,
                x=widget_data.get('x', 0),
                y=widget_data.get('y', 0),
                width=widget_data.get('width', 40),
                height=widget_data.get('height', 12),
                **props
            )
        
        messagebox.showinfo("Success", f"Template '{self.selected_template.metadata.name}' applied!")
        self.window.destroy()
    
    def _export_template(self):
        """Export selected template to JSON file"""
        if not self.selected_template:
            messagebox.showwarning("No Selection", "Please select a template to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Template",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.selected_template.metadata.name}.json"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.selected_template.to_dict(), f, indent=2)
            
            messagebox.showinfo("Success", f"Template exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export template: {e}")
    
    def _import_template(self):
        """Import template from JSON file"""
        filename = filedialog.askopenfilename(
            title="Import Template",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            template = Template.from_dict(data)
            self.library.add_template(template)
            
            messagebox.showinfo("Success", f"Template '{template.metadata.name}' imported successfully!")
            self._refresh_template_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import template: {e}")
    
    def _delete_template(self):
        """Delete selected template"""
        if not self.selected_template:
            messagebox.showwarning("No Selection", "Please select a template to delete")
            return
        
        if not messagebox.askyesno("Confirm Delete", 
                                   f"Are you sure you want to delete '{self.selected_template.metadata.name}'?"):
            return
        
        self.library.remove_template(self.selected_template)
        messagebox.showinfo("Success", "Template deleted successfully!")
        self.selected_template = None
        self._refresh_template_list()


def main():
    """Standalone test"""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    manager = TemplateManagerWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()
