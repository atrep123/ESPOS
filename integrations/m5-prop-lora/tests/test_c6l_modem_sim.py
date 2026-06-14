from __future__ import annotations

import re
import struct
import sys
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_SIM_SPEC = importlib.util.spec_from_file_location(
    "m5_preview_c6l_modem", ROOT / "tools" / "preview_c6l_modem.py"
)
assert _SIM_SPEC is not None and _SIM_SPEC.loader is not None
sim = importlib.util.module_from_spec(_SIM_SPEC)
sys.modules[_SIM_SPEC.name] = sim
_SIM_SPEC.loader.exec_module(sim)

MAIN_CPP = ROOT / "firmware/c6l-modem/src/main.cpp"
MODEM_CONFIG_H = ROOT / "firmware/c6l-modem/src/modem_config.h"
MODEM_CORE_H = ROOT / "firmware/c6l-modem/src/modem_core.h"
MODEM_HAL_H = ROOT / "firmware/c6l-modem/src/modem_hal.h"
PROTOCOL_H = ROOT / "shared/protocol/prop_protocol.h"


def _firmware_src() -> str:
    """Modem firmware sources concatenated. Since the Marlin-style config refactor the
    radio/UART knobs live in modem_config.h and the FRAME_*_OFFSET constants + the
    "ERR TX"/"OK TX" host strings live in modem_core.h (single source w/ the host sim),
    so cross-checks must look across all of them, not just main.cpp."""
    return "\n".join(
        p.read_text(encoding="utf-8")
        for p in (MAIN_CPP, MODEM_CONFIG_H, MODEM_CORE_H, MODEM_HAL_H)
    )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _cpp_num(text: str, name: str) -> float | int:
    m = re.search(rf"\b{name}\s*=\s*(0x[0-9A-Fa-f]+|[0-9]+\.[0-9]+|[0-9]+)", text)
    assert m, f"{name} not found in firmware"
    raw = m.group(1)
    if raw.startswith("0x"):
        return int(raw, 16)
    return float(raw) if "." in raw else int(raw)


def frame(
    *,
    ftype: int = 6,
    key: int = 1,
    src: int = 0x10,
    dst: int = 0x20,
    seq: int = 7,
    nonce: int = 0xABCD,
    payload: bytes = b"",
    mac: bytes | None = None,
) -> bytes:
    header = struct.pack(
        ">HBBBBBIQB",
        sim.PROP_FRAME_MAGIC,
        sim.PROP_PROTOCOL_VERSION,
        ftype,
        key,
        src,
        dst,
        seq,
        nonce,
        len(payload),
    )
    return header + payload + (bytes(sim.MAC_LENGTH) if mac is None else mac)


REQUEST = frame(ftype=3, src=0x10, dst=0x20, seq=7, nonce=0xABCD)            # Preview
MATCHING_ACK = frame(ftype=6, src=0x20, dst=0x10, seq=7, nonce=0xABCD)       # swapped src/dst


# --------------------------------------------------------------------------
# firmware <-> sim constant cross-checks
# --------------------------------------------------------------------------
def test_sim_radio_and_uart_constants_match_main_cpp() -> None:
    cpp = _firmware_src()
    assert sim.LORA_FREQUENCY_MHZ == _cpp_num(cpp, "LORA_FREQUENCY_MHZ")
    assert sim.LORA_BANDWIDTH_KHZ == _cpp_num(cpp, "LORA_BANDWIDTH_KHZ")
    assert sim.LORA_SPREADING_FACTOR == _cpp_num(cpp, "LORA_SPREADING_FACTOR")
    assert sim.LORA_CODING_RATE == _cpp_num(cpp, "LORA_CODING_RATE")
    assert sim.LORA_SYNC_WORD == _cpp_num(cpp, "LORA_SYNC_WORD")
    assert sim.LORA_TX_POWER_DBM == _cpp_num(cpp, "LORA_TX_POWER_DBM")
    assert sim.LORA_PREAMBLE_LENGTH == _cpp_num(cpp, "LORA_PREAMBLE_LENGTH")
    assert sim.LORA_TCXO_VOLTAGE == _cpp_num(cpp, "LORA_TCXO_VOLTAGE")
    assert sim.UART_RX_PIN == _cpp_num(cpp, "UART_RX_PIN")
    assert sim.UART_TX_PIN == _cpp_num(cpp, "UART_TX_PIN")
    assert sim.UART_BAUD == _cpp_num(cpp, "UART_BAUD")
    assert sim.ACK_TIMEOUT_MS == _cpp_num(cpp, "ACK_TIMEOUT_MS")


