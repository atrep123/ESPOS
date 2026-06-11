#pragma once
// =============================================================================
//  modem_config.h  --  c6l-modem (ESP32-C6 + SX1262 LoRa modem) TUNING / CONFIG
// =============================================================================
//  Marlin-style "Configuration.h": the ONE place to tune the c6l-modem's HOST-SIDE
//  knobs (radio band, ESP-NOW channel, host UART) without digging through the FSM
//  logic in main.cpp. Change a value here, rebuild c6l-modem, reflash. The values
//  in this file are the constants that live ONLY in main.cpp -- so each is now
//  defined exactly ONCE, here.
//
//  WHAT IS *NOT* IN THIS FILE (on purpose)
//    The safety/timing constants that the host simulator cross-checks live in
//    modem_core.h INSIDE the DutyBucket / TxQueue / PeerTracker / Modem types and
//    are SINGLE-SOURCE with tools/sim_native/ (the off-device ACK/queue/duty tests
//    in check_modem_core.py assert their exact values). Re-defining them here would
//    (a) duplicate a value the sim build never sees -> silent drift, and (b) break
//    the "one definition" rule. They are DOCUMENTED in section [A2] below with a
//    static_assert tie-back where a main.cpp mirror used to exist -- read them here,
//    but EDIT them in modem_core.h so the host tests move with the firmware.
//
//    Protocol-critical bits (frame magic/version, HMAC framing, the host UART line
//    grammar OK/ERR/RX/HEALTH) deliberately stay in prop_protocol.h / modem_core.h /
//    main.cpp -- editing those breaks the radio link or the Dial<->modem wire format.
//
//  HOW TO USE THIS FILE
//    1. Find the section you care about in the SECTION INDEX below.
//    2. Change the value.
//    3. Rebuild c6l-modem and reflash. The SANITY CHECKS block (bottom of this file)
//       refuses to compile if a value is out of range, so a typo is caught at build
//       time, not on the bench.
//  Every default here reproduces the CURRENT shipping behaviour exactly -- starting
//  from a fresh flash, changing nothing, the modem behaves as before (verified live
//  on RF this session).
//
//  SECTION INDEX
//    [0]  QUICK RECIPES     -- copy/paste cookbook for the most common tweaks
//    [1]  RADIO (FIXED HW)  -- SX1262 wiring pins + LoRa PHY (band/SF/BW/CR/power)
//    [2]  ESP-NOW           -- 2.4 GHz mirror leg: channel, RX queue, broadcast MAC
//    [3]  HOST UART         -- the Serial1 link to the Dial (pins + baud)
//    [4]  OLED STATUS       -- on-board status screen refresh pacing
//    [A]  FEATURE FLAGS     -- compile-time -D build switches (OLED, dual-band)
//    [A2] CORE CONSTANTS    -- READ-ONLY map of the modem_core.h single-source knobs
//    [D]  SANITY CHECKS     -- compile-time validation (do not edit)
// =============================================================================

// =============================================================================
//  [0] QUICK RECIPES  --  the cookbook. Copy a line, apply the change, rebuild.
// =============================================================================
//  Each recipe names the REAL knob below (or the file it lives in) so you can jump
//  straight to it.
//
//   * Turn the on-board OLED status screen OFF (lean/headless build):
//       build with  -DC6L_MODEM_OLED_STATUS=0   (section [A]; it's a -D flag,
//       NOT a constant here -- main.cpp #ifndef-guards the default to 1)
//
//   * Move ESP-NOW to a quieter Wi-Fi channel (BOTH modems must match!):
//       set  ESPNOW_CHANNEL  to 6 or 11          (section [2])
//
//   * Change the LoRa band / region (BOTH ends + the DinMeter must match!):
//       set  LORA_FREQUENCY_MHZ                   (section [1])
//
//   * Trade LoRa range for airtime (shorter airtime = more duty headroom):
//       lower  LORA_SPREADING_FACTOR (e.g. 7->6) or raise LORA_BANDWIDTH_KHZ
//       (faster, less range) -- or the reverse for more range  (section [1])
//
//   * More TX power (check local EIRP limits + antenna!):
//       raise  LORA_TX_POWER_DBM  (SX1262 max ~22 dBm)         (section [1])
//
//   * Slower/quieter OLED redraw (less SPI/CPU spent on the screen):
//       raise  OLED_STATUS_INTERVAL_MS                          (section [4])
//
//   * Deeper ESP-NOW RX backlog (fewer "qdrop" under bursty 2.4 GHz traffic):
//       raise  ESPNOW_RX_QUEUE_DEPTH                            (section [2])
//
//   * Adjust the TX ACK-timeout / TX watchdog / duty-cycle budget:
//       these are NOT here -- edit modem_core.h (Modem::ACK_TIMEOUT_MS,
//       Modem::TX_BUSY_TIMEOUT_MS, DutyBucket::BUDGET_MS) so the host tests in
//       tools/sim_native/ move with the firmware. See section [A2] for the map.
// =============================================================================

