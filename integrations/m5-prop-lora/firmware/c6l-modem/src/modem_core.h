// Pure modem decision logic, extracted from main.cpp so it is single-source between
// ESP32 firmware and the host simulator (tools/sim_native/) -- no Arduino/RadioLib/
// esp_now dependencies. Safety-critical helpers live here so a host test can verify
// them off-device. See c6l-modem/src/main.cpp for the FSM that uses these.
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "modem_mac.h"   // MAC_LEN (shared w/ modem_hal.h; breaks the include cycle)
#include "prop_protocol.h"

namespace modem_core {

constexpr std::size_t MAX_RADIO_FRAME = prop_protocol::MAX_FRAME_LENGTH;

// Wire-frame field offsets (must match prop_protocol header layout). Used by the FSM
// to inspect a frame in place without a full decode (cheap pre-check, MAC unverified).
constexpr std::size_t FRAME_TYPE_OFFSET = 3;
constexpr std::size_t FRAME_KEY_OFFSET = 4;
constexpr std::size_t FRAME_SOURCE_OFFSET = 5;
constexpr std::size_t FRAME_DESTINATION_OFFSET = 6;
constexpr std::size_t FRAME_SEQUENCE_OFFSET = 7;
constexpr std::size_t FRAME_NONCE_OFFSET = 11;

inline std::uint32_t readFrameU32(const std::vector<std::uint8_t>& frame, std::size_t offset) {
    return (static_cast<std::uint32_t>(frame[offset]) << 24) |
           (static_cast<std::uint32_t>(frame[offset + 1]) << 16) |
           (static_cast<std::uint32_t>(frame[offset + 2]) << 8) |
           static_cast<std::uint32_t>(frame[offset + 3]);
}

inline bool hasProtocolHeader(const std::vector<std::uint8_t>& frame) {
    return frame.size() >= prop_protocol::HEADER_LENGTH + prop_protocol::MAC_LENGTH &&
           frame.size() <= MAX_RADIO_FRAME &&
           prop_protocol::readU16(frame.data()) == prop_protocol::PROP_FRAME_MAGIC &&
           frame[2] == prop_protocol::PROP_PROTOCOL_VERSION;
}

// Safety-critical: does `candidate` look like an ACK to `request`? Used by the modem
// FSM to clear WAIT_ACK only when an ACK actually matches the in-flight TX, so a
// stray/old/foreign ACK can never fool the sender into thinking a FIRE was confirmed.
inline bool looksLikeMatchingAck(const std::vector<std::uint8_t>& request,
                                 const std::vector<std::uint8_t>& candidate) {
    if (!hasProtocolHeader(request) || !hasProtocolHeader(candidate)) {
        return false;
    }
    if (candidate[FRAME_TYPE_OFFSET] != static_cast<std::uint8_t>(prop_protocol::FrameType::Ack)) {
        return false;
    }
    if (candidate[FRAME_KEY_OFFSET] != request[FRAME_KEY_OFFSET] ||
        candidate[FRAME_SOURCE_OFFSET] != request[FRAME_DESTINATION_OFFSET] ||
        candidate[FRAME_DESTINATION_OFFSET] != request[FRAME_SOURCE_OFFSET] ||
        readFrameU32(candidate, FRAME_SEQUENCE_OFFSET) != readFrameU32(request, FRAME_SEQUENCE_OFFSET)) {
        return false;
    }
    for (std::size_t i = 0; i < 8; ++i) {
        if (candidate[FRAME_NONCE_OFFSET + i] != request[FRAME_NONCE_OFFSET + i]) {
            return false;
        }
    }
    return true;
}

// ---------------------------------------------------------------------------
// LoRa duty cycle bucket (EU 868 ~1% compliance). The modem FSM charges this
// bucket per LoRa TX and skips non-STOP transmissions that would exceed the
// cap; STOP bypasses (safety: emergency stop must always reach the receiver).
// Pure state machine -- no Arduino/RadioLib deps, host-testable.
// ---------------------------------------------------------------------------

constexpr std::uint32_t LORA_AIRTIME_MS_EST = 20;  // SF7/BW250 estimate; real is per-frame in the sim channel

struct DutyBucket {
    static constexpr std::uint32_t BUDGET_MS = 3600;        // budget over the window (EU 868 ~1%)
    static constexpr std::uint32_t CAP_MS = 36000;          // hard cap on bucket fill
    static constexpr std::uint32_t WINDOW_MS = 360000;      // 6 min sliding window
    static constexpr float DRAIN_PER_MS =
        static_cast<float>(BUDGET_MS) / static_cast<float>(WINDOW_MS);

    float bucketMs = 0.0f;
    std::uint32_t lastMs = 0;   // 0 = sentinel for the first sample (host tests pass nowMs > 0)
    std::uint32_t dropped = 0;  // count of non-STOP frames skipped because the bucket would overflow

    void drain(std::uint32_t nowMs) {
        if (lastMs == 0) { lastMs = nowMs; return; }
        std::uint32_t elapsedMs = nowMs - lastMs;
        lastMs = nowMs;
        if (elapsedMs == 0 || bucketMs <= 0.0f) return;
        bucketMs -= static_cast<float>(elapsedMs) * DRAIN_PER_MS;
        if (bucketMs < 0.0f) bucketMs = 0.0f;
    }

    bool wouldExceedOnAdd(std::uint32_t airtimeMs) const {
        return bucketMs + static_cast<float>(airtimeMs) > static_cast<float>(CAP_MS);
    }

