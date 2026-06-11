#include <Arduino.h>
#include <M5Unified.h>
#include <RadioLib.h>
#include <cstdio>
#include <vector>

#include "prop_protocol.h"
#include "modem_core.h"   // pure decision logic (single source w/ host simulator); see tools/sim_native/
#include "modem_config.h" // USER-TUNABLE knobs (radio band/pins, ESP-NOW, host UART, OLED). The
                          // single-source core timings stay in modem_core.h; see modem_config [A2].

using modem_core::MAX_RADIO_FRAME;
using modem_core::FRAME_TYPE_OFFSET;
using modem_core::FRAME_KEY_OFFSET;
using modem_core::FRAME_SOURCE_OFFSET;
using modem_core::FRAME_DESTINATION_OFFSET;
using modem_core::FRAME_SEQUENCE_OFFSET;
using modem_core::FRAME_NONCE_OFFSET;
using modem_core::readFrameU32;
using modem_core::hasProtocolHeader;
using modem_core::looksLikeMatchingAck;
using modem_core::DutyBucket;
using modem_core::TxQueue;
using modem_core::RadioFsm;
// LORA_AIRTIME_MS_EST / TxRequest / frameIsStop now used only inside modem_core::Modem
// (the TX engine migrated there); main.cpp no longer references them directly.
using modem_core::PeerTracker;
using modem_core::macEquals;
using modem_core::isBroadcastMac;

// User-tunable knobs now live in modem_config.h (defined once there). Pull them into
// this translation unit by name so the call sites below stay unchanged. The radio
// pins/PHY are HARDWARE-FIXED in that header (see modem_config [1]); listed here only
// to reference them, not to imply they're safe to retune.
using modem_config::LORA_FREQUENCY_MHZ;
using modem_config::LORA_BANDWIDTH_KHZ;
using modem_config::LORA_SPREADING_FACTOR;
using modem_config::LORA_CODING_RATE;
using modem_config::LORA_SYNC_WORD;
using modem_config::LORA_TX_POWER_DBM;
using modem_config::LORA_PREAMBLE_LENGTH;
using modem_config::LORA_TCXO_VOLTAGE;
using modem_config::LORA_USE_REGULATOR_LDO;
using modem_config::RADIO_NSS_PIN;
using modem_config::RADIO_DIO1_PIN;
using modem_config::RADIO_BUSY_PIN;
using modem_config::UART_RX_PIN;
using modem_config::UART_TX_PIN;
using modem_config::ESPNOW_CHANNEL;
using modem_config::ESPNOW_RX_QUEUE_DEPTH;
using modem_config::ESPNOW_BROADCAST_MAC;

#include "driver/gpio.h"

#ifndef DUAL_BAND
#define DUAL_BAND 1
#endif

#ifndef C6L_MODEM_OLED_STATUS
#define C6L_MODEM_OLED_STATUS 1
#endif

#if DUAL_BAND
#include <cstring>
#include <esp_now.h>
#include <esp_wifi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <WiFi.h>
#endif

// Radio PHY/pins + host UART pins/baud + ESP-NOW channel/queue/broadcast-MAC now live
// in modem_config.h (defined once; pulled in via the `using` block above). The radio
// values are HARDWARE-FIXED there. ACK_TIMEOUT_MS / TX_STAGGER_MS / PEER_TIMEOUT_MS used
// to be duplicated here but were DEAD (unused) -- the live ones are modem_core::Modem::
// ACK_TIMEOUT_MS / Modem::TX_STAGGER_MS / PeerTracker::TIMEOUT_MS -- so they were removed.
// MAX_RADIO_FRAME + FRAME_*_OFFSET + TX_QUEUE_DEPTH remain modem_core.h (single source).

#if DUAL_BAND
// LORA_AIRTIME_MS_EST + DUTY_* constants now in modem_core::DutyBucket (single source).
struct EspNowRx {
    uint8_t len;
    uint8_t src[ESP_NOW_ETH_ALEN];
    uint8_t data[MAX_RADIO_FRAME];
};