#include <cstdint>
#include "modem_core.h"   // single-source core constants (DutyBucket / TxQueue /
                          // PeerTracker / Modem). Included so the [D] sanity checks
                          // can tie this file's documented mirrors back to the real
                          // values without ever re-defining them. (Arduino-free; the
                          // c6l-modem build already has firmware/c6l-modem/src + the
                          // shared/protocol -I path that this header transitively needs.)

namespace modem_config
{

// ===================== [1] RADIO -- HARDWARE-FIXED for UnitC6L ================
// !!! HARDWARE-FIXED. These describe how the SX1262 is WIRED on the M5Stack Unit
// !!! C6L (ESP32-C6 + SX1262) board and the LoRa PHY the link currently runs at.
// !!! Do NOT change a pin unless you physically swapped the radio module/board.
// !!! A prior automated audit's "wrong SPI pins" claim was a FALSE POSITIVE --
// !!! these are correct and were re-verified on live RF this session.
//
// ----- SX1262 control pins (the RadioLib Module(NSS, DIO1, RESET, BUSY) args) --
// new Module(NSS=23, DIO1=7, RST=RADIOLIB_NC, BUSY=19). RST is RADIOLIB_NC because
// the radio reset is driven through the board's I/O-expander (see setupC6lRadio():
// M5.getIOExpander(0).digitalWrite(7,...) toggles it), NOT a direct GPIO -- hence
// "not connected" to RadioLib. SPI SCK/MISO/MOSI come from the board's default VSPI
// bus (managed by M5Unified / the Arduino core), not passed here.
constexpr int RADIO_NSS_PIN  = 23;   // SPI chip-select  (Module arg 1)
constexpr int RADIO_DIO1_PIN = 7;    // IRQ / DIO1       (Module arg 2)
// RADIO_RST: RADIOLIB_NC (reset via I/O-expander, not a direct GPIO) -- kept as the
// RadioLib macro in the Module(...) call, intentionally not mirrored as an int here.
constexpr int RADIO_BUSY_PIN = 19;   // BUSY             (Module arg 4)

// ----- LoRa PHY parameters (radio.begin(...) args) ---------------------------
// All of these must MATCH on every node on the link (both modems + the DinMeter's
// radio). "L2" notes record the tuning step that shortened airtime for more EU-868
// duty-cycle headroom; do not change one end without the others.
constexpr float LORA_FREQUENCY_MHZ     = 868.1;   // EU 868 band centre
constexpr float LORA_BANDWIDTH_KHZ     = 250.0;   // L2: faster (was 125) -> shorter airtime
constexpr int   LORA_SPREADING_FACTOR  = 7;       // L2: faster (was 8) -> shorter airtime, -3dB range
constexpr int   LORA_CODING_RATE       = 5;       // 4/5
constexpr int   LORA_SYNC_WORD         = 0x34;    // private-network sync word
constexpr int   LORA_TX_POWER_DBM      = 13;      // PA output (SX1262 supports up to ~22)
constexpr int   LORA_PREAMBLE_LENGTH   = 8;       // L2: shorter preamble (was 12)
constexpr float LORA_TCXO_VOLTAGE      = 3.0;     // TCXO control voltage (board-specific)
constexpr bool  LORA_USE_REGULATOR_LDO = true;    // true = LDO (vs DC-DC); board-specific

// ============================ [2] ESP-NOW (2.4 GHz mirror) ====================
// The modem mirrors every queued frame over ESP-NOW as a low-latency 2.4 GHz leg
// alongside LoRa (DUAL_BAND build; see [A]). These are the host-side ESP-NOW knobs.
//
// Wi-Fi channel the ESP-NOW radio parks on. BOTH modems MUST be on the SAME channel
// or the 2.4 GHz leg never pairs. 1..13 (region-dependent). Default 1.
constexpr std::uint8_t  ESPNOW_CHANNEL        = 1;

// Depth of the FreeRTOS queue buffering inbound ESP-NOW frames between the RX
// callback (ISR-ish context) and the main loop's drain. Deeper = more tolerance to
// bursty 2.4 GHz traffic before frames are dropped (the "qdrop" HEALTH counter).
constexpr std::size_t   ESPNOW_RX_QUEUE_DEPTH = 32;

// ESP-NOW broadcast address (all-FF). Used as the destination until a unicast peer
// is adopted (PeerTracker, modem_core.h). Sized 6 = ESP_NOW_ETH_ALEN = modem_core::
// MAC_LEN; main.cpp keeps a static_assert(ESP_NOW_ETH_ALEN == modem_core::MAC_LEN).
// This is the 2.4 GHz L2 broadcast MAC -- NOT a protocol address; do not confuse it
// with the prop_protocol source/destination node ids.
constexpr std::uint8_t  ESPNOW_BROADCAST_MAC[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// ============================== [3] HOST UART (to the Dial) ===================
// The Serial1 link that carries the host<->modem command/report grammar
// (SEND/ACK/FF in; OK/ERR/RX/HEALTH/BOOT out). The line FORMAT is protocol -- it
// lives in main.cpp/modem_core.h and is NOT tunable here; only the transport pins
// and baud are. These are the ESP32-C6 GPIOs wired to the Dial's Grove port.
constexpr int           UART_RX_PIN = 5;        // C6L RX  <- Dial TX
constexpr int           UART_TX_PIN = 4;        // C6L TX  -> Dial RX
constexpr std::uint32_t UART_BAUD   = 115200;   // must match the Dial's host link

// ============================== [4] OLED STATUS SCREEN ========================
// Minimum gap between on-board status-screen redraws (only compiled in when
// C6L_MODEM_OLED_STATUS=1; see [A]). Higher = the screen updates less often,
// spending less SPI/CPU on rendering. Purely cosmetic -- no effect on the radio.
constexpr std::uint32_t OLED_STATUS_INTERVAL_MS = 350;

// ============================== [A] FEATURE FLAGS ============================
// Compile-time on/off switches. These are real -D build flags / #defines (guarded
// with #ifndef in main.cpp) -- NOT constants. They are documented here so you know
// they exist; to change one, pass it on the PlatformIO build_flags, do NOT add a
// #define in this file (that would fight main.cpp's #ifndef default).
//
//   C6L_MODEM_OLED_STATUS  (default 1, set in platformio.ini build_flags)
//       1 = render the on-board status screen (LoRa/ESP-NOW state, peer age, RX
//           RSSI/SNR, forwarded counts, queue-drop/duty/backoff flags).
//       0 = compile the screen out entirely (renderModemStatus() becomes a no-op)
//           for a lean / headless flash. The radio + host link are unaffected.
//
//   DUAL_BAND              (default 1, #ifndef-guarded in main.cpp)
//       1 = mirror every frame over ESP-NOW (2.4 GHz) alongside LoRa, with peer
//           adoption + the [2] ESP-NOW knobs active.
//       0 = LoRa-only build: the whole ESP-NOW path (and section [2]) is #if'd out.
//       Leave at 1 for the live two-band link; 0 is for LoRa-only bring-up/testing.

// ===================== [A2] CORE CONSTANTS (READ-ONLY MAP) ===================
// These knobs are NOT defined here -- they are SINGLE-SOURCE in modem_core.h so the
// host simulator (tools/sim_native/) compiles + tests the SAME values the firmware
// runs. This is a map so you know where to look; EDIT them in modem_core.h.
//
//   TX / ACK timing            -> modem_core.h, class Modem
//       Modem::ACK_TIMEOUT_MS      (900)  ACK wait before "ERR ACK_TIMEOUT" + re-arm
//       Modem::TX_BUSY_TIMEOUT_MS  (500)  TX-DONE watchdog (un-wedges a stuck TxBusy)
//       Modem::TX_STAGGER_MS       (6)    min gap ESP-NOW send -> LoRa start (STOP bypasses)
//       Modem::HEALTH_INTERVAL_MS  (2000) "OK HEALTH ..." host report cadence
//       Modem stop-retry backoff   (25..1000 ms, in Modem::stopRetryBackoffMs)
//
//   EU-868 duty-cycle bucket    -> modem_core.h, struct DutyBucket
//       LORA_AIRTIME_MS_EST        (20)     per-TX airtime charged (SF7/BW250 est.)
//       DutyBucket::BUDGET_MS      (3600)   budget over the window (~1%)
//       DutyBucket::CAP_MS         (36000)  hard cap on bucket fill
//       DutyBucket::WINDOW_MS      (360000) 6 min sliding window
//
//   TX queue + ESP-NOW peer     -> modem_core.h
//       TxQueue::DEPTH             (4)      bounded STOP-priority TX queue depth
//       PeerTracker::TIMEOUT_MS    (5000)   ESP-NOW peer liveness before it's forgotten
//
// The three values below USED to be duplicated as unused constants in main.cpp
// (ACK_TIMEOUT_MS / TX_STAGGER_MS / PEER_TIMEOUT_MS). They were dead (never read --
// the live ones are the modem_core.h members above) so they were deleted to satisfy
// "defined once". These named mirrors exist ONLY to give the [D] sanity checks a
// compile-time tie-back that fires if the modem_core.h value is ever changed without
// updating this documentation. They are NOT used by any compiled logic.
constexpr std::uint32_t DOC_ACK_TIMEOUT_MS = 900;    // mirrors modem_core::Modem::ACK_TIMEOUT_MS
constexpr std::uint32_t DOC_TX_STAGGER_MS  = 6;      // mirrors modem_core::Modem::TX_STAGGER_MS
constexpr std::uint32_t DOC_PEER_TIMEOUT_MS = 5000;  // mirrors modem_core::PeerTracker::TIMEOUT_MS

// ========================== [D] SANITY CHECKS ===============================
// Compile-time validation of the knobs above. If you set something out of range,
// the build FAILS HERE with the message below -- a typo is caught now, not on the
// bench. Do not edit this block; fix the offending value instead.

// ----- [1] RADIO ----------------------------------------------------------
static_assert(RADIO_NSS_PIN >= 0 && RADIO_DIO1_PIN >= 0 && RADIO_BUSY_PIN >= 0,
              "[1] SX1262 control pins must be valid GPIO numbers");
static_assert(LORA_FREQUENCY_MHZ > 0.0f,
              "[1] LORA_FREQUENCY_MHZ must be > 0");
static_assert(LORA_BANDWIDTH_KHZ > 0.0f,
              "[1] LORA_BANDWIDTH_KHZ must be > 0");
static_assert(LORA_SPREADING_FACTOR >= 5 && LORA_SPREADING_FACTOR <= 12,
              "[1] LORA_SPREADING_FACTOR must be in [5,12] (SX1262 LoRa SF range)");
static_assert(LORA_CODING_RATE >= 5 && LORA_CODING_RATE <= 8,
              "[1] LORA_CODING_RATE must be in [5,8] (4/5..4/8)");
static_assert(LORA_PREAMBLE_LENGTH > 0,
              "[1] LORA_PREAMBLE_LENGTH must be > 0");
static_assert(LORA_SYNC_WORD >= 0 && LORA_SYNC_WORD <= 0xFF,
              "[1] LORA_SYNC_WORD must fit in a byte");

// ----- [2] ESP-NOW --------------------------------------------------------
static_assert(ESPNOW_CHANNEL >= 1 && ESPNOW_CHANNEL <= 13,
              "[2] ESPNOW_CHANNEL must be in [1,13] (2.4 GHz Wi-Fi channels)");
static_assert(ESPNOW_RX_QUEUE_DEPTH >= 1,
              "[2] ESPNOW_RX_QUEUE_DEPTH must be at least 1");
static_assert(sizeof(ESPNOW_BROADCAST_MAC) == modem_core::MAC_LEN,
              "[2] ESPNOW_BROADCAST_MAC must be MAC_LEN (6) bytes");

// ----- [3] HOST UART ------------------------------------------------------
static_assert(UART_RX_PIN >= 0 && UART_TX_PIN >= 0,
              "[3] host UART pins must be valid GPIO numbers");
static_assert(UART_RX_PIN != UART_TX_PIN,
              "[3] UART_RX_PIN and UART_TX_PIN must differ");
static_assert(UART_BAUD > 0,
              "[3] UART_BAUD must be > 0");

// ----- [4] OLED -----------------------------------------------------------
static_assert(OLED_STATUS_INTERVAL_MS > 0,
              "[4] OLED_STATUS_INTERVAL_MS must be > 0");

// ----- [A2] CORE-CONSTANT TIE-BACKS --------------------------------------
// These fire if a modem_core.h value drifts from what this file documents -- a
// nudge to update the [A2] map (and the host sim) together. They do NOT change
// behaviour; they only keep the documentation honest.
static_assert(DOC_ACK_TIMEOUT_MS == modem_core::Modem::ACK_TIMEOUT_MS,
              "[A2] Modem::ACK_TIMEOUT_MS changed -- update the [A2] map + DOC_ACK_TIMEOUT_MS");
static_assert(DOC_TX_STAGGER_MS == modem_core::Modem::TX_STAGGER_MS,
              "[A2] Modem::TX_STAGGER_MS changed -- update the [A2] map + DOC_TX_STAGGER_MS");
static_assert(DOC_PEER_TIMEOUT_MS == modem_core::PeerTracker::TIMEOUT_MS,
              "[A2] PeerTracker::TIMEOUT_MS changed -- update the [A2] map + DOC_PEER_TIMEOUT_MS");
// Duty-cycle window sanity (mirrors the host sim's BUDGET/WINDOW drain-rate math).
static_assert(modem_core::DutyBucket::BUDGET_MS > 0 &&
              modem_core::DutyBucket::WINDOW_MS > 0 &&
              modem_core::DutyBucket::CAP_MS >= modem_core::DutyBucket::BUDGET_MS,
              "[A2] DutyBucket budget/window must be > 0 and CAP >= BUDGET");

}  // namespace modem_config
