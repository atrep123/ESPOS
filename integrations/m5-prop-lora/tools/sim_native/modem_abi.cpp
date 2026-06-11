// extern-C ABI exposing the extracted modem_core decision logic
// (firmware/c6l-modem/src/modem_core.h) for ctypes-driven host tests.
// Used by tools/sim_native/check_modem_core.py to verify the safety-critical ACK
// matching off-device, identical to what the firmware FSM runs on the ESP32-C6.

#include <cstdint>
#include <cstring>
#include <new>
#include <utility>
#include <vector>

#include "modem_core.h"

extern "C" {

bool mc_has_protocol_header(const std::uint8_t* data, int len) {
    if (data == nullptr || len < 0) return false;
    std::vector<std::uint8_t> v(data, data + len);
    return modem_core::hasProtocolHeader(v);
}

bool mc_looks_like_matching_ack(const std::uint8_t* req, int req_len,
                                const std::uint8_t* cand, int cand_len) {
    if (req == nullptr || cand == nullptr || req_len < 0 || cand_len < 0) return false;
    std::vector<std::uint8_t> request(req, req + req_len);
    std::vector<std::uint8_t> candidate(cand, cand + cand_len);
    return modem_core::looksLikeMatchingAck(request, candidate);
}

std::uint32_t mc_read_frame_u32(const std::uint8_t* frame, int frame_len, int offset) {
    if (frame == nullptr || offset < 0 || offset + 4 > frame_len) return 0;
    std::vector<std::uint8_t> v(frame, frame + frame_len);
    return modem_core::readFrameU32(v, static_cast<std::size_t>(offset));
}

// --- DutyBucket (opaque buffer ABI: host allocs sizeof bytes, mc_duty_init
//     placement-news a DutyBucket in it; all calls take that buffer pointer).

int mc_duty_sizeof() {
    return static_cast<int>(sizeof(modem_core::DutyBucket));
}

void mc_duty_init(void* p) {
    new (p) modem_core::DutyBucket();
}

void mc_duty_drain(void* p, std::uint32_t now_ms) {
    static_cast<modem_core::DutyBucket*>(p)->drain(now_ms);
}

bool mc_duty_would_exceed(const void* p, std::uint32_t airtime_ms) {
    return static_cast<const modem_core::DutyBucket*>(p)->wouldExceedOnAdd(airtime_ms);
}

void mc_duty_add(void* p, std::uint32_t airtime_ms) {
    static_cast<modem_core::DutyBucket*>(p)->add(airtime_ms);
}

float mc_duty_bucket_ms(const void* p) {
    return static_cast<const modem_core::DutyBucket*>(p)->bucketMs;
}

std::uint32_t mc_duty_dropped(const void* p) {
    return static_cast<const modem_core::DutyBucket*>(p)->dropped;
}

std::uint32_t mc_duty_cap_ms() { return modem_core::DutyBucket::CAP_MS; }
std::uint32_t mc_duty_budget_ms() { return modem_core::DutyBucket::BUDGET_MS; }
std::uint32_t mc_duty_window_ms() { return modem_core::DutyBucket::WINDOW_MS; }

// --- TxQueue (opaque buffer ABI: host allocs sizeof bytes, mc_txqueue_init placement-news
//     a TxQueue in it; MUST call mc_txqueue_destroy before freeing the buffer because
//     TxQueue owns std::vector<TxRequest> and each TxRequest owns std::vector<uint8_t>).
//
// EnqueueResult is returned as int: 0=Accepted, 1=AcceptedStopEvicted, 2=RejectedBusy.

int mc_txqueue_sizeof() {
    return static_cast<int>(sizeof(modem_core::TxQueue));
}

void mc_txqueue_init(void* p) {
    new (p) modem_core::TxQueue();
}

void mc_txqueue_destroy(void* p) {
    static_cast<modem_core::TxQueue*>(p)->~TxQueue();
}

int mc_txqueue_enqueue(void* p, const std::uint8_t* frame, int len,
                       bool wait_for_ack, bool is_stop) {
    if (frame == nullptr || len < 0) return -1;
    modem_core::TxRequest req;
    req.frame.assign(frame, frame + len);
    req.waitForAck = wait_for_ack;
    req.isStop = is_stop;
    auto r = static_cast<modem_core::TxQueue*>(p)->enqueue(std::move(req));
    return static_cast<int>(r);
}

int mc_txqueue_size(const void* p) {
    return static_cast<int>(static_cast<const modem_core::TxQueue*>(p)->size());
}

bool mc_txqueue_empty(const void* p) {
    return static_cast<const modem_core::TxQueue*>(p)->empty();
}

// Reads front: writes flags through the pointers (if non-null) and copies the frame
// bytes into `out` iff `out != nullptr && cap >= n`. Returns frame length, or -1 if
// the queue is empty. Caller can pass out=nullptr to query length first.
int mc_txqueue_front_frame(const void* p, std::uint8_t* out, int cap,
                           bool* out_wait_for_ack, bool* out_is_stop) {
    const auto* q = static_cast<const modem_core::TxQueue*>(p);
    if (q->empty()) return -1;
    const auto& f = q->front();
    if (out_wait_for_ack != nullptr) *out_wait_for_ack = f.waitForAck;
    if (out_is_stop != nullptr) *out_is_stop = f.isStop;
    int n = static_cast<int>(f.frame.size());
    if (out != nullptr && cap >= n) {
        std::memcpy(out, f.frame.data(), static_cast<std::size_t>(n));
    }
    return n;
}

void mc_txqueue_pop_front(void* p) {
    static_cast<modem_core::TxQueue*>(p)->popFront();
}

void mc_txqueue_push_front(void* p, const std::uint8_t* frame, int len,
                           bool wait_for_ack, bool is_stop) {
    if (frame == nullptr || len < 0) return;
    modem_core::TxRequest req;
    req.frame.assign(frame, frame + len);
    req.waitForAck = wait_for_ack;
    req.isStop = is_stop;
    static_cast<modem_core::TxQueue*>(p)->pushFront(std::move(req));
}

int mc_txqueue_depth() {
    return static_cast<int>(modem_core::TxQueue::DEPTH);
}

// --- RadioFsm (opaque buffer ABI: TxQueue-style; owns std::vector pendingAckRef,
//     so caller MUST mc_fsm_destroy before freeing the buffer).
//
// State enum maps to int: 0=RxListen, 1=TxBusy, 2=WaitAck (matches RadioFsm::State).

int mc_fsm_sizeof() {
    return static_cast<int>(sizeof(modem_core::RadioFsm));
}

void mc_fsm_init(void* p) {
    new (p) modem_core::RadioFsm();
}

void mc_fsm_destroy(void* p) {
    static_cast<modem_core::RadioFsm*>(p)->~RadioFsm();
}

int mc_fsm_state(const void* p) {
    return static_cast<int>(static_cast<const modem_core::RadioFsm*>(p)->state);
}

void mc_fsm_abort_tx(void* p) {
    static_cast<modem_core::RadioFsm*>(p)->abortTx();
}

void mc_fsm_begin_tx(void* p, const std::uint8_t* frame, int len, bool wait_for_ack) {
    if (frame == nullptr || len < 0) return;
    std::vector<std::uint8_t> req(frame, frame + len);
    static_cast<modem_core::RadioFsm*>(p)->beginTx(req, wait_for_ack);
}

int mc_fsm_complete_tx(void* p, std::uint32_t now_ms, std::uint32_t ack_timeout_ms) {
    return static_cast<int>(
        static_cast<modem_core::RadioFsm*>(p)->completeTx(now_ms, ack_timeout_ms));
}

bool mc_fsm_try_consume_ack(void* p, const std::uint8_t* cand, int len) {
    if (cand == nullptr || len < 0) return false;
    std::vector<std::uint8_t> v(cand, cand + len);
    return static_cast<modem_core::RadioFsm*>(p)->tryConsumeAck(v);
}

bool mc_fsm_check_ack_timeout(void* p, std::uint32_t now_ms) {
    return static_cast<modem_core::RadioFsm*>(p)->checkAckTimeout(now_ms);
}

void mc_fsm_force_listen_if_not_waiting_ack(void* p) {
    static_cast<modem_core::RadioFsm*>(p)->forceListenIfNotWaitingAck();
}

std::uint32_t mc_fsm_ack_deadline_ms(const void* p) {
    return static_cast<const modem_core::RadioFsm*>(p)->ackDeadlineMs;
}

bool mc_fsm_tx_was_send_with_ack(const void* p) {
    return static_cast<const modem_core::RadioFsm*>(p)->txWasSendWithAck;
}

// Reads the pending-ACK reference frame: writes bytes into `out` iff
// out != nullptr && cap >= n. Returns the byte count (0 if no pending wait).
int mc_fsm_pending_ack_ref(const void* p, std::uint8_t* out, int cap) {
    const auto& ref = static_cast<const modem_core::RadioFsm*>(p)->pendingAckRef;
    int n = static_cast<int>(ref.size());
    if (out != nullptr && cap >= n) {
        std::memcpy(out, ref.data(), static_cast<std::size_t>(n));
    }
    return n;
}

// --- PeerTracker (opaque buffer ABI; no vectors so destroy is symmetric/no-op).
//
// Update enum maps to int: 0=Ignored, 1=Refreshed, 2=AdoptionNeeded, 3=ReplacementNeeded.

int mc_peer_sizeof() {
    return static_cast<int>(sizeof(modem_core::PeerTracker));
}

void mc_peer_init(void* p) {
    new (p) modem_core::PeerTracker();
}

void mc_peer_destroy(void* p) {
    static_cast<modem_core::PeerTracker*>(p)->~PeerTracker();
}

bool mc_peer_have_peer(const void* p) {
    return static_cast<const modem_core::PeerTracker*>(p)->havePeer;
}

int mc_peer_mac(const void* p, std::uint8_t* out, int cap) {
    const auto* pt = static_cast<const modem_core::PeerTracker*>(p);
    int n = static_cast<int>(modem_core::MAC_LEN);
    if (out != nullptr && cap >= n) {
        std::memcpy(out, pt->mac, static_cast<std::size_t>(n));
    }
    return n;
}

std::uint32_t mc_peer_last_seen_ms(const void* p) {
    return static_cast<const modem_core::PeerTracker*>(p)->lastSeenMs;
}

int mc_peer_inspect_rx(void* p, const std::uint8_t* mac, std::uint32_t now_ms) {
    if (mac == nullptr) return -1;
    return static_cast<int>(
        static_cast<modem_core::PeerTracker*>(p)->inspectRx(mac, now_ms));
}

void mc_peer_commit_new_peer(void* p, const std::uint8_t* mac, std::uint32_t now_ms) {
    if (mac == nullptr) return;
    static_cast<modem_core::PeerTracker*>(p)->commitNewPeer(mac, now_ms);
}

bool mc_peer_is_expired(const void* p, std::uint32_t now_ms) {
    return static_cast<const modem_core::PeerTracker*>(p)->isExpired(now_ms);
}

void mc_peer_forget(void* p) {
    static_cast<modem_core::PeerTracker*>(p)->forget();
}

std::uint32_t mc_peer_timeout_ms() { return modem_core::PeerTracker::TIMEOUT_MS; }
int mc_peer_mac_len() { return static_cast<int>(modem_core::MAC_LEN); }

bool mc_is_broadcast_mac(const std::uint8_t* mac) {
    if (mac == nullptr) return false;
    return modem_core::isBroadcastMac(mac);
}

bool mc_mac_equals(const std::uint8_t* a, const std::uint8_t* b) {
    if (a == nullptr || b == nullptr) return false;
    return modem_core::macEquals(a, b);
}

}  // extern "C"