static_assert(ESP_NOW_ETH_ALEN == modem_core::MAC_LEN,
              "modem_core::MAC_LEN must match ESP_NOW_ETH_ALEN");

static QueueHandle_t espnowRxQueue = nullptr;
static volatile uint32_t espnowQueueDropped = 0;
// espnowReady moved out of #if DUAL_BAND (below, next to radioReady) so the Modem
// can bind it by reference in both build configs. lastEspNowSendMs is now a Modem
// member (modem_core::Modem owns the LoRa stagger-gate input).
#endif

// HARDWARE-FIXED SX1262 wiring (UnitC6L): NSS, DIO1, RST=RADIOLIB_NC (reset via the
// board I/O-expander, see setupC6lRadio), BUSY. Pin values in modem_config.h [1].
SX1262 radio = new Module(RADIO_NSS_PIN, RADIO_DIO1_PIN, RADIOLIB_NC, RADIO_BUSY_PIN);

// RadioFsm + TxRequest + TxQueue + DutyBucket + PeerTracker now modem_core::*
// (single source, host-testable). DutyBucket + PeerTracker live outside #if DUAL_BAND
// so the Modem orchestration class can take refs to them in both build configs --
// only the DUAL_BAND code paths in the loop actually charge / update them.

volatile bool radioIrqFlag = false;
bool radioReady = false;
bool espnowReady = false;  // ESP-NOW init flag (set by setupEspNow in DUAL_BAND; bound into Modem)
RadioFsm radioFsm;        // SAFETY: state + pendingAckRef + ackDeadline + txWasSendWithAck
// rxOtherCount + foreignDropped now Modem members (modem.rxOtherCount / modem.foreignDropped).
TxQueue txQueue;          // SAFETY: STOP-priority bounded queue (modem_core::TxQueue)
DutyBucket dutyBucket;    // EU 868 LoRa duty cycle accounting (charged only in DUAL_BAND)
PeerTracker peerTracker;  // ESP-NOW unicast peer + 5s liveness (updated only in DUAL_BAND)

// Forward declaration: the Modem orchestration object is DEFINED later (after the HAL
// adapter instances it binds), but several free functions above that point delegate
// to it (serviceEspNowPeerLiveness, serviceRadioIrq, ...). The extern decl lets them
// name it; the linker resolves to the single definition below.
extern modem_core::Modem modem;

void setRadioIrqFlag() {
    radioIrqFlag = true;
}

bool enterReceive() {
    int state = radio.startReceive();
    if (state != RADIOLIB_ERR_NONE) {
        Serial.printf("startReceive failed, code %d\n", state);
        radioReady = false;
        return false;
    }
    // SAFETY (out16/out25): RX re-arm is the recovery path. A prior transient
    // startReceive() failure leaves radioReady=false and nothing else ever
    // restores it -- so every host frame (incl STOP/ARM/FIRE) is then rejected
    // with ERR RADIO_NOT_READY forever. enterReceive() is the single canonical
    // re-arm helper (boot, post-TX, post-RX, ACK-timeout, TX-fail all route here
    // via Sx1262RadioHal::startReceive), so restoring the flag on a SUCCESSFUL
    // re-arm makes the radio self-heal on the next good RX cycle.
    radioReady = true;
    return true;
}

bool setupC6lRadio() {
    auto& ioe = M5.getIOExpander(0);
    ioe.digitalWrite(7, false);
    delay(100);
    ioe.digitalWrite(7, true);
    ioe.digitalWrite(6, true);
    ioe.digitalWrite(5, true);

    Serial.print("[SX1262] Initializing modem... ");
    int state = radio.begin(
        LORA_FREQUENCY_MHZ,
        LORA_BANDWIDTH_KHZ,
        LORA_SPREADING_FACTOR,
        LORA_CODING_RATE,
        LORA_SYNC_WORD,
        LORA_TX_POWER_DBM,
        LORA_PREAMBLE_LENGTH,
        LORA_TCXO_VOLTAGE,
        LORA_USE_REGULATOR_LDO);
    if (state != RADIOLIB_ERR_NONE) {
        Serial.printf("failed, code %d\n", state);
        return false;
    }
    radio.setDio1Action(setRadioIrqFlag);
    if (!enterReceive()) {
        return false;
    }
    Serial.printf("ok %.1f MHz BW %.1f SF%d CR4/%d SW 0x%02X TX %d dBm\n",
                  LORA_FREQUENCY_MHZ, LORA_BANDWIDTH_KHZ, LORA_SPREADING_FACTOR,
                  LORA_CODING_RATE, LORA_SYNC_WORD, LORA_TX_POWER_DBM);
    return true;
}