    void add(std::uint32_t airtimeMs) {
        bucketMs += static_cast<float>(airtimeMs);
        if (bucketMs > static_cast<float>(CAP_MS)) {
            bucketMs = static_cast<float>(CAP_MS);
        }
    }
};

// ---------------------------------------------------------------------------
// TxQueue: SAFETY-CRITICAL bounded TX queue with STOP priority.
// A2b invariant: a STOP frame must NEVER be dropped -- it evicts the oldest
// queued frame to make room (if full), and always jumps to the front so the
// next startNextQueuedTx() pops it first. Non-STOP rejected when full -> the
// host gets ERR BUSY and can decide. The struct is pure (vector + bools);
// hardware-side ESP-NOW send + LoRa startTransmit stay in the adapter.
// ---------------------------------------------------------------------------

struct TxRequest {
    std::vector<std::uint8_t> frame;
    bool waitForAck = false;
    bool isStop = false;
};

// Cheap in-place check: is this a STOP frame? Reads the type byte at the
// canonical offset (MAC unverified -- the modem only uses this for routing).
inline bool frameIsStop(const std::vector<std::uint8_t>& frame) {
    return frame.size() > FRAME_TYPE_OFFSET &&
           frame[FRAME_TYPE_OFFSET] == static_cast<std::uint8_t>(prop_protocol::FrameType::Stop);
}

// Offset of the 1-byte payload-length field in the wire header (matches
// prop_protocol::decodeFrame's data[19]); used by the structural STOP check below.
constexpr std::size_t FRAME_PAYLOAD_LEN_OFFSET = prop_protocol::HEADER_LENGTH - 1;  // = 19

// SAFETY-CRITICAL: is this a STRUCTURALLY VALID STOP frame? Only a frame that
// passes this check earns STOP privileges in the TX engine (front-of-queue jump,
// queue-full eviction, duty-cycle bypass, indefinite LoRa retry, and the
// radio-down ESP-NOW bypass in enqueueTx). frameIsStop() alone trusts only the
// type byte, so a truncated / garbage UART frame whose byte[3] happens to equal
// Stop could otherwise hijack those privileges and e.g. evict a real queued FIRE
// or wedge the LoRa retry loop. This mirrors decodeFrame()'s pre-HMAC structural
// gate (magic + version + bounds via hasProtocolHeader, valid payload-length byte,
// and len == HEADER + payloadLen + MAC) -- NO HMAC key required, it's purely a
// shape check on bytes the modem already trusts to route.
inline bool frameIsValidStop(const std::vector<std::uint8_t>& frame) {
    if (!hasProtocolHeader(frame)) return false;  // magic + version + min/max bounds
    if (frame[FRAME_TYPE_OFFSET] != static_cast<std::uint8_t>(prop_protocol::FrameType::Stop)) {
        return false;
    }
    const std::uint8_t payloadLen = frame[FRAME_PAYLOAD_LEN_OFFSET];
    if (payloadLen > prop_protocol::MAX_PAYLOAD_LENGTH) return false;
    return frame.size() == prop_protocol::HEADER_LENGTH +
                               static_cast<std::size_t>(payloadLen) +
                               prop_protocol::MAC_LENGTH;
}

struct TxQueue {
    static constexpr std::size_t DEPTH = 4;

    enum class EnqueueResult {
        Accepted,             // pushed to back (non-STOP) or front (STOP), room was there
        AcceptedStopEvicted,  // queue was full + req was STOP -> evicted oldest + jumped front
        RejectedBusy,         // queue was full + req was NOT STOP -> caller should "ERR BUSY"
    };

    std::vector<TxRequest> items;

    bool empty() const { return items.empty(); }
    std::size_t size() const { return items.size(); }
    const TxRequest& front() const { return items.front(); }

    EnqueueResult enqueue(TxRequest req) {
        // Coalesce byte-identical STOP retransmits (out16): the Dial retries the exact
        // same encoded STOP on ACK timeout; without this they stack at the front and
        // can fill the queue with redundant copies (and later spawn duplicate SENDs the
        // receiver silently drops -> ERR ACK_TIMEOUT). A byte-identical STOP carries the
        // same sequence+nonce, so an already-queued copy makes the new one a no-op.
        // A STOP with DIFFERENT bytes (newer sequence) is NOT identical and still
        // enqueues at the front normally -- newer distinct STOPs stay preferred.
        if (req.isStop) {
            for (const auto& it : items) {
                if (it.isStop && it.frame == req.frame) {
                    return EnqueueResult::Accepted;  // already queued -> drop the duplicate
                }
            }
        }
        if (items.size() >= DEPTH) {
            if (!req.isStop) return EnqueueResult::RejectedBusy;
            items.erase(items.begin());                          // evict oldest for the STOP
            items.insert(items.begin(), std::move(req));         // STOP jumps the queue
            return EnqueueResult::AcceptedStopEvicted;
        }
        if (req.isStop) {
            items.insert(items.begin(), std::move(req));         // STOP jumps the queue
        } else {
            items.push_back(std::move(req));
        }
        return EnqueueResult::Accepted;
    }

    void popFront() {
        if (!items.empty()) items.erase(items.begin());
    }

    void pushFront(TxRequest req) {
        items.insert(items.begin(), std::move(req));
    }
};

// ---------------------------------------------------------------------------
// RadioFsm: SAFETY-CRITICAL radio TX/ACK state machine.
// Encapsulates the (state, pendingAckRef, ackDeadline, txWasSendWithAck) tuple
// that gates whether a queued FIRE/STOP/etc. can start, whether an in-flight TX
// is waiting for an ACK, and whether an incoming frame is the ACK we want.
//
// Pure decision logic -- hardware ops (radio.startTransmit, enterReceive,
// reportHost) stay in main.cpp. The FSM tells the caller WHAT to do via state
// transitions; the caller drives the SX1262 + ESP-NOW + UART side.
// ---------------------------------------------------------------------------

struct RadioFsm {
    enum class State {
        RxListen,   // idle, listening for inbound frames; next TX may start here
        TxBusy,     // a LoRa TX is in flight; waiting for TX_DONE IRQ
        WaitAck,    // TX complete, ACK_TIMEOUT_MS deadline armed
    };

    State state = State::RxListen;
    std::vector<std::uint8_t> pendingAckRef;  // copy of the request frame so ACK can be matched
    std::uint32_t ackDeadlineMs = 0;          // millis() value at which WaitAck expires
    std::uint32_t txBusyDeadlineMs = 0;       // millis() value at which a wedged TxBusy is force-aborted
    bool txWasSendWithAck = false;            // whether the in-flight TX expects an ACK

