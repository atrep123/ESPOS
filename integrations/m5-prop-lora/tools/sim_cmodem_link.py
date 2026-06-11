"""End-to-end dual-modem link driven by the REAL firmware modem_core::Modem.

This is the slice-3.2 capstone of "wire the simulator to modem_core": it builds TWO
actual modem_core::Modem instances (the Dial-side modem A and the DinMeter-side modem
B) through the callback HAL (tools/sim_native/modem_abi.cpp, exercised via ctypes),
wires them to a minimal in-process dual-band channel + shared clock, and runs a real
ARM -> FIRE -> ACK exchange. The modem decision logic (TxQueue / DutyBucket / RadioFsm
ACK matching / PeerTracker / STOP priority) is the firmware's, not a Python parallel.

Unlike tools/sim_link.py (which models the modem in Python and only bridges the ACK
matcher), here the modems ARE modem_core. The "apps" above each modem (Dial sender,
DinMeter receiver) are tiny Python shims that talk to their modem exactly like the
real firmware apps do: they call enqueueTx to send, and parse the modem's host lines
("RX <rssi> <snr> <hex>", "OK TX", "ERR ...") to receive.

Run:  python tools/sim_cmodem_link.py            (report)
      python tools/sim_cmodem_link.py --selftest (assertions)
"""
from __future__ import annotations

import argparse
import ctypes
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (os.path.join(ROOT, "shared"), os.path.join(ROOT, "shared", "protocol"),
             os.path.join(HERE, "sim_native")):
    if path not in sys.path:
        sys.path.insert(0, path)

import protocol as PY  # noqa: E402
import check_modem_core as CMC  # reuse load_dll + the CB_* CFUNCTYPE signatures  # noqa: E402

KEY_ID = 1
KEYS = {KEY_ID: CMC.SHARED_KEY}
DIAL_ADDR, RX_ADDR = 0x11, 0x22
LORA_BAND, ESPNOW_BAND = 0, 1
MAC_A = bytes([0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5])
MAC_B = bytes([0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5])


def clamp01(x):
    return max(0.0, min(1.0, x))


def lora_airtime_ms(payload_len):
    """Semtech LoRa airtime for the M5 link params (SF7 / BW250 / CR4:5 / preamble 8 /
    CRC on). Ported verbatim from sim_link.py so the cmodem link uses the same real
    on-air time for collision + duty + delivery timing."""
    sf, bw_hz, coding_rate, preamble, crc, implicit_header = 7, 250000.0, 1, 8, 1, 0
    low_data_rate = 1 if sf >= 11 and bw_hz <= 125000.0 else 0
    tsym_ms = (2 ** sf) / bw_hz * 1000.0
    numerator = 8 * int(payload_len) - 4 * sf + 28 + 16 * crc - 20 * implicit_header
    denominator = 4 * (sf - 2 * low_data_rate)
    payload_symbols = 8 + max(math.ceil(numerator / denominator) * (coding_rate + 4), 0)
    preamble_symbols = preamble + 4.25
    return (preamble_symbols + payload_symbols) * tsym_ms


class GilbertElliott:
    """Two-state burst-loss model (ported from sim_link.py): a 'bad' state with high
    loss that persists for runs, layered on top of a base i.i.d. loss. Models the
    real correlated fading the M5 link sees, not unrealistic independent drops."""

    def __init__(self, rng, enter_bad, stay_bad, good_loss, bad_loss):
        self.rng = rng
        self.enter_bad = float(enter_bad)
        self.stay_bad = float(stay_bad)
        self.good_loss = float(good_loss)
        self.bad_loss = float(bad_loss)
        self.bad = False

    def loss(self, base_loss):
        if self.bad:
            self.bad = self.rng.random() < self.stay_bad
        else:
            self.bad = self.rng.random() < self.enter_bad
        burst_loss = self.bad_loss if self.bad else self.good_loss
        combined = 1.0 - (1.0 - clamp01(base_loss)) * (1.0 - clamp01(burst_loss))
        return self.rng.random() < combined