String readHostLine() {
    static String line;
    static bool overflow = false;
    while (Serial1.available() > 0) {
        char c = static_cast<char>(Serial1.read());
        if (c == '\n') {
            if (overflow) {
                overflow = false;
                line = "";
                return "__LINE_TOO_LONG__";
            }
            String ready = line;
            line = "";
            ready.trim();
            return ready;
        }
        if (c == '\r') {
            continue;
        }
        if (line.length() < 256) {
            if (!overflow) {
                line += c;
            }
        } else {
            overflow = true;
        }
    }
    return "";
}

void reportHost(const String& line) {
    Serial1.println(line);
    Serial.println(line);
}

#if C6L_MODEM_OLED_STATUS
// OLED_STATUS_INTERVAL_MS now in modem_config.h [4] (defined once); referenced below.
using modem_config::OLED_STATUS_INTERVAL_MS;

std::uint32_t currentEspNowQueueDropped() {
#if DUAL_BAND
    return espnowQueueDropped;
#else
    return 0;
#endif
}

std::uint32_t currentEspNowRxFree() {
#if DUAL_BAND
    return espnowRxQueue ? static_cast<std::uint32_t>(uxQueueSpacesAvailable(espnowRxQueue)) : 0;
#else
    return 0;
#endif
}

bool modemDisplayAvailable() {
    return M5.Display.width() > 0 && M5.Display.height() > 0;
}

void formatCount3(std::uint32_t value, char* out, std::size_t cap) {
    if (cap == 0) return;
    if (value < 1000) {
        std::snprintf(out, cap, "%lu", static_cast<unsigned long>(value));
    } else if (value < 100000) {
        std::snprintf(out, cap, "%luk", static_cast<unsigned long>(value / 1000));
    } else if (value < 1000000) {
        std::snprintf(out, cap, "99k");
    } else if (value < 10000000) {
        std::snprintf(out, cap, "%luM", static_cast<unsigned long>(value / 1000000));
    } else {
        std::snprintf(out, cap, "9M");
    }
}

void formatCount2(std::uint32_t value, char* out, std::size_t cap) {
    if (cap == 0) return;
    if (value < 100) {
        std::snprintf(out, cap, "%lu", static_cast<unsigned long>(value));
    } else if (value < 10000) {
        std::uint32_t thousands = value / 1000;
        if (thousands == 0) thousands = 1;
        std::snprintf(out, cap, "%luk", static_cast<unsigned long>(thousands));
    } else if (value < 10000000) {
        std::uint32_t millions = value / 1000000;
        if (millions == 0) millions = 1;
        std::snprintf(out, cap, "%luM", static_cast<unsigned long>(millions));
    } else {
        std::snprintf(out, cap, "9M");
    }
}

int roundedSignal(float value) {
    return static_cast<int>(value + (value >= 0.0f ? 0.5f : -0.5f));
}

void drawStatusLine(int row, const char* text) {
    M5.Display.setCursor(0, row * 8);
    M5.Display.print(text);
}