    // Resets the FSM to the idle listening state and clears all wait-state. Used by
    // failure recovery paths (TX start error, finish-TX error) so the next pass of
    // startNextQueuedTx() can pick up the queue from a known-good baseline.
    void abortTx() {
        state = State::RxListen;
        pendingAckRef.clear();
        txWasSendWithAck = false;
    }

    // Called when LoRa startTransmit() succeeded. Stores the request frame (only if
    // waitForAck) so a later ACK candidate can be matched, then transitions to TxBusy.
    // Arms the TX-busy watchdog (txBusyDeadlineMs) so a missing/spurious TX_DONE IRQ
    // can't wedge the FSM in TxBusy forever (out18) -- see Modem::checkTxBusyTimeout.
    void beginTx(const std::vector<std::uint8_t>& requestFrame, bool waitForAck,
                 std::uint32_t nowMs = 0, std::uint32_t txBusyTimeoutMs = 0) {
        if (waitForAck) {
            pendingAckRef = requestFrame;
        } else {
            pendingAckRef.clear();
        }
        txWasSendWithAck = waitForAck;
        txBusyDeadlineMs = nowMs + txBusyTimeoutMs;
        state = State::TxBusy;
    }

    // TX watchdog: if a TX has been in flight (TxBusy) past its deadline -- e.g. a
    // spurious/unknown IRQ was serviced as ClearAndReceive and TX_DONE never fired --
    // force the FSM back to RxListen so future TX is never permanently blocked.
    // Returns true iff it fired (caller reports "ERR TX <code>" + re-arms RX). Pure +
    // wrap-safe (signed subtraction), same shape as checkAckTimeout. A zero deadline
    // (legacy beginTx call without the watchdog args) disables the check.
    bool checkTxBusyTimeout(std::uint32_t nowMs) {
        if (state != State::TxBusy) return false;
        if (txBusyDeadlineMs == 0) return false;
        if (static_cast<std::int32_t>(nowMs - txBusyDeadlineMs) < 0) return false;
        state = State::RxListen;
        pendingAckRef.clear();
        txWasSendWithAck = false;
        return true;
    }

    // Called from the TX_DONE IRQ path. If the TX was send-with-ACK, arms the ACK
    // timeout and transitions to WaitAck; otherwise drops back to RxListen and the
    // caller reports "OK TX". Returns the new state so the caller can branch.
    State completeTx(std::uint32_t nowMs, std::uint32_t ackTimeoutMs) {
        if (txWasSendWithAck) {
            ackDeadlineMs = nowMs + ackTimeoutMs;
            state = State::WaitAck;
        } else {
            state = State::RxListen;
            pendingAckRef.clear();
            txWasSendWithAck = false;
        }
        return state;
    }

    // Called for every received frame (LoRa OR ESP-NOW dual-band). Returns true iff
    // we are in WaitAck AND `candidate` is a valid ACK for the in-flight request;
    // in that case the FSM transitions to RxListen and clears all wait-state.
    // Returns false otherwise (caller decides what to do -- log non-ACK while WaitAck,
    // route normal RX while RxListen, etc.).
    bool tryConsumeAck(const std::vector<std::uint8_t>& candidate) {
        if (state != State::WaitAck) return false;
        if (!looksLikeMatchingAck(pendingAckRef, candidate)) return false;
        state = State::RxListen;
        pendingAckRef.clear();
        txWasSendWithAck = false;
        return true;
    }

    // Called periodically from the main loop. If we are in WaitAck and the deadline
    // has passed (signed-subtraction wrap-safe), transitions to RxListen and returns
    // true so the caller can reportHost("ERR ACK_TIMEOUT") + re-arm RX. Else false.
    bool checkAckTimeout(std::uint32_t nowMs) {
        if (state != State::WaitAck) return false;
        if (static_cast<std::int32_t>(nowMs - ackDeadlineMs) < 0) return false;
        state = State::RxListen;
        pendingAckRef.clear();
        txWasSendWithAck = false;
        return true;
    }

    // Called by the LoRa RX-IRQ handler after processing a received frame: forces
    // the FSM back to RxListen unless we are still actively waiting for an ACK
    // (i.e. the candidate wasn't the matching ACK for the in-flight TX). Recovers
    // from the rare TxBusy + RX_DONE case where an RX IRQ fires mid-transmit.
    void forceListenIfNotWaitingAck() {
        if (state != State::WaitAck) {
            state = State::RxListen;
        }
    }
};

// ---------------------------------------------------------------------------
// PeerTracker: ESP-NOW unicast peer adoption + liveness tracking.
//
// Pure decision logic -- hardware ops (esp_now_add_peer / esp_now_del_peer) stay
// in main.cpp. The tracker tells the caller which hardware op is needed via the
// Update enum, and only mutates its (mac, lastSeenMs) state after the caller
// confirms the hardware op succeeded by calling commitNewPeer(). This is the key
// safety improvement over the in-tree firmware code, which overwrote the MAC
// buffer eagerly and could leave it stale if esp_now_add_peer failed.
// ---------------------------------------------------------------------------

// MAC_LEN now in modem_mac.h (shared w/ modem_hal.h to break the include cycle).

inline bool isBroadcastMac(const std::uint8_t* mac) {
    for (std::size_t i = 0; i < MAC_LEN; ++i) {
        if (mac[i] != 0xFF) return false;
    }
    return true;
}

inline bool macEquals(const std::uint8_t* a, const std::uint8_t* b) {
    for (std::size_t i = 0; i < MAC_LEN; ++i) {
        if (a[i] != b[i]) return false;
    }
    return true;
}

struct PeerTracker {
    // Matches firmware PEER_TIMEOUT_MS (5s). If no traffic from the peer for this
    // long, isExpired() returns true and the caller forgets() the peer.
    static constexpr std::uint32_t TIMEOUT_MS = 5000;