// ---------------------------------------------------------------------------
// HAL mock implementations + ModemHarness test fixture. Deterministic stand-ins
// for the real ESP32 hardware adapters in firmware/c6l-modem/src/main.cpp, so a
// host test can construct a modem_core::Modem and exercise its tick methods.
// ---------------------------------------------------------------------------

namespace {

class MockClock : public modem_core::IClock {
public:
    std::uint32_t now = 0;
    std::uint32_t nowMs() override { return now; }
};

class MockHostLink : public modem_core::IHostLink {
public:
    std::vector<std::string> writtenLines;
    std::string readLine() override { return std::string(); }
    void writeLine(const std::string& line) override { writtenLines.push_back(line); }
};

class MockRadio : public modem_core::IRadio {
public:
    int startReceiveCount = 0;
    int startTransmitCount = 0;
    int finishTransmitCount = 0;
    std::uint32_t irqFlags = 0;
    bool irqPending = false;
    // startTransmit return code (0 = OK); tests flip to a non-zero error code to
    // exercise the tickStartNextTx failure path (ERR TX + STOP retry).
    int startTransmitResult = 0;
    std::vector<std::uint8_t> lastTxFrame;  // bytes handed to the last startTransmit
    bool startReceive() override { ++startReceiveCount; return true; }
    int startTransmit(const std::uint8_t* data, std::size_t len) override {
        ++startTransmitCount;
        lastTxFrame.assign(data, data + len);
        return startTransmitResult;
    }
    bool finishTransmit() override { ++finishTransmitCount; return true; }
    std::vector<std::uint8_t> readReceivedFrame() override { return {}; }
    std::uint32_t getIrqFlags() override { return irqFlags; }
    void clearIrqFlags() override { irqFlags = 0; }
    bool takeIrqFlag() override {
        bool t = irqPending;
        irqPending = false;
        return t;
    }
};

class MockEspNow : public modem_core::IEspNow {
public:
    int sendCount = 0;
    int addPeerCount = 0;
    int deletePeerCount = 0;
    // Last MAC passed to addPeer / deletePeer (zeroed until first call).
    std::uint8_t lastAddedMac[modem_core::MAC_LEN] = {};
    std::uint8_t lastDeletedMac[modem_core::MAC_LEN] = {};
    // Default true so rememberPeer commits the new peer; tests can flip to false
    // to exercise the "HW add failed -> forget the deleted-old replacement" branch.
    bool addPeerResult = true;
    // FIFO of RX items returned by successive pollRx() calls. Tests enqueue here
    // to simulate ESP-NOW traffic arriving from the network.
    std::vector<RxItem> rxQueue;

