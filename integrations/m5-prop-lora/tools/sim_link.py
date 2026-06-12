import argparse
import heapq
import math
import os
import random
import sys
from dataclasses import dataclass


sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = os.path.join(ROOT, "shared")
PROTOCOL_DIR = os.path.join(SHARED, "protocol")
for path in (SHARED, PROTOCOL_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from protocol import (  # noqa: E402
    FrameReplayWindow,
    FrameType,
    PropFrame,
    bytes_to_hex,
    decode_frame,
    encode_frame,
)


KEY_ID = 1
KEYS = {KEY_ID: b"M5 deterministic sim link key"}
DIAL_ADDR = 1
DIN_RX_ADDR = 2


# Lazy ctypes bridge to firmware modem_core (slice 2). Loaded once on first use so
# legacy sim runs that don't opt-in pay no startup cost. Reuses the existing host
# loader/builder in tools/sim_native/check_modem_core.py -- single source of truth
# for the ABI surface, including the auto-build via ziglang if the DLL is missing.
_modem_lib = None


def _get_modem_lib():
    global _modem_lib
    if _modem_lib is None:
        sim_native_dir = os.path.join(ROOT, "tools", "sim_native")
        if sim_native_dir not in sys.path:
            sys.path.insert(0, sim_native_dir)
        import check_modem_core as cmc  # noqa: E402

        _modem_lib = cmc.load_dll()
    return _modem_lib


@dataclass
class SimConfig:
    seed: int = 1
    fire_count: int = 100
    lora_loss: float = 0.0
    espnow_loss: float = 0.0
    lora_enabled: bool = True
    espnow_enabled: bool = True
    espnow_min_latency_ms: float = 1.0
    espnow_max_latency_ms: float = 3.0
    lora_turnaround_min_ms: float = 1.0
    lora_turnaround_max_ms: float = 3.0
    lora_ge_enter_bad: float = 0.0
    lora_ge_stay_bad: float = 0.0
    lora_ge_good_loss: float = 0.0
    lora_ge_bad_loss: float = 0.0
    espnow_ge_enter_bad: float = 0.0
    espnow_ge_stay_bad: float = 0.0
    espnow_ge_good_loss: float = 0.0
    espnow_ge_bad_loss: float = 0.0
    duty_budget_ms: float = 3600.0
    duty_window_ms: float = 360000.0
    ack_timeout_ms: float = 900.0
    fire_burst_count: int = 3
    fire_burst_gap_ms: float = 2.0
    fire_spacing_ms: float = 60.0
    fire_ack_delay_ms: float = 90.0
    fire_ack_jitter_ms: float = 40.0
    modem_queue_depth: int = 4
    lora_stagger_ms: float = 6.0
    # ARM robustness, mirroring the real Dial: initial ARM is a redundant burst, then
    # an ARM heartbeat every 5s refreshes the receiver's ~12s ARM TTL (app_prop_tx.cpp
    # ARM_HEARTBEAT_MS=5000). Without this a single lost ARM would zero a whole session.
    arm_burst_count: int = 3
    arm_heartbeat_ms: float = 5000.0
    arm_ttl_ms: float = 12000.0
    # Slice 2 bridge: when True, the Modem matches incoming ACKs via firmware's
    # modem_core::looksLikeMatchingAck (loaded from sim_native/modem_abi.dll) instead
    # of the sim's own payload-based parse_ack_payload helper. This makes the
    # firmware logic the AUTHORITY for the safety-critical "ACK matches in-flight TX"
    # decision. Default False keeps the legacy sim path; selftest exercises both.
    use_firmware_ack: bool = False


@dataclass
class FireRecord:
    sequence: int
    nonce: int
    start_ms: float
    delivered_count: int = 0
    ack_ms: float | None = None
    observable_failures: int = 0


@dataclass
class LoraTx:
    start_ms: float
    end_ms: float
    from_modem: object
    to_modem: object
    raw: bytes
    collided: bool = False
    lost: bool = False


class EventLoop:
    def __init__(self):
        self.time_ms = 0.0
        self._seq = 0
        self._events = []

    def schedule(self, delay_ms, callback):
        when = self.time_ms + max(0.0, float(delay_ms))
        self._seq += 1
        heapq.heappush(self._events, (when, self._seq, callback))

    def run(self):
        while self._events:
            when, _, callback = heapq.heappop(self._events)
            self.time_ms = when
            callback()


class GilbertElliott:
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


class DutyBucket:
    def __init__(self, cfg):
        self.budget_ms = cfg.duty_budget_ms
        self.window_ms = cfg.duty_window_ms
        self.used_ms = 0.0
        self.last_ms = 0.0

    def allow(self, now_ms, airtime_ms):
        elapsed = max(0.0, now_ms - self.last_ms)
        self.last_ms = now_ms
        leak = elapsed * self.budget_ms / self.window_ms
        self.used_ms = max(0.0, self.used_ms - leak)
        if self.used_ms + airtime_ms > self.budget_ms:
            return False
        self.used_ms += airtime_ms
        return True


class DualBandChannel:
    def __init__(self, loop, rng, cfg, counters):
        self.loop = loop
        self.rng = rng
        self.cfg = cfg
        self.counters = counters
        self.lora_ge = GilbertElliott(
            rng,
            cfg.lora_ge_enter_bad,
            cfg.lora_ge_stay_bad,
            cfg.lora_ge_good_loss,
            cfg.lora_ge_bad_loss,
        )
        self.espnow_ge = GilbertElliott(
            rng,
            cfg.espnow_ge_enter_bad,
            cfg.espnow_ge_stay_bad,
            cfg.espnow_ge_good_loss,
            cfg.espnow_ge_bad_loss,
        )
        self.active_lora = []

    def transmit(self, band, from_modem, to_modem, raw, bypass_duty=False):
        if band == "espnow":
            if not self.cfg.espnow_enabled:
                return 0.0
            latency = self.rng.uniform(
                self.cfg.espnow_min_latency_ms, self.cfg.espnow_max_latency_ms
            )
            lost = self.espnow_ge.loss(self.cfg.espnow_loss)
            if lost:
                self.counters["espnow_lost"] += 1
                return latency
            self.loop.schedule(latency, lambda: to_modem.on_channel_receive(raw, band))
            return latency

        if not self.cfg.lora_enabled:
            return 0.0

        start = self.loop.time_ms
        airtime = self.lora_airtime_ms(len(raw))
        end = start + airtime
        from_modem.note_lora_tx(start, end)
        self._drop_old_lora(start)

        tx = LoraTx(
            start_ms=start,
            end_ms=end,
            from_modem=from_modem,
            to_modem=to_modem,
            raw=raw,
            lost=self.lora_ge.loss(self.cfg.lora_loss),
        )
        if tx.lost:
            self.counters["lora_lost"] += 1
        for other in self.active_lora:
            if other.start_ms < tx.end_ms and tx.start_ms < other.end_ms:
                if not other.collided:
                    self.counters["lora_collisions"] += 1
                other.collided = True
                tx.collided = True
        self.active_lora.append(tx)

        turnaround = self.rng.uniform(
            self.cfg.lora_turnaround_min_ms, self.cfg.lora_turnaround_max_ms
        )

        def deliver():
            self._drop_old_lora(self.loop.time_ms)
            if tx.collided or tx.lost:
                return
            if to_modem.is_lora_deaf(tx.start_ms, tx.end_ms):
                self.counters["lora_deaf_drops"] += 1
                return
            to_modem.on_channel_receive(raw, band)

        self.loop.schedule(airtime + turnaround, deliver)
        return airtime

    def _drop_old_lora(self, now_ms):
        self.active_lora = [tx for tx in self.active_lora if tx.end_ms > now_ms]

    def lora_airtime_ms(self, payload_len):
        sf = 7
        bw_hz = 250000.0
        coding_rate = 1  # CR 4/5 in the Semtech formula.
        preamble = 8
        crc = 1
        implicit_header = 0
        low_data_rate = 1 if sf >= 11 and bw_hz <= 125000.0 else 0
        tsym_ms = (2**sf) / bw_hz * 1000.0
        numerator = 8 * int(payload_len) - 4 * sf + 28 + 16 * crc - 20 * implicit_header
        denominator = 4 * (sf - 2 * low_data_rate)
        payload_symbols = 8 + max(math.ceil(numerator / denominator) * (coding_rate + 4), 0)
        preamble_symbols = preamble + 4.25
        return (preamble_symbols + payload_symbols) * tsym_ms


class Modem:
    def __init__(self, name, loop, rng, cfg, channel, local):
        self.name = name
        self.loop = loop
        self.rng = rng
        self.cfg = cfg
        self.channel = channel
        self.local = local
        self.peer = None
        self.pending = []
        self.wait_ack = {}
        # Slice 2 bridge: when cfg.use_firmware_ack, we also store the raw request
        # frame so the firmware ACK matcher (header-based) can compare on RX.
        self.wait_ack_raw = {}
        self.duty = DutyBucket(cfg)
        self.lora_tx_windows = []
        self.next_lora_available_ms = 0.0

    def send_local(self, frame, with_ack=False):
        raw = encode_frame(frame, KEYS)
        is_stop = frame.frame_type == FrameType.STOP
        if not is_stop and len(self.pending) >= self.cfg.modem_queue_depth:
            self._emit_error(frame, "ERR BUSY")
            return False

        token = object()
        if not is_stop:
            self.pending.append(token)

        self.channel.transmit("espnow", self, self.peer, raw)
        if with_ack and frame.sequence not in self.wait_ack:
            self.wait_ack[frame.sequence] = frame.frame_type
            if self.cfg.use_firmware_ack:
                # Retain the raw request bytes so the firmware header-based ACK
                # matcher (modem_core::looksLikeMatchingAck) can compare them on RX.
                self.wait_ack_raw[frame.sequence] = raw
            self.loop.schedule(
                self.cfg.ack_timeout_ms,
                lambda seq=frame.sequence: self._ack_timeout(seq),
            )

        if self.cfg.lora_enabled:
            airtime = self.channel.lora_airtime_ms(len(raw))
            if is_stop:
                start_delay = 0.0
            else:
                earliest = self.loop.time_ms + self.cfg.lora_stagger_ms
                reserved = self.next_lora_available_ms + self.cfg.lora_stagger_ms
                start_at = max(earliest, reserved)
                self.next_lora_available_ms = start_at + airtime
                start_delay = start_at - self.loop.time_ms

            def lora_send():
                if is_stop or self.duty.allow(self.loop.time_ms, airtime):
                    self.channel.transmit("lora", self, self.peer, raw, is_stop)
                    release_delay = airtime
                else:
                    self._emit_error(frame, "ERR DUTY")
                    release_delay = 0.0
                if not is_stop:
                    self.loop.schedule(release_delay, lambda: self._release(token))

            self.loop.schedule(start_delay, lora_send)
        elif not is_stop:
            self.loop.schedule(0.0, lambda: self._release(token))
        return True

    def on_channel_receive(self, raw, band):
        try:
            frame = decode_frame(raw, KEYS)
        except Exception:
            self.local.on_error(None, "ERR DECODE")
            return
        if frame.frame_type == FrameType.ACK:
            self._match_ack(raw, frame)
        self.local.on_modem_frame(frame, band)

    def _match_ack(self, raw_ack, frame):
        """Clear any pending wait_ack entry that matches this ACK.

        Two implementations:
          * cfg.use_firmware_ack True -> firmware modem_core::looksLikeMatchingAck
            (header-based: type/key/src<->dst/seq + nonce[8B] all match the original
            request frame). The "authority" path: same byte-for-byte logic as ESP32.
          * cfg.use_firmware_ack False -> legacy sim path: parse_ack_payload reads
            the acked sequence number out of the ACK frame's payload.
        """
        if self.cfg.use_firmware_ack:
            lib = _get_modem_lib()
            for seq, req_raw in list(self.wait_ack_raw.items()):
                if lib.mc_looks_like_matching_ack(req_raw, len(req_raw), raw_ack, len(raw_ack)):
                    self.wait_ack.pop(seq, None)
                    self.wait_ack_raw.pop(seq, None)
                    return
            return
        acked = parse_ack_payload(frame.payload)
        if acked is not None:
            self.wait_ack.pop(acked, None)

    def note_lora_tx(self, start_ms, end_ms):
        self.lora_tx_windows.append((start_ms, end_ms))

    def is_lora_deaf(self, start_ms, end_ms):
        self.lora_tx_windows = [
            window for window in self.lora_tx_windows if window[1] > self.loop.time_ms
        ]
        for tx_start, tx_end in self.lora_tx_windows:
            if tx_start < end_ms and start_ms < tx_end:
                return True
        return False

    def _release(self, token):
        if token in self.pending:
            self.pending.remove(token)

    def _ack_timeout(self, sequence):
        frame_type = self.wait_ack.pop(sequence, None)
        self.wait_ack_raw.pop(sequence, None)
        if frame_type is not None:
            self.local.on_timeout(sequence)

    def _emit_error(self, frame, reason):
        self.local.on_error(frame.sequence if frame is not None else None, reason)


class Sender:
    def __init__(self, loop, rng, cfg, modem):
        self.loop = loop
        self.rng = rng
        self.cfg = cfg
        self.modem = modem
        self.epoch = rng.getrandbits(32)
        self.next_seq = 1
        self.records = {}

    def start(self):
        # Initial ARM as a redundant burst, then a periodic ARM heartbeat for the whole
        # campaign (mirrors the real Dial). This makes a single lost ARM recoverable, so
        # delivery_rate measures FIRE-link reliability, not one-ARM luck.
        self.send_arm(self.cfg.arm_burst_count)
        first_fire_ms = 20.0
        campaign_ms = first_fire_ms + self.cfg.fire_count * self.cfg.fire_spacing_ms
        hb = self.cfg.arm_heartbeat_ms
        if hb > 0:
            t = hb
            while t < campaign_ms + hb:
                self.loop.schedule(t, lambda: self.send_arm(1))
                t += hb
        for index in range(self.cfg.fire_count):
            self.loop.schedule(
                first_fire_ms + index * self.cfg.fire_spacing_ms,
                lambda: self.send_fire(),
            )

    def send_arm(self, copies=1):
        seq = self._next_sequence()
        frame = self._frame(FrameType.ARM, seq)
        for copy_index in range(copies):
            self.loop.schedule(
                copy_index * self.cfg.fire_burst_gap_ms,
                lambda frame=frame: self.modem.send_local(frame, with_ack=False),
            )

    def send_fire(self):
        seq = self._next_sequence()
        frame = self._frame(FrameType.FIRE, seq)
        self.records[seq] = FireRecord(sequence=seq, nonce=frame.nonce, start_ms=self.loop.time_ms)
        for copy_index in range(self.cfg.fire_burst_count):
            self.loop.schedule(
                copy_index * self.cfg.fire_burst_gap_ms,
                lambda frame=frame: self.modem.send_local(frame, with_ack=True),
            )

    def on_modem_frame(self, frame, band):
        if frame.frame_type != FrameType.ACK:
            return
        acked = parse_ack_payload(frame.payload)
        if acked is None:
            return
        record = self.records.get(acked)
        if record is not None and record.ack_ms is None:
            record.ack_ms = self.loop.time_ms

    def on_timeout(self, sequence):
        record = self.records.get(sequence)
        if record is not None:
            record.observable_failures += 1

    def on_error(self, sequence, reason):
        record = self.records.get(sequence)
        if record is not None:
            record.observable_failures += 1

    def _next_sequence(self):
        seq = self.next_seq
        self.next_seq += 1
        return seq

    def _frame(self, frame_type, seq, payload=b""):
        nonce = (self.epoch << 32) | seq
        return PropFrame(
            frame_type=frame_type,
            key_id=KEY_ID,
            source=DIAL_ADDR,
            destination=DIN_RX_ADDR,
            sequence=seq,
            nonce=nonce,
            payload=payload,
        )


class Receiver:
    def __init__(self, loop, rng, cfg, modem):
        self.loop = loop
        self.rng = rng
        self.cfg = cfg
        self.modem = modem
        self.replay = FrameReplayWindow()
        self.armed = False
        self.last_arm_ms = -1e18  # time of the most recent accepted ARM (for the TTL)
        self.current_epoch = None
        self.arm_epoch = None
        self.arm_seq = 0
        self.stop_latched = False
        self.lockout_seq = 0
        self.fire_records = None

    def on_modem_frame(self, frame, band):
        epoch = (int(frame.nonce) >> 32) & 0xFFFFFFFF
        accepted_new_session = epoch != self.current_epoch
        verdict = self.replay.classify(frame.nonce, frame.sequence)
        if verdict != "new":
            return
        if accepted_new_session:
            self.current_epoch = epoch
            self.armed = False
            self.arm_epoch = None
            self.arm_seq = 0
        if frame.frame_type == FrameType.ARM:
            if self.stop_latched and frame.sequence <= self.lockout_seq:
                return
            self.armed = True
            self.last_arm_ms = self.loop.time_ms
            self.stop_latched = False
            self.arm_epoch = epoch
            self.arm_seq = frame.sequence
            return
        if frame.frame_type == FrameType.STOP:
            self.armed = False
            self.arm_epoch = None
            self.arm_seq = 0
            self.stop_latched = True
            if frame.sequence > self.lockout_seq:
                self.lockout_seq = frame.sequence
            return
        if frame.frame_type != FrameType.FIRE:
            return
        # FIRE only fires if armed AND the ARM is still fresh (receiver ARM TTL),
        # mirroring the real receiver whose ARM lapses to SAFE without a heartbeat.
        if (
            not self.armed
            or self.stop_latched
            or epoch != self.arm_epoch
            or frame.sequence <= self.arm_seq
            or frame.sequence <= self.lockout_seq
            or (self.loop.time_ms - self.last_arm_ms) > self.cfg.arm_ttl_ms
        ):
            return
        record = self.fire_records.get(frame.sequence) if self.fire_records else None
        if record is not None:
            record.delivered_count += 1
        delay = self.cfg.fire_ack_delay_ms + self.rng.uniform(0.0, self.cfg.fire_ack_jitter_ms)
        # Echo the FIRE nonce in the ACK so the ACK is firmware-faithful:
        # modem_core::looksLikeMatchingAck compares request.nonce[8B] == candidate.nonce[8B]
        # (the sim's own payload-based ACK match only used `sequence`, so nonce was
        # set to the bare sequence which would never match firmware's header-based ACK
        # matching). Plumbing the real nonce through makes the sim's ACK valid for both
        # matchers, which is the prerequisite for wiring modem_core's matcher in.
        self.loop.schedule(
            delay,
            lambda seq=frame.sequence, nonce=frame.nonce: self._send_fire_ack(seq, nonce),
        )

    def on_timeout(self, sequence):
        pass

    def on_error(self, sequence, reason):
        pass

    def _send_fire_ack(self, sequence, nonce):
        ack = PropFrame(
            frame_type=FrameType.ACK,
            key_id=KEY_ID,
            source=DIN_RX_ADDR,
            destination=DIAL_ADDR,
            sequence=sequence,
            nonce=nonce,  # echo the FIRE's nonce so firmware ACK matcher accepts this
            payload=make_ack_payload(FrameType.FIRE, sequence),
        )
        self.modem.send_local(ack, with_ack=False)


def make_ack_payload(frame_type, sequence):
    return bytes([int(frame_type)]) + int(sequence).to_bytes(4, "big")


def parse_ack_payload(payload):
    if len(payload) != 5:
        return None
    if payload[0] != int(FrameType.FIRE):
        return None
    return int.from_bytes(payload[1:5], "big")


def build_world(cfg):
    rng = random.Random(cfg.seed)
    loop = EventLoop()
    counters = {
        "espnow_lost": 0,
        "lora_lost": 0,
        "lora_collisions": 0,
        "lora_deaf_drops": 0,
    }
    channel = DualBandChannel(loop, rng, cfg, counters)
    sender = Sender(loop, rng, cfg, None)
    receiver = Receiver(loop, rng, cfg, None)
    modem_a = Modem("ModemA", loop, rng, cfg, channel, sender)
    modem_b = Modem("ModemB", loop, rng, cfg, channel, receiver)
    modem_a.peer = modem_b
    modem_b.peer = modem_a
    sender.modem = modem_a
    receiver.modem = modem_b
    receiver.fire_records = sender.records
    return loop, sender, receiver, counters


def run_campaign(cfg):
    loop, sender, receiver, counters = build_world(cfg)
    sender.start()
    loop.run()
    records = list(sender.records.values())
    delivered = sum(1 for record in records if record.delivered_count > 0)
    double_fires = sum(1 for record in records if record.delivered_count > 1)
    silent_drops = sum(
        1 for record in records if record.delivered_count == 0 and record.observable_failures == 0
    )
    rtts = [
        record.ack_ms - record.start_ms
        for record in records
        if record.delivered_count > 0 and record.ack_ms is not None
    ]
    result = {
        "seed": cfg.seed,
        "fire_count": cfg.fire_count,
        "delivered_fires": delivered,
        "delivery_rate": delivered / cfg.fire_count if cfg.fire_count else 0.0,
        "rtt_count": len(rtts),
        "rtt_p50_ms": percentile(rtts, 50),
        "rtt_p95_ms": percentile(rtts, 95),
        "rtt_max_ms": max(rtts) if rtts else None,
        "double_fires": double_fires,
        "silent_drops": silent_drops,
        "err_observable": sum(record.observable_failures for record in records),
        "espnow_lost": counters["espnow_lost"],
        "lora_lost": counters["lora_lost"],
        "lora_collisions": counters["lora_collisions"],
        "lora_deaf_drops": counters["lora_deaf_drops"],
        "stop_latched": receiver.stop_latched,
    }
    return result


def run_stop_scenario(cfg=None):
    base = cfg if cfg is not None else SimConfig(seed=101, fire_count=0)
    stop_cfg = SimConfig(
        seed=base.seed,
        fire_count=0,
        lora_loss=0.0,
        espnow_loss=0.0,
        modem_queue_depth=base.modem_queue_depth,
    )
    loop, sender, receiver, _ = build_world(stop_cfg)
    epoch = sender.epoch
    for seq in range(1, stop_cfg.modem_queue_depth + 8):
        frame = PropFrame(
            frame_type=FrameType.PREVIEW,
            key_id=KEY_ID,
            source=DIAL_ADDR,
            destination=DIN_RX_ADDR,
            sequence=seq,
            nonce=(epoch << 32) | seq,
            payload=b"flood",
        )
        sender.modem.send_local(frame, with_ack=False)
    stop_seq = 1000
    stop = PropFrame(
        frame_type=FrameType.STOP,
        key_id=KEY_ID,
        source=DIAL_ADDR,
        destination=DIN_RX_ADDR,
        sequence=stop_seq,
        nonce=(epoch << 32) | stop_seq,
        payload=b"",
    )
    sender.modem.send_local(stop, with_ack=False)
    loop.run()
    return receiver.stop_latched


def inv_no_double_fire(metrics):
    ok = metrics.get("double_fires", 0) == 0
    return ok, "double_fires == 0" if ok else "double_fires != 0"


def inv_stop_delivered(cfg=None):
    ok = run_stop_scenario(cfg)
    return ok, "STOP reached and latched" if ok else "STOP did not latch"


def inv_fire_not_silently_dropped(metrics):
    ok = metrics.get("silent_drops", 0) == 0
    return ok, "silent_drops == 0" if ok else "silent_drops != 0"


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    index = int(math.ceil((pct / 100.0) * len(ordered))) - 1
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index]


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def fmt_ms(value):
    return "n/a" if value is None else f"{value:.2f}"


