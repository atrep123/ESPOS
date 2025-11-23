#!/usr/bin/env python3
"""
Screenshot and Video Capture for ESP32 Simulator
Capture terminal output as images and animated GIFs
"""

import time
import os
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CaptureConfig:
    """Configuration for capture"""
    output_dir: str = "captures"
    format: str = "png"  # png, txt, html
    fps: int = 10  # For GIF/video
    duration: float = 5.0  # seconds
    width: int = 800
    height: int = 600


class ScreenshotCapture:
    """Capture simulator output as images"""
    
    def __init__(self, config: CaptureConfig):
        self.config = config
        self.frames: List[str] = []
        
        # Create output directory
        os.makedirs(config.output_dir, exist_ok=True)
    
    def capture_text_frame(self, lines: List[str]) -> str:
        """Capture current frame as text"""
        return "\n".join(lines)
    
    def save_text_screenshot(self, lines: List[str], filename: Optional[str] = None) -> str:
        """Save screenshot as text file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.txt"
        
        filepath = os.path.join(self.config.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.capture_text_frame(lines))
            
            print(f"📸 Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Failed to save screenshot: {e}")
            return ""
    
    def save_html_screenshot(self, lines: List[str], filename: Optional[str] = None) -> str:
        """Save screenshot as HTML with ANSI colors preserved"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.html"
        
        filepath = os.path.join(self.config.output_dir, filename)
        
        # Convert ANSI to HTML
        html_content = self._ansi_to_html(lines)
        
        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ESP32 Simulator Screenshot</title>
    <style>
        body {{
            background: #1a1a1a;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            padding: 20px;
            margin: 0;
        }}
        pre {{
            margin: 0;
            line-height: 1.2;
        }}
        .screenshot {{
            background: #000;
            border: 2px solid #00ffff;
            padding: 10px;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <div class="screenshot">
        <pre>{html_content}</pre>
    </div>
    <p style="color: #888; font-size: 12px; margin-top: 20px;">
        Captured: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    </p>
</body>
</html>"""
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_template)
            
            print(f"📸 HTML screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Failed to save HTML screenshot: {e}")
            return ""
    
    def _ansi_to_html(self, lines: List[str]) -> str:
        """Convert ANSI escape sequences to HTML spans"""
        import re
        
        # ANSI color map
        color_map = {
            '30': '#000000',  # Black
            '31': '#ff0000',  # Red
            '32': '#00ff00',  # Green
            '33': '#ffff00',  # Yellow
            '34': '#0000ff',  # Blue
            '35': '#ff00ff',  # Magenta
            '36': '#00ffff',  # Cyan
            '37': '#ffffff',  # White
        }
        
        html_lines = []
        for line in lines:
            # Remove ANSI sequences and convert to HTML
            # Simplified version - full implementation would parse all ANSI codes
            html_line = line
            
            # Remove ANSI codes (basic)
            html_line = re.sub(r'\x1b\[[0-9;]*m', '', html_line)
            
            # Escape HTML
            html_line = html_line.replace('&', '&amp;')
            html_line = html_line.replace('<', '&lt;')
            html_line = html_line.replace('>', '&gt;')
            
            html_lines.append(html_line)
        
        return '\n'.join(html_lines)
    
    def start_recording(self):
        """Start recording frames for GIF"""
        self.frames = []
        print("🎬 Recording started...")
    
    def capture_frame(self, lines: List[str]):
        """Capture single frame during recording"""
        self.frames.append(self.capture_text_frame(lines))
    
    def stop_recording_and_save(self, filename: Optional[str] = None) -> str:
        """Stop recording and save as multi-frame file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.txt"
        
        filepath = os.path.join(self.config.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for i, frame in enumerate(self.frames):
                    f.write(f"\n{'='*60}\n")
                    f.write(f"Frame {i+1}/{len(self.frames)}\n")
                    f.write(f"{'='*60}\n\n")
                    f.write(frame)
                    f.write("\n")
            
            print(f"🎬 Recording saved: {filepath} ({len(self.frames)} frames)")
            self.frames = []
            return filepath
        except Exception as e:
            print(f"❌ Failed to save recording: {e}")
            return ""
    
    def create_gif(self, filename: Optional[str] = None) -> str:
        """Create animated GIF from frames (requires PIL/Pillow)"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("❌ PIL/Pillow not installed. Install with: pip install Pillow")
            return ""
        
        if not self.frames:
            print("❌ No frames captured")
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"animation_{timestamp}.gif"
        
        filepath = os.path.join(self.config.output_dir, filename)
        
        try:
            # Create images from text frames
            images = []
            
            for frame_text in self.frames:
                # Create image
                img = Image.new('RGB', (self.config.width, self.config.height), color='black')
                draw = ImageDraw.Draw(img)
                
                # Use monospace font
                try:
                    font = ImageFont.truetype("cour.ttf", 12)  # Courier
                except Exception:
                    font = ImageFont.load_default()
                
                # Draw text
                y_offset = 10
                for line in frame_text.split('\n'):
                    # Remove ANSI codes
                    import re
                    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                    draw.text((10, y_offset), clean_line, fill='#00ff00', font=font)
                    y_offset += 15
                
                images.append(img)
            
            # Save as GIF
            if images:
                images[0].save(
                    filepath,
                    save_all=True,
                    append_images=images[1:],
                    duration=int(1000 / self.config.fps),
                    loop=0
                )
                
                print(f"🎞️ GIF created: {filepath} ({len(images)} frames)")
                return filepath
        
        except Exception as e:
            print(f"❌ Failed to create GIF: {e}")
        
        return ""


def integrate_with_simulator(sim_module):
    """
    Integration hook for sim_run.py
    
    Add to sim_run.py main loop:
    
    # Add CLI args
    parser.add_argument('--capture-screenshot', action='store_true', help='Enable screenshot capture (S key)')
    parser.add_argument('--record-gif', action='store_true', help='Enable GIF recording (R key start/stop)')
    
    # In main loop after get_key_nonblocking():
    if args.capture_screenshot and key == 's':
        capture.save_html_screenshot(lines)
    elif args.record_gif and key == 'r':
        if not recording:
            capture.start_recording()
            recording = True
        else:
            capture.stop_recording_and_save()
            capture.create_gif()
            recording = False
    
    # During recording:
    if recording and frame % (args.fps // capture_config.fps) == 0:
        capture.capture_frame(lines)
    """
    pass


if __name__ == '__main__':
    # Demo usage
    print("📸 Screenshot Capture Module")
    print("\nIntegration:")
    print("  1. Add --capture-screenshot flag to sim_run.py")
    print("  2. Press 'S' during simulation to capture screenshot")
    print("  3. Add --record-gif flag for GIF recording")
    print("  4. Press 'R' to start/stop recording")
    print("\nExample:")
    print("  python sim_run.py --capture-screenshot --record-gif")