    bool havePeer = false;
    std::uint8_t mac[MAC_LEN] = {};
    std::uint32_t lastSeenMs = 0;

    enum class Update {
        Ignored,            // input was broadcast -> caller does nothing
        Refreshed,          // same MAC as current peer -> lastSeenMs bumped, no HW op
        AdoptionNeeded,     // no prior peer -> caller esp_now_add_peer then commitNewPeer
        ReplacementNeeded,  // different MAC -> caller del_peer(old) + add_peer(new) + commit
    };

    // Inspects a received MAC. Refreshed is the only branch that mutates state;
    // for AdoptionNeeded / ReplacementNeeded the caller MUST perform the hardware
    // op and -- iff it succeeds -- call commitNewPeer(macIn, nowMs) to record the
    // new peer. If hardware fails, do not call commit and state stays consistent.
    Update inspectRx(const std::uint8_t* macIn, std::uint32_t nowMs) {
        if (isBroadcastMac(macIn)) return Update::Ignored;
        if (havePeer && macEquals(macIn, mac)) {
            lastSeenMs = nowMs;
            return Update::Refreshed;
        }
        return havePeer ? Update::ReplacementNeeded : Update::AdoptionNeeded;
    }

    void commitNewPeer(const std::uint8_t* macIn, std::uint32_t nowMs) {
        for (std::size_t i = 0; i < MAC_LEN; ++i) mac[i] = macIn[i];
        havePeer = true;
        lastSeenMs = nowMs;
    }

    // True iff the current peer hasn't been seen for > TIMEOUT_MS. Signed-subtract
    // wrap-safe (lastSeenMs sentinel <= nowMs unless millis() overflowed ~49 days).
    bool isExpired(std::uint32_t nowMs) const {
        if (!havePeer) return false;
        return static_cast<std::int32_t>(nowMs - lastSeenMs) >
               static_cast<std::int32_t>(TIMEOUT_MS);
    }

    void forget() {
        havePeer = false;
        for (std::size_t i = 0; i < MAC_LEN; ++i) mac[i] = 0;
        lastSeenMs = 0;
    }
};

struct ModemHealthSnapshot {
    bool radioReady = false;
    bool espnowReady = false;
    bool radioFault = false;
    bool stopBackoffActive = false;
    std::uint32_t stopRetryCount = 0;

    bool havePeer = false;
    std::uint32_t peerAgeSeconds = 0;

    bool hasLoraQuality = false;
    float loraRssi = 0.0f;
    float loraSnr = 0.0f;

    std::uint32_t forwarded = 0;
    std::uint32_t espnowEnqueued = 0;
    std::uint32_t espnowQueueDropped = 0;
    std::uint32_t rxFree = 0;
    std::uint32_t dutyDropped = 0;
};

}  // namespace modem_core

#include <cstdio>  // std::snprintf for the "%.1f" RSSI/SNR formatting in tickRadioRx

// ---------------------------------------------------------------------------
// Modem: orchestration class -- the host-testable counterpart of c6l-modem's
// main.cpp loop. Holds REFERENCES to the four state structs (so this slice can
// migrate one tick method at a time without ripping out the firmware globals
// in a single patch) plus REFERENCES to the four HAL interfaces (modem_hal.h).
// Real-hardware adapters live in main.cpp; deterministic mocks live in
// tools/sim_native/modem_abi.cpp for the host tests.
//
// Migrated methods so far:
//   - tickAckTimeout(): replaces main.cpp's free-function serviceAckTimeout().
//
// Pending (future slices in this branch):
//   - tick() (drain duty + peer liveness + start next tx)
//   - serviceRadioIrq() (LoRa IRQ dispatch)
//   - serviceEspNowRx() (ESP-NOW intake)
//   - handleHostFrame() (UART -> queueRadioFrame)
//   - reportHealth()
// ---------------------------------------------------------------------------

#include "modem_hal.h"

namespace modem_core {

class Modem {
public:
    // 4 state refs + 4 HAL refs + 2 readiness-flag refs. Espnow is nullable for
    // single-band builds. radioReady / espnowReady are held BY REFERENCE (same model
    // as the state structs) rather than moved into the Modem because main.cpp's
    // enterReceive() + setup() -- which run before the Modem global is constructed --
    // need to read/write them; binding by ref lets both sides share one flag without
    // the construction-order problem a Modem-owned member would create.
    Modem(DutyBucket& duty,
          TxQueue& queue,
          RadioFsm& fsm,
          PeerTracker& peer,
          IClock& clock,
          IHostLink& host,
          IRadio& radio,
          IEspNow* espnow,
          bool& radioReady,
          bool& espnowReady)
        : duty_(duty), queue_(queue), fsm_(fsm), peer_(peer),
          clock_(clock), host_(host), radio_(radio), espnow_(espnow),
          radioReady_(radioReady), espnowReady_(espnowReady) {}

    // Configurable ACK timeout (matches firmware's ACK_TIMEOUT_MS = 900 ms).
    static constexpr std::uint32_t ACK_TIMEOUT_MS = 900;

    // TX watchdog window. A real SF7/BW250 transmit of even the largest frame is
    // tens of ms; if TX_DONE has not arrived within this bound the FSM is wedged
    // in TxBusy (e.g. a spurious IRQ was serviced as ClearAndReceive and TX_DONE
    // never fired) -- force-abort so future TX is never permanently blocked (out18).
    static constexpr std::uint32_t TX_BUSY_TIMEOUT_MS = 500;

    // Replaces main.cpp serviceAckTimeout(). Returns true iff the deadline fired
    // (the caller may want to log/count; main.cpp doesn't, the tests do).
    bool tickAckTimeout() {
        if (fsm_.checkAckTimeout(clock_.nowMs())) {
            host_.writeLine("ERR ACK_TIMEOUT");
            (void)radio_.startReceive();  // best-effort re-arm; matches main.cpp
            return true;
        }
        return false;
    }