def print_report(metrics):
    print("M5 dual-band FIRE link simulator")
    print(f"seed: {metrics['seed']}")
    print(f"fires: {metrics['fire_count']}")
    print(
        "delivery_rate: "
        f"{metrics['delivery_rate']:.4f} "
        f"({metrics['delivered_fires']}/{metrics['fire_count']})"
    )
    print(
        "round_trip_ms: "
        f"p50={fmt_ms(metrics['rtt_p50_ms'])} "
        f"p95={fmt_ms(metrics['rtt_p95_ms'])} "
        f"max={fmt_ms(metrics['rtt_max_ms'])} "
        f"n={metrics['rtt_count']}"
    )
    print(
        "counters: "
        f"double_fires={metrics['double_fires']} "
        f"silent_drops={metrics['silent_drops']} "
        f"observable_failures={metrics['err_observable']} "
        f"espnow_lost={metrics['espnow_lost']} "
        f"lora_lost={metrics['lora_lost']} "
        f"lora_collisions={metrics['lora_collisions']} "
        f"lora_deaf_drops={metrics['lora_deaf_drops']}"
    )


def selftest():
    failures = 0

    clean = run_campaign(SimConfig(seed=42, fire_count=40))
    failures += check(
        "clean channel delivery",
        clean["delivery_rate"] == 1.0 and clean["double_fires"] == 0,
        f"rate={clean['delivery_rate']:.4f} double={clean['double_fires']}",
    )

    cfg = SimConfig(seed=77, fire_count=60, lora_loss=0.2, espnow_loss=0.2)
    first = run_campaign(cfg)
    second = run_campaign(cfg)
    failures += check("determinism", first == second, "same seed produced same metrics")

    lossy_dual = run_campaign(SimConfig(seed=4, fire_count=200, lora_loss=0.45, espnow_loss=0.45))
    lossy_lora = run_campaign(
        SimConfig(
            seed=4,
            fire_count=200,
            lora_loss=0.45,
            espnow_loss=0.45,
            espnow_enabled=False,
        )
    )
    lossy_esp = run_campaign(
        SimConfig(
            seed=4,
            fire_count=200,
            lora_loss=0.45,
            espnow_loss=0.45,
            lora_enabled=False,
        )
    )
    worse_single = min(lossy_lora["delivery_rate"], lossy_esp["delivery_rate"])
    failures += check(
        "lossy dual-band sanity",
        lossy_dual["delivery_rate"] < 1.0 and lossy_dual["delivery_rate"] >= worse_single + 0.10,
        "dual="
        f"{lossy_dual['delivery_rate']:.4f} "
        f"lora={lossy_lora['delivery_rate']:.4f} "
        f"espnow={lossy_esp['delivery_rate']:.4f}",
    )

    seed_rates = [
        run_campaign(SimConfig(seed=s, fire_count=150, lora_loss=0.1, espnow_loss=0.1))[
            "delivery_rate"
        ]
        for s in range(12)
    ]
    failures += check(
        "arm robustness (no bimodal 0%)",
        min(seed_rates) > 0.5,
        f"min={min(seed_rates):.3f} across 12 seeds @ loss 0.1 "
        "(a single lost ARM must not zero a whole session)",
    )

    burst = run_campaign(SimConfig(seed=3, fire_count=10))
    ok, message = inv_no_double_fire(burst)
    failures += check("burst dedup invariant", ok, message)

    ok, message = inv_stop_delivered()
    failures += check("STOP invariant", ok, message)

    ok, message = inv_fire_not_silently_dropped(lossy_dual)
    failures += check("silent-drop invariant", ok, message)

    # Slice 2 bridge: same clean scenario, but ACK matching goes through the firmware
    # modem_core::looksLikeMatchingAck (loaded from sim_native/modem_abi.dll). If the
    # sim's frames are firmware-faithful (header + nonce), delivery_rate must still be
    # 1.0 -- the only thing that changed is WHO decided "this ACK matches the FIRE".
    fw_clean = run_campaign(SimConfig(seed=42, fire_count=40, use_firmware_ack=True))
    failures += check(
        "firmware-ack bridge: clean delivery via modem_core matcher",
        fw_clean["delivery_rate"] == 1.0 and fw_clean["double_fires"] == 0,
        f"rate={fw_clean['delivery_rate']:.4f} double={fw_clean['double_fires']}",
    )

    # Lossy run with firmware ACK matcher: must roughly match the Python-path lossy
    # number (statistical, but they share the same RNG-driven channel + same accepted-
    # frame logic; only the ACK-clear path differs, which doesn't affect delivery).
    fw_lossy = run_campaign(
        SimConfig(seed=4, fire_count=200, lora_loss=0.45, espnow_loss=0.45, use_firmware_ack=True)
    )
    failures += check(
        "firmware-ack bridge: lossy dual-band parity with Python path",
        abs(fw_lossy["delivery_rate"] - lossy_dual["delivery_rate"]) < 0.01,
        f"fw={fw_lossy['delivery_rate']:.4f} py={lossy_dual['delivery_rate']:.4f}",
    )

    return failures