    // Last send() call observability (for enqueueTx ESP-NOW mirror tests).
    std::uint8_t lastSentDst[modem_core::MAC_LEN] = {};
    int lastSentLen = -1;
    bool send(const std::uint8_t* mac, const std::uint8_t*, std::size_t len) override {
        ++sendCount;
        if (mac != nullptr) std::memcpy(lastSentDst, mac, modem_core::MAC_LEN);
        lastSentLen = static_cast<int>(len);
        return true;
    }
    bool addPeer(const std::uint8_t* mac) override {
        ++addPeerCount;
        if (mac != nullptr) std::memcpy(lastAddedMac, mac, modem_core::MAC_LEN);
        return addPeerResult;
    }
    void deletePeer(const std::uint8_t* mac) override {
        ++deletePeerCount;
        if (mac != nullptr) {
            std::memcpy(lastDeletedMac, mac, modem_core::MAC_LEN);
        }
    }
    RxItem pollRx() override {
        if (rxQueue.empty()) return RxItem{};
        RxItem item = std::move(rxQueue.front());
        rxQueue.erase(rxQueue.begin());
        return item;
    }
};

struct ModemHarness {
    modem_core::DutyBucket duty;
    modem_core::TxQueue queue;
    modem_core::RadioFsm fsm;
    modem_core::PeerTracker peer;
    MockClock clock;
    MockHostLink host;
    MockRadio radio;
    MockEspNow espnow;
    bool radioReady = false;   // bound into the Modem by ref (matches main.cpp's global)
    bool espnowReady = false;
    modem_core::Modem modem{duty, queue, fsm, peer, clock, host, radio, &espnow,
                            radioReady, espnowReady};
};

}  // anonymous namespace