    // TX-busy watchdog tick (out18): if a LoRa TX has been "in flight" past
    // TX_BUSY_TIMEOUT_MS without a TX_DONE/RX_DONE resolving it, the FSM is wedged
    // in TxBusy and canStartNextTx() would block ALL future TX (incl STOP) forever.
    // Force the FSM back to RxListen, tell the host (ERR TX TIMEOUT so the wire
    // format stays "ERR TX ..."), and best-effort re-arm RX. Returns true iff fired.
    bool tickTxWatchdog() {
        if (fsm_.checkTxBusyTimeout(clock_.nowMs())) {
            host_.writeLine("ERR TX TIMEOUT");
            (void)radio_.startReceive();  // best-effort re-arm; matches the ACK path
            return true;
        }
        return false;
    }

    // Replaces main.cpp serviceEspNowPeerLiveness() (DUAL_BAND build path).
    // If the current ESP-NOW peer hasn't been heard from for > PeerTracker::TIMEOUT_MS,
    // delete the hardware peer entry and forget the tracker state. Returns true iff
    // a peer was expired this tick. Espnow_ is null on single-band builds -- guarded.
    bool tickPeerLiveness() {
        if (!peer_.isExpired(clock_.nowMs())) return false;
        if (espnow_ != nullptr) espnow_->deletePeer(peer_.mac);
        peer_.forget();
        return true;
    }

    // Replaces main.cpp's inlined dutyBucket.drain(millis()) call at the top of loop().
    // Trivial single-line method but kept for consistency with the other tick* methods
    // so the firmware loop is a series of modem.tick*() calls in a single style.
    void tickDutyDrain() { duty_.drain(clock_.nowMs()); }

    // Stagger gate constant: minimum ms between an ESP-NOW send and the LoRa TX of
    // the SAME frame. Mirrors main.cpp's TX_STAGGER_MS=6 (so the LoRa start isn't
    // crowded by the ESP-NOW SPI traffic). STOP frames bypass the gate -- emergency
    // stop must always reach LoRa regardless of bus contention.
    static constexpr std::uint32_t TX_STAGGER_MS = 6;

    // Diagnostic counters (migrated from main.cpp globals so reportHealth +
    // tickEspNowRx + future tickRadioIrq migrations can read/write them via the
    // Modem instance). Public for the same reason main.cpp's globals were --
    // they're plain counters with no invariants.
    std::uint32_t foreignDropped = 0;  // frames lacking a valid protocol header
    std::uint32_t rxOtherCount = 0;    // non-matching RX while WaitAck (LoRa path)

    // Replaces main.cpp's serviceEspNowRx(): drains every ESP-NOW RX item from
    // espnow_.pollRx(), validates the protocol header, remembers the unicast peer
    // (delegating hardware add/delete to espnow_), logs "RX 0.0 0.0 <hex>" via
    // host_.writeLine, and lets the FSM consume the frame as an ACK iff it matches
    // an in-flight WaitAck. Frames with no header bump foreignDropped. No-op when
    // espnow_ is null (single-band builds).
    void tickEspNowRx() {
        if (espnow_ == nullptr) return;
        for (;;) {
            auto item = espnow_->pollRx();
            if (item.data.empty()) break;  // queue drained
            if (!hasProtocolHeader(item.data)) {
                ++foreignDropped;
                continue;
            }
            rememberPeer(item.src);
            // ESP-NOW doesn't surface RSSI/SNR -> use 0.0/0.0 placeholders to match
            // the firmware's prior log format (and the host-side parser expectations).
            std::string hex = prop_protocol::bytesToHex(item.data.data(),
                                                       item.data.size());
            host_.writeLine("RX 0.0 0.0 " + hex);
            bumpForwarded();
            (void)fsm_.tryConsumeAck(item.data);
        }
    }

    // Action returned by classifyRadioIrq(). Caller (main.cpp serviceRadioIrq)
    // performs the HW-side side effect for each action: FinishTx -> tickTxComplete
    // via the existing wrapper (which reads RadioLib finishTransmit + startReceive
    // codes); HandleRx -> tickRadioRx via the wrapper (which reads frame + RSSI +
    // SNR via RadioLib readData); ClearAndReceive -> radio.clearIrqFlags + the
    // enterReceive helper. None means the IRQ-pending check fell through and
    // there's no action to take this tick.
    enum class IrqAction { None, FinishTx, HandleRx, ClearAndReceive };

    // Replaces the dispatch portion of main.cpp serviceRadioIrq(): given the IRQ
    // flag bitmask + the chip's TX_DONE / RX_DONE bit values, decides which path
    // to take. The caller already validated radioReady + cleared the volatile
    // radioIrqFlag before calling this -- it's a pure switch on (FSM state,
    // irqFlags) with no side effects.
    IrqAction classifyRadioIrq(std::uint32_t irqFlags,
                               std::uint32_t txDoneBit,
                               std::uint32_t rxDoneBit) const {
        if (fsm_.state == RadioFsm::State::TxBusy && (irqFlags & txDoneBit)) {
            return IrqAction::FinishTx;
        }
        if (fsm_.state == RadioFsm::State::TxBusy && (irqFlags & rxDoneBit)) {
            return IrqAction::HandleRx;
        }
        if (irqFlags & rxDoneBit) return IrqAction::HandleRx;
        return IrqAction::ClearAndReceive;
    }

    // Parsed host-UART command kind. Returned by parseHostFrame(); caller dispatches.
    enum class HostCommand {
        LineTooLong,  // sentinel "__LINE_TOO_LONG__" from the UART line buffer
        Ping,         // "PING" -> caller emits "OK C6L_MODEM"
        SendAck,      // "SEND <hex>"  -> queue frame waiting for ACK
        SendNoAck,    // "ACK <hex>" or "FF <hex>" -> queue frame without ACK wait
        BadFrame,     // recognised prefix but the hex parse / length check failed
        BadCommand,   // none of the known prefixes matched
    };

