# Icon Palette Tool - Visual Icon Manager for ESP32OS
#
# Features:
# - Drag & drop icon import from PNG/SVG
# - Visual preview grid with search/filter
# - Export to C arrays for ESP32
# - Icon library management
# - Batch operations (resize, format conversion)

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import pytest

tk_available: bool = False
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    tk_available = True
except Exception:  # pragma: no cover - headless environments
    pytest.skip("tkinter not available", allow_module_level=True)
TK_AVAILABLE: bool = tk_available

from PIL import Image, ImageDraw, ImageTk

ALL_FILES = ("All files", "*.*")


class Icon:
    """Represents a single icon"""
    
    def __init__(self, name: str, width: int, height: int, data: bytes, format: str = "RGBA"):
        self.name = name
        self.width = width
        self.height = height
        self.data = data
        self.format = format
        self.tags: List[str] = []
    
    @classmethod
    def from_file(cls, filepath: str, name: Optional[str] = None):
        """Load icon from image file"""
        img = Image.open(filepath)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        if name is None:
            name = Path(filepath).stem
        
        data = img.tobytes()
        return cls(name, img.width, img.height, data, "RGBA")
    
    @classmethod
    def from_pil(cls, img: Image.Image, name: str):
        """Create icon from PIL Image"""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return cls(name, img.width, img.height, img.tobytes(), "RGBA")
    
    def to_pil(self) -> Image.Image:
        """Convert to PIL Image"""
        return Image.frombytes(self.format, (self.width, self.height), self.data)
    
    def resize(self, width: int, height: int) -> 'Icon':
        """Create resized copy of icon"""
        img = self.to_pil()
        resized = img.resize((width, height), Image.Resampling.LANCZOS)
        return Icon.from_pil(resized, self.name)
    
    def to_c_array(self, var_name: Optional[str] = None) -> str:
        """Export as C array for ESP32"""
        if var_name is None:
            var_name = f"icon_{self.name.replace('-', '_')}"
        
        # Convert to RGB565 format (common for ESP32 displays)
        img = self.to_pil()
        rgb565_data: List[int] = []
        
        for y in range(self.height):
            for x in range(self.width):
                r, g, b, a = cast(Tuple[int, int, int, int], img.getpixel((x, y)))
                # RGB565 conversion
                r5 = (r >> 3) & 0x1F
                g6 = (g >> 2) & 0x3F
                b5 = (b >> 3) & 0x1F
                rgb565 = (r5 << 11) | (g6 << 5) | b5
                rgb565_data.append(rgb565)
        
        # Generate C code
        c_code = f"// Icon: {self.name} ({self.width}x{self.height})\n"
        c_code += f"const uint16_t {var_name}[] = {{\n"
        
        for i in range(0, len(rgb565_data), 16):
            chunk: List[int] = rgb565_data[i:i+16]
            hex_vals = [f"0x{val:04X}" for val in chunk]
            c_code += "    " + ", ".join(hex_vals)
            if i + 16 < len(rgb565_data):
                c_code += ","
            c_code += "\n"
        
        c_code += "};\n"
        return c_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "data": base64.b64encode(self.data).decode('utf-8'),
            "format": self.format,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Icon':
        """Deserialize from dictionary"""
        icon = cls(
            data["name"],
            data["width"],
            data["height"],
            base64.b64decode(data["data"]),
            data.get("format", "RGBA")
        )
        icon.tags = data.get("tags", [])
        return icon


class IconLibrary:
    """Manages collection of icons"""
    
    def __init__(self):
        self.icons: Dict[str, Icon] = {}
    
    def add(self, icon: Icon):
        """Add icon to library"""
        self.icons[icon.name] = icon
    
    def remove(self, name: str):
        """Remove icon from library"""
        if name in self.icons:
            del self.icons[name]
    
    def get(self, name: str) -> Optional[Icon]:
        """Get icon by name"""
        return self.icons.get(name)
    
    def search(self, query: str) -> List[Icon]:
        """Search icons by name or tags"""
        query_lower = query.lower()
        results: List[Icon] = []
        for icon in self.icons.values():
            if query_lower in icon.name.lower() or any(query_lower in tag.lower() for tag in icon.tags):
                results.append(icon)
        return results
    
    def save(self, filepath: str):
        """Save library to JSON file"""
        data = {
            "icons": [icon.to_dict() for icon in self.icons.values()]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, filepath: str):
        """Load library from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.icons.clear()
        for icon_data in data["icons"]:
            icon = Icon.from_dict(icon_data)
            self.add(icon)
    
    def export_all_to_c(self, output_dir: str):
        """Export all icons as C arrays"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate individual files
        for icon in self.icons.values():
            c_code = icon.to_c_array()
            filepath = os.path.join(output_dir, f"{icon.name}.c")
            with open(filepath, 'w') as f:
                f.write(c_code)
        
        # Generate header file
        header = "// Auto-generated icon library\n"
        header += "#ifndef ICONS_H\n#define ICONS_H\n\n"
        header += "#include <stdint.h>\n\n"
        
        for icon in self.icons.values():
            var_name = f"icon_{icon.name.replace('-', '_')}"
            header += f"extern const uint16_t {var_name}[];\n"
            header += f"#define {var_name.upper()}_WIDTH {icon.width}\n"
            header += f"#define {var_name.upper()}_HEIGHT {icon.height}\n\n"
        
        header += "#endif // ICONS_H\n"
        
        with open(os.path.join(output_dir, "icons.h"), 'w') as f:
            f.write(header)