def test_sim_frame_offsets_match_main_cpp() -> None:
    cpp = _firmware_src()
    assert sim.FRAME_TYPE_OFFSET == _cpp_num(cpp, "FRAME_TYPE_OFFSET")
    assert sim.FRAME_KEY_OFFSET == _cpp_num(cpp, "FRAME_KEY_OFFSET")
    assert sim.FRAME_SOURCE_OFFSET == _cpp_num(cpp, "FRAME_SOURCE_OFFSET")
    assert sim.FRAME_DESTINATION_OFFSET == _cpp_num(cpp, "FRAME_DESTINATION_OFFSET")
    assert sim.FRAME_SEQUENCE_OFFSET == _cpp_num(cpp, "FRAME_SEQUENCE_OFFSET")
    assert sim.FRAME_NONCE_OFFSET == _cpp_num(cpp, "FRAME_NONCE_OFFSET")


def test_protocol_constants_match_prop_protocol_h() -> None:
    h = PROTOCOL_H.read_text(encoding="utf-8")
    assert sim.PROP_FRAME_MAGIC == _cpp_num(h, "PROP_FRAME_MAGIC")
    assert sim.PROP_PROTOCOL_VERSION == _cpp_num(h, "PROP_PROTOCOL_VERSION")
    assert sim.MAC_LENGTH == _cpp_num(h, "MAC_LENGTH")
    assert sim.HEADER_LENGTH == _cpp_num(h, "HEADER_LENGTH")
    assert sim.MAX_RADIO_FRAME == _cpp_num(h, "HEADER_LENGTH") + _cpp_num(h, "MAX_PAYLOAD_LENGTH") + _cpp_num(h, "MAC_LENGTH")
    # FrameType::Ack = 6 in the header enum.
    assert int(sim.FrameType.ACK) == 6
    assert re.search(r"Ack\s*=\s*6", h)


def test_firmware_emits_uppercase_hex_and_sim_matches() -> None:
    # prop_protocol::nibbleToHex uses 'A' + (nibble-10) -> UPPERCASE hex output.
    h = PROTOCOL_H.read_text(encoding="utf-8")
    assert "'A' + (nibble - 10)" in h
    assert sim.bytes_to_hex(b"\xab\xcd\x0f") == "ABCD0F"
    assert sim.bytes_to_hex(b"\xab\xcd\x0f") != b"\xab\xcd\x0f".hex()  # not lowercase


def test_host_response_strings_present_in_firmware() -> None:
    cpp = _firmware_src()
    for literal in (
        "OK C6L_MODEM",
        "ERR BAD_COMMAND",
        "ERR LINE_TOO_LONG",
        "ERR BAD_FRAME",
        "ERR RADIO_NOT_READY",
        "ERR ACK_TIMEOUT",
        "OK TX",
        "ERR TX ",
        "RX ",
        "BOOT C6L_MODEM 115200",
        "OK RADIO_READY",
        "ERR RADIO_INIT",
        "__LINE_TOO_LONG__",
    ):
        assert literal in cpp, literal


# --------------------------------------------------------------------------
# host command/response protocol
# --------------------------------------------------------------------------
def test_ping_and_unknown_command() -> None:
    assert sim.process_host_line("PING", radio_ready=True) == ["OK C6L_MODEM"]
    assert sim.process_host_line("NONSENSE", radio_ready=True) == ["ERR BAD_COMMAND"]
    assert sim.process_host_line("", radio_ready=True) == ["ERR BAD_COMMAND"]


def test_line_too_long_sentinel() -> None:
    assert sim.process_host_line(sim.LINE_TOO_LONG, radio_ready=True) == ["ERR LINE_TOO_LONG"]