    // Replaces main.cpp handleHostLine()'s parsing portion: classifies one line of
    // host UART input. On a SEND/ACK/FF command the parsed frame bytes are written
    // into `out_frame` (consuming the whole hex body, trimmed of trailing CR/LF/
    // space); on Ping / LineTooLong / BadFrame / BadCommand out_frame is cleared.
    // Caller (main.cpp) does the side effects: reportHost on Ping / errors, and
    // sendRadioFrame / sendAndWaitForAck on the SEND-class commands.
    HostCommand parseHostFrame(const std::string& line,
                               std::vector<std::uint8_t>& out_frame) {
        out_frame.clear();
        if (line == "__LINE_TOO_LONG__") return HostCommand::LineTooLong;
        if (line == "PING") return HostCommand::Ping;
        // Reusable hex extractor: takes the substring after the prefix, trims
        // whitespace, decodes via prop_protocol::hexToBytes, and bounds-checks
        // against MAX_RADIO_FRAME. Returns false iff the body is unparseable
        // or empty / oversized (which the caller surfaces as ERR BAD_FRAME).
        auto parseHexBody = [&](std::size_t prefix_len) -> bool {
            std::string hex = line.substr(prefix_len);
            while (!hex.empty() && (hex.back() == ' ' || hex.back() == '\r' ||
                                    hex.back() == '\n' || hex.back() == '\t')) {
                hex.pop_back();
            }
            while (!hex.empty() && (hex.front() == ' ' || hex.front() == '\t')) {
                hex.erase(0, 1);
            }
            if (!prop_protocol::hexToBytes(hex, out_frame)) {
                out_frame.clear();
                return false;
            }
            if (out_frame.empty() || out_frame.size() > MAX_RADIO_FRAME) {
                out_frame.clear();
                return false;
            }
            return true;
        };
        if (line.compare(0, 5, "SEND ") == 0) {
            return parseHexBody(5) ? HostCommand::SendAck : HostCommand::BadFrame;
        }
        if (line.compare(0, 4, "ACK ") == 0) {
            return parseHexBody(4) ? HostCommand::SendNoAck : HostCommand::BadFrame;
        }
        if (line.compare(0, 3, "FF ") == 0) {
            return parseHexBody(3) ? HostCommand::SendNoAck : HostCommand::BadFrame;
        }
        return HostCommand::BadCommand;
    }

    // Replaces main.cpp finishTxFromIrq()'s state-machine portion: takes the
    // RadioLib HW finishTransmit return code (0 = OK, non-zero = error). On error
    // emits "ERR TX <code>" and aborts the FSM back to RxListen. On success runs
    // completeTx -- if it returns RxListen (not WaitAck) the TX is fully done and
    // we emit "OK TX". The RadioLib startReceive error path stays in main.cpp
    // because it owns the radioReady flag (re-arming is HW-side, not Modem-side).
    void tickTxComplete(int hwTxStatus) {
        if (hwTxStatus != 0) {
            host_.writeLine("ERR TX " + std::to_string(hwTxStatus));
            fsm_.abortTx();
            return;
        }
        if (fsm_.completeTx(clock_.nowMs(), ACK_TIMEOUT_MS) ==
            RadioFsm::State::RxListen) {
            host_.writeLine("OK TX");
        }
    }

    // Replaces main.cpp handleRxFromIrq()'s body: takes the LoRa-read frame +
    // signal-quality, runs the header check + ACK match + RX log, then re-arms
    // the radio (clearIrqFlags + startReceive) and forces back to RxListen unless
    // we're still waiting for an ACK. Caller (main.cpp) reads the HW frame +
    // RSSI/SNR via the RadioLib adapter; if the read failed it passes an empty
    // frame (post-processing still runs to clear IRQs + re-arm).
    void tickRadioRx(const std::vector<std::uint8_t>& frame, float rssi, float snr) {
        if (!frame.empty()) {
            if (hasProtocolHeader(frame)) {
                std::string hex = prop_protocol::bytesToHex(frame.data(),
                                                           frame.size());
                // "%.1f" mirrors Arduino's String(rssi, 1) format (e.g. "-99.5").
                char qual[24];
                std::snprintf(qual, sizeof(qual), "%.1f %.1f", rssi, snr);
                host_.writeLine("RX " + std::string(qual) + " " + hex);
                recordLoraQuality(rssi, snr);
                bumpForwarded();
                bool wasWaitingForAck = fsm_.state == RadioFsm::State::WaitAck;
                if (!fsm_.tryConsumeAck(frame) && wasWaitingForAck) {
                    ++rxOtherCount;
                }
            } else {
                ++foreignDropped;
            }
        }
        radio_.clearIrqFlags();
        (void)radio_.startReceive();
        fsm_.forceListenIfNotWaitingAck();
    }

    // 2 s health interval (mirrors main.cpp's `if (millis() - lastHealthMs >= 2000)`).
    static constexpr std::uint32_t HEALTH_INTERVAL_MS = 2000;

    // Replaces main.cpp's reportHealth() + the 2s throttle gate around it. Returns
    // true iff this tick emitted a health line. espnowQueueDropped + rxFree are
    // passed in (they're owned by the ESP-NOW RX callback / FreeRTOS queue, which
    // stay main.cpp-side -- migrating them would need IEspNow extensions and
    // doesn't unlock further migrations, so they ride as args for now).
    bool tickHealthReport(std::uint32_t now_ms,
                          std::uint32_t espnow_queue_dropped,
                          std::uint32_t rx_free) {
        refreshHealthSnapshot(now_ms, espnow_queue_dropped, rx_free);
        if (now_ms - lastHealthMs_ < HEALTH_INTERVAL_MS) return false;
        lastHealthMs_ = now_ms;
        std::string line = "OK HEALTH foreign=" + std::to_string(foreignDropped) +
                           " qdrop=" + std::to_string(health_.espnowQueueDropped) +
                           " rxfree=" + std::to_string(health_.rxFree) +
                           " peer=" + (health_.havePeer ? "1" : "0") +
                           " dutyskip=" + std::to_string(health_.dutyDropped);
        host_.writeLine(line);
        return true;
    }