class Clock:
    def __init__(self):
        self.now_ms = 0


class _LoraTx:
    __slots__ = ("start", "end", "dst", "raw", "src_mac", "collided", "lost", "deliver_at")

    def __init__(self, start, end, dst, raw, src_mac, lost, turnaround):
        self.start = start
        self.end = end
        self.dst = dst
        self.raw = raw
        self.src_mac = src_mac
        self.collided = False
        self.lost = lost
        self.deliver_at = end + turnaround


class Channel:
    """Faithful dual-band channel ported from sim_link.py's DualBandChannel: real LoRa
    airtime (Semtech formula), Gilbert-Elliott burst loss per band, LoRa co-channel
    collision (overlapping on-air windows), and half-duplex deafness (a modem TXing
    LoRa cannot hear an inbound LoRa frame). ESP-NOW is a separate fast 2.4 GHz band
    (latency + GE loss, no collision/deafness). Deterministic via the supplied RNG."""

    def __init__(self, clock, rng, lora_loss=0.0, espnow_loss=0.0,
                 lora_ge=(0.0, 0.0, 0.0, 0.0), espnow_ge=(0.0, 0.0, 0.0, 0.0),
                 lora_turnaround=2.0):
        self.clock = clock
        self.rng = rng
        self.lora_loss = lora_loss
        self.espnow_loss = espnow_loss
        self.lora_ge = GilbertElliott(rng, *lora_ge)
        self.espnow_ge = GilbertElliott(rng, *espnow_ge)
        self.lora_turnaround = lora_turnaround
        self.active_lora = []          # in-flight _LoraTx (shared on-air medium)
        self.espnow_inflight = []      # (deliver_at, dst_node, raw, src_mac)
        self.counters = {"lora_lost": 0, "espnow_lost": 0, "lora_tx": 0,
                         "espnow_tx": 0, "lora_collisions": 0, "lora_deaf_drops": 0}

    def send(self, band, src_node, dst_node, raw, src_mac):
        now = self.clock.now_ms
        if band == ESPNOW_BAND:
            self.counters["espnow_tx"] += 1
            if self.espnow_ge.loss(self.espnow_loss):
                self.counters["espnow_lost"] += 1
                return
            self.espnow_inflight.append((now + 2, dst_node, raw, src_mac))
            return

        # LoRa: occupy the shared medium for the frame's airtime.
        self.counters["lora_tx"] += 1
        airtime = lora_airtime_ms(len(raw))
        start, end = now, now + airtime
        src_node.note_lora_tx(start, end)  # for the OTHER end's deafness check
        lost = self.lora_ge.loss(self.lora_loss)
        if lost:
            self.counters["lora_lost"] += 1
        tx = _LoraTx(start, end, dst_node, raw, src_mac, lost, self.lora_turnaround)
        # Co-channel collision: any temporal overlap with another in-flight LoRa TX
        # (a lost frame still occupies the air, so it can still collide others).
        for other in self.active_lora:
            if other.start < tx.end and tx.start < other.end:
                if not other.collided:
                    self.counters["lora_collisions"] += 1
                other.collided = True
                tx.collided = True
        self.active_lora.append(tx)

    def deliver_due(self):
        """Hand every frame whose delivery time has passed to its destination modem,
        applying loss / collision / deafness exactly like the real RF channel."""
        now = self.clock.now_ms
        # ESP-NOW (no collision / deafness).
        ready_esp = [it for it in self.espnow_inflight if it[0] <= now]
        self.espnow_inflight = [it for it in self.espnow_inflight if it[0] > now]
        for _, dst_node, raw, src_mac in ready_esp:
            dst_node.on_channel_frame(ESPNOW_BAND, raw, src_mac)
        # LoRa: deliver at end-of-airtime + turnaround; drop if lost/collided/deaf.
        ready_lora = [tx for tx in self.active_lora if tx.deliver_at <= now]
        self.active_lora = [tx for tx in self.active_lora if tx.deliver_at > now]
        for tx in ready_lora:
            if tx.lost or tx.collided:
                continue
            if tx.dst.is_lora_deaf(tx.start, tx.end):
                self.counters["lora_deaf_drops"] += 1
                continue
            tx.dst.on_channel_frame(LORA_BAND, tx.raw, tx.src_mac)