extern "C" {

int mc_harness_sizeof() { return static_cast<int>(sizeof(ModemHarness)); }
void mc_harness_init(void* p) { new (p) ModemHarness(); }
void mc_harness_destroy(void* p) { static_cast<ModemHarness*>(p)->~ModemHarness(); }

// MockClock control
void mc_harness_set_now_ms(void* p, std::uint32_t now) {
    static_cast<ModemHarness*>(p)->clock.now = now;
}

// Seed the FSM into WaitAck state without going through beginTx+completeTx (so the
// test can isolate tickAckTimeout). req_frame is the (would-be) in-flight TX bytes
// used by modem_core::looksLikeMatchingAck if an ACK had arrived.
void mc_harness_seed_wait_ack(void* p, std::uint32_t deadline_ms,
                              const std::uint8_t* req_frame, int req_len) {
    auto* h = static_cast<ModemHarness*>(p);
    h->fsm.state = modem_core::RadioFsm::State::WaitAck;
    h->fsm.ackDeadlineMs = deadline_ms;
    h->fsm.txWasSendWithAck = true;
    if (req_frame != nullptr && req_len > 0) {
        h->fsm.pendingAckRef.assign(req_frame, req_frame + req_len);
    } else {
        h->fsm.pendingAckRef.clear();
    }
}

// Invoke Modem.tickAckTimeout(); returns whether the timeout fired.
bool mc_harness_tick_ack_timeout(void* p) {
    return static_cast<ModemHarness*>(p)->modem.tickAckTimeout();
}

// Observable getters from mocks
int mc_harness_start_receive_count(const void* p) {
    return static_cast<const ModemHarness*>(p)->radio.startReceiveCount;
}

int mc_harness_written_line_count(const void* p) {
    return static_cast<int>(static_cast<const ModemHarness*>(p)->host.writtenLines.size());
}

// Copies the idx-th written line (NUL-terminated) into out. Returns line length, or
// -1 on out-of-range. Pass out=nullptr/cap=0 to query length first.
int mc_harness_written_line(const void* p, int idx, char* out, int cap) {
    const auto& lines = static_cast<const ModemHarness*>(p)->host.writtenLines;
    if (idx < 0 || static_cast<std::size_t>(idx) >= lines.size()) return -1;
    const std::string& s = lines[idx];
    int n = static_cast<int>(s.size());
    if (out != nullptr && cap >= n + 1) {
        std::memcpy(out, s.data(), static_cast<std::size_t>(n));
        out[n] = '\0';
    }
    return n;
}

int mc_harness_fsm_state(const void* p) {
    return static_cast<int>(static_cast<const ModemHarness*>(p)->fsm.state);
}

// PeerTracker seeding via the harness (so Python tests can construct a peer state
// without needing access to the inner PeerTracker pointer + worrying about double-
// init via placement new).
void mc_harness_peer_commit(void* p, const std::uint8_t* mac, std::uint32_t now_ms) {
    if (mac == nullptr) return;
    static_cast<ModemHarness*>(p)->peer.commitNewPeer(mac, now_ms);
}

bool mc_harness_peer_have_peer(const void* p) {
    return static_cast<const ModemHarness*>(p)->peer.havePeer;
}

int mc_harness_peer_mac(const void* p, std::uint8_t* out, int cap) {
    const auto& peer = static_cast<const ModemHarness*>(p)->peer;
    int n = static_cast<int>(modem_core::MAC_LEN);
    if (out != nullptr && cap >= n) {
        std::memcpy(out, peer.mac, static_cast<std::size_t>(n));
    }
    return n;
}

std::uint32_t mc_harness_peer_last_seen_ms(const void* p) {
    return static_cast<const ModemHarness*>(p)->peer.lastSeenMs;
}

// Invoke Modem.tickPeerLiveness(); returns whether a peer expired this tick.
bool mc_harness_tick_peer_liveness(void* p) {
    return static_cast<ModemHarness*>(p)->modem.tickPeerLiveness();
}

// FSM state seeding (independent of WaitAck-specific seeder).
void mc_harness_seed_fsm_state(void* p, int state) {
    static_cast<ModemHarness*>(p)->fsm.state =
        static_cast<modem_core::RadioFsm::State>(state);
}

// TxQueue seeding via the harness (enqueue a frame onto the inner txQueue).
// Returns EnqueueResult as int (0=Accepted, 1=AcceptedStopEvicted, 2=RejectedBusy).
int mc_harness_queue_enqueue(void* p, const std::uint8_t* frame, int len,
                             bool wait_for_ack, bool is_stop) {
    if (frame == nullptr || len < 0) return -1;
    modem_core::TxRequest req;
    req.frame.assign(frame, frame + len);
    req.waitForAck = wait_for_ack;
    req.isStop = is_stop;
    auto r = static_cast<ModemHarness*>(p)->queue.enqueue(std::move(req));
    return static_cast<int>(r);
}

int mc_harness_queue_size(const void* p) {
    return static_cast<int>(static_cast<const ModemHarness*>(p)->queue.size());
}

// Modem.canStartNextTx guard predicate.
bool mc_harness_can_start_next_tx(void* p, bool radio_ready,
                                  std::uint32_t last_espnow_send_ms) {
    return static_cast<ModemHarness*>(p)->modem.canStartNextTx(
        radio_ready, last_espnow_send_ms);
}

// MockEspNow RX-queue seeding + observability + addPeer success-toggle for the
// rememberPeer test paths.
void mc_harness_seed_espnow_rx(void* p, const std::uint8_t* src_mac,
                               const std::uint8_t* data, int len) {
    if (src_mac == nullptr || data == nullptr || len < 0) return;
    modem_core::IEspNow::RxItem item;
    std::memcpy(item.src, src_mac, modem_core::MAC_LEN);
    item.data.assign(data, data + len);
    static_cast<ModemHarness*>(p)->espnow.rxQueue.push_back(std::move(item));
}

void mc_harness_set_addpeer_result(void* p, bool result) {
    static_cast<ModemHarness*>(p)->espnow.addPeerResult = result;
}

int mc_harness_espnow_add_peer_count(const void* p) {
    return static_cast<const ModemHarness*>(p)->espnow.addPeerCount;
}

int mc_harness_espnow_last_added_mac(const void* p, std::uint8_t* out, int cap) {
    const auto& espnow = static_cast<const ModemHarness*>(p)->espnow;
    int n = static_cast<int>(modem_core::MAC_LEN);
    if (out != nullptr && cap >= n) {
        std::memcpy(out, espnow.lastAddedMac, static_cast<std::size_t>(n));
    }
    return n;
}

// Modem.tickEspNowRx (full RX drain): hasProtocolHeader + rememberPeer +
// host_.writeLine "RX 0.0 0.0 <hex>" + fsm_.tryConsumeAck per item.
void mc_harness_tick_espnow_rx(void* p) {
    static_cast<ModemHarness*>(p)->modem.tickEspNowRx();
}

// Counter accessors (Modem owns foreignDropped + rxOtherCount now).
std::uint32_t mc_harness_foreign_dropped(const void* p) {
    return static_cast<const ModemHarness*>(p)->modem.foreignDropped;
}

std::uint32_t mc_harness_rx_other_count(const void* p) {
    return static_cast<const ModemHarness*>(p)->modem.rxOtherCount;
}

// Modem.tickHealthReport(now, espnow_queue_dropped, rx_free) -> bool fired.
bool mc_harness_tick_health_report(void* p, std::uint32_t now_ms,
                                   std::uint32_t qdrop, std::uint32_t rx_free) {
    return static_cast<ModemHarness*>(p)->modem.tickHealthReport(
        now_ms, qdrop, rx_free);
}

// Modem.tickRadioRx(frame, rssi, snr): LoRa RX path (HW read in main.cpp; logic
// + log + re-arm here). Pass len<0 or frame=nullptr to signal an empty frame
// (still runs the post-process: clearIrqFlags + startReceive + forceListen).
void mc_harness_tick_radio_rx(void* p, const std::uint8_t* frame, int len,
                              float rssi, float snr) {
    std::vector<std::uint8_t> v;
    if (frame != nullptr && len > 0) {
        v.assign(frame, frame + len);
    }
    static_cast<ModemHarness*>(p)->modem.tickRadioRx(v, rssi, snr);
}

// Modem.tickTxComplete(hw_tx_status): TX completion path -- 0=ok, non-zero=error.
void mc_harness_tick_tx_complete(void* p, int hw_tx_status) {
    static_cast<ModemHarness*>(p)->modem.tickTxComplete(hw_tx_status);
}

// Seed FSM into TxBusy with a specific in-flight request frame + waitForAck flag
// (via RadioFsm.beginTx). Lets tests prepare the state tickTxComplete completes.
void mc_harness_seed_tx_busy(void* p, const std::uint8_t* frame, int len,
                             bool wait_for_ack) {
    std::vector<std::uint8_t> req;
    if (frame != nullptr && len > 0) req.assign(frame, frame + len);
    static_cast<ModemHarness*>(p)->fsm.beginTx(req, wait_for_ack);
}

// Modem.classifyRadioIrq(flags, txDoneBit, rxDoneBit) -> int (IrqAction:
// 0=None, 1=FinishTx, 2=HandleRx, 3=ClearAndReceive).
int mc_harness_classify_radio_irq(const void* p, std::uint32_t flags,
                                  std::uint32_t tx_done_bit,
                                  std::uint32_t rx_done_bit) {
    return static_cast<int>(
        static_cast<const ModemHarness*>(p)->modem.classifyRadioIrq(
            flags, tx_done_bit, rx_done_bit));
}

// --- TX engine (enqueueTx + tickStartNextTx) + readiness flags ---

void mc_harness_set_radio_ready(void* p, bool ready) {
    static_cast<ModemHarness*>(p)->radioReady = ready;
}
void mc_harness_set_espnow_ready(void* p, bool ready) {
    static_cast<ModemHarness*>(p)->espnowReady = ready;
}
void mc_harness_set_tx_result(void* p, int result) {
    static_cast<ModemHarness*>(p)->radio.startTransmitResult = result;
}

// Modem.enqueueTx(frame, waitForAck) -> bool accepted.
bool mc_harness_enqueue_tx(void* p, const std::uint8_t* frame, int len, bool wait_for_ack) {
    std::vector<std::uint8_t> v;
    if (frame != nullptr && len > 0) v.assign(frame, frame + len);
    return static_cast<ModemHarness*>(p)->modem.enqueueTx(v, wait_for_ack);
}

// Modem.tickStartNextTx(radioIrqPending).
void mc_harness_tick_start_next_tx(void* p, bool radio_irq_pending) {
    static_cast<ModemHarness*>(p)->modem.tickStartNextTx(radio_irq_pending);
}

// MockRadio TX observability.
int mc_harness_start_transmit_count(const void* p) {
    return static_cast<const ModemHarness*>(p)->radio.startTransmitCount;
}
int mc_harness_last_tx_frame(const void* p, std::uint8_t* out, int cap) {
    const auto& f = static_cast<const ModemHarness*>(p)->radio.lastTxFrame;
    int n = static_cast<int>(f.size());
    if (out != nullptr && cap >= n) std::memcpy(out, f.data(), static_cast<std::size_t>(n));
    return n;
}

// MockEspNow send observability.
int mc_harness_espnow_send_count(const void* p) {
    return static_cast<const ModemHarness*>(p)->espnow.sendCount;
}
int mc_harness_espnow_last_sent_len(const void* p) {
    return static_cast<const ModemHarness*>(p)->espnow.lastSentLen;
}
int mc_harness_espnow_last_sent_dst(const void* p, std::uint8_t* out, int cap) {
    const auto& espnow = static_cast<const ModemHarness*>(p)->espnow;
    int n = static_cast<int>(modem_core::MAC_LEN);
    if (out != nullptr && cap >= n) std::memcpy(out, espnow.lastSentDst, static_cast<std::size_t>(n));
    return n;
}

// DutyBucket dropped counter (for the ERR DUTY path test).
std::uint32_t mc_harness_duty_dropped(const void* p) {
    return static_cast<const ModemHarness*>(p)->duty.dropped;
}
void mc_harness_duty_add(void* p, std::uint32_t airtime_ms) {
    static_cast<ModemHarness*>(p)->duty.add(airtime_ms);
}

// Modem.parseHostFrame(line) -> int (HostCommand enum value: 0=LineTooLong,
// 1=Ping, 2=SendAck, 3=SendNoAck, 4=BadFrame, 5=BadCommand). out_frame may
// be passed nullptr if the test only cares about the kind.
int mc_harness_parse_host_frame(void* p, const char* line,
                                std::uint8_t* out_frame, int out_cap,
                                int* out_len) {
    std::string s(line == nullptr ? "" : line);
    std::vector<std::uint8_t> frame;
    auto cmd = static_cast<ModemHarness*>(p)->modem.parseHostFrame(s, frame);
    if (out_len != nullptr) *out_len = static_cast<int>(frame.size());
    if (out_frame != nullptr && out_cap >= static_cast<int>(frame.size())) {
        std::memcpy(out_frame, frame.data(), frame.size());
    }
    return static_cast<int>(cmd);
}

// MockEspNow observability
int mc_harness_espnow_delete_peer_count(const void* p) {
    return static_cast<const ModemHarness*>(p)->espnow.deletePeerCount;
}

int mc_harness_espnow_last_deleted_mac(const void* p, std::uint8_t* out, int cap) {
    const auto& espnow = static_cast<const ModemHarness*>(p)->espnow;
    int n = static_cast<int>(modem_core::MAC_LEN);
    if (out != nullptr && cap >= n) {
        std::memcpy(out, espnow.lastDeletedMac, static_cast<std::size_t>(n));
    }
    return n;
}

}  // extern "C"