    bool consumeHealthSnapshot(std::uint32_t now_ms,
                               std::uint32_t espnow_queue_dropped,
                               std::uint32_t rx_free,
                               ModemHealthSnapshot& out) {
        refreshHealthSnapshot(now_ms, espnow_queue_dropped, rx_free);
        if (!healthDirty_) return false;
        out = health_;
        healthDirty_ = false;
        return true;
    }

    bool healthSnapshotDirty() const { return healthDirty_; }

    // Guard predicate for the first half of main.cpp's startNextQueuedTx(): returns
    // true iff the modem is ready to pop the next queued TX and hand it to the radio.
    // Reasons for false:
    //   - !radioReady (caller-managed, set by hardware init/error paths in main.cpp)
    //   - FSM != RxListen (TxBusy or WaitAck -- the radio is occupied)
    //   - queue empty
    //   - DUAL_BAND: !STOP front + ESP-NOW recently sent (stagger gate)
    // STOP frames bypass the stagger gate. The actual TX (radio.startTransmit, duty
    // charge, ESP-NOW peer notification) still lives in main.cpp for this slice --
    // future migration step will move it through the radio_/espnow_ HAL fully.
    bool canStartNextTx(bool radioReady,
                        std::uint32_t lastEspNowSendMs,
                        std::uint32_t txStaggerMs = TX_STAGGER_MS) {
        if (!radioReady) return false;
        if (fsm_.state != RadioFsm::State::RxListen) return false;
        if (queue_.empty()) return false;
        if (queue_.front().isStop && stopTxBackoffUntilMs_ != 0 &&
            static_cast<std::int32_t>(clock_.nowMs() - stopTxBackoffUntilMs_) < 0) {
            return false;
        }
        if (espnow_ != nullptr && !queue_.front().isStop) {
            // Signed-subtract wrap-safe gate (matches main.cpp's millis() math).
            if (clock_.nowMs() - lastEspNowSendMs < txStaggerMs) return false;
        }
        return true;
    }

