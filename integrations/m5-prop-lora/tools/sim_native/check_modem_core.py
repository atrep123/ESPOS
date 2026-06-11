"""Host cross-validation of the extracted modem_core decision logic.

Builds modem_abi.dll (firmware/c6l-modem/src/modem_core.h compiled via zig),
ctypes-loads it, and verifies the safety-critical ACK matching + header check
behave correctly off-device -- identical logic to what runs on the ESP32-C6.
The intent is to catch any future drift if main.cpp/modem_core.h is edited.
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DLL = HERE / "modem_abi.dll"

# Bring the Python protocol mirror onto the path (used to build firmware-faithful
# test frames -- already proven byte-identical to the C++ encoder by the parity check).
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "shared" / "protocol"))
import protocol as PY  # type: ignore  # noqa: E402

SHARED_KEY = bytes(range(0x00, 0x100, 0x11))[:16]  # {0x00,0x11,0x22,...,0xFF} -- firmware SHARED_KEY
KEYS = {1: SHARED_KEY}

# --- Callback HAL CFUNCTYPE signatures (must match the typedefs in modem_abi.cpp) ---
# data/mac pointers are passed as c_void_p; read with ctypes.string_at(ptr, n), write
# with ctypes.memmove(ptr, bytes, n). Keep created CFUNCTYPE instances alive (ctypes
# does NOT hold a reference once passed to C) or the callbacks get GC'd mid-run.
CB_NOW_MS = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p)
CB_WRITE_LINE = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)
CB_START_TX = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int)
CB_ESP_SEND = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int)
CB_ESP_ADD_PEER = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
CB_ESP_DEL_PEER = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)
CB_ESP_POLL_RX = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int)


def build_dll() -> None:
    """Compile modem_abi.cpp + sha256.c + md_shim.c via ziglang into a host DLL."""
    cache_root = Path.home() / ".codex" / "memories" / "zig-cache-sim-native"
    (cache_root / "global").mkdir(parents=True, exist_ok=True)
    (cache_root / "local").mkdir(parents=True, exist_ok=True)
    build_dll_path = cache_root / "modem_abi_build.dll"
    cmd = [
        sys.executable, "-m", "ziglang", "c++",
        "-shared", "-O2", "-std=c++17", "-Wno-nullability-completeness",
        "-I", "shared/protocol",
        "-I", "tools/sim_native/shim",
        "-I", "firmware/c6l-modem/src",
        "-x", "c++",
        "tools/sim_native/modem_abi.cpp",
        "tools/sim_native/sha256.c",
        "tools/sim_native/md_shim.c",
        "-o", str(build_dll_path),
    ]
    env = os.environ.copy()
    env.setdefault("ZIG_GLOBAL_CACHE_DIR", str(cache_root / "global"))
    env.setdefault("ZIG_LOCAL_CACHE_DIR", str(cache_root / "local"))
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, env=env)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    shutil.copy2(build_dll_path, DLL)
    print(f"OK {DLL}")


def load_dll() -> ctypes.CDLL:
    if not DLL.exists():
        build_dll()
    lib = ctypes.CDLL(str(DLL))
    lib.mc_has_protocol_header.restype = ctypes.c_bool
    lib.mc_has_protocol_header.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.mc_looks_like_matching_ack.restype = ctypes.c_bool
    lib.mc_looks_like_matching_ack.argtypes = [
        ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
    ]
    # DutyBucket (opaque buffer ABI: host allocs sizeof bytes, mc_duty_init places one in it).
    lib.mc_duty_sizeof.restype = ctypes.c_int
    lib.mc_duty_sizeof.argtypes = []
    lib.mc_duty_init.restype = None
    lib.mc_duty_init.argtypes = [ctypes.c_void_p]
    lib.mc_duty_drain.restype = None
    lib.mc_duty_drain.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mc_duty_would_exceed.restype = ctypes.c_bool
    lib.mc_duty_would_exceed.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mc_duty_add.restype = None
    lib.mc_duty_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mc_duty_bucket_ms.restype = ctypes.c_float
    lib.mc_duty_bucket_ms.argtypes = [ctypes.c_void_p]
    lib.mc_duty_dropped.restype = ctypes.c_uint32
    lib.mc_duty_dropped.argtypes = [ctypes.c_void_p]
    for fn in ("mc_duty_cap_ms", "mc_duty_budget_ms", "mc_duty_window_ms"):
        getattr(lib, fn).restype = ctypes.c_uint32
        getattr(lib, fn).argtypes = []
    # TxQueue (opaque buffer ABI: TxQueue owns vectors -> must destroy before free).
    lib.mc_txqueue_sizeof.restype = ctypes.c_int
    lib.mc_txqueue_sizeof.argtypes = []
    lib.mc_txqueue_init.restype = None
    lib.mc_txqueue_init.argtypes = [ctypes.c_void_p]
    lib.mc_txqueue_destroy.restype = None
    lib.mc_txqueue_destroy.argtypes = [ctypes.c_void_p]
    lib.mc_txqueue_enqueue.restype = ctypes.c_int
    lib.mc_txqueue_enqueue.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_bool, ctypes.c_bool,
    ]
    lib.mc_txqueue_size.restype = ctypes.c_int
    lib.mc_txqueue_size.argtypes = [ctypes.c_void_p]
    lib.mc_txqueue_empty.restype = ctypes.c_bool
    lib.mc_txqueue_empty.argtypes = [ctypes.c_void_p]
    lib.mc_txqueue_front_frame.restype = ctypes.c_int
    lib.mc_txqueue_front_frame.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
        ctypes.POINTER(ctypes.c_bool), ctypes.POINTER(ctypes.c_bool),
    ]
    lib.mc_txqueue_pop_front.restype = None
    lib.mc_txqueue_pop_front.argtypes = [ctypes.c_void_p]
    lib.mc_txqueue_push_front.restype = None
    lib.mc_txqueue_push_front.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_bool, ctypes.c_bool,
    ]
    lib.mc_txqueue_depth.restype = ctypes.c_int
    lib.mc_txqueue_depth.argtypes = []
    # RadioFsm (opaque buffer ABI; State enum maps to int 0/1/2 = RxListen/TxBusy/WaitAck).
    lib.mc_fsm_sizeof.restype = ctypes.c_int
    lib.mc_fsm_sizeof.argtypes = []
    lib.mc_fsm_init.restype = None
    lib.mc_fsm_init.argtypes = [ctypes.c_void_p]
    lib.mc_fsm_destroy.restype = None
    lib.mc_fsm_destroy.argtypes = [ctypes.c_void_p]
    lib.mc_fsm_state.restype = ctypes.c_int
    lib.mc_fsm_state.argtypes = [ctypes.c_void_p]
    lib.mc_fsm_abort_tx.restype = None
    lib.mc_fsm_abort_tx.argtypes = [ctypes.c_void_p]
    lib.mc_fsm_begin_tx.restype = None
    lib.mc_fsm_begin_tx.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_bool,
    ]
    lib.mc_fsm_complete_tx.restype = ctypes.c_int
    lib.mc_fsm_complete_tx.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
    lib.mc_fsm_try_consume_ack.restype = ctypes.c_bool
    lib.mc_fsm_try_consume_ack.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    lib.mc_fsm_check_ack_timeout.restype = ctypes.c_bool
    lib.mc_fsm_check_ack_timeout.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mc_fsm_force_listen_if_not_waiting_ack.restype = None
    lib.mc_fsm_force_listen_if_not_waiting_ack.argtypes = [ctypes.c_void_p]
    lib.mc_fsm_ack_deadline_ms.restype = ctypes.c_uint32
    lib.mc_fsm_ack_deadline_ms.argtypes = [ctypes.c_void_p]
    lib.mc_fsm_tx_was_send_with_ack.restype = ctypes.c_bool
    lib.mc_fsm_tx_was_send_with_ack.argtypes = [ctypes.c_void_p]
    lib.mc_fsm_pending_ack_ref.restype = ctypes.c_int
    lib.mc_fsm_pending_ack_ref.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    # PeerTracker (opaque buffer ABI; Update enum maps to 0/1/2/3 =
    # Ignored/Refreshed/AdoptionNeeded/ReplacementNeeded).
    lib.mc_peer_sizeof.restype = ctypes.c_int
    lib.mc_peer_sizeof.argtypes = []
    lib.mc_peer_init.restype = None
    lib.mc_peer_init.argtypes = [ctypes.c_void_p]
    lib.mc_peer_destroy.restype = None
    lib.mc_peer_destroy.argtypes = [ctypes.c_void_p]
    lib.mc_peer_have_peer.restype = ctypes.c_bool
    lib.mc_peer_have_peer.argtypes = [ctypes.c_void_p]
    lib.mc_peer_mac.restype = ctypes.c_int
    lib.mc_peer_mac.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    lib.mc_peer_last_seen_ms.restype = ctypes.c_uint32
    lib.mc_peer_last_seen_ms.argtypes = [ctypes.c_void_p]
    lib.mc_peer_inspect_rx.restype = ctypes.c_int
    lib.mc_peer_inspect_rx.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    lib.mc_peer_commit_new_peer.restype = None
    lib.mc_peer_commit_new_peer.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    lib.mc_peer_is_expired.restype = ctypes.c_bool
    lib.mc_peer_is_expired.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mc_peer_forget.restype = None
    lib.mc_peer_forget.argtypes = [ctypes.c_void_p]
    lib.mc_peer_timeout_ms.restype = ctypes.c_uint32
    lib.mc_peer_timeout_ms.argtypes = []
    lib.mc_peer_mac_len.restype = ctypes.c_int
    lib.mc_peer_mac_len.argtypes = []
    lib.mc_is_broadcast_mac.restype = ctypes.c_bool
    lib.mc_is_broadcast_mac.argtypes = [ctypes.c_char_p]
    lib.mc_mac_equals.restype = ctypes.c_bool
    lib.mc_mac_equals.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    # ModemHarness: HAL foundation slice -- exercises modem_core::Modem.tickAckTimeout
    # via mock IClock/IHostLink/IRadio/IEspNow implementations in modem_abi.cpp.
    lib.mc_harness_sizeof.restype = ctypes.c_int
    lib.mc_harness_sizeof.argtypes = []
    lib.mc_harness_init.restype = None
    lib.mc_harness_init.argtypes = [ctypes.c_void_p]
    lib.mc_harness_destroy.restype = None
    lib.mc_harness_destroy.argtypes = [ctypes.c_void_p]
    lib.mc_harness_set_now_ms.restype = None
    lib.mc_harness_set_now_ms.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.mc_harness_seed_wait_ack.restype = None
    lib.mc_harness_seed_wait_ack.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_int,
    ]
    lib.mc_harness_tick_ack_timeout.restype = ctypes.c_bool
    lib.mc_harness_tick_ack_timeout.argtypes = [ctypes.c_void_p]
    lib.mc_harness_start_receive_count.restype = ctypes.c_int
    lib.mc_harness_start_receive_count.argtypes = [ctypes.c_void_p]
    lib.mc_harness_written_line_count.restype = ctypes.c_int
    lib.mc_harness_written_line_count.argtypes = [ctypes.c_void_p]
    lib.mc_harness_written_line.restype = ctypes.c_int
    lib.mc_harness_written_line.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
    ]
    lib.mc_harness_fsm_state.restype = ctypes.c_int
    lib.mc_harness_fsm_state.argtypes = [ctypes.c_void_p]
    # PeerTracker seeding + observability via the harness
    lib.mc_harness_peer_commit.restype = None
    lib.mc_harness_peer_commit.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    lib.mc_harness_peer_have_peer.restype = ctypes.c_bool
    lib.mc_harness_peer_have_peer.argtypes = [ctypes.c_void_p]
    lib.mc_harness_peer_mac.restype = ctypes.c_int
    lib.mc_harness_peer_mac.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    lib.mc_harness_peer_last_seen_ms.restype = ctypes.c_uint32
    lib.mc_harness_peer_last_seen_ms.argtypes = [ctypes.c_void_p]
    # Modem.tickPeerLiveness + MockEspNow observability
    lib.mc_harness_tick_peer_liveness.restype = ctypes.c_bool
    lib.mc_harness_tick_peer_liveness.argtypes = [ctypes.c_void_p]
    lib.mc_harness_espnow_delete_peer_count.restype = ctypes.c_int
    lib.mc_harness_espnow_delete_peer_count.argtypes = [ctypes.c_void_p]
    lib.mc_harness_espnow_last_deleted_mac.restype = ctypes.c_int
    lib.mc_harness_espnow_last_deleted_mac.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
    ]
    # FSM/Queue seeding + canStartNextTx guard predicate
    lib.mc_harness_seed_fsm_state.restype = None
    lib.mc_harness_seed_fsm_state.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.mc_harness_queue_enqueue.restype = ctypes.c_int
    lib.mc_harness_queue_enqueue.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_bool, ctypes.c_bool,
    ]
    lib.mc_harness_queue_size.restype = ctypes.c_int
    lib.mc_harness_queue_size.argtypes = [ctypes.c_void_p]
    lib.mc_harness_can_start_next_tx.restype = ctypes.c_bool
    lib.mc_harness_can_start_next_tx.argtypes = [
        ctypes.c_void_p, ctypes.c_bool, ctypes.c_uint32,
    ]
    # tickEspNowRx + MockEspNow rx-queue seeding + observability
    lib.mc_harness_seed_espnow_rx.restype = None
    lib.mc_harness_seed_espnow_rx.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int,
    ]
    lib.mc_harness_set_addpeer_result.restype = None
    lib.mc_harness_set_addpeer_result.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    lib.mc_harness_espnow_add_peer_count.restype = ctypes.c_int
    lib.mc_harness_espnow_add_peer_count.argtypes = [ctypes.c_void_p]
    lib.mc_harness_espnow_last_added_mac.restype = ctypes.c_int
    lib.mc_harness_espnow_last_added_mac.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
    ]
    lib.mc_harness_tick_espnow_rx.restype = None
    lib.mc_harness_tick_espnow_rx.argtypes = [ctypes.c_void_p]
    lib.mc_harness_foreign_dropped.restype = ctypes.c_uint32
    lib.mc_harness_foreign_dropped.argtypes = [ctypes.c_void_p]
    lib.mc_harness_rx_other_count.restype = ctypes.c_uint32
    lib.mc_harness_rx_other_count.argtypes = [ctypes.c_void_p]
    # tickHealthReport (2s throttle + reportHealth body)
    lib.mc_harness_tick_health_report.restype = ctypes.c_bool
    lib.mc_harness_tick_health_report.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
    ]
    # tickRadioRx (LoRa RX path: header check + ACK consume + RX log + re-arm)
    lib.mc_harness_tick_radio_rx.restype = None
    lib.mc_harness_tick_radio_rx.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_float, ctypes.c_float,
    ]
    # tickTxComplete + seed_tx_busy (TX completion path)
    lib.mc_harness_tick_tx_complete.restype = None
    lib.mc_harness_tick_tx_complete.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.mc_harness_seed_tx_busy.restype = None
    lib.mc_harness_seed_tx_busy.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_bool,
    ]
    # parseHostFrame (UART command parser)
    lib.mc_harness_parse_host_frame.restype = ctypes.c_int
    lib.mc_harness_parse_host_frame.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p,
        ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int),
    ]
    # classifyRadioIrq (LoRa IRQ dispatcher decision)
    lib.mc_harness_classify_radio_irq.restype = ctypes.c_int
    lib.mc_harness_classify_radio_irq.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
    ]
    # TX engine: enqueueTx + tickStartNextTx + readiness flags + observability
    lib.mc_harness_set_radio_ready.restype = None
    lib.mc_harness_set_radio_ready.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    lib.mc_harness_set_espnow_ready.restype = None
    lib.mc_harness_set_espnow_ready.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    lib.mc_harness_set_tx_result.restype = None
    lib.mc_harness_set_tx_result.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.mc_harness_enqueue_tx.restype = ctypes.c_bool
    lib.mc_harness_enqueue_tx.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_bool,
    ]
    lib.mc_harness_tick_start_next_tx.restype = None
    lib.mc_harness_tick_start_next_tx.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    lib.mc_harness_start_transmit_count.restype = ctypes.c_int
    lib.mc_harness_start_transmit_count.argtypes = [ctypes.c_void_p]
    lib.mc_harness_last_tx_frame.restype = ctypes.c_int
    lib.mc_harness_last_tx_frame.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    lib.mc_harness_espnow_send_count.restype = ctypes.c_int
    lib.mc_harness_espnow_send_count.argtypes = [ctypes.c_void_p]
    lib.mc_harness_espnow_last_sent_len.restype = ctypes.c_int
    lib.mc_harness_espnow_last_sent_len.argtypes = [ctypes.c_void_p]
    lib.mc_harness_espnow_last_sent_dst.restype = ctypes.c_int
    lib.mc_harness_espnow_last_sent_dst.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
    ]
    lib.mc_harness_duty_dropped.restype = ctypes.c_uint32
    lib.mc_harness_duty_dropped.argtypes = [ctypes.c_void_p]
    lib.mc_harness_duty_add.restype = None
    lib.mc_harness_duty_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    # Callback-HAL Modem (sim_link wiring): create/destroy + tick drivers.
    lib.mc_cbmodem_create.restype = ctypes.c_void_p
    lib.mc_cbmodem_create.argtypes = [
        ctypes.c_void_p, CB_NOW_MS, CB_WRITE_LINE, CB_START_TX,
        CB_ESP_SEND, CB_ESP_ADD_PEER, CB_ESP_DEL_PEER, CB_ESP_POLL_RX, ctypes.c_int,
    ]
    lib.mc_cbmodem_destroy.restype = None
    lib.mc_cbmodem_destroy.argtypes = [ctypes.c_void_p]
    lib.mc_cbmodem_set_radio_ready.restype = None
    lib.mc_cbmodem_set_radio_ready.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.mc_cbmodem_set_espnow_ready.restype = None
    lib.mc_cbmodem_set_espnow_ready.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.mc_cbmodem_enqueue_tx.restype = ctypes.c_int
    lib.mc_cbmodem_enqueue_tx.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int,
    ]
    for fn in ("mc_cbmodem_tick_start_next_tx",):
        getattr(lib, fn).restype = None
        getattr(lib, fn).argtypes = [ctypes.c_void_p, ctypes.c_int]
    for fn in ("mc_cbmodem_tick_ack_timeout", "mc_cbmodem_tick_duty_drain",
               "mc_cbmodem_tick_peer_liveness", "mc_cbmodem_tick_espnow_rx"):
        getattr(lib, fn).restype = None
        getattr(lib, fn).argtypes = [ctypes.c_void_p]
    lib.mc_cbmodem_tick_radio_rx.restype = None
    lib.mc_cbmodem_tick_radio_rx.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_float, ctypes.c_float,
    ]
    lib.mc_cbmodem_tick_tx_complete.restype = None
    lib.mc_cbmodem_tick_tx_complete.argtypes = [ctypes.c_void_p, ctypes.c_int]
    for fn in ("mc_cbmodem_fsm_state", "mc_cbmodem_queue_size", "mc_cbmodem_have_peer"):
        getattr(lib, fn).restype = ctypes.c_int
        getattr(lib, fn).argtypes = [ctypes.c_void_p]
    return lib


def encode(frame_type: PY.FrameType, src: int, dst: int, seq: int, nonce: int,
           payload: bytes = b"") -> bytes:
    """Build a firmware-faithful frame via the Python mirror (cross-validated parity)."""
    return PY.encode_frame(
        PY.PropFrame(frame_type=frame_type, key_id=1, source=src, destination=dst,
                     sequence=seq, nonce=nonce, payload=payload),
        KEYS,
    )


def has_header(lib: ctypes.CDLL, buf: bytes) -> bool:
    return bool(lib.mc_has_protocol_header(buf, len(buf)))


def looks_match(lib: ctypes.CDLL, req: bytes, cand: bytes) -> bool:
    return bool(lib.mc_looks_like_matching_ack(req, len(req), cand, len(cand)))


def check(name: str, ok: bool, detail: str = "") -> int:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" -- {detail}" if detail else ""))
    return 0 if ok else 1


def main() -> int:
    lib = load_dll()
    failures = 0

    # Build a representative FIRE (Dial=0x11 -> RX=0x22, seq=42, nonce w/ epoch).
    DIAL, DINRX = 0x11, 0x22
    seq = 42
    nonce = (0x12345678 << 32) | seq
    fire = encode(PY.FrameType.FIRE, DIAL, DINRX, seq, nonce, payload=b"FIRE-1")
    matching_ack = encode(PY.FrameType.ACK, DINRX, DIAL, seq, nonce, payload=b"FIRED")

    # hasProtocolHeader
    failures += check("hasProtocolHeader: valid FIRE", has_header(lib, fire))
    failures += check("hasProtocolHeader: too short", not has_header(lib, b"\x00" * 16))
    failures += check("hasProtocolHeader: bad magic",
                      not has_header(lib, b"\xFF\xFF" + fire[2:]))
    failures += check("hasProtocolHeader: bad version",
                      not has_header(lib, fire[:2] + b"\xEE" + fire[3:]))

    # looksLikeMatchingAck: positive
    failures += check("matching ACK -> True", looks_match(lib, fire, matching_ack))

    # Negatives
    wrong_seq = encode(PY.FrameType.ACK, DINRX, DIAL, seq + 1,
                       (0x12345678 << 32) | (seq + 1), payload=b"x")
    failures += check("wrong seq -> False", not looks_match(lib, fire, wrong_seq))

    wrong_nonce = encode(PY.FrameType.ACK, DINRX, DIAL, seq,
                         (0xDEADBEEF << 32) | seq, payload=b"x")
    failures += check("wrong nonce -> False", not looks_match(lib, fire, wrong_nonce))

    no_swap = encode(PY.FrameType.ACK, DIAL, DINRX, seq, nonce, payload=b"x")  # src/dst not swapped
    failures += check("no src/dst swap -> False", not looks_match(lib, fire, no_swap))

    wrong_type = encode(PY.FrameType.STATUS, DINRX, DIAL, seq, nonce, payload=b"x")
    failures += check("non-ACK type -> False", not looks_match(lib, fire, wrong_type))

    # Wrong key_id: encode using key_id=2 (which we don't have a key for). Use raw byte tweak instead:
    # build a real ACK then flip the key_id byte (offset 4) -- MAC won't match, but looksLikeMatchingAck
    # doesn't verify MAC (it's a cheap pre-check), only that key_id matches the request.
    wrong_key = bytearray(matching_ack)
    wrong_key[4] = 0xFE  # change key_id field
    failures += check("wrong key_id -> False", not looks_match(lib, fire, bytes(wrong_key)))

    # Request also rejected if header invalid
    failures += check("invalid request -> False", not looks_match(lib, b"\x00" * 16, matching_ack))

    # --- DutyBucket: EU 868 ~1% duty cycle accounting (safety-relevant: STOP bypasses) ---
    size = lib.mc_duty_sizeof()
    buf = (ctypes.c_ubyte * size)()
    lib.mc_duty_init(buf)
    failures += check("duty init bucket=0", abs(lib.mc_duty_bucket_ms(buf)) < 1e-6)
    failures += check("duty init dropped=0", lib.mc_duty_dropped(buf) == 0)

    # First drain sets the lastMs sentinel without draining anything.
    lib.mc_duty_drain(buf, 1000)
    failures += check("duty first drain leaves bucket=0",
                      abs(lib.mc_duty_bucket_ms(buf)) < 1e-6)

    lib.mc_duty_add(buf, 20)
    failures += check("duty add(20) -> bucket=20",
                      abs(lib.mc_duty_bucket_ms(buf) - 20.0) < 0.001,
                      f"bucket={lib.mc_duty_bucket_ms(buf):.4f}")

    # Drain rate = BUDGET / WINDOW ms/ms (e.g. 3600/360000 = 0.01). 1000 ms -> 10 ms drained.
    lib.mc_duty_drain(buf, 2000)
    drain_rate = lib.mc_duty_budget_ms() / float(lib.mc_duty_window_ms())
    expected = 20.0 - 1000.0 * drain_rate
    actual = lib.mc_duty_bucket_ms(buf)
    failures += check("duty drain 1s -> matches BUDGET/WINDOW math",
                      abs(actual - expected) < 0.01,
                      f"actual={actual:.3f} expected={expected:.3f}")

    # Pile in more than CAP -> must clamp.
    cap = float(lib.mc_duty_cap_ms())
    for _ in range(2000):
        lib.mc_duty_add(buf, 100)
    failures += check("duty cap clamp",
                      abs(lib.mc_duty_bucket_ms(buf) - cap) < 0.5,
                      f"bucket={lib.mc_duty_bucket_ms(buf):.1f} cap={cap}")
    failures += check("duty would_exceed at cap", lib.mc_duty_would_exceed(buf, 1))

    # Below cap: would_exceed False (room for one airtime).
    fresh = (ctypes.c_ubyte * size)()
    lib.mc_duty_init(fresh)
    lib.mc_duty_add(fresh, 100)
    failures += check("duty would_exceed below cap",
                      not lib.mc_duty_would_exceed(fresh, 100))

    # --- TxQueue: SAFETY-CRITICAL bounded queue with STOP priority (A2b invariant) ---
    # Opaque buffer ABI: TxQueue owns std::vector<TxRequest> (each owns its own
    # std::vector<uint8_t> frame) -> we MUST mc_txqueue_destroy before freeing.
    tq_size = lib.mc_txqueue_sizeof()
    tq = (ctypes.c_ubyte * tq_size)()
    lib.mc_txqueue_init(tq)
    try:
        failures += check("txqueue init empty", lib.mc_txqueue_empty(tq))
        failures += check("txqueue init size == 0", lib.mc_txqueue_size(tq) == 0)
        failures += check("txqueue depth == 4", lib.mc_txqueue_depth() == 4)

        # 4 distinct STATUS (non-STOP) frames + 1 extra for the overflow test.
        statuses = [
            encode(PY.FrameType.STATUS, DIAL, DINRX, 100 + i,
                   (0xCAFE0000 << 32) | (100 + i), payload=bytes([0x20 + i]))
            for i in range(5)
        ]

        # Fill: 4 non-STOP enqueues all return Accepted(0).
        for i in range(4):
            r = lib.mc_txqueue_enqueue(tq, statuses[i], len(statuses[i]), False, False)
            failures += check(f"txqueue enqueue non-STOP #{i} -> Accepted(0)", r == 0)
        failures += check("txqueue full -> size == 4", lib.mc_txqueue_size(tq) == 4)

        # 5th non-STOP must be REJECTED (queue full + not STOP).
        r = lib.mc_txqueue_enqueue(tq, statuses[4], len(statuses[4]), False, False)
        failures += check("txqueue full + non-STOP -> RejectedBusy(2)", r == 2)
        failures += check("txqueue size unchanged after reject", lib.mc_txqueue_size(tq) == 4)

        # STOP into a FULL queue: must evict oldest + jump front (A2b safety invariant).
        stop = encode(PY.FrameType.STOP, DIAL, DINRX, 200,
                      (0xDEAD0000 << 32) | 200, payload=b"!")
        r = lib.mc_txqueue_enqueue(tq, stop, len(stop), True, True)
        failures += check("txqueue full + STOP -> AcceptedStopEvicted(1)", r == 1)
        failures += check("txqueue size still 4 after STOP eviction",
                          lib.mc_txqueue_size(tq) == 4)

        # Front == STOP, with isStop=True + waitForAck=True.
        out_buf = (ctypes.c_ubyte * 256)()
        out_wfa = ctypes.c_bool(False)
        out_stop = ctypes.c_bool(False)
        n = lib.mc_txqueue_front_frame(tq, out_buf, 256,
                                       ctypes.byref(out_wfa), ctypes.byref(out_stop))
        failures += check("txqueue front len matches STOP", n == len(stop))
        failures += check("txqueue front is_stop=True", out_stop.value)
        failures += check("txqueue front wait_for_ack=True", out_wfa.value)
        failures += check("txqueue front bytes match STOP", bytes(out_buf[:n]) == stop)

        # Pop STOP -> next front == statuses[1] (statuses[0] was the one evicted).
        lib.mc_txqueue_pop_front(tq)
        failures += check("txqueue size 3 after pop STOP", lib.mc_txqueue_size(tq) == 3)
        n = lib.mc_txqueue_front_frame(tq, out_buf, 256,
                                       ctypes.byref(out_wfa), ctypes.byref(out_stop))
        failures += check("txqueue after STOP pop -> front == statuses[1]",
                          bytes(out_buf[:n]) == statuses[1])
        failures += check("txqueue next front is_stop=False", not out_stop.value)

        # STOP with room available -> Accepted(0), still jumps the front.
        r = lib.mc_txqueue_enqueue(tq, stop, len(stop), True, True)
        failures += check("txqueue STOP with room -> Accepted(0)", r == 0)
        failures += check("txqueue size 4 after STOP-with-room",
                          lib.mc_txqueue_size(tq) == 4)
        n = lib.mc_txqueue_front_frame(tq, out_buf, 256,
                                       ctypes.byref(out_wfa), ctypes.byref(out_stop))
        failures += check("txqueue STOP-with-room jumps front", out_stop.value)

        # pushFront (retry path): pop the STOP, re-insert a custom frame at front.
        lib.mc_txqueue_pop_front(tq)
        retry = encode(PY.FrameType.FIRE, DIAL, DINRX, 999,
                       (0xBEEF0000 << 32) | 999, payload=b"R")
        lib.mc_txqueue_push_front(tq, retry, len(retry), True, False)
        n = lib.mc_txqueue_front_frame(tq, out_buf, 256,
                                       ctypes.byref(out_wfa), ctypes.byref(out_stop))
        failures += check("txqueue push_front -> front == retry frame",
                          bytes(out_buf[:n]) == retry)
        failures += check("txqueue retry wait_for_ack=True", out_wfa.value)
        failures += check("txqueue retry is_stop=False", not out_stop.value)

        # Length-only query: out=NULL still returns the frame length.
        n2 = lib.mc_txqueue_front_frame(tq, None, 0, None, None)
        failures += check("txqueue front_frame(out=NULL) returns length", n2 == n)
    finally:
        lib.mc_txqueue_destroy(tq)

    # --- RadioFsm: SAFETY-CRITICAL radio TX/ACK state machine ---
    # State enum: 0=RxListen, 1=TxBusy, 2=WaitAck.
    fsm_size = lib.mc_fsm_sizeof()
    fsm_buf = (ctypes.c_ubyte * fsm_size)()
    lib.mc_fsm_init(fsm_buf)
    try:
        # Init: RxListen, no pending, txWasSendWithAck=False.
        failures += check("radiofsm init -> RxListen(0)", lib.mc_fsm_state(fsm_buf) == 0)
        failures += check("radiofsm init -> txWasSendWithAck=False",
                          not lib.mc_fsm_tx_was_send_with_ack(fsm_buf))
        failures += check("radiofsm init -> pendingAckRef empty",
                          lib.mc_fsm_pending_ack_ref(fsm_buf, None, 0) == 0)
        failures += check("radiofsm init -> ackDeadline=0",
                          lib.mc_fsm_ack_deadline_ms(fsm_buf) == 0)

        # beginTx with ACK: TxBusy + pending=request + txWasSendWithAck=True.
        fire2 = encode(PY.FrameType.FIRE, DIAL, DINRX, 77,
                       (0xABCD0000 << 32) | 77, payload=b"F2")
        lib.mc_fsm_begin_tx(fsm_buf, fire2, len(fire2), True)
        failures += check("radiofsm beginTx(ack=True) -> TxBusy(1)",
                          lib.mc_fsm_state(fsm_buf) == 1)
        failures += check("radiofsm beginTx(ack=True) -> txWasSendWithAck=True",
                          lib.mc_fsm_tx_was_send_with_ack(fsm_buf))
        pend_buf = (ctypes.c_ubyte * 256)()
        n = lib.mc_fsm_pending_ack_ref(fsm_buf, pend_buf, 256)
        failures += check("radiofsm beginTx -> pendingAckRef len matches", n == len(fire2))
        failures += check("radiofsm beginTx -> pendingAckRef bytes == fire",
                          bytes(pend_buf[:n]) == fire2)

        # completeTx (waitForAck=True) -> WaitAck + ackDeadline armed.
        new_state = lib.mc_fsm_complete_tx(fsm_buf, 5000, 900)
        failures += check("radiofsm completeTx(waitForAck) -> WaitAck(2)", new_state == 2)
        failures += check("radiofsm after completeTx -> state WaitAck",
                          lib.mc_fsm_state(fsm_buf) == 2)
        failures += check("radiofsm completeTx -> ackDeadline = now+timeout",
                          lib.mc_fsm_ack_deadline_ms(fsm_buf) == 5900)

        # tryConsumeAck(stale) -> False, state unchanged.
        stale_ack = encode(PY.FrameType.ACK, DINRX, DIAL, 99,
                           (0xABCD0000 << 32) | 99, payload=b"x")
        failures += check("radiofsm tryConsumeAck(stale) -> False",
                          not lib.mc_fsm_try_consume_ack(fsm_buf, stale_ack, len(stale_ack)))
        failures += check("radiofsm after stale -> still WaitAck",
                          lib.mc_fsm_state(fsm_buf) == 2)

        # tryConsumeAck(matching) -> True, state -> RxListen, pending cleared.
        match_ack = encode(PY.FrameType.ACK, DINRX, DIAL, 77,
                           (0xABCD0000 << 32) | 77, payload=b"OK")
        failures += check("radiofsm tryConsumeAck(matching) -> True",
                          lib.mc_fsm_try_consume_ack(fsm_buf, match_ack, len(match_ack)))
        failures += check("radiofsm after matching ACK -> RxListen(0)",
                          lib.mc_fsm_state(fsm_buf) == 0)
        failures += check("radiofsm after matching ACK -> txWasSendWithAck=False",
                          not lib.mc_fsm_tx_was_send_with_ack(fsm_buf))
        failures += check("radiofsm after matching ACK -> pendingAckRef cleared",
                          lib.mc_fsm_pending_ack_ref(fsm_buf, None, 0) == 0)

        # beginTx without ACK -> TxBusy, pending EMPTY, txWasSendWithAck=False.
        no_ack = encode(PY.FrameType.FIRE, DIAL, DINRX, 88,
                        (0xABCD0000 << 32) | 88, payload=b"F3")
        lib.mc_fsm_begin_tx(fsm_buf, no_ack, len(no_ack), False)
        failures += check("radiofsm beginTx(ack=False) -> TxBusy(1)",
                          lib.mc_fsm_state(fsm_buf) == 1)
        failures += check("radiofsm beginTx(ack=False) -> txWasSendWithAck=False",
                          not lib.mc_fsm_tx_was_send_with_ack(fsm_buf))
        failures += check("radiofsm beginTx(ack=False) -> pending empty",
                          lib.mc_fsm_pending_ack_ref(fsm_buf, None, 0) == 0)

        # completeTx(waitForAck=False) -> RxListen immediately.
        new_state = lib.mc_fsm_complete_tx(fsm_buf, 8000, 900)
        failures += check("radiofsm completeTx(no-ack) -> RxListen(0)", new_state == 0)
        failures += check("radiofsm completeTx(no-ack) -> state RxListen",
                          lib.mc_fsm_state(fsm_buf) == 0)

        # ACK-timeout path: re-arm WaitAck, advance time past deadline.
        lib.mc_fsm_begin_tx(fsm_buf, fire2, len(fire2), True)
        lib.mc_fsm_complete_tx(fsm_buf, 10000, 900)
        failures += check("radiofsm re-arm -> WaitAck(2)", lib.mc_fsm_state(fsm_buf) == 2)
        # 1ms before deadline -> still waiting
        failures += check("radiofsm checkAckTimeout(deadline-1) -> False",
                          not lib.mc_fsm_check_ack_timeout(fsm_buf, 10899))
        failures += check("radiofsm pre-timeout -> still WaitAck",
                          lib.mc_fsm_state(fsm_buf) == 2)
        # at deadline -> True, transition to RxListen
        failures += check("radiofsm checkAckTimeout(deadline) -> True",
                          lib.mc_fsm_check_ack_timeout(fsm_buf, 10900))
        failures += check("radiofsm post-timeout -> RxListen(0)",
                          lib.mc_fsm_state(fsm_buf) == 0)

        # abortTx from TxBusy -> RxListen, pending cleared.
        lib.mc_fsm_begin_tx(fsm_buf, fire2, len(fire2), True)
        failures += check("radiofsm beginTx(abort test) -> TxBusy(1)",
                          lib.mc_fsm_state(fsm_buf) == 1)
        lib.mc_fsm_abort_tx(fsm_buf)
        failures += check("radiofsm abortTx -> RxListen(0)", lib.mc_fsm_state(fsm_buf) == 0)
        failures += check("radiofsm abortTx -> pendingAckRef cleared",
                          lib.mc_fsm_pending_ack_ref(fsm_buf, None, 0) == 0)
        failures += check("radiofsm abortTx -> txWasSendWithAck=False",
                          not lib.mc_fsm_tx_was_send_with_ack(fsm_buf))

        # forceListenIfNotWaitingAck:
        #  - from WaitAck: STAYS (still waiting for the ACK -> not safe to force listen)
        lib.mc_fsm_begin_tx(fsm_buf, fire2, len(fire2), True)
        lib.mc_fsm_complete_tx(fsm_buf, 20000, 900)
        failures += check("radiofsm setup -> WaitAck(2)", lib.mc_fsm_state(fsm_buf) == 2)
        lib.mc_fsm_force_listen_if_not_waiting_ack(fsm_buf)
        failures += check("radiofsm forceListen from WaitAck -> stays WaitAck",
                          lib.mc_fsm_state(fsm_buf) == 2)
        lib.mc_fsm_abort_tx(fsm_buf)
        #  - from TxBusy: -> RxListen (recovers from the rare RX-DONE-during-TX-BUSY case)
        lib.mc_fsm_begin_tx(fsm_buf, fire2, len(fire2), False)
        failures += check("radiofsm pre-force TxBusy(1)", lib.mc_fsm_state(fsm_buf) == 1)
        lib.mc_fsm_force_listen_if_not_waiting_ack(fsm_buf)
        failures += check("radiofsm forceListen from TxBusy -> RxListen(0)",
                          lib.mc_fsm_state(fsm_buf) == 0)

        # tryConsumeAck in non-WaitAck states: no-op (False, no state change).
        failures += check("radiofsm tryConsumeAck in RxListen -> False",
                          not lib.mc_fsm_try_consume_ack(fsm_buf, match_ack, len(match_ack)))
        failures += check("radiofsm tryConsumeAck in RxListen -> state unchanged",
                          lib.mc_fsm_state(fsm_buf) == 0)
    finally:
        lib.mc_fsm_destroy(fsm_buf)

    # --- PeerTracker: ESP-NOW unicast peer adoption + liveness (TIMEOUT_MS=5000) ---
    # Update enum: 0=Ignored, 1=Refreshed, 2=AdoptionNeeded, 3=ReplacementNeeded.
    BCAST = bytes([0xFF] * 6)
    MAC_A = bytes([0x10, 0x20, 0x30, 0x40, 0x50, 0x60])
    MAC_B = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF])
    MAC_C = bytes([0x10, 0x20, 0x30, 0x40, 0x50, 0x61])  # one-byte off from A

    # Standalone helpers first
    failures += check("MAC_LEN == 6", lib.mc_peer_mac_len() == 6)
    failures += check("PEER timeout == 5000ms", lib.mc_peer_timeout_ms() == 5000)
    failures += check("is_broadcast_mac(FF*6) -> True", lib.mc_is_broadcast_mac(BCAST))
    failures += check("is_broadcast_mac(MAC_A) -> False", not lib.mc_is_broadcast_mac(MAC_A))
    failures += check("mac_equals(MAC_A, MAC_A) -> True", lib.mc_mac_equals(MAC_A, MAC_A))
    failures += check("mac_equals(MAC_A, MAC_C) one-byte diff -> False",
                      not lib.mc_mac_equals(MAC_A, MAC_C))

    peer_size = lib.mc_peer_sizeof()
    pt = (ctypes.c_ubyte * peer_size)()
    lib.mc_peer_init(pt)
    try:
        # Init: no peer, lastSeen=0, mac all zeros, not expired.
        failures += check("peer init -> havePeer=False", not lib.mc_peer_have_peer(pt))
        failures += check("peer init -> lastSeen=0", lib.mc_peer_last_seen_ms(pt) == 0)
        failures += check("peer init -> isExpired=False (no peer)",
                          not lib.mc_peer_is_expired(pt, 100000))
        mac_buf = (ctypes.c_ubyte * 6)()
        lib.mc_peer_mac(pt, mac_buf, 6)
        failures += check("peer init -> mac is zero", bytes(mac_buf) == b"\x00" * 6)

        # Broadcast MAC -> Ignored, state unchanged.
        r = lib.mc_peer_inspect_rx(pt, BCAST, 1000)
        failures += check("inspectRx(BROADCAST) -> Ignored(0)", r == 0)
        failures += check("after broadcast -> still no peer", not lib.mc_peer_have_peer(pt))

        # First valid MAC -> AdoptionNeeded; state still unchanged until commit.
        r = lib.mc_peer_inspect_rx(pt, MAC_A, 2000)
        failures += check("inspectRx(MAC_A first) -> AdoptionNeeded(2)", r == 2)
        failures += check("after AdoptionNeeded (pre-commit) -> havePeer still False",
                          not lib.mc_peer_have_peer(pt))
        # Now commit (simulates esp_now_add_peer succeeded)
        lib.mc_peer_commit_new_peer(pt, MAC_A, 2000)
        failures += check("after commit -> havePeer=True", lib.mc_peer_have_peer(pt))
        lib.mc_peer_mac(pt, mac_buf, 6)
        failures += check("after commit -> mac == MAC_A", bytes(mac_buf) == MAC_A)
        failures += check("after commit -> lastSeen == 2000",
                          lib.mc_peer_last_seen_ms(pt) == 2000)

        # Same MAC again -> Refreshed (lastSeen bumped immediately, no HW op).
        r = lib.mc_peer_inspect_rx(pt, MAC_A, 3000)
        failures += check("inspectRx(MAC_A again) -> Refreshed(1)", r == 1)
        failures += check("after Refreshed -> lastSeen bumped",
                          lib.mc_peer_last_seen_ms(pt) == 3000)
        failures += check("after Refreshed -> still MAC_A", lib.mc_peer_have_peer(pt))
        lib.mc_peer_mac(pt, mac_buf, 6)
        failures += check("after Refreshed -> mac unchanged == MAC_A",
                          bytes(mac_buf) == MAC_A)

        # Different MAC -> ReplacementNeeded; pre-commit, state UNCHANGED.
        r = lib.mc_peer_inspect_rx(pt, MAC_B, 4000)
        failures += check("inspectRx(MAC_B) -> ReplacementNeeded(3)", r == 3)
        lib.mc_peer_mac(pt, mac_buf, 6)
        failures += check("ReplacementNeeded pre-commit -> mac still MAC_A",
                          bytes(mac_buf) == MAC_A)
        failures += check("ReplacementNeeded pre-commit -> lastSeen still 3000",
                          lib.mc_peer_last_seen_ms(pt) == 3000)
        # Commit the replacement (simulates del_peer(old) + add_peer(new) OK)
        lib.mc_peer_commit_new_peer(pt, MAC_B, 4000)
        lib.mc_peer_mac(pt, mac_buf, 6)
        failures += check("after replacement commit -> mac == MAC_B", bytes(mac_buf) == MAC_B)
        failures += check("after replacement commit -> lastSeen == 4000",
                          lib.mc_peer_last_seen_ms(pt) == 4000)

        # Expiry boundary: 5000ms after lastSeen is NOT expired (strict >); 5001ms IS.
        failures += check("isExpired(lastSeen + TIMEOUT_MS) -> False (strict >)",
                          not lib.mc_peer_is_expired(pt, 9000))
        failures += check("isExpired(lastSeen + TIMEOUT_MS + 1) -> True",
                          lib.mc_peer_is_expired(pt, 9001))

        # forget -> no peer, mac zeroed.
        lib.mc_peer_forget(pt)
        failures += check("forget -> havePeer=False", not lib.mc_peer_have_peer(pt))
        failures += check("forget -> lastSeen=0", lib.mc_peer_last_seen_ms(pt) == 0)
        lib.mc_peer_mac(pt, mac_buf, 6)
        failures += check("forget -> mac is zero", bytes(mac_buf) == b"\x00" * 6)
        failures += check("forget -> isExpired=False (no peer)",
                          not lib.mc_peer_is_expired(pt, 999999))

        # After forget, inspectRx(any valid MAC) should be AdoptionNeeded (not Replacement).
        r = lib.mc_peer_inspect_rx(pt, MAC_C, 10000)
        failures += check("after forget, inspectRx(MAC_C) -> AdoptionNeeded(2)", r == 2)
    finally:
        lib.mc_peer_destroy(pt)

    # --- HAL foundation: Modem.tickAckTimeout via mock HAL ---
    # The Modem orchestration class wraps the four state structs + four HAL interfaces.
    # Real ESP32 builds wire RadioLib + Serial + esp_now as adapters in main.cpp; the
    # host test uses MockClock / MockHostLink / MockRadio / NullEspNow bundled by a
    # ModemHarness fixture so we can exercise tickAckTimeout() deterministically.
    def written_lines(p):
        n = lib.mc_harness_written_line_count(p)
        result = []
        for i in range(n):
            buf = (ctypes.c_char * 64)()
            length = lib.mc_harness_written_line(p, i, buf, 64)
            if length >= 0:
                result.append(bytes(buf[:length]).decode("ascii", errors="replace"))
        return result

    h_size = lib.mc_harness_sizeof()
    harness = (ctypes.c_ubyte * h_size)()
    lib.mc_harness_init(harness)
    try:
        # 1) RxListen state (default after init): tickAckTimeout is a no-op.
        failures += check("harness init -> RxListen(0)",
                          lib.mc_harness_fsm_state(harness) == 0)
        lib.mc_harness_set_now_ms(harness, 999999)
        fired = lib.mc_harness_tick_ack_timeout(harness)
        failures += check("tick in RxListen -> no fire", not fired)
        failures += check("tick in RxListen -> no host writes",
                          lib.mc_harness_written_line_count(harness) == 0)
        failures += check("tick in RxListen -> no startReceive",
                          lib.mc_harness_start_receive_count(harness) == 0)

        # 2) WaitAck + now < deadline -> still waiting.
        fire = encode(PY.FrameType.FIRE, DIAL, DINRX, 55,
                      (0xACE10000 << 32) | 55, payload=b"WAIT")
        lib.mc_harness_seed_wait_ack(harness, 5000, fire, len(fire))
        failures += check("after seed -> WaitAck(2)",
                          lib.mc_harness_fsm_state(harness) == 2)
        lib.mc_harness_set_now_ms(harness, 4999)
        fired = lib.mc_harness_tick_ack_timeout(harness)
        failures += check("tick at deadline-1 -> no fire", not fired)
        failures += check("tick pre-deadline -> still WaitAck",
                          lib.mc_harness_fsm_state(harness) == 2)
        failures += check("tick pre-deadline -> no host writes yet",
                          lib.mc_harness_written_line_count(harness) == 0)

        # 3) WaitAck + now >= deadline -> fire, ERR ACK_TIMEOUT, startReceive.
        lib.mc_harness_set_now_ms(harness, 5000)
        fired = lib.mc_harness_tick_ack_timeout(harness)
        failures += check("tick at deadline -> fired", fired)
        failures += check("after timeout -> RxListen(0)",
                          lib.mc_harness_fsm_state(harness) == 0)
        lines = written_lines(harness)
        failures += check("after timeout -> one host line written",
                          len(lines) == 1,
                          f"lines={lines}")
        failures += check("after timeout -> line == 'ERR ACK_TIMEOUT'",
                          lines == ["ERR ACK_TIMEOUT"],
                          f"lines={lines}")
        failures += check("after timeout -> startReceive called once",
                          lib.mc_harness_start_receive_count(harness) == 1)

        # 4) Tick again immediately after firing: state is RxListen, no-op.
        fired = lib.mc_harness_tick_ack_timeout(harness)
        failures += check("tick again after fire -> no fire", not fired)
        failures += check("after second tick -> still one host line",
                          lib.mc_harness_written_line_count(harness) == 1)
        failures += check("after second tick -> startReceive still 1",
                          lib.mc_harness_start_receive_count(harness) == 1)

        # --- Modem.tickPeerLiveness via mock HAL (replaces serviceEspNowPeerLiveness) ---
        # No peer + tick at any time -> no-op, no deletePeer call.
        failures += check("harness peer init -> havePeer=False",
                          not lib.mc_harness_peer_have_peer(harness))
        lib.mc_harness_set_now_ms(harness, 999999)
        fired = lib.mc_harness_tick_peer_liveness(harness)
        failures += check("tick liveness no-peer -> no fire", not fired)
        failures += check("tick liveness no-peer -> no deletePeer",
                          lib.mc_harness_espnow_delete_peer_count(harness) == 0)

        # Adopt a peer at now=1000.
        MAC = bytes([0x42, 0x42, 0x42, 0x42, 0x42, 0x42])
        lib.mc_harness_peer_commit(harness, MAC, 1000)
        failures += check("after commit -> havePeer=True",
                          lib.mc_harness_peer_have_peer(harness))
        failures += check("after commit -> lastSeen=1000",
                          lib.mc_harness_peer_last_seen_ms(harness) == 1000)

        # Tick at now=6000 (exactly TIMEOUT_MS=5000 elapsed) -> not yet expired (strict >).
        lib.mc_harness_set_now_ms(harness, 6000)
        fired = lib.mc_harness_tick_peer_liveness(harness)
        failures += check("tick at +TIMEOUT_MS exact -> no fire", not fired)
        failures += check("tick at +TIMEOUT_MS -> peer still adopted",
                          lib.mc_harness_peer_have_peer(harness))
        failures += check("tick at +TIMEOUT_MS -> no deletePeer",
                          lib.mc_harness_espnow_delete_peer_count(harness) == 0)

        # Tick at now=6001 (one past TIMEOUT_MS) -> expired, peer forgotten + deletePeer.
        lib.mc_harness_set_now_ms(harness, 6001)
        fired = lib.mc_harness_tick_peer_liveness(harness)
        failures += check("tick at +TIMEOUT_MS+1 -> fired", fired)
        failures += check("after liveness fire -> havePeer=False",
                          not lib.mc_harness_peer_have_peer(harness))
        failures += check("after liveness fire -> deletePeer count == 1",
                          lib.mc_harness_espnow_delete_peer_count(harness) == 1)
        deleted_mac = (ctypes.c_ubyte * 6)()
        lib.mc_harness_espnow_last_deleted_mac(harness, deleted_mac, 6)
        failures += check("after liveness fire -> deletePeer mac == original",
                          bytes(deleted_mac) == MAC,
                          f"got={bytes(deleted_mac).hex()} want={MAC.hex()}")

        # Tick again after fire -> no-op (no peer).
        fired = lib.mc_harness_tick_peer_liveness(harness)
        failures += check("tick after liveness fire -> no fire", not fired)
        failures += check("tick after liveness fire -> deletePeer still 1",
                          lib.mc_harness_espnow_delete_peer_count(harness) == 1)

        # --- Modem.canStartNextTx guard predicate (replaces the first guard +
        # stagger block of main.cpp's startNextQueuedTx()) ---
        # Reset FSM to RxListen explicitly (the liveness tests left it RxListen
        # post-tickAckTimeout-fire; the explicit seed is also a sanity check).
        lib.mc_harness_seed_fsm_state(harness, 0)  # RxListen
        failures += check("seed FSM RxListen -> state=0",
                          lib.mc_harness_fsm_state(harness) == 0)

        # Empty queue -> False regardless of radioReady.
        failures += check("canStartNextTx empty queue -> False",
                          not lib.mc_harness_can_start_next_tx(harness, True, 0))

        # Enqueue a non-STOP STATUS frame.
        status_frame = encode(PY.FrameType.STATUS, DIAL, DINRX, 10,
                              (0xC0DE0000 << 32) | 10, payload=b"S")
        r = lib.mc_harness_queue_enqueue(harness, status_frame, len(status_frame),
                                         False, False)
        failures += check("enqueue non-STOP -> Accepted(0)", r == 0)
        failures += check("queue size == 1 after enqueue",
                          lib.mc_harness_queue_size(harness) == 1)

        # radioReady=False -> False even with valid queue + FSM.
        lib.mc_harness_set_now_ms(harness, 1000)
        failures += check("canStartNextTx !radioReady -> False",
                          not lib.mc_harness_can_start_next_tx(harness, False, 0))

        # radioReady=True + FSM=TxBusy -> False (radio is occupied).
        lib.mc_harness_seed_fsm_state(harness, 1)  # TxBusy
        failures += check("canStartNextTx FSM=TxBusy -> False",
                          not lib.mc_harness_can_start_next_tx(harness, True, 0))

        # radioReady=True + FSM=WaitAck -> False (waiting for the previous ACK).
        lib.mc_harness_seed_fsm_state(harness, 2)  # WaitAck
        failures += check("canStartNextTx FSM=WaitAck -> False",
                          not lib.mc_harness_can_start_next_tx(harness, True, 0))

        # Back to RxListen.
        lib.mc_harness_seed_fsm_state(harness, 0)

        # Stagger gate (DUAL_BAND): non-STOP front + now-lastEspNow < TX_STAGGER_MS=6
        # blocks the TX. now=1000, lastEspNowSendMs=999 -> 1ms elapsed -> < 6 -> False.
        failures += check("canStartNextTx non-STOP + stagger (1ms<6) -> False",
                          not lib.mc_harness_can_start_next_tx(harness, True, 999))

        # Boundary: now-lastEspNow == TX_STAGGER_MS=6 -> the < check is False -> True.
        # (1000 - 994 = 6, NOT less than 6, so gate opens.)
        failures += check("canStartNextTx non-STOP + stagger boundary (6ms==6) -> True",
                          lib.mc_harness_can_start_next_tx(harness, True, 994))

        # Well past stagger: 1000 - 0 = 1000ms -> True.
        failures += check("canStartNextTx non-STOP + post-stagger -> True",
                          lib.mc_harness_can_start_next_tx(harness, True, 0))

        # STOP at the front bypasses the stagger gate (safety: STOP must reach LoRa
        # even under heavy ESP-NOW traffic). Enqueue a STOP -> jumps to front.
        stop_frame = encode(PY.FrameType.STOP, DIAL, DINRX, 11,
                            (0xC0DE0000 << 32) | 11, payload=b"!")
        r = lib.mc_harness_queue_enqueue(harness, stop_frame, len(stop_frame),
                                         True, True)
        failures += check("enqueue STOP -> Accepted(0)", r == 0)
        # Stagger violated (lastEspNow=999, now=1000, 1ms < 6) but STOP bypasses.
        failures += check("canStartNextTx STOP + stagger violated -> True (STOP bypass)",
                          lib.mc_harness_can_start_next_tx(harness, True, 999))

        # --- Modem.tickEspNowRx (replaces main.cpp's serviceEspNowRx + the inlined
        # rememberEspNowPeer free function) ---
        # Reset host's writtenLines indirectly: the harness keeps accumulating, so
        # we'll just snapshot pre-counts and assert deltas.
        pre_lines = lib.mc_harness_written_line_count(harness)
        pre_foreign = lib.mc_harness_foreign_dropped(harness)
        pre_add = lib.mc_harness_espnow_add_peer_count(harness)
        failures += check("tickEspNowRx empty queue -> no side effects", True)
        lib.mc_harness_tick_espnow_rx(harness)
        failures += check("empty rx queue -> no host lines added",
                          lib.mc_harness_written_line_count(harness) == pre_lines)
        failures += check("empty rx queue -> foreignDropped unchanged",
                          lib.mc_harness_foreign_dropped(harness) == pre_foreign)
        failures += check("empty rx queue -> no addPeer",
                          lib.mc_harness_espnow_add_peer_count(harness) == pre_add)

        # Seed a foreign frame (no protocol header) -> foreignDropped++ + no host line.
        SRC_MAC = bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66])
        garbage = bytes([0x00] * 16)
        lib.mc_harness_seed_espnow_rx(harness, SRC_MAC, garbage, len(garbage))
        lib.mc_harness_tick_espnow_rx(harness)
        failures += check("foreign frame -> foreignDropped += 1",
                          lib.mc_harness_foreign_dropped(harness) == pre_foreign + 1)
        failures += check("foreign frame -> no addPeer (header check failed first)",
                          lib.mc_harness_espnow_add_peer_count(harness) == pre_add)
        failures += check("foreign frame -> no host line",
                          lib.mc_harness_written_line_count(harness) == pre_lines)

        # Seed a valid protocol frame -> addPeer called + RX line written +
        # tryConsumeAck attempted (FSM is RxListen so no actual consume).
        valid = encode(PY.FrameType.STATUS, DIAL, DINRX, 200,
                       (0xFADE0000 << 32) | 200, payload=b"hello")
        lib.mc_harness_seed_espnow_rx(harness, SRC_MAC, valid, len(valid))
        lib.mc_harness_tick_espnow_rx(harness)
        failures += check("valid frame -> addPeer count += 1",
                          lib.mc_harness_espnow_add_peer_count(harness) == pre_add + 1)
        added_mac = (ctypes.c_ubyte * 6)()
        lib.mc_harness_espnow_last_added_mac(harness, added_mac, 6)
        failures += check("valid frame -> addPeer mac == SRC_MAC",
                          bytes(added_mac) == SRC_MAC)
        failures += check("valid frame -> peerTracker.havePeer=True",
                          lib.mc_harness_peer_have_peer(harness))
        last_line = ""
        n_lines = lib.mc_harness_written_line_count(harness)
        if n_lines == pre_lines + 1:
            buf = (ctypes.c_char * 256)()
            length = lib.mc_harness_written_line(harness, n_lines - 1, buf, 256)
            last_line = bytes(buf[:length]).decode("ascii", errors="replace") if length >= 0 else ""
        failures += check("valid frame -> exactly one new host line",
                          n_lines == pre_lines + 1, f"n={n_lines} pre={pre_lines}")
        failures += check("host line starts with 'RX 0.0 0.0 '",
                          last_line.startswith("RX 0.0 0.0 "),
                          f"line={last_line!r}")
        # Hex should match the frame's encoding (firmware bytesToHex uses uppercase).
        expected_hex = valid.hex().upper()
        failures += check("host line hex == frame.hex().upper()",
                          last_line == f"RX 0.0 0.0 {expected_hex}",
                          f"line={last_line!r}")

        # Same MAC arrives again -> Refreshed (no addPeer), still logs RX.
        pre_add2 = lib.mc_harness_espnow_add_peer_count(harness)
        pre_lines2 = lib.mc_harness_written_line_count(harness)
        valid2 = encode(PY.FrameType.STATUS, DIAL, DINRX, 201,
                        (0xFADE0000 << 32) | 201, payload=b"world")
        lib.mc_harness_seed_espnow_rx(harness, SRC_MAC, valid2, len(valid2))
        lib.mc_harness_tick_espnow_rx(harness)
        failures += check("refresh peer -> no addPeer",
                          lib.mc_harness_espnow_add_peer_count(harness) == pre_add2)
        failures += check("refresh peer -> +1 host line (RX log)",
                          lib.mc_harness_written_line_count(harness) == pre_lines2 + 1)

        # Two items in queue at once -> drain both in a single tick.
        lib.mc_harness_seed_espnow_rx(harness, SRC_MAC, valid, len(valid))
        lib.mc_harness_seed_espnow_rx(harness, SRC_MAC, valid2, len(valid2))
        pre_lines3 = lib.mc_harness_written_line_count(harness)
        lib.mc_harness_tick_espnow_rx(harness)
        failures += check("drain 2 items in one tick -> +2 host lines",
                          lib.mc_harness_written_line_count(harness) == pre_lines3 + 2)
    finally:
        lib.mc_harness_destroy(harness)

    # --- Modem.tickHealthReport (replaces 2s throttle + reportHealth body) ---
    # Fresh harness so counters / lastHealthMs_ are zero for deterministic asserts.
    hr_buf = (ctypes.c_ubyte * h_size)()
    lib.mc_harness_init(hr_buf)
    try:
        # Pre-deadline: 1999 ms < HEALTH_INTERVAL_MS=2000 -> False, no host line.
        failures += check("tickHealthReport at 1999 -> False (throttled)",
                          not lib.mc_harness_tick_health_report(hr_buf, 1999, 0, 0))
        failures += check("tickHealthReport at 1999 -> no host line",
                          lib.mc_harness_written_line_count(hr_buf) == 0)

        # At threshold: 2000 ms == HEALTH_INTERVAL_MS -> fires once.
        failures += check("tickHealthReport at 2000 -> True (fired)",
                          lib.mc_harness_tick_health_report(hr_buf, 2000, 5, 32))
        failures += check("tickHealthReport at 2000 -> 1 host line",
                          lib.mc_harness_written_line_count(hr_buf) == 1)

        buf = (ctypes.c_char * 128)()
        length = lib.mc_harness_written_line(hr_buf, 0, buf, 128)
        line = bytes(buf[:length]).decode("ascii", errors="replace")
        expected = "OK HEALTH foreign=0 qdrop=5 rxfree=32 peer=0 dutyskip=0"
        failures += check("health line format",
                          line == expected,
                          f"got={line!r} want={expected!r}")

        # 500 ms later: still throttled (only 500 ms since last fire).
        failures += check("tickHealthReport at 2500 -> False (500ms < 2000)",
                          not lib.mc_harness_tick_health_report(hr_buf, 2500, 5, 32))
        failures += check("tickHealthReport at 2500 -> still 1 line",
                          lib.mc_harness_written_line_count(hr_buf) == 1)

        # 4000 ms: exactly 2000 ms since last -> fires again.
        failures += check("tickHealthReport at 4000 -> True (fires again)",
                          lib.mc_harness_tick_health_report(hr_buf, 4000, 7, 30))
        failures += check("tickHealthReport at 4000 -> 2 lines",
                          lib.mc_harness_written_line_count(hr_buf) == 2)
        length = lib.mc_harness_written_line(hr_buf, 1, buf, 128)
        line2 = bytes(buf[:length]).decode("ascii", errors="replace")
        expected2 = "OK HEALTH foreign=0 qdrop=7 rxfree=30 peer=0 dutyskip=0"
        failures += check("health line 2 reflects new qdrop/rxfree",
                          line2 == expected2,
                          f"got={line2!r} want={expected2!r}")

        # Counter values propagate: enqueue a foreign frame to bump foreignDropped,
        # then re-fire health and check the field updated.
        garbage = bytes([0x00] * 16)
        SRC = bytes([0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE])
        lib.mc_harness_seed_espnow_rx(hr_buf, SRC, garbage, len(garbage))
        lib.mc_harness_tick_espnow_rx(hr_buf)
        failures += check("post-garbage foreignDropped == 1",
                          lib.mc_harness_foreign_dropped(hr_buf) == 1)
        # Next fire at 6000 ms (2000 ms after last health fire at 4000).
        failures += check("tickHealthReport at 6000 -> True",
                          lib.mc_harness_tick_health_report(hr_buf, 6000, 7, 30))
        # Third health line: index 2 (after the two earlier + the foreign tickEspNowRx
        # didn't add any line because the garbage failed hasProtocolHeader).
        length = lib.mc_harness_written_line(hr_buf, 2, buf, 128)
        line3 = bytes(buf[:length]).decode("ascii", errors="replace")
        expected3 = "OK HEALTH foreign=1 qdrop=7 rxfree=30 peer=0 dutyskip=0"
        failures += check("health line 3 reflects foreignDropped=1",
                          line3 == expected3,
                          f"got={line3!r} want={expected3!r}")
    finally:
        lib.mc_harness_destroy(hr_buf)

    # --- Modem.tickRadioRx (replaces main.cpp handleRxFromIrq body) ---
    # Fresh harness so counters / state are zeroed.
    rrx = (ctypes.c_ubyte * h_size)()
    lib.mc_harness_init(rrx)
    try:
        # Empty frame (HW read failed): no log, no counter change, but still re-arms
        # (startReceive called) + forceListenIfNotWaitingAck (FSM stays RxListen).
        lib.mc_harness_tick_radio_rx(rrx, None, 0, -65.5, 8.2)
        failures += check("empty frame -> no host line",
                          lib.mc_harness_written_line_count(rrx) == 0)
        failures += check("empty frame -> foreignDropped unchanged (0)",
                          lib.mc_harness_foreign_dropped(rrx) == 0)
        failures += check("empty frame -> startReceive count == 1 (re-arm)",
                          lib.mc_harness_start_receive_count(rrx) == 1)

        # Garbage frame (no protocol header) -> foreignDropped++ + re-arm.
        garbage = bytes([0] * 16)
        lib.mc_harness_tick_radio_rx(rrx, garbage, len(garbage), -70.0, 5.0)
        failures += check("garbage frame -> foreignDropped == 1",
                          lib.mc_harness_foreign_dropped(rrx) == 1)
        failures += check("garbage frame -> still no host line",
                          lib.mc_harness_written_line_count(rrx) == 0)
        failures += check("garbage frame -> startReceive count == 2",
                          lib.mc_harness_start_receive_count(rrx) == 2)

        # Valid STATUS frame, FSM=RxListen -> "RX rssi snr hex" line, no rxOther bump.
        status = encode(PY.FrameType.STATUS, DINRX, DIAL, 30,
                        (0xBABA0000 << 32) | 30, payload=b"ping")
        lib.mc_harness_tick_radio_rx(rrx, status, len(status), -65.5, 8.2)
        failures += check("valid STATUS @ RxListen -> 1 host line",
                          lib.mc_harness_written_line_count(rrx) == 1)
        buf = (ctypes.c_char * 256)()
        n = lib.mc_harness_written_line(rrx, 0, buf, 256)
        line = bytes(buf[:n]).decode("ascii", errors="replace")
        expected_rx = f"RX -65.5 8.2 {status.hex().upper()}"
        failures += check("RX line format == 'RX -65.5 8.2 <UPPER_HEX>'",
                          line == expected_rx,
                          f"got={line!r} want={expected_rx!r}")
        failures += check("RxListen frame -> rxOtherCount unchanged",
                          lib.mc_harness_rx_other_count(rrx) == 0)
        failures += check("RxListen frame -> startReceive count == 3",
                          lib.mc_harness_start_receive_count(rrx) == 3)

        # Seed WaitAck with a FIRE; matching ACK arrives -> tryConsumeAck succeeds,
        # FSM -> RxListen, line still emitted, no rxOtherCount increment.
        fire = encode(PY.FrameType.FIRE, DIAL, DINRX, 88,
                      (0xCAFE0000 << 32) | 88, payload=b"GO")
        lib.mc_harness_seed_wait_ack(rrx, 5000, fire, len(fire))
        failures += check("seed -> WaitAck(2)",
                          lib.mc_harness_fsm_state(rrx) == 2)
        match_ack = encode(PY.FrameType.ACK, DINRX, DIAL, 88,
                           (0xCAFE0000 << 32) | 88, payload=b"OK")
        lib.mc_harness_tick_radio_rx(rrx, match_ack, len(match_ack), -50.0, 9.5)
        failures += check("matching ACK @ WaitAck -> RxListen(0)",
                          lib.mc_harness_fsm_state(rrx) == 0)
        failures += check("matching ACK @ WaitAck -> +1 host line",
                          lib.mc_harness_written_line_count(rrx) == 2)
        failures += check("matching ACK @ WaitAck -> rxOtherCount unchanged (0)",
                          lib.mc_harness_rx_other_count(rrx) == 0)

        # Re-seed WaitAck with the same FIRE; this time a non-matching frame
        # arrives (STATUS instead of an ACK -> tryConsumeAck=False, was WaitAck
        # -> rxOtherCount++). FSM stays WaitAck after forceListenIfNotWaitingAck.
        lib.mc_harness_seed_wait_ack(rrx, 10000, fire, len(fire))
        non_match = encode(PY.FrameType.STATUS, DINRX, DIAL, 99,
                           (0xCAFE0000 << 32) | 99, payload=b"x")
        lib.mc_harness_tick_radio_rx(rrx, non_match, len(non_match), -60.0, 7.0)
        failures += check("non-matching frame @ WaitAck -> rxOtherCount == 1",
                          lib.mc_harness_rx_other_count(rrx) == 1)
        failures += check("non-matching frame @ WaitAck -> FSM stays WaitAck",
                          lib.mc_harness_fsm_state(rrx) == 2)
        failures += check("non-matching frame -> +1 host line",
                          lib.mc_harness_written_line_count(rrx) == 3)
    finally:
        lib.mc_harness_destroy(rrx)

    # --- Modem.tickTxComplete (replaces main.cpp finishTxFromIrq's FSM/log part) ---
    tx = (ctypes.c_ubyte * h_size)()
    lib.mc_harness_init(tx)
    try:
        fire_tx = encode(PY.FrameType.FIRE, DIAL, DINRX, 42,
                         (0xDEAF0000 << 32) | 42, payload=b"GO")

        # 1) TxBusy + waitForAck=False + tickTxComplete(0) -> completeTx returns
        # RxListen, host emits "OK TX", FSM=RxListen.
        lib.mc_harness_seed_tx_busy(tx, fire_tx, len(fire_tx), False)
        failures += check("seed TxBusy -> state=1",
                          lib.mc_harness_fsm_state(tx) == 1)
        lib.mc_harness_set_now_ms(tx, 1000)
        lib.mc_harness_tick_tx_complete(tx, 0)
        failures += check("tickTxComplete(0, !waitAck) -> RxListen(0)",
                          lib.mc_harness_fsm_state(tx) == 0)
        failures += check("tickTxComplete(0, !waitAck) -> 1 host line",
                          lib.mc_harness_written_line_count(tx) == 1)
        buf = (ctypes.c_char * 64)()
        n = lib.mc_harness_written_line(tx, 0, buf, 64)
        line = bytes(buf[:n]).decode("ascii", errors="replace")
        failures += check("line == 'OK TX'", line == "OK TX",
                          f"got={line!r}")

        # 2) TxBusy + waitForAck=True + tickTxComplete(0) -> completeTx returns
        # WaitAck (deadline armed), NO "OK TX" emitted.
        lib.mc_harness_seed_tx_busy(tx, fire_tx, len(fire_tx), True)
        failures += check("seed TxBusy waitAck -> state=1",
                          lib.mc_harness_fsm_state(tx) == 1)
        pre_lines = lib.mc_harness_written_line_count(tx)
        lib.mc_harness_set_now_ms(tx, 2000)
        lib.mc_harness_tick_tx_complete(tx, 0)
        failures += check("tickTxComplete(0, waitAck) -> WaitAck(2)",
                          lib.mc_harness_fsm_state(tx) == 2)
        failures += check("tickTxComplete(0, waitAck) -> NO new host line",
                          lib.mc_harness_written_line_count(tx) == pre_lines)
        # ACK_TIMEOUT_MS == 900 (Modem const); deadline should be 2000+900 = 2900.
        # (We can't directly read ackDeadlineMs through the harness, but tick at
        # 2899 should leave FSM in WaitAck and at 2900 should fire timeout.)
        lib.mc_harness_set_now_ms(tx, 2899)
        failures += check("pre-deadline ackTimeout still WaitAck",
                          not lib.mc_harness_tick_ack_timeout(tx))
        lib.mc_harness_set_now_ms(tx, 2900)
        failures += check("at-deadline ackTimeout fires", lib.mc_harness_tick_ack_timeout(tx))

        # 3) TxBusy + tickTxComplete(-5) -> error path: emits "ERR TX -5", FSM
        # back to RxListen via abortTx.
        lib.mc_harness_seed_tx_busy(tx, fire_tx, len(fire_tx), True)
        pre_lines = lib.mc_harness_written_line_count(tx)
        lib.mc_harness_tick_tx_complete(tx, -5)
        failures += check("tickTxComplete(error) -> RxListen(0)",
                          lib.mc_harness_fsm_state(tx) == 0)
        failures += check("tickTxComplete(error) -> +1 host line",
                          lib.mc_harness_written_line_count(tx) == pre_lines + 1)
        n = lib.mc_harness_written_line(tx, pre_lines, buf, 64)
        line = bytes(buf[:n]).decode("ascii", errors="replace")
        failures += check("error line == 'ERR TX -5'", line == "ERR TX -5",
                          f"got={line!r}")
    finally:
        lib.mc_harness_destroy(tx)

    # --- Modem.parseHostFrame (replaces main.cpp handleHostLine parser) ---
    # HostCommand enum: 0=LineTooLong, 1=Ping, 2=SendAck, 3=SendNoAck, 4=BadFrame, 5=BadCommand
    ph = (ctypes.c_ubyte * h_size)()
    lib.mc_harness_init(ph)
    try:
        def parse(line: str):
            buf = (ctypes.c_ubyte * 256)()
            out_len = ctypes.c_int(0)
            kind = lib.mc_harness_parse_host_frame(
                ph, line.encode("ascii"), buf, 256, ctypes.byref(out_len)
            )
            return kind, bytes(buf[:out_len.value])

        kind, frame = parse("__LINE_TOO_LONG__")
        failures += check("parseHostFrame __LINE_TOO_LONG__ -> LineTooLong(0)",
                          kind == 0 and len(frame) == 0)
        kind, frame = parse("PING")
        failures += check("parseHostFrame PING -> Ping(1)",
                          kind == 1 and len(frame) == 0)

        # SEND with a valid encoded frame
        send_frame = encode(PY.FrameType.FIRE, DIAL, DINRX, 1,
                            (0xF00D0000 << 32) | 1, payload=b"x")
        kind, frame = parse("SEND " + send_frame.hex())
        failures += check("parseHostFrame SEND <valid> -> SendAck(2)", kind == 2)
        failures += check("parseHostFrame SEND -> frame bytes match",
                          frame == send_frame)

        # ACK + FF dispatch to SendNoAck
        kind, frame = parse("ACK " + send_frame.hex())
        failures += check("parseHostFrame ACK <valid> -> SendNoAck(3)",
                          kind == 3 and frame == send_frame)
        kind, frame = parse("FF " + send_frame.hex())
        failures += check("parseHostFrame FF <valid> -> SendNoAck(3)",
                          kind == 3 and frame == send_frame)

        # Bad hex
        kind, frame = parse("SEND zzzz")
        failures += check("parseHostFrame SEND <bad_hex> -> BadFrame(4)",
                          kind == 4 and len(frame) == 0)
        # Empty hex body
        kind, frame = parse("SEND ")
        failures += check("parseHostFrame SEND <empty> -> BadFrame(4)",
                          kind == 4 and len(frame) == 0)
        # Trailing whitespace tolerated
        kind, frame = parse("SEND " + send_frame.hex() + "\r\n")
        failures += check("parseHostFrame SEND <valid>\\r\\n -> SendAck(2)",
                          kind == 2 and frame == send_frame)

        # Unknown command
        kind, frame = parse("FOOBAR")
        failures += check("parseHostFrame FOOBAR -> BadCommand(5)",
                          kind == 5 and len(frame) == 0)
        kind, frame = parse("")
        failures += check("parseHostFrame '' -> BadCommand(5)",
                          kind == 5 and len(frame) == 0)
    finally:
        lib.mc_harness_destroy(ph)

    # --- Modem.classifyRadioIrq (LoRa IRQ dispatcher) ---
    # IrqAction enum: 0=None, 1=FinishTx, 2=HandleRx, 3=ClearAndReceive.
    # Test bit values: TX_DONE=0x01, RX_DONE=0x02 (arbitrary -- the real RadioLib
    # values are RADIOLIB_SX126X_IRQ_TX_DONE/RX_DONE; classifyRadioIrq is generic).
    TX_DONE, RX_DONE = 0x01, 0x02
    ci = (ctypes.c_ubyte * h_size)()
    lib.mc_harness_init(ci)
    try:
        # FSM=TxBusy (state=1)
        lib.mc_harness_seed_fsm_state(ci, 1)
        failures += check("classifyRadioIrq TxBusy + TX_DONE -> FinishTx(1)",
                          lib.mc_harness_classify_radio_irq(ci, TX_DONE, TX_DONE, RX_DONE) == 1)
        failures += check("classifyRadioIrq TxBusy + RX_DONE -> HandleRx(2)",
                          lib.mc_harness_classify_radio_irq(ci, RX_DONE, TX_DONE, RX_DONE) == 2)
        failures += check("classifyRadioIrq TxBusy + flags=0 -> ClearAndReceive(3)",
                          lib.mc_harness_classify_radio_irq(ci, 0, TX_DONE, RX_DONE) == 3)
        # TX_DONE takes precedence over RX_DONE in TxBusy state.
        failures += check("classifyRadioIrq TxBusy + (TX|RX)_DONE -> FinishTx(1) (TX wins)",
                          lib.mc_harness_classify_radio_irq(ci, TX_DONE | RX_DONE,
                                                             TX_DONE, RX_DONE) == 1)

        # FSM=RxListen (state=0): stray TX_DONE is unexpected -> ClearAndReceive,
        # RX_DONE is a normal RX -> HandleRx.
        lib.mc_harness_seed_fsm_state(ci, 0)
        failures += check("classifyRadioIrq RxListen + TX_DONE -> ClearAndReceive(3)",
                          lib.mc_harness_classify_radio_irq(ci, TX_DONE, TX_DONE, RX_DONE) == 3)
        failures += check("classifyRadioIrq RxListen + RX_DONE -> HandleRx(2)",
                          lib.mc_harness_classify_radio_irq(ci, RX_DONE, TX_DONE, RX_DONE) == 2)
        failures += check("classifyRadioIrq RxListen + flags=0 -> ClearAndReceive(3)",
                          lib.mc_harness_classify_radio_irq(ci, 0, TX_DONE, RX_DONE) == 3)

        # FSM=WaitAck (state=2): RX_DONE is the ACK or stray frame -> HandleRx;
        # everything else just clears + re-arms (tickRadioRx still preserves WaitAck
        # via forceListenIfNotWaitingAck).
        lib.mc_harness_seed_fsm_state(ci, 2)
        failures += check("classifyRadioIrq WaitAck + RX_DONE -> HandleRx(2)",
                          lib.mc_harness_classify_radio_irq(ci, RX_DONE, TX_DONE, RX_DONE) == 2)
        failures += check("classifyRadioIrq WaitAck + flags=0 -> ClearAndReceive(3)",
                          lib.mc_harness_classify_radio_irq(ci, 0, TX_DONE, RX_DONE) == 3)
    finally:
        lib.mc_harness_destroy(ci)

    # --- Modem.enqueueTx (replaces main.cpp queueRadioFrame) ---
    def last_line(p):
        n = lib.mc_harness_written_line_count(p)
        if n == 0:
            return ""
        b = (ctypes.c_char * 128)()
        ln = lib.mc_harness_written_line(p, n - 1, b, 128)
        return bytes(b[:ln]).decode("ascii", errors="replace") if ln >= 0 else ""

    eq = (ctypes.c_ubyte * h_size)()
    lib.mc_harness_init(eq)
    try:
        fire = encode(PY.FrameType.FIRE, DIAL, DINRX, 1,
                      (0xF11E0000 << 32) | 1, payload=b"GO")

        # radioReady=False -> ERR RADIO_NOT_READY, not enqueued.
        failures += check("enqueueTx !radioReady -> False",
                          not lib.mc_harness_enqueue_tx(eq, fire, len(fire), True))
        failures += check("enqueueTx !radioReady -> 'ERR RADIO_NOT_READY'",
                          last_line(eq) == "ERR RADIO_NOT_READY")
        failures += check("enqueueTx !radioReady -> queue empty",
                          lib.mc_harness_queue_size(eq) == 0)

        # radioReady=True, empty frame -> ERR BAD_FRAME.
        lib.mc_harness_set_radio_ready(eq, True)
        failures += check("enqueueTx empty frame -> False",
                          not lib.mc_harness_enqueue_tx(eq, b"", 0, True))
        failures += check("enqueueTx empty frame -> 'ERR BAD_FRAME'",
                          last_line(eq) == "ERR BAD_FRAME")

        # Valid frame, espnowReady=False -> enqueued, NO ESP-NOW send.
        pre_send = lib.mc_harness_espnow_send_count(eq)
        failures += check("enqueueTx valid (espnow off) -> True",
                          lib.mc_harness_enqueue_tx(eq, fire, len(fire), True))
        failures += check("enqueueTx valid -> queue size 1",
                          lib.mc_harness_queue_size(eq) == 1)
        failures += check("enqueueTx espnow off -> no ESP-NOW send",
                          lib.mc_harness_espnow_send_count(eq) == pre_send)

        # espnowReady=True -> ESP-NOW mirror send to BROADCAST (no peer yet).
        lib.mc_harness_set_espnow_ready(eq, True)
        lib.mc_harness_set_now_ms(eq, 5000)
        failures += check("enqueueTx (espnow on) -> True",
                          lib.mc_harness_enqueue_tx(eq, fire, len(fire), False))
        failures += check("enqueueTx espnow on -> send count += 1",
                          lib.mc_harness_espnow_send_count(eq) == pre_send + 1)
        failures += check("enqueueTx espnow on -> sent len == frame len",
                          lib.mc_harness_espnow_last_sent_len(eq) == len(fire))
        dst = (ctypes.c_ubyte * 6)()
        lib.mc_harness_espnow_last_sent_dst(eq, dst, 6)
        failures += check("enqueueTx no-peer -> sent to BROADCAST (FF*6)",
                          bytes(dst) == b"\xFF" * 6)

        # Adopt a peer, then enqueue -> sends to the peer MAC, not broadcast.
        PEER = bytes([0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F])
        lib.mc_harness_peer_commit(eq, PEER, 5000)
        lib.mc_harness_enqueue_tx(eq, fire, len(fire), False)
        lib.mc_harness_espnow_last_sent_dst(eq, dst, 6)
        failures += check("enqueueTx with peer -> sent to peer MAC",
                          bytes(dst) == PEER)
    finally:
        lib.mc_harness_destroy(eq)

    # --- Modem.tickStartNextTx (replaces main.cpp startNextQueuedTx) ---
    # Seed the queue directly (mc_harness_queue_enqueue) so lastEspNowSendMs_ stays 0
    # and the stagger gate is open (now >= TX_STAGGER_MS).
    ts = (ctypes.c_ubyte * h_size)()
    lib.mc_harness_init(ts)
    try:
        lib.mc_harness_set_radio_ready(ts, True)
        lib.mc_harness_set_now_ms(ts, 10000)
        status = encode(PY.FrameType.STATUS, DIAL, DINRX, 5,
                        (0xC0DE0000 << 32) | 5, payload=b"S")

        # radioIrqPending=True -> no-op even with a queued frame.
        lib.mc_harness_queue_enqueue(ts, status, len(status), False, False)
        lib.mc_harness_tick_start_next_tx(ts, True)
        failures += check("tickStartNextTx irqPending -> no startTransmit",
                          lib.mc_harness_start_transmit_count(ts) == 0)
        failures += check("tickStartNextTx irqPending -> frame still queued",
                          lib.mc_harness_queue_size(ts) == 1)

        # Normal path: startTransmit called, frame popped, FSM -> TxBusy.
        lib.mc_harness_tick_start_next_tx(ts, False)
        failures += check("tickStartNextTx -> startTransmit count 1",
                          lib.mc_harness_start_transmit_count(ts) == 1)
        txbuf = (ctypes.c_ubyte * 128)()
        n = lib.mc_harness_last_tx_frame(ts, txbuf, 128)
        failures += check("tickStartNextTx -> startTransmit got the frame",
                          bytes(txbuf[:n]) == status)
        failures += check("tickStartNextTx -> queue drained",
                          lib.mc_harness_queue_size(ts) == 0)
        failures += check("tickStartNextTx -> FSM TxBusy(1)",
                          lib.mc_harness_fsm_state(ts) == 1)

        # startTransmit failure (non-STOP): ERR TX, FSM -> RxListen, NOT re-queued.
        lib.mc_harness_seed_fsm_state(ts, 0)  # back to RxListen
        lib.mc_harness_set_tx_result(ts, -7)
        lib.mc_harness_queue_enqueue(ts, status, len(status), False, False)
        pre_lines = lib.mc_harness_written_line_count(ts)
        lib.mc_harness_tick_start_next_tx(ts, False)
        failures += check("tickStartNextTx TX fail non-STOP -> RxListen(0)",
                          lib.mc_harness_fsm_state(ts) == 0)
        failures += check("tickStartNextTx TX fail non-STOP -> not re-queued",
                          lib.mc_harness_queue_size(ts) == 0)
        b = (ctypes.c_char * 64)()
        ln = lib.mc_harness_written_line(ts, pre_lines, b, 64)
        failures += check("tickStartNextTx TX fail -> 'ERR TX -7'",
                          bytes(b[:ln]).decode("ascii", errors="replace") == "ERR TX -7")

        # startTransmit failure (STOP): re-queued at front (bounded retry).
        lib.mc_harness_seed_fsm_state(ts, 0)
        stop = encode(PY.FrameType.STOP, DIAL, DINRX, 6,
                      (0xC0DE0000 << 32) | 6, payload=b"!")
        lib.mc_harness_queue_enqueue(ts, stop, len(stop), True, True)
        lib.mc_harness_tick_start_next_tx(ts, False)
        failures += check("tickStartNextTx TX fail STOP -> re-queued at front",
                          lib.mc_harness_queue_size(ts) == 1)

        # Recover (tx result 0), drain the retried STOP.
        lib.mc_harness_set_tx_result(ts, 0)
        lib.mc_harness_seed_fsm_state(ts, 0)
        lib.mc_harness_tick_start_next_tx(ts, False)
        failures += check("tickStartNextTx STOP retry success -> drained",
                          lib.mc_harness_queue_size(ts) == 0)
        failures += check("tickStartNextTx STOP retry success -> TxBusy(1)",
                          lib.mc_harness_fsm_state(ts) == 1)
    finally:
        lib.mc_harness_destroy(ts)

    # --- tickStartNextTx duty gate (ERR DUTY for non-STOP; STOP bypasses) ---
    dg = (ctypes.c_ubyte * h_size)()
    lib.mc_harness_init(dg)
    try:
        lib.mc_harness_set_radio_ready(dg, True)
        lib.mc_harness_set_now_ms(dg, 10000)
        # Fill the duty bucket to the cap so wouldExceedOnAdd(LORA_AIRTIME_MS_EST) is true.
        lib.mc_harness_duty_add(dg, 36000)  # CAP_MS; clamps at cap
        status = encode(PY.FrameType.STATUS, DIAL, DINRX, 7,
                        (0xDDDD0000 << 32) | 7, payload=b"S")
        lib.mc_harness_queue_enqueue(dg, status, len(status), False, False)
        pre_drop = lib.mc_harness_duty_dropped(dg)
        pre_tx = lib.mc_harness_start_transmit_count(dg)
        lib.mc_harness_tick_start_next_tx(dg, False)
        failures += check("tickStartNextTx duty-exceed non-STOP -> dropped += 1",
                          lib.mc_harness_duty_dropped(dg) == pre_drop + 1)
        failures += check("tickStartNextTx duty-exceed non-STOP -> no startTransmit",
                          lib.mc_harness_start_transmit_count(dg) == pre_tx)
        failures += check("tickStartNextTx duty-exceed non-STOP -> 'ERR DUTY'",
                          last_line(dg) == "ERR DUTY")

        # STOP bypasses the duty gate even at cap -> startTransmit happens.
        lib.mc_harness_seed_fsm_state(dg, 0)
        stop = encode(PY.FrameType.STOP, DIAL, DINRX, 8,
                      (0xDDDD0000 << 32) | 8, payload=b"!")
        lib.mc_harness_queue_enqueue(dg, stop, len(stop), True, True)
        lib.mc_harness_tick_start_next_tx(dg, False)
        failures += check("tickStartNextTx STOP bypasses duty gate -> startTransmit",
                          lib.mc_harness_start_transmit_count(dg) == pre_tx + 1)
        failures += check("tickStartNextTx STOP bypass -> FSM TxBusy(1)",
                          lib.mc_harness_fsm_state(dg) == 1)
    finally:
        lib.mc_harness_destroy(dg)

    # --- Callback-HAL Modem (sim_link wiring foundation) ---
    # Drive the REAL modem_core::Modem through Python-supplied HAL callbacks, exactly
    # as sim_link.py will. Proves the callback path end-to-end before the sim rewire.
    state = {"t": 1000}
    host_lines: list[str] = []
    tx_frames: list[bytes] = []
    esp_sends: list[tuple] = []
    esp_rx: list[tuple] = []  # FIFO of (src_bytes, data_bytes)

    def _now(ctx):
        return state["t"]

    def _write(ctx, line):
        host_lines.append(line.decode("ascii", errors="replace") if line else "")

    def _starttx(ctx, data, length):
        tx_frames.append(ctypes.string_at(data, length))
        return 0  # OK

    def _espsend(ctx, mac, data, length):
        esp_sends.append((ctypes.string_at(mac, 6), ctypes.string_at(data, length)))
        return 1

    def _espadd(ctx, mac):
        return 1

    def _espdel(ctx, mac):
        return None

    def _esppoll(ctx, src6, data_out, cap):
        if not esp_rx:
            return -1
        src, data = esp_rx.pop(0)
        ctypes.memmove(src6, src, 6)
        n = min(len(data), cap)
        ctypes.memmove(data_out, data, n)
        return n

    # Keep CFUNCTYPE instances alive for the handle's lifetime (ctypes won't).
    keep = [CB_NOW_MS(_now), CB_WRITE_LINE(_write), CB_START_TX(_starttx),
            CB_ESP_SEND(_espsend), CB_ESP_ADD_PEER(_espadd), CB_ESP_DEL_PEER(_espdel),
            CB_ESP_POLL_RX(_esppoll)]
    cm = lib.mc_cbmodem_create(None, *keep, 1)  # has_espnow=1
    try:
        lib.mc_cbmodem_set_radio_ready(cm, 1)
        lib.mc_cbmodem_set_espnow_ready(cm, 1)

        DIAL2, RX2 = 0x11, 0x22
        seq = 7
        nonce = (0x5A5A0000 << 32) | seq
        fire = encode(PY.FrameType.FIRE, DIAL2, RX2, seq, nonce, payload=b"GO")

        # enqueueTx: queued + ESP-NOW mirror to broadcast, no error line.
        ok = lib.mc_cbmodem_enqueue_tx(cm, fire, len(fire), 1)
        failures += check("cbmodem enqueueTx -> accepted", ok == 1)
        failures += check("cbmodem enqueueTx -> queue size 1",
                          lib.mc_cbmodem_queue_size(cm) == 1)
        failures += check("cbmodem enqueueTx -> 1 ESP-NOW send", len(esp_sends) == 1)
        failures += check("cbmodem enqueueTx -> sent to BROADCAST",
                          esp_sends[0][0] == b"\xFF" * 6)
        failures += check("cbmodem enqueueTx -> ESP-NOW payload == fire",
                          esp_sends[0][1] == fire)
        failures += check("cbmodem enqueueTx -> no host error line",
                          len(host_lines) == 0)

        # tickStartNextTx after the stagger window (advance clock past TX_STAGGER_MS=6).
        state["t"] = 1010
        lib.mc_cbmodem_tick_start_next_tx(cm, 0)
        failures += check("cbmodem tickStartNextTx -> startTransmit got the fire",
                          len(tx_frames) == 1 and tx_frames[0] == fire)
        failures += check("cbmodem tickStartNextTx -> FSM TxBusy(1)",
                          lib.mc_cbmodem_fsm_state(cm) == 1)
        failures += check("cbmodem tickStartNextTx -> queue drained",
                          lib.mc_cbmodem_queue_size(cm) == 0)

        # tickTxComplete(0) with waitForAck -> WaitAck (no OK TX).
        lib.mc_cbmodem_tick_tx_complete(cm, 0)
        failures += check("cbmodem tickTxComplete(waitAck) -> WaitAck(2)",
                          lib.mc_cbmodem_fsm_state(cm) == 2)

        # A matching ACK arrives over ESP-NOW -> tickEspNowRx consumes it -> RxListen.
        match_ack = encode(PY.FrameType.ACK, RX2, DIAL2, seq, nonce, payload=b"OK")
        esp_rx.append((bytes([0xAA] * 6), match_ack))
        lib.mc_cbmodem_tick_espnow_rx(cm)
        failures += check("cbmodem matching ACK via tickEspNowRx -> RxListen(0)",
                          lib.mc_cbmodem_fsm_state(cm) == 0)
        failures += check("cbmodem ACK source adopted as peer",
                          lib.mc_cbmodem_have_peer(cm) == 1)
        # The RX log line was emitted for the ACK frame.
        failures += check("cbmodem tickEspNowRx -> RX host line emitted",
                          any(line.startswith("RX 0.0 0.0 ") for line in host_lines))

        # ERR BUSY: fill the queue (DEPTH=4) with non-STOP, 5th rejected.
        host_lines.clear()
        for i in range(4):
            f = encode(PY.FrameType.STATUS, DIAL2, RX2, 20 + i,
                       (0x5A5A0000 << 32) | (20 + i), payload=bytes([i]))
            lib.mc_cbmodem_enqueue_tx(cm, f, len(f), 0)
        extra = encode(PY.FrameType.STATUS, DIAL2, RX2, 99,
                       (0x5A5A0000 << 32) | 99, payload=b"x")
        ok = lib.mc_cbmodem_enqueue_tx(cm, extra, len(extra), 0)
        failures += check("cbmodem 5th non-STOP -> rejected", ok == 0)
        failures += check("cbmodem queue full -> 'ERR BUSY' host line",
                          "ERR BUSY" in host_lines)
    finally:
        lib.mc_cbmodem_destroy(cm)
        del keep  # callbacks no longer referenced by C

    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILURES'}")
    return failures


if __name__ == "__main__":
    sys.exit(main())