def test_boot_lines() -> None:
    assert sim.boot_lines(True) == ["BOOT C6L_MODEM 115200", "OK RADIO_READY"]
    assert sim.boot_lines(False) == ["BOOT C6L_MODEM 115200", "ERR RADIO_INIT"]


@pytest.mark.parametrize("cmd", ["SEND ", "ACK "])
def test_bad_frame_on_unparseable_hex(cmd: str) -> None:
    assert sim.process_host_line(cmd + "zz", radio_ready=True) == ["ERR BAD_FRAME"]      # invalid hex
    assert sim.process_host_line(cmd + "abc", radio_ready=True) == ["ERR BAD_FRAME"]     # odd length
    assert sim.process_host_line(cmd + "", radio_ready=True) == ["ERR BAD_FRAME"]        # empty frame
    assert sim.process_host_line(cmd + "00" * (sim.MAX_RADIO_FRAME + 1), radio_ready=True) == ["ERR BAD_FRAME"]


def test_radio_not_ready_blocks_send_and_ack() -> None:
    assert sim.process_host_line("SEND " + REQUEST.hex(), radio_ready=False) == ["ERR RADIO_NOT_READY"]
    assert sim.process_host_line("ACK " + REQUEST.hex(), radio_ready=False) == ["ERR RADIO_NOT_READY"]


def test_tx_failure_reports_err_tx_with_code() -> None:
    assert sim.process_host_line("ACK " + REQUEST.hex(), radio_ready=True, tx_ok=False, tx_err_code=7) == ["ERR TX 7"]
    assert sim.process_host_line("SEND " + REQUEST.hex(), radio_ready=True, tx_ok=False, tx_err_code=-2) == ["ERR TX -2"]


def test_ack_command_transmits_and_reports_ok_tx() -> None:
    assert sim.process_host_line("ACK " + REQUEST.hex(), radio_ready=True) == ["OK TX"]


def test_send_with_matching_ack_emits_rx_then_returns() -> None:
    out = sim.process_host_line("SEND " + REQUEST.hex(), radio_ready=True, incoming=[MATCHING_ACK])
    assert out == [f"RX -80.0 9.0 {sim.bytes_to_hex(MATCHING_ACK)}"]
    # RX hex MUST be uppercase (firmware bytesToHex).
    assert out[0].split(" ", 3)[3] == out[0].split(" ", 3)[3].upper()


def test_send_with_no_ack_times_out() -> None:
    assert sim.process_host_line("SEND " + REQUEST.hex(), radio_ready=True, incoming=[]) == ["ERR ACK_TIMEOUT"]


def test_send_with_nonmatching_then_matching_ack() -> None:
    wrong = frame(ftype=6, src=0x99, dst=0x88, seq=7, nonce=0xABCD)  # wrong src/dst
    out = sim.process_host_line("SEND " + REQUEST.hex(), radio_ready=True, incoming=[wrong, MATCHING_ACK])
    assert out == [
        f"RX -80.0 9.0 {sim.bytes_to_hex(wrong)}",
        f"RX -80.0 9.0 {sim.bytes_to_hex(MATCHING_ACK)}",
    ]


def test_send_with_only_nonmatching_acks_times_out() -> None:
    wrong = frame(ftype=6, src=0x99, dst=0x88, seq=7, nonce=0xABCD)
    out = sim.process_host_line("SEND " + REQUEST.hex(), radio_ready=True, incoming=[wrong])
    assert out == [f"RX -80.0 9.0 {sim.bytes_to_hex(wrong)}", "ERR ACK_TIMEOUT"]


# --------------------------------------------------------------------------
# line framing (readHostLine)
# --------------------------------------------------------------------------
def test_frame_host_lines_basic_cr_lf_trim() -> None:
    assert sim.frame_host_lines("PING\n") == ["PING"]
    assert sim.frame_host_lines("PING\r\n") == ["PING"]
    assert sim.frame_host_lines("  PING  \r\n") == ["PING"]
    assert sim.frame_host_lines("A\nB\n") == ["A", "B"]


def test_frame_host_lines_ignores_unterminated_remainder() -> None:
    assert sim.frame_host_lines("PING") == []            # no newline yet -> buffered
    assert sim.frame_host_lines("A\nB") == ["A"]          # B unterminated