// ===========================================================================
// Callback HAL: a modem_core::Modem whose IClock/IHostLink/IRadio/IEspNow
// delegate to C function pointers supplied by the caller (sim_link.py via ctypes
// CFUNCTYPE). This lets the Python dual-band simulator run the REAL firmware modem
// logic end-to-end: the sim's EventLoop/DualBandChannel back the HAL, and the sim
// drives the Modem tick methods at sim-events directly (it knows the event type,
// so no SX1262 IRQ-dispatch emulation is needed -- the unused IRadio reads stub out).
// ===========================================================================

extern "C" {
typedef std::uint32_t (*MC_NowMs)(void* ctx);
typedef void (*MC_WriteLine)(void* ctx, const char* line);
typedef int (*MC_StartTransmit)(void* ctx, const std::uint8_t* data, int len);  // HW status (0=OK)
typedef int (*MC_EspSend)(void* ctx, const std::uint8_t* mac, const std::uint8_t* data, int len);  // bool
typedef int (*MC_EspAddPeer)(void* ctx, const std::uint8_t* mac);  // bool
typedef void (*MC_EspDeletePeer)(void* ctx, const std::uint8_t* mac);
// Fills src6 (6 bytes) + data_out (up to data_cap); returns data length, or -1 if
// the ESP-NOW RX queue is empty.
typedef int (*MC_EspPollRx)(void* ctx, std::uint8_t* src6, std::uint8_t* data_out, int data_cap);
}  // extern "C"