class ModemNode:
    """One real modem_core::Modem (via the callback HAL) + the channel/clock binding.

    Owns the ctypes callbacks (kept alive in self._cb) and the cbmodem handle. The
    `app` is an object with on_rx(frame, band) / on_ok_tx() / on_err(reason) hooks
    that the modem's host-line output is routed to (mirrors the real UART app)."""

    def __init__(self, lib, clock, channel, my_mac, peer_node_getter, app):
        self.lib = lib
        self.clock = clock
        self.channel = channel
        self.my_mac = my_mac
        self._peer_node = peer_node_getter  # callable -> the other ModemNode
        self.app = app
        self.espnow_inbox = []  # FIFO of (src_mac, raw) for tickEspNowRx -> esp_poll_rx
        self.host_lines = []
        self.lora_tx_windows = []  # (start,end) of this node's LoRa TXs (half-duplex deafness)

        # --- HAL callbacks (must outlive the handle) ---
        def now_ms(ctx):
            return self.clock.now_ms

        def write_line(ctx, line):
            text = line.decode("ascii", errors="replace") if line else ""
            self.host_lines.append(text)
            self._route_host_line(text)

        def start_transmit(ctx, data, length):
            raw = ctypes.string_at(data, length)
            self.channel.send(LORA_BAND, self, self._peer_node(), raw, self.my_mac)
            # Faithful to the firmware: TX completes a bit later (airtime) -> the app
            # layer triggers tick_tx_complete; here we self-schedule via a marker.
            self._pending_tx_complete = True
            return 0  # RADIOLIB_ERR_NONE

        def esp_send(ctx, mac, data, length):
            raw = ctypes.string_at(data, length)
            self.channel.send(ESPNOW_BAND, self, self._peer_node(), raw, self.my_mac)
            return 1

        def esp_add_peer(ctx, mac):
            return 1

        def esp_delete_peer(ctx, mac):
            return None

        def esp_poll_rx(ctx, src6, data_out, cap):
            if not self.espnow_inbox:
                return -1
            src, raw = self.espnow_inbox.pop(0)
            ctypes.memmove(src6, src, 6)
            n = min(len(raw), cap)
            ctypes.memmove(data_out, raw, n)
            return n

        self._cb = [CMC.CB_NOW_MS(now_ms), CMC.CB_WRITE_LINE(write_line),
                    CMC.CB_START_TX(start_transmit), CMC.CB_ESP_SEND(esp_send),
                    CMC.CB_ESP_ADD_PEER(esp_add_peer), CMC.CB_ESP_DEL_PEER(esp_delete_peer),
                    CMC.CB_ESP_POLL_RX(esp_poll_rx)]
        self._pending_tx_complete = False
        self.handle = lib.mc_cbmodem_create(None, *self._cb, 1)  # has_espnow=1
        lib.mc_cbmodem_set_radio_ready(self.handle, 1)
        lib.mc_cbmodem_set_espnow_ready(self.handle, 1)

    def close(self):
        self.lib.mc_cbmodem_destroy(self.handle)
        self._cb = None

    # --- app -> modem ---
    def enqueue(self, frame, wait_for_ack):
        raw = PY.encode_frame(frame, KEYS)
        return self.lib.mc_cbmodem_enqueue_tx(self.handle, raw, len(raw),
                                              1 if wait_for_ack else 0) == 1

    # --- channel -> modem ---
    def on_channel_frame(self, band, raw, src_mac):
        if band == LORA_BAND:
            # Drive the LoRa RX path directly (sim knows it's an RX event).
            self.lib.mc_cbmodem_tick_radio_rx(self.handle, raw, len(raw), -65.0, 8.0)
        else:
            self.espnow_inbox.append((src_mac, raw))
            self.lib.mc_cbmodem_tick_espnow_rx(self.handle)

    # --- periodic service (mirrors the firmware loop) ---
    def service(self):
        self.lib.mc_cbmodem_tick_duty_drain(self.handle)
        self.lib.mc_cbmodem_tick_peer_liveness(self.handle)
        self.lib.mc_cbmodem_tick_start_next_tx(self.handle, 0)
        # If a LoRa TX was started this service window, complete it (TX_DONE).
        if self._pending_tx_complete:
            self._pending_tx_complete = False
            self.lib.mc_cbmodem_tick_tx_complete(self.handle, 0)
        self.lib.mc_cbmodem_tick_ack_timeout(self.handle)

    # --- half-duplex deafness support (this node's own LoRa TX windows) ---
    def note_lora_tx(self, start, end):
        self.lora_tx_windows.append((start, end))

    def is_lora_deaf(self, start, end):
        """True if this node is mid-LoRa-TX over [start,end] -> cannot hear inbound
        LoRa (SX1262 half-duplex). Prunes windows older than the current sim time."""
        now = self.clock.now_ms
        self.lora_tx_windows = [w for w in self.lora_tx_windows if w[1] > now]
        for ws, we in self.lora_tx_windows:
            if ws < end and start < we:
                return True
        return False

    def fsm_state(self):
        return self.lib.mc_cbmodem_fsm_state(self.handle)

    def _route_host_line(self, text):
        if text.startswith("RX "):
            parts = text.split()
            hex_str = parts[-1]
            try:
                raw = bytes.fromhex(hex_str)
                frame = PY.decode_frame(raw, KEYS)
            except Exception:
                return
            self.app.on_rx(frame)
        elif text == "OK TX":
            self.app.on_ok_tx()
        elif text.startswith("ERR "):
            self.app.on_err(text)