class IconPaletteTool:
    """Visual icon manager GUI"""
    
    def __init__(self, root: Optional[tk.Tk] = None):
        if root is None:
            self.root = tk.Tk()
            self.own_root = True
        else:
            self.root = root
            self.own_root = False
        
        self.root.title("Icon Palette Tool")
        self.root.geometry("1000x700")
        
        self.library = IconLibrary()
        self.selected_icon: Optional[str] = None
        self.icon_thumbnails: Dict[str, ImageTk.PhotoImage] = {}
        
        self._setup_ui()
        self._setup_drag_drop()
    
    def _setup_ui(self):
        """Setup GUI layout"""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import Icons...", command=self._import_icons)
        file_menu.add_command(label="Save Library...", command=self._save_library)
        file_menu.add_command(label="Load Library...", command=self._load_library)
        file_menu.add_separator()
        file_menu.add_command(label="Export to C...", command=self._export_c)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._quit)
        
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="Import", command=self._import_icons).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Delete", command=self._delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Resize", command=self._resize_selected).pack(side=tk.LEFT, padx=5)
        
        # Main content area
        content = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Icon grid (left)
        grid_frame = ttk.Frame(content)
        content.add(grid_frame, weight=3)
        
        # Scrollable canvas for icons
        self.canvas = tk.Canvas(grid_frame, bg="white")
        scrollbar_y = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.canvas.yview)  # type: ignore[arg-type]
        scrollbar_x = ttk.Scrollbar(grid_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)  # type: ignore[arg-type]
        
        self.canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.grid_frame_inner = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame_inner, anchor=tk.NW)
        
        self.grid_frame_inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Details panel (right)
        details_frame = ttk.Frame(content)
        content.add(details_frame, weight=1)
        
        ttk.Label(details_frame, text="Icon Details", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.details_text = tk.Text(details_frame, width=30, height=20, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Preview
        self.preview_label = ttk.Label(details_frame, text="No preview")
        self.preview_label.pack(pady=10)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _setup_drag_drop(self):
        """Setup drag and drop support (placeholder)"""
        # Note: Full drag-drop requires tkinterdnd2 package
        # This is a simplified version
        pass
    
    def _on_frame_configure(self, event: tk.Event):
        """Update scroll region when frame changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event: tk.Event):
        """Adjust canvas window width to canvas width"""
        self.canvas.itemconfig(self.canvas_window, width=int(event.width))
    
    def _refresh_grid(self, icons: Optional[List[Icon]] = None):
        """Refresh icon grid display"""
        # Clear existing widgets
        for widget in self.grid_frame_inner.winfo_children():
            widget.destroy()
        
        if icons is None:
            icons = list(self.library.icons.values())
        
        # Grid layout parameters
        cols = 5
        cell_size = 120
        
        for idx, icon in enumerate(icons):
            row = idx // cols
            col = idx % cols
            
            # Create cell frame
            cell = ttk.Frame(self.grid_frame_inner, relief=tk.RAISED, borderwidth=1)
            cell.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Create thumbnail
            thumb = self._create_thumbnail(icon, cell_size - 20)
            self.icon_thumbnails[icon.name] = thumb
            
            # Icon image
            img_label = ttk.Label(cell, image=thumb)
            img_label.pack(pady=5)
            img_label.bind("<Button-1>", lambda e, name=icon.name: self._select_icon(name))
            
            # Icon name
            name_label = ttk.Label(cell, text=icon.name, font=("Arial", 9))
            name_label.pack()
            name_label.bind("<Button-1>", lambda e, name=icon.name: self._select_icon(name))
            
            # Size info
            size_label = ttk.Label(cell, text=f"{icon.width}×{icon.height}", font=("Arial", 8), foreground="gray")
            size_label.pack()
        
        self.status_var.set(f"Showing {len(icons)} icons")
    
    def _create_thumbnail(self, icon: Icon, size: int) -> ImageTk.PhotoImage:
        """Create thumbnail for icon"""
        img = icon.to_pil()
        
        # Calculate aspect ratio
        aspect = img.width / img.height
        if aspect > 1:
            thumb_w = size
            thumb_h = int(size / aspect)
        else:
            thumb_h = size
            thumb_w = int(size * aspect)
        
        # Resize with high quality
        thumb = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        
        # Add checkerboard background for transparency
        bg = Image.new("RGBA", (size, size), (255, 255, 255, 255))
        checker = self._create_checker_pattern(size, size)
        bg.paste(checker, (0, 0))
        
        # Center icon on background
        offset_x = (size - thumb_w) // 2
        offset_y = (size - thumb_h) // 2
        bg.paste(thumb, (offset_x, offset_y), thumb)
        
        return ImageTk.PhotoImage(bg)
    
    def _create_checker_pattern(self, width: int, height: int, square_size: int = 8) -> Image.Image:
        """Create checkerboard pattern for transparency preview"""
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        for y in range(0, height, square_size):
            for x in range(0, width, square_size):
                if (x // square_size + y // square_size) % 2 == 0:
                    draw.rectangle([x, y, x + square_size, y + square_size], fill=(220, 220, 220))
        
        return img
    
    def _select_icon(self, name: str):
        """Select an icon and show details"""
        self.selected_icon = name
        icon = self.library.get(name)
        
        if icon:
            # Update details
            details = f"Name: {icon.name}\n"
            details += f"Size: {icon.width}×{icon.height}\n"
            details += f"Format: {icon.format}\n"
            details += f"Tags: {', '.join(icon.tags) if icon.tags else 'None'}\n"
            
            self.details_text.delete("1.0", tk.END)
            self.details_text.insert("1.0", details)
            
            # Update preview (larger)
            preview = self._create_thumbnail(icon, 200)
            self.preview_label.configure(image=preview, text="")
            self.preview_label.image = preview  # type: ignore[attr-defined]
            
            self.status_var.set(f"Selected: {name}")
    
    def _import_icons(self):
        """Import icons from files"""
        filepaths = filedialog.askopenfilenames(
            title="Import Icons",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ALL_FILES,
            ],
        )
        
        if not filepaths:
            return
        
        count = 0
        for filepath in filepaths:
            try:
                icon = Icon.from_file(filepath)
                self.library.add(icon)
                count += 1
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import {filepath}:\n{e}")
        
        if count > 0:
            self._refresh_grid()
            self.status_var.set(f"Imported {count} icon(s)")
    
    def _delete_selected(self):
        """Delete selected icon"""
        selected = self.selected_icon
        if not selected:
            messagebox.showwarning("No Selection", "Please select an icon to delete")
            return
        
        if messagebox.askyesno("Confirm Delete", f"Delete icon '{selected}'?"):
            self.library.remove(selected)
            self.selected_icon = None
            self._refresh_grid()
            self.details_text.delete("1.0", tk.END)
            self.preview_label.configure(image="", text="No preview")
    
    def _resize_selected(self):
        """Resize selected icon"""
        selected = self.selected_icon
        if not selected:
            messagebox.showwarning("No Selection", "Please select an icon to resize")
            return
        
        # Simple resize dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Resize Icon")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="New Width:").grid(row=0, column=0, padx=10, pady=10)
        width_var = tk.IntVar(value=64)
        ttk.Entry(dialog, textvariable=width_var).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="New Height:").grid(row=1, column=0, padx=10, pady=10)
        height_var = tk.IntVar(value=64)
        ttk.Entry(dialog, textvariable=height_var).grid(row=1, column=1, padx=10, pady=10)
        
        def do_resize():
            icon = self.library.get(selected)
            if icon:
                resized = icon.resize(width_var.get(), height_var.get())
                self.library.add(resized)  # Replace or add as new?
                self._refresh_grid()
                dialog.destroy()
        
        ttk.Button(dialog, text="Resize", command=do_resize).grid(row=2, column=0, columnspan=2, pady=10)
    
    def _save_library(self):
        """Save library to file"""
        filepath = filedialog.asksaveasfilename(
            title="Save Icon Library",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ALL_FILES],
        )
        
        if filepath:
            try:
                self.library.save(filepath)
                self.status_var.set(f"Library saved to {filepath}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save library:\n{e}")
    
    def _load_library(self):
        """Load library from file"""
        filepath = filedialog.askopenfilename(
            title="Load Icon Library",
            filetypes=[("JSON files", "*.json"), ALL_FILES],
        )
        
        if filepath:
            try:
                self.library.load(filepath)
                self._refresh_grid()
                self.status_var.set(f"Library loaded from {filepath}")
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load library:\n{e}")
    
    def _export_c(self):
        """Export all icons to C arrays"""
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        
        if output_dir:
            try:
                self.library.export_all_to_c(output_dir)
                messagebox.showinfo("Export Complete", f"Icons exported to {output_dir}")
                self.status_var.set(f"Exported {len(self.library.icons)} icons to C")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export:\n{e}")
    
    def _on_search(self):
        """Handle search query"""
        query = self.search_var.get()
        if query:
            results = self.library.search(query)
            self._refresh_grid(results)
        else:
            self._refresh_grid()
    
    def _quit(self):
        """Quit application"""
        if self.own_root:
            self.root.quit()
        else:
            self.root.destroy()
    
    def run(self):
        """Run the application"""
        if self.own_root:
            self.root.mainloop()


def main():
    """Main entry point"""
    app = IconPaletteTool()
    app.run()


if __name__ == "__main__":
    main()
