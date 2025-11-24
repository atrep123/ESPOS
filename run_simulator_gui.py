#!/usr/bin/env python3
"""
ESP32 Simulator GUI Wrapper
Runs the simulator in a Tkinter window with visual display
"""
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional

from PIL import Image, ImageDraw, ImageTk


class SimulatorGUI:
    """Visual GUI window for ESP32 simulator"""
    
    def __init__(self, width=128, height=64, port=8765):
        self.width = width
        self.height = height
        self.port = port
        self.sim_process: Optional[subprocess.Popen] = None
        self.running = False
        
        # Create window
        self.root = tk.Tk()
        self.root.title(f"ESP32 Simulator - {width}×{height}")
        self.root.configure(bg='#1e1e1e')
        
        # Apply dark theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(".", background='#2b2b2b', foreground='#ffffff',
                       fieldbackground='#1a1a1a')
        style.configure("TButton", background='#4d4d4d')
        style.configure("TLabel", background='#2b2b2b', foreground='#ffffff')
        style.configure("TFrame", background='#2b2b2b')
        
        self._setup_ui()
        self._start_simulator()
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def _setup_ui(self):
        """Setup GUI layout"""
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="ESP32 Simulator", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(toolbar, text="🔄 Reset", command=self._reset_sim).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="⏸️ Pause", command=self._toggle_pause).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(toolbar, text="Inicializace...")
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Display canvas (scaled up for visibility)
        self.scale = 4
        canvas_width = self.width * self.scale
        canvas_height = self.height * self.scale
        
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, 
                               width=canvas_width, 
                               height=canvas_height,
                               bg='#000000',
                               highlightthickness=1,
                               highlightbackground='#444444')
        self.canvas.pack()
        
        # Create PIL Image for display
        self.display_image = Image.new('RGB', (self.width, self.height), color=(0, 0, 0))
        self.photo_image = None
        
        # Info panel
        info_frame = ttk.LabelFrame(self.root, text="Informace", padding=5)
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        self.info_text = tk.Text(info_frame, height=4, bg='#1a1a1a', fg='#888888',
                                font=("Consolas", 9), relief=tk.FLAT)
        self.info_text.pack(fill=tk.X)
        self.info_text.insert("1.0", "Čekání na simulátor...\n")
        self.info_text.config(state=tk.DISABLED)
        
    def _start_simulator(self):
        """Start simulator subprocess"""
        try:
            import sys
            cmd = [sys.executable, "scripts/sim_run.py", 
                   "--rpc-port", str(self.port),
                   "--headless"]  # Run without terminal UI
            
            self.sim_process = subprocess.Popen(cmd, 
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
            
            self.running = True
            
            # Start update thread
            threading.Thread(target=self._update_loop, daemon=True).start()
            
            self.status_label.config(text=f"Běží (port {self.port})")
            self._update_info("✅ Simulátor spuštěn\n")
            
        except Exception as e:
            self.status_label.config(text=f"Chyba: {e}")
            self._update_info(f"❌ Chyba při spuštění: {e}\n")
    
    def _update_loop(self):
        """Update display in background"""
        time.sleep(1)  # Wait for simulator to start
        
        while self.running:
            try:
                # Connect to simulator RPC to get display state
                # For now, just draw a test pattern
                self._draw_test_pattern()
                self._refresh_display()
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"Update error: {e}")
                time.sleep(0.1)
    
    def _draw_test_pattern(self):
        """Draw test pattern (replace with actual simulator data)"""
        draw = ImageDraw.Draw(self.display_image)
        
        # Clear
        draw.rectangle([0, 0, self.width, self.height], fill=(10, 10, 10))
        
        # Draw border
        draw.rectangle([0, 0, self.width-1, self.height-1], outline=(0, 122, 204), width=1)
        
        # Draw text
        try:
            draw.text((10, 10), "ESP32 Simulator", fill=(255, 255, 255))
            draw.text((10, 30), f"{self.width}×{self.height}", fill=(200, 200, 200))
        except:
            pass  # Font issues, skip text
    
    def _refresh_display(self):
        """Refresh canvas with current display image"""
        # Scale up for visibility
        scaled = self.display_image.resize(
            (self.width * self.scale, self.height * self.scale),
            Image.NEAREST
        )
        
        self.photo_image = ImageTk.PhotoImage(scaled)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
    
    def _update_info(self, text: str):
        """Update info text"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.insert(tk.END, text)
        self.info_text.see(tk.END)
        self.info_text.config(state=tk.DISABLED)
    
    def _reset_sim(self):
        """Reset simulator"""
        self._update_info("🔄 Reset simulátoru\n")
    
    def _toggle_pause(self):
        """Toggle pause"""
        self._update_info("⏸️ Pause/Resume\n")
    
    def _on_close(self):
        """Handle window close"""
        self.running = False
        if self.sim_process:
            self.sim_process.terminate()
            self.sim_process.wait(timeout=2)
        self.root.destroy()
    
    def run(self):
        """Run GUI main loop"""
        self.root.mainloop()


def main():
    """Main entry point"""
    print("🚀 Spouštím ESP32 Simulator GUI...")
    sim = SimulatorGUI(width=128, height=64, port=8765)
    sim.run()


if __name__ == "__main__":
    main()