void renderModemStatus() {
    static std::uint32_t lastDrawMs = 0;
    const std::uint32_t now = millis();
    if (lastDrawMs != 0 && now - lastDrawMs < OLED_STATUS_INTERVAL_MS) return;
    if (!modemDisplayAvailable()) return;

    modem_core::ModemHealthSnapshot snap;
    if (!modem.consumeHealthSnapshot(now, currentEspNowQueueDropped(),
                                     currentEspNowRxFree(), snap)) {
        return;
    }

    lastDrawMs = now;
    M5.Display.setFont(&fonts::Font0);
    M5.Display.setTextSize(1);
    M5.Display.setTextColor(TFT_WHITE, TFT_BLACK);
    M5.Display.fillScreen(TFT_BLACK);

    char line[18];
    drawStatusLine(0, "C6L");

    const char* lora = !snap.radioReady ? "NO" : (snap.radioFault ? "FLT" : "OK");
    const char* esp = snap.espnowReady ? "OK" : "--";
    std::snprintf(line, sizeof(line), "L:%s E:%s", lora, esp);
    drawStatusLine(1, line);

    if (snap.havePeer) {
        std::uint32_t age = snap.peerAgeSeconds > 999 ? 999 : snap.peerAgeSeconds;
        std::snprintf(line, sizeof(line), "P 1/1 %lus", static_cast<unsigned long>(age));
    } else {
        std::snprintf(line, sizeof(line), "P 0/1 --");
    }
    drawStatusLine(2, line);

    if (snap.hasLoraQuality) {
        std::snprintf(line, sizeof(line), "RX %d S%d",
                      roundedSignal(snap.loraRssi), roundedSignal(snap.loraSnr));
    } else {
        std::snprintf(line, sizeof(line), "RX -- S--");
    }
    drawStatusLine(3, line);

    char fwd[4];
    char enq[4];
    formatCount3(snap.forwarded, fwd, sizeof(fwd));
    formatCount3(snap.espnowEnqueued, enq, sizeof(enq));
    // ESP-NOW has no delivery ACK here; the second count is accepted-for-send.
    std::snprintf(line, sizeof(line), "F %s/%s", fwd, enq);
    drawStatusLine(4, line);

    char qdrop[3];
    char duty[3];
    formatCount2(snap.espnowQueueDropped, qdrop, sizeof(qdrop));
    formatCount2(snap.dutyDropped, duty, sizeof(duty));
    std::snprintf(line, sizeof(line), "Q%s D%s B%c", qdrop, duty,
                  (snap.stopBackoffActive || snap.radioFault) ? '1' : '0');
    drawStatusLine(5, line);
}
#else
void renderModemStatus() {}
#endif

#if DUAL_BAND
bool reportEspNowInitFailure() {
    reportHost("ERR ESPNOW");
    return false;
}

// macEquals + isBroadcastMac now modem_core::* (single source w/ host simulator).

void restoreEspNowChannel() {
    (void)esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);
}

void reportBootChannelScan() {
    int channelCounts[14] = {};
    int networkCount = WiFi.scanNetworks(false, true, true);
    if (networkCount >= 0) {
        for (int i = 0; i < networkCount; ++i) {
            int channel = WiFi.channel(i);
            if (channel >= 1 && channel <= 13) {
                ++channelCounts[channel];
            }
        }
        reportHost(String("OK SCAN ch1=") + channelCounts[1] +
                   " ch6=" + channelCounts[6] +
                   " ch11=" + channelCounts[11] +
                   " cur=" + ESPNOW_CHANNEL);
        WiFi.scanDelete();
    } else {
        reportHost(String("OK SCAN skipped cur=") + ESPNOW_CHANNEL);
    }
    restoreEspNowChannel();
}

// rememberEspNowPeer migrated to Modem::rememberPeer (private helper called from
// Modem.tickEspNowRx). The hardware add/delete now flow through the IEspNow HAL
// (EspNowHal::addPeer / deletePeer), so the ESP-IDF specifics (peer_info channel /
// ifidx / encrypt) live in the adapter, not the orchestration.

void serviceEspNowPeerLiveness() {
    // HAL slice: delegated to Modem.tickPeerLiveness() (peer expiry + HW del_peer +
    // forget). Behaviorally identical to the previous free-function version.
    (void)modem.tickPeerLiveness();
}

// drainDutyBucket() now DutyBucket::drain() (modem_core.h, single source).

void onEspNowRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
    if (espnowRxQueue == nullptr || info == nullptr || info->src_addr == nullptr ||
        data == nullptr || len <= 0 ||
        len > static_cast<int>(MAX_RADIO_FRAME)) {
        return;
    }

    EspNowRx item{};
    item.len = static_cast<uint8_t>(len);
    memcpy(item.src, info->src_addr, ESP_NOW_ETH_ALEN);
    memcpy(item.data, data, len);
    if (xQueueSend(espnowRxQueue, &item, 0) != pdTRUE) {
        ++espnowQueueDropped;
    }
}

bool setupEspNow() {
    espnowReady = false;
    espnowRxQueue = xQueueCreate(ESPNOW_RX_QUEUE_DEPTH, sizeof(EspNowRx));
    if (espnowRxQueue == nullptr) {
        return reportEspNowInitFailure();
    }

    if (!WiFi.mode(WIFI_STA)) {
        return reportEspNowInitFailure();
    }
    WiFi.disconnect();

    if (esp_wifi_set_ps(WIFI_PS_NONE) != ESP_OK) {
        return reportEspNowInitFailure();
    }
    // NOTE: boot AP scan removed -- WiFi.scanNetworks() here left the radio/stack in a
    // state that broke ESP-NOW (verified on HW: espnow delivery dropped to 0, no pairing).
    // Channel-congestion diagnostics will be re-added later with proper WiFi save/restore.
    if (esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE) != ESP_OK) {
        return reportEspNowInitFailure();
    }
    if (esp_now_init() != ESP_OK) {
        return reportEspNowInitFailure();
    }

    esp_now_peer_info_t peer{};
    memcpy(peer.peer_addr, ESPNOW_BROADCAST_MAC, ESP_NOW_ETH_ALEN);
    peer.channel = ESPNOW_CHANNEL;
    peer.ifidx = WIFI_IF_STA;
    peer.encrypt = false;
    esp_err_t peerState = esp_now_add_peer(&peer);
    if (peerState != ESP_OK && peerState != ESP_ERR_ESPNOW_EXIST) {
        return reportEspNowInitFailure();
    }

    // Register the recv callback LAST (after the peer + queue are ready) so no
    // broadcast can be queued and emitted as an "RX" line before "OK ESPNOW".
    if (esp_now_register_recv_cb(onEspNowRecv) != ESP_OK) {
        return reportEspNowInitFailure();
    }

    espnowReady = true;
    reportHost("OK ESPNOW");
    return true;
}
#endif

// parseHexArg migrated to Modem.parseHostFrame's inline hex-body lambda (batch 8);
// the host UART command parsing is single-source w/ the simulator now.

// readFrameU32, hasProtocolHeader, looksLikeMatchingAck now in modem_core.h
// (single source w/ host sim; brought in via the `using` declarations at the top).

bool readRadioFrame(std::vector<uint8_t>& frame, float& rssi, float& snr) {
    size_t length = radio.getPacketLength();
    if (length == 0 || length > MAX_RADIO_FRAME) {
        return false;
    }
    frame.assign(length, 0);
    int state = radio.readData(frame.data(), frame.size());
    if (state != RADIOLIB_ERR_NONE) {
        Serial.printf("LoRa read failed %d\n", state);
        return false;
    }
    rssi = radio.getRSSI();
    snr = radio.getSNR();
    return true;
}

// ---------------------------------------------------------------------------
// HAL adapters: thin wrappers exposing the existing hardware globals (radio,
// Serial, esp_now*, espnowRxQueue, millis, radioIrqFlag) as modem_core::I*
// interfaces. This is the bridge that lets the Modem orchestration class run
// on the real ESP32-C6 hardware (these adapters) AND in host tests (mocks in
// tools/sim_native/modem_abi.cpp). One foundation slice -- only tickAckTimeout()
// flows through Modem so far; the other free functions still touch globals
// directly until they migrate in follow-up slices.
// ---------------------------------------------------------------------------

class ArduinoClockHal : public modem_core::IClock {
public:
    std::uint32_t nowMs() override { return millis(); }
};