    // Replaces main.cpp's queueRadioFrame(): host-side TX entry point. Validates
    // radio readiness + frame bounds, enqueues onto the STOP-priority TxQueue, and
    // (dual-band) immediately mirrors the frame onto ESP-NOW (unicast peer if known,
    // else broadcast) recording lastEspNowSendMs_ for the LoRa stagger gate. Emits
    // the same host error lines as the firmware. Returns true iff the frame was
    // accepted onto the queue.
    bool enqueueTx(const std::vector<std::uint8_t>& frame, bool waitForAck) {
        // SAFETY: a structurally valid STOP must survive a not-ready LoRa radio.
        // A transient startReceive() failure can leave radioReady_=false; the master
        // -off STOP must still be accepted + mirrored over ESP-NOW (when that leg is
        // up) so the receiver clears -- otherwise the host gets ERR RADIO_NOT_READY,
        // the Dial drops its pending state on ERR, and the receiver stays latched on.
        // (out16/out25). The structural check (frameIsValidStop) gates this bypass so
        // a garbage frame whose byte[3]==Stop can't slip past the readiness guard.
        const bool isValidStop = frameIsValidStop(frame);
        const bool espnowUsable = (espnow_ != nullptr && espnowReady_);
        if (!radioReady_ && !(isValidStop && espnowUsable)) {
            host_.writeLine("ERR RADIO_NOT_READY");
            return false;
        }
        if (frame.empty() || frame.size() > MAX_RADIO_FRAME) {
            host_.writeLine("ERR BAD_FRAME");
            return false;
        }
        // A2b (0.2): STOP must never be dropped. TxQueue encapsulates the invariant
        // (queue-full reject for non-STOP, evict + jump-front for STOP). STOP priority
        // is granted ONLY to a structurally valid STOP frame (frameIsValidStop) -- a
        // malformed UART frame whose type byte == Stop must not evict queued FIREs,
        // bypass duty, or trigger the indefinite LoRa retry (out16).
        TxRequest request;
        request.frame = frame;
        request.waitForAck = waitForAck;
        request.isStop = isValidStop;
        if (queue_.enqueue(request) == TxQueue::EnqueueResult::RejectedBusy) {
            host_.writeLine("ERR BUSY");
            return false;
        }
        if (espnow_ != nullptr && espnowReady_) {
            static const std::uint8_t broadcast[MAC_LEN] =
                {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
            const std::uint8_t* dst = peer_.havePeer ? peer_.mac : broadcast;
            if (espnow_->send(dst, frame.data(), frame.size())) {
                bumpEspNowEnqueued();
                bumpForwarded();
            }
            lastEspNowSendMs_ = clock_.nowMs();
        }
        return true;
    }

    // Replaces main.cpp's startNextQueuedTx() in full: pops the next queued TX,
    // applies the EU 868 duty gate (STOP bypasses), hands the frame to the radio
    // via radio_.startTransmit, and on success transitions the FSM to TxBusy. On
    // a LoRa start failure a STOP is retained at the front indefinitely with
    // backoff; it must not vanish on a LoRa-only emergency-stop link.
    // radioIrqPending is the volatile ISR flag (main.cpp owns it); if set this tick
    // is skipped so we don't start a TX while an IRQ is mid-service.
    void tickStartNextTx(bool radioIrqPending) {
        if (radioIrqPending) return;
        if (!canStartNextTx(radioReady_, lastEspNowSendMs_)) return;

        TxRequest request = queue_.front();
        queue_.popFront();

        // A2b (0.2): STOP always transmits on LoRa too -- never duty-skipped.
        if (espnow_ != nullptr && !request.isStop &&
            duty_.wouldExceedOnAdd(LORA_AIRTIME_MS_EST)) {
            ++duty_.dropped;
            // Tell the host so it can retry immediately instead of waiting on a slow
            // upstream timeout (used to vanish silently -> the host lost the FIRE/ARM).
            host_.writeLine("ERR DUTY");
            return;
        }

        int txStatus = radio_.startTransmit(request.frame.data(), request.frame.size());
        if (txStatus != 0) {
            host_.writeLine("ERR TX " + std::to_string(txStatus));
            setHealthField(health_.radioFault, true);
            // STOP must never be dropped: re-queue at the FRONT with backoff so the
            // next eligible pass retries the LoRa transmit forever. Non-STOP is not retried.
            if (request.isStop) {
                ++stopTxRetryCount_;
                stopTxBackoffUntilMs_ = clock_.nowMs() + stopRetryBackoffMs(stopTxRetryCount_);
                queue_.pushFront(request);
            }
            (void)radio_.startReceive();
            fsm_.abortTx();
            return;
        }
        stopTxRetryCount_ = 0;      // a transmit started OK -> clear STOP retry state
        stopTxBackoffUntilMs_ = 0;
        setHealthField(health_.radioFault, false);

        if (espnow_ != nullptr) {
            duty_.add(LORA_AIRTIME_MS_EST);
        }
        bumpForwarded();
        // Arm the TX-busy watchdog alongside the TX so a missing/spurious TX_DONE
        // can't wedge the FSM in TxBusy forever (out18; serviced by tickTxWatchdog).
        fsm_.beginTx(request.frame, request.waitForAck, clock_.nowMs(), TX_BUSY_TIMEOUT_MS);
    }

    // Readiness-flag accessors (main.cpp reads/writes these through the same refs).
    bool radioReady() const { return radioReady_; }
    bool espnowReady() const { return espnowReady_; }

    // Accessors (mainly for tests; main.cpp accesses the refs directly).
    DutyBucket& dutyBucket() { return duty_; }
    TxQueue& txQueue() { return queue_; }
    RadioFsm& radioFsm() { return fsm_; }
    PeerTracker& peerTracker() { return peer_; }

private:
    template <typename T>
    void setHealthField(T& field, const T& value) {
        if (field == value) return;
        field = value;
        healthDirty_ = true;
    }

    static std::uint32_t stopRetryBackoffMs(std::uint32_t retry_count) {
        static constexpr std::uint32_t INITIAL_MS = 25;
        static constexpr std::uint32_t MAX_MS = 1000;
        std::uint32_t delay_ms = INITIAL_MS;
        for (std::uint32_t i = 1; i < retry_count && delay_ms < MAX_MS; ++i) {
            delay_ms <<= 1;
            if (delay_ms > MAX_MS) delay_ms = MAX_MS;
        }
        return delay_ms;
    }

    void bumpForwarded() {
        ++health_.forwarded;
        healthDirty_ = true;
    }

    void bumpEspNowEnqueued() {
        ++health_.espnowEnqueued;
        healthDirty_ = true;
    }

    void recordLoraQuality(float rssi, float snr) {
        setHealthField(health_.hasLoraQuality, true);
        setHealthField(health_.loraRssi, rssi);
        setHealthField(health_.loraSnr, snr);
    }

    void refreshHealthSnapshot(std::uint32_t now_ms,
                               std::uint32_t espnow_queue_dropped,
                               std::uint32_t rx_free) {
        setHealthField(health_.radioReady, radioReady_);
        setHealthField(health_.espnowReady, espnowReady_);
        const bool stop_backoff_active =
            stopTxBackoffUntilMs_ != 0 &&
            static_cast<std::int32_t>(now_ms - stopTxBackoffUntilMs_) < 0;
        setHealthField(health_.stopBackoffActive, stop_backoff_active);
        setHealthField(health_.stopRetryCount, stopTxRetryCount_);
        setHealthField(health_.havePeer, peer_.havePeer);
        setHealthField(health_.peerAgeSeconds,
                       peer_.havePeer ? ((now_ms - peer_.lastSeenMs) / 1000) : 0);
        setHealthField(health_.espnowQueueDropped, espnow_queue_dropped);
        setHealthField(health_.rxFree, rx_free);
        setHealthField(health_.dutyDropped, duty_.dropped);
    }

    // Inline of main.cpp's old rememberEspNowPeer(): inspectRx -> hardware add/delete
    // through the IEspNow interface -> commit only on add success. Safety improvement
    // over the original ESP-IDF flow (which overwrote peerMac eagerly): if the new add
    // fails after the old peer was deleted, forget() so the next TX falls back to
    // broadcast. Called only from tickEspNowRx (private helper).
    void rememberPeer(const std::uint8_t* mac) {
        auto upd = peer_.inspectRx(mac, clock_.nowMs());
        if (upd == PeerTracker::Update::Ignored ||
            upd == PeerTracker::Update::Refreshed) {
            return;
        }
        if (espnow_ == nullptr) return;
        if (upd == PeerTracker::Update::ReplacementNeeded) {
            espnow_->deletePeer(peer_.mac);
        }
        if (espnow_->addPeer(mac)) {
            peer_.commitNewPeer(mac, clock_.nowMs());
        } else if (upd == PeerTracker::Update::ReplacementNeeded) {
            peer_.forget();
        }
    }

    DutyBucket& duty_;
    TxQueue& queue_;
    RadioFsm& fsm_;
    PeerTracker& peer_;
    IClock& clock_;
    IHostLink& host_;
    IRadio& radio_;
    IEspNow* espnow_;     // nullable (single-band builds)
    bool& radioReady_;    // HW radio init/usable flag (shared w/ main.cpp by ref)
    bool& espnowReady_;   // ESP-NOW init flag (shared w/ main.cpp by ref)
    std::uint32_t lastHealthMs_ = 0;       // 2s health throttle (0 = first fires at >=2000)
    std::uint32_t lastEspNowSendMs_ = 0;   // last ESP-NOW send time (LoRa stagger gate input)
    std::uint32_t stopTxRetryCount_ = 0;   // unbounded STOP start-failure retry count
    std::uint32_t stopTxBackoffUntilMs_ = 0;
    ModemHealthSnapshot health_;
    bool healthDirty_ = true;
};

}  // namespace modem_core