class SenderApp:
    """Dial side: sends ARM + FIREs (with-ACK). Tracks which FIRE seqs got their ACK
    (the modem clears WaitAck on a matching ACK; the app sees the ACK as an RX line)."""

    def __init__(self):
        self.node = None
        self.acked = set()
        self.ok_tx = 0
        self.errors = []

    def on_rx(self, frame):
        if frame.frame_type == PY.FrameType.ACK:
            acked = _parse_ack_payload(frame.payload)
            if acked is not None:
                self.acked.add(acked)

    def on_ok_tx(self):
        self.ok_tx += 1

    def on_err(self, reason):
        self.errors.append(reason)


class ReceiverApp:
    """DinMeter side: on FIRE (when armed) records delivery + sends an ACK back."""

    def __init__(self):
        self.node = None
        self.armed = False
        self.fired = set()
        self.stopped = False

    def on_rx(self, frame):
        if frame.frame_type == PY.FrameType.ARM:
            self.armed = True
            return
        if frame.frame_type == PY.FrameType.STOP:
            self.stopped = True
            return
        if frame.frame_type == PY.FrameType.FIRE and self.armed:
            self.fired.add(frame.sequence)
            ack = PY.PropFrame(frame_type=PY.FrameType.ACK, key_id=KEY_ID,
                               source=RX_ADDR, destination=DIAL_ADDR,
                               sequence=frame.sequence, nonce=frame.nonce,
                               payload=_make_ack_payload(frame.sequence))
            self.node.enqueue(ack, wait_for_ack=False)

    def on_ok_tx(self):
        pass

    def on_err(self, reason):
        pass


def _make_ack_payload(sequence):
    return bytes([int(PY.FrameType.FIRE)]) + int(sequence).to_bytes(4, "big")


def _parse_ack_payload(payload):
    if len(payload) != 5 or payload[0] != int(PY.FrameType.FIRE):
        return None
    return int.from_bytes(payload[1:5], "big")