namespace {

class CbClock : public modem_core::IClock {
public:
    void* ctx = nullptr;
    MC_NowMs fn = nullptr;
    std::uint32_t nowMs() override { return fn(ctx); }
};

class CbHostLink : public modem_core::IHostLink {
public:
    void* ctx = nullptr;
    MC_WriteLine fn = nullptr;
    std::string readLine() override { return std::string(); }  // sim injects via enqueueTx
    void writeLine(const std::string& line) override { fn(ctx, line.c_str()); }
};

// The sim drives tickRadioRx / tickTxComplete directly at sim-events, so the
// IRQ-side reads are never invoked -> safe stubs. Only startTransmit is real
// (the Modem calls it from tickStartNextTx to hand a frame to the LoRa channel).
class CbRadio : public modem_core::IRadio {
public:
    void* ctx = nullptr;
    MC_StartTransmit txfn = nullptr;
    bool startReceive() override { return true; }
    int startTransmit(const std::uint8_t* data, std::size_t len) override {
        return txfn(ctx, data, static_cast<int>(len));
    }
    bool finishTransmit() override { return true; }
    std::vector<std::uint8_t> readReceivedFrame() override { return {}; }
    std::uint32_t getIrqFlags() override { return 0; }
    void clearIrqFlags() override {}
    bool takeIrqFlag() override { return false; }
};

class CbEspNow : public modem_core::IEspNow {
public:
    void* ctx = nullptr;
    MC_EspSend sendfn = nullptr;
    MC_EspAddPeer addfn = nullptr;
    MC_EspDeletePeer delfn = nullptr;
    MC_EspPollRx pollfn = nullptr;
    bool send(const std::uint8_t* mac, const std::uint8_t* data, std::size_t len) override {
        return sendfn(ctx, mac, data, static_cast<int>(len)) != 0;
    }
    bool addPeer(const std::uint8_t* mac) override { return addfn(ctx, mac) != 0; }
    void deletePeer(const std::uint8_t* mac) override { delfn(ctx, mac); }
    RxItem pollRx() override {
        RxItem item;
        std::uint8_t src[modem_core::MAC_LEN] = {};
        std::uint8_t buf[256];
        int n = pollfn(ctx, src, buf, static_cast<int>(sizeof(buf)));
        if (n < 0) return item;  // empty -> item.data stays empty
        std::memcpy(item.src, src, modem_core::MAC_LEN);
        item.data.assign(buf, buf + n);
        return item;
    }
};

struct CbHarness {
    modem_core::DutyBucket duty;
    modem_core::TxQueue queue;
    modem_core::RadioFsm fsm;
    modem_core::PeerTracker peer;
    CbClock clock;
    CbHostLink host;
    CbRadio radio;
    CbEspNow espnow;
    bool radioReady = false;
    bool espnowReady = false;
    modem_core::Modem* modem = nullptr;  // heap-constructed after the HAL is wired
};

}  // anonymous namespace

