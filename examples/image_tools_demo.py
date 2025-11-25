#!/usr/bin/env python3
"""
Praktické příklady použití image tools pro ESPOS.

Tento soubor ukazuje nejčastější workflow:
1. Načtení obrázku/ikony
2. Dithering a převod na XBM
3. Deduplikace pro úsporu paměti
4. Export do C kódu
"""

from PIL import Image

from tools.bdf_font_export import export_font_subset
from tools.image_dithering import image_to_xbm
from tools.xbm_utils import xbm_pixelate, xbm_scale, xbm_to_ascii
from tools.xbmp_dedup import XBMPManager


# ============================================================
# PŘÍKLAD 1: Převod PNG ikony na C kód
# ============================================================
def example_1_convert_icon():
    """Nejjednodušší workflow: PNG → dithering → C kód"""
    print("=" * 60)
    print("PŘÍKLAD 1: Převod PNG ikony na C kód")
    print("=" * 60)
    
    # 1. Načti obrázek (můžeš použít jakýkoli PNG/JPG/BMP)
    # image = Image.open("icons/wifi.png").convert("L")
    
    # Pro demo vytvoříme testovací gradientový obrázek
    pixels = [[int(x * 255 / 32) for x in range(32)] for _ in range(32)]
    
    # 2. Převeď na XBM s ditheragem
    width, height, bitmap = image_to_xbm(
        pixels, 32, 32, 
        dither_method="floyd-steinberg"
    )
    
    # 3. Zobraz ASCII preview
    from tools.xbm_utils import xbm_to_ascii
    print(f"\nVýsledek ({width}x{height}):")
    print(xbm_to_ascii(bitmap, width, height))
    
    # 4. Vygeneruj C kód
    print("\nC kód pro ESPOS:")
    print(f"static const uint8_t wifi_icon_{width}x{height}[] = {{")
    for i, byte in enumerate(bitmap):
        if i % 12 == 0:
            print("    ", end="")
        print(f"0x{byte:02x}", end="")
        if i < len(bitmap) - 1:
            print(", ", end="")
        if (i + 1) % 12 == 0:
            print()
    print("\n};")
    
    return bitmap, width, height


# ============================================================
# PŘÍKLAD 2: Deduplikace více ikon (šetří paměť)
# ============================================================
def example_2_deduplicate_icons():
    """Více ikon s automatickou deduplikací"""
    print("\n" + "=" * 60)
    print("PŘÍKLAD 2: Deduplikace ikon (šetří 30-50% paměti)")
    print("=" * 60)
    
    xbmp = XBMPManager(default_dither="floyd-steinberg")
    
    # Simulace načtení více ikon
    # V reálu bys použil: Image.open("icon1.png")
    
    # Přidej několik ikon (některé duplikáty)
    pixels1 = [[int(x * 255 / 16) for x in range(16)] for _ in range(16)]
    pixels2 = [[int(y * 255 / 16) for _ in range(16)] for y in range(16)]  # jiná
    pixels3 = [[int(x * 255 / 16) for x in range(16)] for _ in range(16)]   # duplicita!
    
    from PIL import Image
    img1 = Image.new("L", (16, 16))
    img1.putdata([p for row in pixels1 for p in row])
    
    img2 = Image.new("L", (16, 16))
    img2.putdata([p for row in pixels2 for p in row])
    
    img3 = Image.new("L", (16, 16))
    img3.putdata([p for row in pixels3 for p in row])
    
    # Přidej do správce (automaticky deduplikuje)
    xbmp.add_icon_from_pil(img1)
    xbmp.add_icon_from_pil(img2)
    xbmp.add_icon_from_pil(img3)  # bude ukazovat na img1
    
    print("\nPřidáno ikon: 3")
    print(f"Unikátních bitmap: {len(xbmp.bitmaps)}")
    print(f"Úspora paměti: {(1 - len(xbmp.bitmaps)/3)*100:.0f}%")
    
    # Vygeneruj C kód
    c_code = xbmp.generate_c_code()
    print("\nVygenerovaný C kód:")
    print(c_code[:500] + "...\n")  # ukáž začátek
    
    return xbmp


# ============================================================
# PŘÍKLAD 3: BDF font rendering
# ============================================================
def example_3_render_text():
    """Vykreslení textu pomocí BDF fontu"""
    print("\n" + "=" * 60)
    print("PŘÍKLAD 3: Vykreslení textu BDF fontem")
    print("=" * 60)
    
    # Pro demo použijeme vestavěný testovací font
    from tools.bdf_font import create_simple_font
    font = create_simple_font()
    
    # V reálu načteš BDF soubor:
    # font = BDFFont.load("fonts/5x7.bdf")
    
    # Vykresli text
    text = "ABC"
    width, height, bitmap = font.render_text(text, spacing=1)
    
    print(f"\nText: '{text}'")
    print(f"Velikost: {width}x{height} px")
    print("\nASCII preview:")
    from tools.xbm_utils import xbm_to_ascii
    print(xbm_to_ascii(bitmap, width, height))
    
    # Export jako C kód (pouze použité znaky!)
    c_code = export_font_subset(font, text, "my_font")
    print("\nC kód (ukázka):")
    print(c_code[:400] + "...\n")
    
    return font, bitmap