def run_link(seed=1, fire_count=20, lora_loss=0.0, espnow_loss=0.0, arm_bursts=3,
             wait_for_ack=True, fire_burst=1,
             lora_ge=(0.0, 0.0, 0.0, 0.0), espnow_ge=(0.0, 0.0, 0.0, 0.0)):
    """Build A<->B, run ARM + FIREs, return metrics. Real modem_core on both ends.

    wait_for_ack: if True each FIRE makes the modem enter WaitAck (serialized TX --
      a lost ACK stalls the queue for ACK_TIMEOUT_MS=900). The product's FIRE path is
      fire-and-forget (wait_for_ack=False) precisely to avoid that stall under loss;
      set wait_for_ack=False + fire_burst>1 to model the real Dial burst + dual-band
      + receiver dedup redundancy. This faithfully reflects firmware modem_core: the
      single RadioFsm serializes TX, unlike sim_link.py's concurrent Python Modem."""
    lib = CMC.load_dll()
    clock = Clock()
    rng = random.Random(seed)
    channel = Channel(clock, rng, lora_loss=lora_loss, espnow_loss=espnow_loss,
                      lora_ge=lora_ge, espnow_ge=espnow_ge)

    sender_app, receiver_app = SenderApp(), ReceiverApp()
    nodes = {}
    node_a = ModemNode(lib, clock, channel, MAC_A, lambda: nodes["b"], sender_app)
    node_b = ModemNode(lib, clock, channel, MAC_B, lambda: nodes["a"], receiver_app)
    nodes["a"], nodes["b"] = node_a, node_b
    sender_app.node, receiver_app.node = node_a, node_b

    try:
        epoch = rng.getrandbits(32)
        seq = [1]

        def arm():
            for _ in range(arm_bursts):
                n = PY.PropFrame(frame_type=PY.FrameType.ARM, key_id=KEY_ID,
                                 source=DIAL_ADDR, destination=RX_ADDR,
                                 sequence=seq[0], nonce=(epoch << 32) | seq[0], payload=b"")
                node_a.enqueue(n, wait_for_ack=False)
                seq[0] += 1

        fire_seqs = []

        def fire():
            s = seq[0]
            seq[0] += 1
            # Fire-and-forget burst: fire_burst copies share seq+nonce (receiver dedups
            # by sequence). With wait_for_ack=False the modem returns to RxListen after
            # each TX so the burst flows without an ACK-stall.
            for _ in range(fire_burst):
                n = PY.PropFrame(frame_type=PY.FrameType.FIRE, key_id=KEY_ID,
                                 source=DIAL_ADDR, destination=RX_ADDR,
                                 sequence=s, nonce=(epoch << 32) | s, payload=b"F")
                node_a.enqueue(n, wait_for_ack=wait_for_ack)
            fire_seqs.append(s)

        # Schedule: ARM burst at t=0, FIREs spaced every 60 ms, ARM heartbeat every 5 s.
        schedule = {0: arm}
        t = 60
        for _ in range(fire_count):
            schedule[t] = fire
            t += 60
        campaign_end = t + 4000
        hb = 5000
        ht = hb
        while ht < campaign_end:
            schedule.setdefault(ht, arm)
            ht += hb

        # Time-stepped driver: 1 ms steps. Each step: fire scheduled events, deliver
        # due channel frames, then service both modems (mirrors the firmware loop()).
        while clock.now_ms <= campaign_end:
            if clock.now_ms in schedule:
                schedule[clock.now_ms]()
            channel.deliver_due()
            node_a.service()
            node_b.service()
            clock.now_ms += 1

        delivered = len(receiver_app.fired)
        acked = len(sender_app.acked & set(fire_seqs))
        return {
            "fire_count": fire_count,
            "delivered": delivered,
            "delivery_rate": delivered / fire_count if fire_count else 0.0,
            "acked": acked,
            "ack_rate": acked / fire_count if fire_count else 0.0,
            "ok_tx": sender_app.ok_tx,
            "errors": list(sender_app.errors),
            "lora_lost": channel.counters["lora_lost"],
            "espnow_lost": channel.counters["espnow_lost"],
            "lora_collisions": channel.counters["lora_collisions"],
            "lora_deaf_drops": channel.counters["lora_deaf_drops"],
        }
    finally:
        node_a.close()
        node_b.close()