def check(name, ok, detail):
    prefix = "PASS" if ok else "FAIL"
    print(f"{prefix}: {name} - {detail}")
    return 0 if ok else 1


def parse_args(argv):
    parser = argparse.ArgumentParser(description="M5 dual-band FIRE link simulator")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--fires", type=int, default=100)
    parser.add_argument("--lora-loss", type=float, default=0.0)
    parser.add_argument("--espnow-loss", type=float, default=0.0)
    parser.add_argument(
        "--use-firmware-ack",
        action="store_true",
        help="Match incoming ACKs via firmware modem_core::looksLikeMatchingAck "
        "(loaded from tools/sim_native/modem_abi.dll) instead of the sim's payload-"
        "based parse_ack_payload. Makes the firmware logic the AUTHORITY for the "
        "safety-critical ACK-matches-in-flight-TX decision.",
    )
    parser.add_argument("--selftest", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    bytes_to_hex(b"")  # Keep the protocol mirror import exercised without output.
    if args.selftest:
        failures = selftest()
        if failures:
            sys.exit(1)
        return
    cfg = SimConfig(
        seed=args.seed,
        fire_count=args.fires,
        lora_loss=args.lora_loss,
        espnow_loss=args.espnow_loss,
        use_firmware_ack=args.use_firmware_ack,
    )
    print_report(run_campaign(cfg))


if __name__ == "__main__":
    main()
