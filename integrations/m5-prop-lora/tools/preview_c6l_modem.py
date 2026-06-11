"""Deterministic desktop model of the c6l-modem UART<->LoRa bridge host protocol.

Mirrors firmware/c6l-modem/src/main.cpp closely enough for pytest to catch drift
in: the host-line command/response protocol, line framing (readHostLine), hex-arg
parsing (parseHexArg / hexToBytes), and ACK matching (looksLikeMatchingAck). The
c6l-modem has NO display; radio outcomes are injected so the model stays
deterministic.

NOTE on provenance: drafted by a local model (qwen2.5-coder:32b) then corrected
against the firmware (the draft had a wrong import that fell back to bad constants,
lowercase RX hex, break-on-overflow framing, and whitespace-tolerant hex parsing).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from shared.protocol.protocol import (  # noqa: E402
        MAC_LENGTH,
        MAGIC as PROP_FRAME_MAGIC,
        MAX_FRAME_LENGTH,
        HEADER_LENGTH,
        VERSION as PROP_PROTOCOL_VERSION,
        FrameType,
    )
except ImportError:  # defensive fallbacks mirror prop_protocol.h EXACTLY
    MAX_FRAME_LENGTH = 96
    HEADER_LENGTH = 20
    MAC_LENGTH = 12
    PROP_FRAME_MAGIC = 0x504C
    PROP_PROTOCOL_VERSION = 1

    class FrameType:  # type: ignore[no-redef]
        ACK = 6


# LoRa radio config (must match firmware constants in modem_config.h).
LORA_FREQUENCY_MHZ = 868.1
LORA_BANDWIDTH_KHZ = 250.0   # L2: faster (was 125) -> shorter airtime
LORA_SPREADING_FACTOR = 7    # L2: faster (was 8) -> shorter airtime
LORA_CODING_RATE = 5
LORA_SYNC_WORD = 0x34
LORA_TX_POWER_DBM = 13
LORA_PREAMBLE_LENGTH = 8     # L2: shorter preamble (was 12)
LORA_TCXO_VOLTAGE = 3.0
UART_RX_PIN = 5
UART_TX_PIN = 4
UART_BAUD = 115200
ACK_TIMEOUT_MS = 900

# Frame field offsets (must match main.cpp).
FRAME_TYPE_OFFSET = 3
FRAME_KEY_OFFSET = 4
FRAME_SOURCE_OFFSET = 5
FRAME_DESTINATION_OFFSET = 6
FRAME_SEQUENCE_OFFSET = 7
FRAME_NONCE_OFFSET = 11

MAX_RADIO_FRAME = MAX_FRAME_LENGTH
HOST_LINE_MAX = 256
LINE_TOO_LONG = "__LINE_TOO_LONG__"

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def bytes_to_hex(frame: bytes) -> str:
    """Uppercase hex, matching firmware prop_protocol::bytesToHex (nibbleToHex)."""
    return frame.hex().upper()


def hex_to_bytes(hex_str: str) -> bytes | None:
    """Strict hex decode mirroring prop_protocol::hexToBytes.

    Even length required; only [0-9a-fA-F] permitted (NO embedded whitespace,
    unlike ``bytes.fromhex``). Returns None on any violation.
    """
    if len(hex_str) % 2 != 0:
        return None
    if any(c not in _HEX_DIGITS for c in hex_str):
        return None
    return bytes.fromhex(hex_str)


def u32_be(frame: bytes, offset: int) -> int:
    return int.from_bytes(frame[offset:offset + 4], "big")


def frame_host_lines(raw: str) -> list[str]:
    """Split a raw host stream into completed lines, mirroring readHostLine.

    '\\r' is dropped; '\\n' terminates a line; a completed line is trimmed; a line
    whose non-CR length exceeds 256 chars becomes the LINE_TOO_LONG sentinel
    (processing continues for later lines). Only \\n-terminated lines are returned
    (a trailing unterminated remainder is still buffered in firmware, so it is
    ignored here). Empty completed lines yield no entry (the firmware loop skips
    zero-length host lines).
    """
    completed = raw.split("\n")[:-1]
    out: list[str] = []
    for line in completed:
        without_cr = line.replace("\r", "")
        if len(without_cr) > HOST_LINE_MAX:
            out.append(LINE_TOO_LONG)
            continue
        trimmed = without_cr.strip()
        if trimmed:
            out.append(trimmed)
    return out


def parse_hex_arg(line: str, prefix: str) -> bytes | None:
    """Mirror parseHexArg: prefix match, strict hex, non-empty, <= MAX_RADIO_FRAME."""
    if not line.startswith(prefix):
        return None
    decoded = hex_to_bytes(line[len(prefix):].strip())
    if decoded is None or len(decoded) == 0 or len(decoded) > MAX_RADIO_FRAME:
        return None
    return decoded


def has_protocol_header(frame: bytes) -> bool:
    return (
        len(frame) >= HEADER_LENGTH + MAC_LENGTH
        and len(frame) <= MAX_RADIO_FRAME
        and int.from_bytes(frame[0:2], "big") == PROP_FRAME_MAGIC
        and frame[2] == PROP_PROTOCOL_VERSION
    )


def looks_like_matching_ack(request: bytes, candidate: bytes) -> bool:
    if not has_protocol_header(request) or not has_protocol_header(candidate):
        return False
    if candidate[FRAME_TYPE_OFFSET] != int(FrameType.ACK):
        return False
    return (
        candidate[FRAME_KEY_OFFSET] == request[FRAME_KEY_OFFSET]
        and candidate[FRAME_SOURCE_OFFSET] == request[FRAME_DESTINATION_OFFSET]
        and candidate[FRAME_DESTINATION_OFFSET] == request[FRAME_SOURCE_OFFSET]
        and u32_be(candidate, FRAME_SEQUENCE_OFFSET) == u32_be(request, FRAME_SEQUENCE_OFFSET)
        and candidate[FRAME_NONCE_OFFSET:FRAME_NONCE_OFFSET + 8]
        == request[FRAME_NONCE_OFFSET:FRAME_NONCE_OFFSET + 8]
    )


def _rx_line(rssi: float, snr: float, frame: bytes) -> str:
    # Firmware: "RX " + String(rssi,1) + " " + String(snr,1) + " " + hex(UPPER).
    return f"RX {rssi:.1f} {snr:.1f} {bytes_to_hex(frame)}"


def boot_lines(radio_ready: bool) -> list[str]:
    """Mirror setup(): the host-link boot banner + radio status line."""
    return ["BOOT C6L_MODEM 115200", "OK RADIO_READY" if radio_ready else "ERR RADIO_INIT"]


def process_host_line(
    line: str,
    *,
    radio_ready: bool,
    tx_ok: bool = True,
    tx_err_code: int = 0,
    incoming: list[bytes] | None = None,
    rssi: float = -80.0,
    snr: float = 9.0,
) -> list[str]:
    """Deterministic model of handleHostLine + sendRadioFrame + sendAndWaitForAck.

    Returns the exact host response line(s) the firmware would emit.
    """
    if line == LINE_TOO_LONG:
        return ["ERR LINE_TOO_LONG"]
    if line.startswith("SEND "):
        frame = parse_hex_arg(line, "SEND ")
        if frame is None:
            return ["ERR BAD_FRAME"]
        if not radio_ready:
            return ["ERR RADIO_NOT_READY"]
        if not frame or len(frame) > MAX_RADIO_FRAME:
            return ["ERR BAD_FRAME"]
        if not tx_ok:
            return [f"ERR TX {tx_err_code}"]
        out: list[str] = []
        for candidate in incoming or []:
            out.append(_rx_line(rssi, snr, candidate))
            if looks_like_matching_ack(frame, candidate):
                return out
        out.append("ERR ACK_TIMEOUT")
        return out
    if line.startswith("ACK "):
        frame = parse_hex_arg(line, "ACK ")
        if frame is None:
            return ["ERR BAD_FRAME"]
        if not radio_ready:
            return ["ERR RADIO_NOT_READY"]
        if not frame or len(frame) > MAX_RADIO_FRAME:
            return ["ERR BAD_FRAME"]
        if not tx_ok:
            return [f"ERR TX {tx_err_code}"]
        return ["OK TX"]
    if line == "PING":
        return ["OK C6L_MODEM"]
    return ["ERR BAD_COMMAND"]


def _demo_frame(ftype: int, key: int, src: int, dst: int, seq: int, nonce: int) -> bytes:
    import struct

    header = struct.pack(
        ">HBBBBBIQB", PROP_FRAME_MAGIC, PROP_PROTOCOL_VERSION, ftype, key, src, dst, seq, nonce, 0
    )
    return header + bytes(MAC_LENGTH)


if __name__ == "__main__":
    print("boot       ->", boot_lines(True))
    print("PING       ->", process_host_line("PING", radio_ready=True))
    print("bad cmd    ->", process_host_line("NONSENSE", radio_ready=True))
    req = _demo_frame(3, 1, 0x10, 0x20, 7, 0xABCD)
    ack = _demo_frame(int(FrameType.ACK), 1, 0x20, 0x10, 7, 0xABCD)
    print("SEND+ack   ->", process_host_line("SEND " + req.hex(), radio_ready=True, incoming=[ack]))
    print("SEND+miss  ->", process_host_line("SEND " + req.hex(), radio_ready=True, incoming=[]))
    print("ACK ok     ->", process_host_line("ACK " + req.hex(), radio_ready=True))
    print("SEND nordy ->", process_host_line("SEND " + req.hex(), radio_ready=False))