def test_frame_host_lines_skips_empty_lines() -> None:
    assert sim.frame_host_lines("\n\nPING\n\n") == ["PING"]


def test_frame_host_lines_overflow_boundary_and_continue() -> None:
    assert sim.frame_host_lines("x" * 256 + "\n") == ["x" * 256]            # 256 OK
    assert sim.frame_host_lines("x" * 257 + "\n") == [sim.LINE_TOO_LONG]    # 257 -> sentinel
    # overflow does not stop processing of later lines
    assert sim.frame_host_lines("x" * 300 + "\nPING\n") == [sim.LINE_TOO_LONG, "PING"]


# --------------------------------------------------------------------------
# parse_hex_arg / hex_to_bytes
# --------------------------------------------------------------------------
def test_parse_hex_arg_rules() -> None:
    assert sim.parse_hex_arg("SEND 504C", "SEND ") == b"\x50\x4c"
    assert sim.parse_hex_arg("WRONG 504C", "SEND ") is None     # prefix mismatch
    assert sim.parse_hex_arg("SEND abc", "SEND ") is None       # odd length
    assert sim.parse_hex_arg("SEND zz", "SEND ") is None        # invalid char
    assert sim.parse_hex_arg("SEND AA BB", "SEND ") is None     # embedded whitespace rejected
    assert sim.parse_hex_arg("SEND ", "SEND ") is None          # empty
    assert sim.parse_hex_arg("SEND " + "00" * (sim.MAX_RADIO_FRAME + 1), "SEND ") is None  # too long
    assert sim.parse_hex_arg("SEND " + "00" * sim.MAX_RADIO_FRAME, "SEND ") == bytes(sim.MAX_RADIO_FRAME)


def test_hex_to_bytes_accepts_mixed_case() -> None:
    assert sim.hex_to_bytes("aAbB") == b"\xaa\xbb"
    assert sim.hex_to_bytes("XY") is None
    assert sim.hex_to_bytes("abc") is None


# --------------------------------------------------------------------------
# has_protocol_header / looks_like_matching_ack
# --------------------------------------------------------------------------
def test_has_protocol_header_bounds_magic_version() -> None:
    assert sim.has_protocol_header(REQUEST) is True
    assert sim.has_protocol_header(REQUEST[:-1]) is False                       # too short (no full mac)
    assert sim.has_protocol_header(b"\x00\x00" + REQUEST[2:]) is False          # wrong magic
    bad_ver = bytearray(REQUEST); bad_ver[2] = 0xFF  # any value != PROP_PROTOCOL_VERSION (now 2)
    assert sim.has_protocol_header(bytes(bad_ver)) is False                     # wrong version
    assert sim.has_protocol_header(frame(payload=b"\x00" * 65)) is False        # > MAX_RADIO_FRAME


def test_looks_like_matching_ack_accepts_valid_pair() -> None:
    assert sim.looks_like_matching_ack(REQUEST, MATCHING_ACK) is True


@pytest.mark.parametrize(
    "bad",
    [
        frame(ftype=3, src=0x20, dst=0x10, seq=7, nonce=0xABCD),   # not an ACK type
        frame(ftype=6, key=9, src=0x20, dst=0x10, seq=7, nonce=0xABCD),  # wrong key
        frame(ftype=6, src=0x10, dst=0x20, seq=7, nonce=0xABCD),   # src/dst not swapped
        frame(ftype=6, src=0x20, dst=0x10, seq=8, nonce=0xABCD),   # wrong sequence
        frame(ftype=6, src=0x20, dst=0x10, seq=7, nonce=0x1234),   # wrong nonce
    ],
)
def test_looks_like_matching_ack_rejects(bad: bytes) -> None:
    assert sim.looks_like_matching_ack(REQUEST, bad) is False


def test_looks_like_matching_ack_rejects_headerless() -> None:
    assert sim.looks_like_matching_ack(REQUEST, b"\x00" * 32) is False
    assert sim.looks_like_matching_ack(b"\x00" * 32, MATCHING_ACK) is False