class SerialHostLinkHal : public modem_core::IHostLink {
public:
    // Buffer-line intake is still the legacy readHostLine() helper for this slice;
    // a future slice will migrate the line buffering into this adapter so the Modem
    // can call readLine() directly from its tick loop.
    std::string readLine() override { return std::string(); }
    // MUST mirror reportHost(): write to BOTH the host UART link (Serial1, read by
    // the Dial) AND the USB debug console (Serial). Writing only Serial would make
    // every migrated host line (ERR/OK/RX/HEALTH) invisible to the Dial -- a
    // protocol-breaking regression (caught by the Codex council review, 2026-05-29).
    void writeLine(const std::string& line) override {
        Serial1.println(line.c_str());
        Serial.println(line.c_str());
    }
};

class Sx1262RadioHal : public modem_core::IRadio {
public:
    bool startReceive() override { return enterReceive(); }
    int startTransmit(const std::uint8_t* data, std::size_t len) override {
        // RadioLib's signature takes uint8_t* (non-const); we cast (the data isn't
        // modified, just transmitted -- the const_cast keeps our interface honest).
        // Returns the RadioLib status code directly (0 = RADIOLIB_ERR_NONE).
        return radio.startTransmit(const_cast<std::uint8_t*>(data), len);
    }
    bool finishTransmit() override { return radio.finishTransmit() == RADIOLIB_ERR_NONE; }
    std::vector<std::uint8_t> readReceivedFrame() override {
        std::vector<std::uint8_t> frame;
        float rssi = 0.0f, snr = 0.0f;
        if (!readRadioFrame(frame, rssi, snr)) frame.clear();
        return frame;
    }
    std::uint32_t getIrqFlags() override { return radio.getIrqFlags(); }
    void clearIrqFlags() override { radio.clearIrqFlags(RADIOLIB_SX126X_IRQ_ALL); }
    bool takeIrqFlag() override {
        bool t = radioIrqFlag;
        radioIrqFlag = false;
        return t;
    }
};

#if DUAL_BAND
class EspNowHal : public modem_core::IEspNow {
public:
    bool send(const std::uint8_t* mac, const std::uint8_t* data, std::size_t len) override {
        return esp_now_send(mac, data, len) == ESP_OK;
    }
    bool addPeer(const std::uint8_t* mac) override {
        esp_now_peer_info_t peer{};
        memcpy(peer.peer_addr, mac, ESP_NOW_ETH_ALEN);
        peer.channel = ESPNOW_CHANNEL;
        peer.ifidx = WIFI_IF_STA;
        peer.encrypt = false;
        esp_err_t r = esp_now_add_peer(&peer);
        return r == ESP_OK || r == ESP_ERR_ESPNOW_EXIST;
    }
    void deletePeer(const std::uint8_t* mac) override {
        (void)esp_now_del_peer(const_cast<std::uint8_t*>(mac));
    }
    RxItem pollRx() override {
        RxItem item;
        if (espnowRxQueue == nullptr) return item;
        EspNowRx raw{};
        if (xQueueReceive(espnowRxQueue, &raw, 0) != pdTRUE) return item;
        memcpy(item.src, raw.src, modem_core::MAC_LEN);
        item.data.assign(raw.data, raw.data + raw.len);
        return item;
    }
};
#endif

// HAL adapter instances (one of each; lifetime = program). Used to construct the
// single Modem orchestration object below. Note: order of construction is fine
// because Modem only DEREFERENCES these in its methods -- not during the ctor.
static ArduinoClockHal g_clockHal;
static SerialHostLinkHal g_hostHal;
static Sx1262RadioHal g_radioHal;
#if DUAL_BAND
static EspNowHal g_espnowHal;
modem_core::Modem modem(dutyBucket, txQueue, radioFsm, peerTracker,
                        g_clockHal, g_hostHal, g_radioHal, &g_espnowHal,
                        radioReady, espnowReady);
#else
modem_core::Modem modem(dutyBucket, txQueue, radioFsm, peerTracker,
                        g_clockHal, g_hostHal, g_radioHal, nullptr,
                        radioReady, espnowReady);
#endif

