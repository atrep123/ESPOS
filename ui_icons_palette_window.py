# Icon Palette Window Implementation
# This file extends ui_designer_preview.py with the IconPaletteWindow class
# Append this to the end of ui_designer_preview.py

class IconPaletteWindow(tk.Toplevel):
    """Icon palette window for browsing and selecting Material Icons"""
    
    def __init__(self, parent, preview_window: VisualPreviewWindow):
        super().__init__(parent)
        self.preview_window = preview_window
        
        self.title("Icon Palette - Material Icons")
        self.geometry("500x700")
        self.configure(bg="#2b2b2b")
        
        # Setup UI
        self._setup_ui()
        self._load_icons()
    
    def _setup_ui(self):
        """Setup palette UI"""
        # Header
        header = ttk.Frame(self)
        header.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header, text="🎨 Material Icons (53)", 
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # Size selector
        size_frame = ttk.Frame(self)
        size_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Label(size_frame, text="Size:").pack(side=tk.LEFT, padx=5)
        self.size_var = tk.StringVar(value="16px")
        ttk.Radiobutton(size_frame, text="16×16", variable=self.size_var, value="16px").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(size_frame, text="24×24", variable=self.size_var, value="24px").pack(side=tk.LEFT, padx=5)
        
        # Category filter
        filter_frame = ttk.Frame(self)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="Category:").pack(side=tk.LEFT, padx=5)
        
        categories = ["All"] + get_all_categories()
        self.category_var = tk.StringVar(value="All")
        category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var,
                          values=categories, width=20, state="readonly")
        category_combo.pack(side=tk.LEFT, padx=5)
        category_combo.bind("<<ComboboxSelected>>", lambda e: self._load_icons())
        
        # Search box
        search_frame = ttk.Frame(self)
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self._load_icons())
        
        # Icon list (scrollable)
        list_frame = ttk.Frame(self)
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas with scrollbar
        canvas = tk.Canvas(list_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        
        self.icons_frame = ttk.Frame(canvas)
        self.icons_frame.bind("<Configure>", 
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.icons_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = canvas
        
        # Info footer
        info = ttk.Label(self, text="Click icon to copy symbol name • Drag to add to canvas (future)", 
                        font=("Arial", 9), foreground="#8b949e", background="#2b2b2b")
        info.pack(side=tk.BOTTOM, pady=10)
    
    def _load_icons(self):
        """Load and display icons based on filters"""
        # Clear existing
        for widget in self.icons_frame.winfo_children():
            widget.destroy()
        
        # Get filtered icons
        category = self.category_var.get()
        search = self.search_var.get().lower()
        icons = MATERIAL_ICONS
        
        if category != "All":
            icons = [i for i in icons if i["category"] == category]
        if search:
            icons = [i for i in icons if search in i["name"].lower() or 
                    search in i["usage"].lower() or 
                    search in i["symbol"].lower()]
        
        # Display icons
        for i, icon in enumerate(icons):
            self._create_icon_card(icon, i)
    
    def _create_icon_card(self, icon, index):
        """Create an icon card in the palette"""
        card = ttk.Frame(self.icons_frame, relief=tk.RAISED, borderwidth=1)
        card.pack(fill=tk.X, padx=5, pady=5)
        
        # Header with icon symbol and name
        header = ttk.Frame(card)
        header.pack(fill=tk.X, padx=10, pady=8)
        
        # ASCII preview
        ascii_label = ttk.Label(header, text=icon["ascii"], font=("Segoe UI Emoji", 20))
        ascii_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Name and category
        info_frame = ttk.Frame(header)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(info_frame, text=icon["name"], font=("Arial", 11, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"{icon['category'].title()} • {icon['symbol']}", 
                 font=("Courier", 9), foreground="#58a6ff").pack(anchor=tk.W)
        
        # Usage description
        ttk.Label(card, text=icon["usage"], font=("Arial", 9), 
                 foreground="#8b949e", wraplength=450).pack(anchor=tk.W, padx=10, pady=(0, 8))
        
        # Action buttons
        button_frame = ttk.Frame(card)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="📋 Copy Symbol", 
                  command=lambda: self._copy_symbol(icon["symbol"])).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="ℹ Info", 
                  command=lambda: self._show_icon_info(icon)).pack(side=tk.LEFT, padx=2)
    
    def _copy_symbol(self, symbol: str):
        """Copy icon symbol to clipboard"""
        self.clipboard_clear()
        self.clipboard_append(symbol)
        # Show toast notification
        messagebox.showinfo("Copied", f"Symbol '{symbol}' copied to clipboard!")
    
    def _show_icon_info(self, icon):
        """Show detailed icon information"""
        size = self.size_var.get()
        size_field = "size_16" if size == "16px" else "size_24"
        
        info_text = f"""Icon: {icon['name']}
Category: {icon['category'].title()}
Usage: {icon['usage']}

C Symbol ({size}): {icon[size_field]}
ASCII Fallback: {icon['ascii']}

Example (C):
  #include "icons.h"
  display_draw_icon(&{icon[size_field]}, x, y);

Example (JSON/Python):
  {{"type": "icon", "icon": "{icon['symbol']}", "x": 10, "y": 20}}
"""
        
        # Create info dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Icon Info - {icon['name']}")
        dialog.geometry("500x400")
        dialog.configure(bg="#1e1e1e")
        
        # ASCII preview (large)
        preview = ttk.Label(dialog, text=icon["ascii"], font=("Segoe UI Emoji", 48), 
                           background="#1e1e1e", foreground="#58a6ff")
        preview.pack(pady=20)
        
        # Info text
        text = tk.Text(dialog, width=60, height=15, bg="#2b2b2b", fg="#c9d1d9", 
                      font=("Courier", 10), wrap=tk.WORD)
        text.insert("1.0", info_text)
        text.config(state=tk.DISABLED)
        text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)


# Add this class to the end of ui_designer_preview.py