# ============================================================
# PŘÍKLAD 4: Bitmap efekty (pixelate, scale, rotate)
# ============================================================
def example_4_bitmap_effects():
    """Různé efekty na XBM bitmap"""
    print("\n" + "=" * 60)
    print("PŘÍKLAD 4: Bitmap efekty")
    print("=" * 60)
    
    from tools.xbm_utils import xbm_rotate_90
    
    # Vytvoř testovací bitmap
    pixels = [[int(x * 255 / 16) for x in range(16)] for _ in range(16)]
    width, height, bitmap = image_to_xbm(pixels, 16, 16, "floyd-steinberg")
    
    print("\nOriginál (16x16):")
    print(xbm_to_ascii(bitmap, width, height))
    
    # Efekt 1: Pixelate (mosaic)
    pixelated = xbm_pixelate(bitmap, width, height, pixel_size=4)
    print("\nPixelated (4px bloky):")
    print(xbm_to_ascii(pixelated, width, height))
    
    # Efekt 2: Scale 2x
    scaled, sw, sh = xbm_scale(bitmap, width, height, scale_x=2, scale_y=2)
    print(f"\nScaled 2x ({sw}x{sh}):")
    print(xbm_to_ascii(scaled, sw, sh))
    
    # Efekt 3: Rotate 90°
    rotated, rw, rh = xbm_rotate_90(bitmap, width, height)
    print(f"\nRotated 90° ({rw}x{rh}):")
    print(xbm_to_ascii(rotated, rw, rh))


# ============================================================
# PŘÍKLAD 5: Kompletní workflow pro UI Designer
# ============================================================
def example_5_complete_workflow():
    """Kompletní workflow: ikony + text → C kód pro ESPOS"""
    print("\n" + "=" * 60)
    print("PŘÍKLAD 5: Kompletní workflow pro UI Designer")
    print("=" * 60)
    
    # 1. Připrav ikony s deduplikací
    xbmp = XBMPManager(default_dither="floyd-steinberg")
    
    # V reálu:
    # for icon_path in Path("ui/icons").glob("*.png"):
    #     img = Image.open(icon_path).resize((16, 16))
    #     xbmp.add_icon_from_pil(img, name=icon_path.stem)
    
    # Demo: 3 ikony
    for _, horizontal in enumerate([True, False, True]):
        if horizontal:
            pixels = [[int(x * 255 / 16) for x in range(16)] for _ in range(16)]
        else:
            pixels = [[int(y * 255 / 16) for _ in range(16)] for y in range(16)]
        img = Image.new("L", (16, 16))
        img.putdata([p for row in pixels for p in row])
        xbmp.add_icon_from_pil(img)
    
    # 2. Připrav font
    from tools.bdf_font import create_simple_font
    font = create_simple_font()
    # V reálu: font = BDFFont.load("fonts/terminus-12.bdf")
    
    # 3. Vygeneruj C kód
    print("\n// ===== ui_assets.h =====")
    print("#pragma once")
    print("#include <stdint.h>\n")
    
    # Ikony
    print("// Bitmap ikony (deduplikované)")
    print(xbmp.generate_c_code())
    
    # Font
    print("\n// Font pro text")
    font_code = export_font_subset(font, "ABC", "ui_font")
    print(font_code[:300] + "...\n")
    
    print(f"\n✅ Hotovo! Unikátních bitmap: {len(xbmp.bitmaps)}")
    print(f"   Úspora paměti: {(1 - len(xbmp.bitmaps)/3)*100:.0f}%")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("\n" + "🎨" * 30)
    print("ESPOS Image Tools - Praktické příklady")
    print("🎨" * 30)
    
    # Spusť všechny příklady
    example_1_convert_icon()
    example_2_deduplicate_icons()
    example_3_render_text()
    example_4_bitmap_effects()
    example_5_complete_workflow()
    
    print("\n" + "=" * 60)
    print("✅ Všechny příklady dokončeny!")
    print("=" * 60)
    print("\nDalší kroky:")
    print("1. Zkopíruj příklad, který potřebuješ")
    print("2. Uprav cesty k obrázkům/fontům")
    print("3. Spusť: python examples/image_tools_demo.py")
    print("4. C kód zkopíruj do svého projektu")
    print("\nDokumentace: docs/IMAGE_TOOLS_README.md")
