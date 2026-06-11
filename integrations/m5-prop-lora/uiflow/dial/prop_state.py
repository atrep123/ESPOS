# prop_state.py -- pure persistence logic for the UIFlow2 Dial app (main.py).
#
# PURPOSE
# -------
# Decides *what* the Dial UI persists across a reboot:
#   * the tuned per-LED palette (hues), so a power-cycle doesn't reset colours, and
#   * the frame sequence high-water, so the monotonic counter never goes backwards.
#
# WHY A SEPARATE MODULE
#   Like prop_frame.py, this file has NO hardware/NVS imports, so it is unit-tested
#   on CPython (tests/test_uiflow_prop_state.py) -- the same "prove the logic, then
#   verify the thin device layer on hardware" split the PoC uses everywhere.
#   main.py supplies the actual esp32.NVS read/write; this module only decides the
#   bytes (palette codec) and the integers (sequence reservation maths).
#
# FLASH WEAR
#   ESP32 NVS lives in flash with a finite erase budget. Writing the sequence on
#   *every* frame would burn it out. Instead we reserve a BLOCK of sequence numbers
#   per write (seq_next_reservation): one NVS write buys SEQ_RESERVE_BLOCK frames,
#   and on reboot we resume one past the last reservation so a number is never
#   reused -- even if power was lost mid-block. Palette writes are naturally rare
#   (only when the operator leaves the NASTAVENI edit screen).

SEQ_RESERVE_BLOCK = 64   # sequence numbers claimed per NVS write (flash-wear budget)


# ---------------------------------------------------------------------------
# Palette codec  (hue is 0..359 -> needs 2 bytes; 1 byte would clip >255)
# ---------------------------------------------------------------------------
def hues_to_blob(hues):
    """Pack a hue list big-endian, 2 bytes per hue. Inverse of blob_to_hues()."""
    out = bytearray()
    for h in hues:
        h = int(h) & 0xFFFF
        out.append((h >> 8) & 0xFF)
        out.append(h & 0xFF)
    return bytes(out)


def blob_to_hues(blob, count):
    """Unpack `count` hues from a 2-byte-each blob, each normalised to 0..359.

    Returns None when the blob is missing or shorter than expected, so the caller
    cleanly falls back to the factory palette."""
    if not blob or len(blob) < count * 2:
        return None
    return [(((blob[2 * i] << 8) | blob[2 * i + 1]) % 360) for i in range(count)]


# ---------------------------------------------------------------------------
# Sequence reservation  (monotonic counter that survives reboot, flash-friendly)
# ---------------------------------------------------------------------------
def seq_resume_from(saved_reservation):
    """Boot start value: one past the last RESERVED high-water (never reuse a
    number). A missing/zero/garbage reservation means "first boot" -> start at 1,
    matching PropSender's default."""
    try:
        saved = int(saved_reservation)
    except (TypeError, ValueError):
        return 1
    return saved + 1 if saved > 0 else 1


def seq_next_reservation(current_seq, reserved_until, block=SEQ_RESERVE_BLOCK):
    """Decide whether a fresh block of sequence numbers must be reserved.

    Returns (new_reserved_until, should_write):
      * should_write True  -> the counter has caught up to the reservation; claim
        a new block (current_seq + block) and persist new_reserved_until.
      * should_write False -> still inside the reserved block; keep it, no NVS write.
    """
    if current_seq >= reserved_until:
        return current_seq + block, True
    return reserved_until, False
