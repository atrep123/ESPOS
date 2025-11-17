# Icon Design Guidelines (Monochrome OLED)

These recommendations help ensure icons render crisply and legibly on small 1bpp displays.

## Size & Grid

- Prefer 16×16 px for 128×64 OLED; use 24×24 px for larger screens.
- Align strokes to whole pixels to avoid blur on 1bpp.
- Maintain consistent padding: keep 1–2 px margin inside the bounding box.

## Strokes & Contrast

- Use bold silhouettes; avoid hairline strokes under 1 px.
- Favor filled shapes with subtractive cutouts instead of outlines.
- Avoid diagonals with long shallow slopes; prefer 45° or orthogonal segments.

## Visual Weight & Balance

- Keep average black coverage similar across the set to avoid visual jumps.
- Center content optically, not just geometrically (account for glyph shapes).

## Clarity & Metaphors

- Choose universally recognized metaphors (home, folder, search, lock, etc.).
- Avoid letter-dependent glyphs unless necessary (e.g., PDF, JS) and keep them bold.

## Inversion & States

- Ensure icons remain readable when inverted (white-on-black) using `invert=true`.
- For stateful icons (e.g., battery, volume), keep progress or state marks thick and distinct.

## Export & Verification

- Preview icons at 1×, 2×, and 4× zoom to catch aliasing issues.
- Test in simulator using ASCII fallbacks to verify semantics and layout.
- When converting to 1bpp, review packed bitmaps for gaps and unintended holes.

## Accessibility

- Pair icons with text where space allows; never rely on color alone.
- Maintain sufficient spacing around tap targets (minimum 24 px square recommended on touch displays).