// HAL slice: full TX path migrated to modem_core::Modem.
//   queueRadioFrame  -> Modem.enqueueTx (radioReady/bounds/enqueue + ESP-NOW mirror)
//   startNextQueuedTx -> Modem.tickStartNextTx (pop + duty gate + HW startTransmit +
//                        STOP retry + FSM beginTx), via the radio_ / espnow_ / duty_
//                        HAL refs. radioReady + espnowReady are bound into the Modem
//                        by reference; lastEspNowSendMs + the STOP retry budget are
//                        now Modem members. main.cpp keeps only these thin wrappers.
bool queueRadioFrame(const std::vector<uint8_t>& frame, bool waitForAck) {
    return modem.enqueueTx(frame, waitForAck);
}

void sendRadioFrame(const std::vector<uint8_t>& frame) {
    queueRadioFrame(frame, false);
}

void sendAndWaitForAck(const std::vector<uint8_t>& frame) {
    queueRadioFrame(frame, true);
}

void startNextQueuedTx() {
    modem.tickStartNextTx(radioIrqFlag);
    renderModemStatus();
}

void finishTxFromIrq() {
    // HAL slice: HW finishTransmit + startReceive stay main.cpp-side (RadioLib
    // codes + radioReady flag ownership). FSM completeTx + "ERR TX" / "OK TX"
    // host emission flow through Modem.tickTxComplete.
    int txState = radio.finishTransmit();
    int rxState = radio.startReceive();
    if (rxState != RADIOLIB_ERR_NONE) {
        Serial.printf("startReceive failed, code %d\n", rxState);
        radioReady = false;
    } else {
        // SAFETY (out16/out25): mirror enterReceive() -- a successful post-TX RX
        // re-arm restores radioReady so a prior transient fault can't keep the
        // radio latched "not ready" once it is demonstrably receiving again.
        radioReady = true;
    }
    modem.tickTxComplete(txState);
}

void handleRxFromIrq() {
    // HAL slice: HW read here, decision logic + log + re-arm in Modem.tickRadioRx.
    std::vector<uint8_t> frame;
    float rssi = 0.0f, snr = 0.0f;
    if (!readRadioFrame(frame, rssi, snr)) {
        frame.clear();  // signal "no frame" -- tickRadioRx still does the re-arm
    }
    modem.tickRadioRx(frame, rssi, snr);
}

void serviceRadioIrq() {
    // HAL slice: dispatch decision flows through Modem.classifyRadioIrq. main.cpp
    // still owns the radioReady + radioIrqFlag globals + the HW reads (RadioLib
    // getIrqFlags / clearIrqFlags / startReceive), and dispatches by action.
    if (!radioReady || !radioIrqFlag) return;
    radioIrqFlag = false;
    uint32_t irq = radio.getIrqFlags();
    using Action = modem_core::Modem::IrqAction;
    switch (modem.classifyRadioIrq(irq, RADIOLIB_SX126X_IRQ_TX_DONE,
                                   RADIOLIB_SX126X_IRQ_RX_DONE)) {
        case Action::FinishTx:        finishTxFromIrq(); return;
        case Action::HandleRx:        handleRxFromIrq(); return;
        case Action::ClearAndReceive: radio.clearIrqFlags(RADIOLIB_SX126X_IRQ_ALL);
                                      enterReceive();    return;
        case Action::None:            return;
    }
}

#if DUAL_BAND
void serviceEspNowRx() {
    // HAL slice: full body migrated to Modem.tickEspNowRx() which drains the queue
    // via espnow_.pollRx(), runs hasProtocolHeader + (inlined) rememberPeer +
    // host_.writeLine "RX 0.0 0.0 <hex>" + fsm_.tryConsumeAck. Behaviorally identical
    // to the previous code; foreignDropped now lives on Modem and is bumped there.
    modem.tickEspNowRx();
}

// reportHealth migrated to Modem.tickHealthReport (called below from loop()).
// The remaining args (espnowQueueDropped, rxFree) are passed in -- they live in
// FreeRTOS-side state that's main.cpp's responsibility for now.
#endif

void serviceAckTimeout() {
    // Foundation slice of HAL refactor: the FSM tick now flows through the Modem
    // orchestration class, which calls clock_/host_/radio_ via the HAL interfaces.
    // Behaviourally identical to the previous free-function version (the Modem
    // method also emits "ERR ACK_TIMEOUT" + re-arms RX); host-testable via mocks.
    (void)modem.tickAckTimeout();
}