extern "C" {

// Creates a callback-HAL Modem. has_espnow=0 makes it a single-band modem
// (espnow ptr = nullptr). Returns an opaque handle; caller must mc_cbmodem_destroy.
void* mc_cbmodem_create(void* ctx,
                        MC_NowMs now_ms, MC_WriteLine write_line,
                        MC_StartTransmit start_transmit,
                        MC_EspSend esp_send, MC_EspAddPeer esp_add_peer,
                        MC_EspDeletePeer esp_delete_peer, MC_EspPollRx esp_poll_rx,
                        int has_espnow) {
    auto* h = new CbHarness();
    h->clock.ctx = ctx;        h->clock.fn = now_ms;
    h->host.ctx = ctx;         h->host.fn = write_line;
    h->radio.ctx = ctx;        h->radio.txfn = start_transmit;
    h->espnow.ctx = ctx;       h->espnow.sendfn = esp_send;
    h->espnow.addfn = esp_add_peer; h->espnow.delfn = esp_delete_peer;
    h->espnow.pollfn = esp_poll_rx;
    modem_core::IEspNow* espnow = has_espnow ? &h->espnow : nullptr;
    h->modem = new modem_core::Modem(h->duty, h->queue, h->fsm, h->peer,
                                     h->clock, h->host, h->radio, espnow,
                                     h->radioReady, h->espnowReady);
    return h;
}

void mc_cbmodem_destroy(void* handle) {
    auto* h = static_cast<CbHarness*>(handle);
    delete h->modem;
    delete h;
}

void mc_cbmodem_set_radio_ready(void* handle, int ready) {
    static_cast<CbHarness*>(handle)->radioReady = (ready != 0);
}
void mc_cbmodem_set_espnow_ready(void* handle, int ready) {
    static_cast<CbHarness*>(handle)->espnowReady = (ready != 0);
}

int mc_cbmodem_enqueue_tx(void* handle, const std::uint8_t* frame, int len, int wait_for_ack) {
    std::vector<std::uint8_t> v;
    if (frame != nullptr && len > 0) v.assign(frame, frame + len);
    return static_cast<CbHarness*>(handle)->modem->enqueueTx(v, wait_for_ack != 0) ? 1 : 0;
}

void mc_cbmodem_tick_start_next_tx(void* handle, int radio_irq_pending) {
    static_cast<CbHarness*>(handle)->modem->tickStartNextTx(radio_irq_pending != 0);
}
void mc_cbmodem_tick_ack_timeout(void* handle) {
    static_cast<CbHarness*>(handle)->modem->tickAckTimeout();
}
void mc_cbmodem_tick_duty_drain(void* handle) {
    static_cast<CbHarness*>(handle)->modem->tickDutyDrain();
}
void mc_cbmodem_tick_peer_liveness(void* handle) {
    static_cast<CbHarness*>(handle)->modem->tickPeerLiveness();
}
void mc_cbmodem_tick_espnow_rx(void* handle) {
    static_cast<CbHarness*>(handle)->modem->tickEspNowRx();
}
void mc_cbmodem_tick_radio_rx(void* handle, const std::uint8_t* frame, int len,
                              float rssi, float snr) {
    std::vector<std::uint8_t> v;
    if (frame != nullptr && len > 0) v.assign(frame, frame + len);
    static_cast<CbHarness*>(handle)->modem->tickRadioRx(v, rssi, snr);
}
void mc_cbmodem_tick_tx_complete(void* handle, int hw_status) {
    static_cast<CbHarness*>(handle)->modem->tickTxComplete(hw_status);
}

int mc_cbmodem_fsm_state(void* handle) {
    return static_cast<int>(static_cast<CbHarness*>(handle)->modem->radioFsm().state);
}
int mc_cbmodem_queue_size(void* handle) {
    return static_cast<int>(static_cast<CbHarness*>(handle)->modem->txQueue().size());
}
int mc_cbmodem_have_peer(void* handle) {
    return static_cast<CbHarness*>(handle)->modem->peerTracker().havePeer ? 1 : 0;
}

}  // extern "C"