def run_stop(seed=5):
    """ARM then STOP; assert the receiver latches STOP (real modem_core link)."""
    lib = CMC.load_dll()
    clock = Clock()
    rng = random.Random(seed)
    channel = Channel(clock, rng)
    sender_app, receiver_app = SenderApp(), ReceiverApp()
    nodes = {}
    node_a = ModemNode(lib, clock, channel, MAC_A, lambda: nodes["b"], sender_app)
    node_b = ModemNode(lib, clock, channel, MAC_B, lambda: nodes["a"], receiver_app)
    nodes["a"], nodes["b"] = node_a, node_b
    sender_app.node, receiver_app.node = node_a, node_b
    try:
        epoch = rng.getrandbits(32)
        s = 1
        arm = PY.PropFrame(frame_type=PY.FrameType.ARM, key_id=KEY_ID, source=DIAL_ADDR,
                           destination=RX_ADDR, sequence=s, nonce=(epoch << 32) | s, payload=b"")
        node_a.enqueue(arm, wait_for_ack=False)
        s += 1
        stop = PY.PropFrame(frame_type=PY.FrameType.STOP, key_id=KEY_ID, source=DIAL_ADDR,
                            destination=RX_ADDR, sequence=s, nonce=(epoch << 32) | s, payload=b"!")
        scheduled_stop_at = 100
        while clock.now_ms <= 400:
            if clock.now_ms == scheduled_stop_at:
                node_a.enqueue(stop, wait_for_ack=False)
            channel.deliver_due()
            node_a.service()
            node_b.service()
            clock.now_ms += 1
        return receiver_app.stopped
    finally:
        node_a.close()
        node_b.close()


def _check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" - {detail}" if detail else ""))
    return 0 if ok else 1