void handleHostLine(const String& line) {
    // HAL slice: parsing flows through Modem.parseHostFrame (single source w/
    // host sim). main.cpp keeps the dispatch + Serial USB debug diagnostics.
    std::vector<uint8_t> frame;
    auto cmd = modem.parseHostFrame(std::string(line.c_str()), frame);
    switch (cmd) {
        case modem_core::Modem::HostCommand::LineTooLong:
            reportHost("ERR LINE_TOO_LONG");
            return;
        case modem_core::Modem::HostCommand::Ping:
            reportHost("OK C6L_MODEM");
            return;
        case modem_core::Modem::HostCommand::SendAck:
            sendAndWaitForAck(frame);
            return;
        case modem_core::Modem::HostCommand::SendNoAck:
            sendRadioFrame(frame);
            return;
        case modem_core::Modem::HostCommand::BadFrame:
            Serial.print("DBG BADFRAME len="); Serial.print(line.length());
            Serial.print(" ["); Serial.print(line); Serial.println("]");
            reportHost("ERR BAD_FRAME");
            return;
        case modem_core::Modem::HostCommand::BadCommand:
            Serial.print("DBG BADCMD len="); Serial.print(line.length());
            Serial.print(" ["); Serial.print(line); Serial.println("]");
            reportHost("ERR BAD_COMMAND");
            return;
    }
}

void setup() {
    auto cfg = M5.config();
    M5.begin(cfg);
    Serial.begin(115200);
    Serial1.begin(modem_config::UART_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN); // SEND / ACK / RX host link.

    // 0.4 root-fix: idle-high the host UART via internal pull-ups so a booting or
    // disconnected peer never presents a floating line that reads as boot garbage
    // (covers any power-on order; complements the boot-drain at the end of setup()).
    gpio_pullup_en((gpio_num_t)UART_RX_PIN);
    gpio_pullup_en((gpio_num_t)UART_TX_PIN);

    delay(500);
    Serial.println("C6L UART LoRa modem");
    Serial1.println("BOOT C6L_MODEM 115200");
    radioReady = setupC6lRadio();
    reportHost(radioReady ? "OK RADIO_READY" : "ERR RADIO_INIT");
#if DUAL_BAND
    if (radioReady) {
        setupEspNow();
    }
#endif

    // A2b: discard any boot-time garbage that accumulated on the host UART RX FIFO
    // (pre-init pin noise from the Dial). Otherwise it prepends to the first real
    // command and is parsed as one ERR BAD_COMMAND. (The Dial also flushes its side
    // via a leading newline; this is the proper modem-side defense, e.g. after a
    // modem-only brownout reset where the Dial does not re-flush.)
    while (Serial1.available()) {
        (void)Serial1.read();
    }
}

void loop() {
#if DUAL_BAND
    modem.tickDutyDrain();         // HAL: was dutyBucket.drain(millis())
    serviceEspNowPeerLiveness();   // HAL-delegated free function (modem.tickPeerLiveness)
#endif

    String hostLine = readHostLine();
    if (hostLine.length() > 0) {
        handleHostLine(hostLine);
    }

    serviceRadioIrq();
#if DUAL_BAND
    serviceEspNowRx();
    // HAL: 2s throttle + reportHealth body now in Modem.tickHealthReport. ESP-NOW
    // queue counters (espnowQueueDropped, rxFree from uxQueueSpacesAvailable) ride
    // as args -- they live in FreeRTOS-side state that's still main.cpp's domain.
    std::uint32_t rxFree = espnowRxQueue ? uxQueueSpacesAvailable(espnowRxQueue) : 0;
    modem.tickHealthReport(millis(), espnowQueueDropped, rxFree);
#endif
    serviceAckTimeout();
    (void)modem.tickTxWatchdog();  // out18: recover a TxBusy wedge (spurious/missing TX_DONE)
    startNextQueuedTx();

    delayMicroseconds(200);
}