def selftest():
    failures = 0

    # Clean link, fire-and-forget (the product's real FIRE path, #63): every FIRE is
    # delivered (ESP-NOW always carries it; the LoRa copy may collide with the return
    # ACK on the shared half-duplex medium, which is exactly why dual-band exists).
    clean = run_link(seed=42, fire_count=20, wait_for_ack=False, fire_burst=1)
    failures += _check(
        "clean link: 100% FIRE delivery via real modem_core both ends",
        clean["delivery_rate"] == 1.0,
        f"delivered={clean['delivered']}/{clean['fire_count']} errors={clean['errors'][:3]}")

    # Determinism (fire-and-forget, the product's real FIRE path).
    det1 = run_link(seed=7, fire_count=15, lora_loss=0.3, espnow_loss=0.3,
                    wait_for_ack=False, fire_burst=3)
    det2 = run_link(seed=7, fire_count=15, lora_loss=0.3, espnow_loss=0.3,
                    wait_for_ack=False, fire_burst=3)
    failures += _check("determinism: same seed -> same metrics", det1 == det2,
                       f"r={det1['delivery_rate']:.3f}")

    # Lossy fire-and-forget + burst=3 + dual-band over the REAL RF model (Semtech
    # airtime + collision + half-duplex deafness). At a brutal 50%/50% per-band loss
    # the burst+dual-band redundancy still carries most FIREs; collisions on the shared
    # LoRa medium make it less than the naive 0.5^6 bound, which is the realistic point.
    lossy = run_link(seed=3, fire_count=60, lora_loss=0.5, espnow_loss=0.5,
                     wait_for_ack=False, fire_burst=3)
    failures += _check(
        "lossy fire-and-forget: burst+dual-band keeps delivery high (real RF model)",
        lossy["delivery_rate"] >= 0.75,
        f"rate={lossy['delivery_rate']:.3f} loraLost={lossy['lora_lost']} "
        f"espLost={lossy['espnow_lost']} collisions={lossy['lora_collisions']} "
        f"deaf={lossy['lora_deaf_drops']}")

    # FIDELITY FINDING (documented as a test): wait_for_ack=True is FRAGILE on the real
    # channel. modem_core enters WaitAck only after its LoRa TX completes (~stagger +
    # airtime); the fast ESP-NOW ACK often arrives BEFORE that and is ignored, so the
    # only ACK that clears WaitAck is a late one from the LoRa FIRE reception -- which
    # collision/loss frequently kills. The modem then stalls 900ms in WaitAck and the
    # DEPTH=4 queue overflows (ERR BUSY). Fire-and-forget has no WaitAck and rides the
    # ESP-NOW path freely. This faithfully reflects firmware modem_core (sim_link.py's
    # concurrent Python Modem could never show it) and VALIDATES the fire-and-forget
    # design choice (#63) on the realistic RF model.
    waitack = run_link(seed=42, fire_count=20, wait_for_ack=True, fire_burst=1)
    failures += _check(
        "fidelity: wait_for_ack on real RF << fire-and-forget (WaitAck stall + collision)",
        waitack["delivery_rate"] < clean["delivery_rate"],
        f"waitack={waitack['delivery_rate']:.3f} faf={clean['delivery_rate']:.3f} "
        f"busy={sum(1 for e in waitack['errors'] if 'BUSY' in e)} "
        "(real RadioFsm serialization -- validates fire-and-forget #63)")

    # Gilbert-Elliott BURST loss (correlated fading, not i.i.d.) on BOTH bands, with
    # fire-and-forget burst=3 + dual-band. Even with deep bursty fades the redundancy
    # holds. This is the definitive M5 reliability sim: real firmware modem_core over a
    # real RF channel model (airtime + GE burst + collision + half-duplex deafness).
    ge = (0.15, 0.85, 0.02, 0.7)  # enter_bad, stay_bad, good_loss, bad_loss
    burst = run_link(seed=11, fire_count=80, wait_for_ack=False, fire_burst=3,
                     lora_ge=ge, espnow_ge=ge)
    failures += _check(
        "Gilbert-Elliott burst loss: fire-and-forget + dual-band rides through fades",
        burst["delivery_rate"] >= 0.75,
        f"rate={burst['delivery_rate']:.3f} loraLost={burst['lora_lost']} "
        f"espLost={burst['espnow_lost']} collisions={burst['lora_collisions']} "
        f"deaf={burst['lora_deaf_drops']}")
    failures += _check(
        "RF model active: burst run exercised loss + collisions (GE + airtime fired)",
        burst["lora_lost"] + burst["espnow_lost"] > 0 and burst["lora_collisions"] > 0,
        f"loraLost={burst['lora_lost']} espLost={burst['espnow_lost']} "
        f"collisions={burst['lora_collisions']}")

    failures += _check("STOP latched at receiver (real modem_core link)", run_stop())

    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILURES'}")
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="Dual-modem link on real modem_core")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--fires", type=int, default=20)
    parser.add_argument("--lora-loss", type=float, default=0.0)
    parser.add_argument("--espnow-loss", type=float, default=0.0)
    args = parser.parse_args(argv)
    if args.selftest:
        sys.exit(1 if selftest() else 0)
    m = run_link(seed=args.seed, fire_count=args.fires,
                 lora_loss=args.lora_loss, espnow_loss=args.espnow_loss)
    print(f"delivery_rate={m['delivery_rate']:.4f} ack_rate={m['ack_rate']:.4f} "
          f"delivered={m['delivered']}/{m['fire_count']} ok_tx={m['ok_tx']} "
          f"lora_lost={m['lora_lost']} espnow_lost={m['espnow_lost']} errors={len(m['errors'])}")


if __name__ == "__main__":
    main()
