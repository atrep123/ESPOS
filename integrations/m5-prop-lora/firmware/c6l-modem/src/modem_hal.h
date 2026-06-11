// Hardware Abstraction Layer for the c6l-modem.
//
// Pure abstract interfaces so the orchestration logic in modem_core::Modem can run
// on the real ESP32-C6 (where the adapters in main.cpp wrap RadioLib + esp-now +
// HardwareSerial + millis()) AND on the host simulator/tests (where the adapters
// are deterministic mocks). Single-source: this header compiles for both targets;
// no Arduino/RadioLib/esp_now deps -- only std::vector + cstdint + std::string.
//
// Conventions:
//   * Methods return bool for "operation accepted/completed OK" where applicable.
//   * Time is std::uint32_t milliseconds, monotonic since boot (wraps ~49 days).
//   * Frame bytes are std::vector<std::uint8_t> on the boundary; the modem owns
//     allocations and the adapters do reads/writes via .data() + .size().
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "modem_mac.h"  // for MAC_LEN (dependency-free; avoids a modem_core.h cycle)

namespace modem_core {

// Monotonic clock source. nowMs() must be wrap-safe; callers use signed-diff math.
class IClock {
public:
    virtual ~IClock() = default;
    virtual std::uint32_t nowMs() = 0;
};

// Host UART link (Serial on ESP32). Lines are framed by the adapter.
class IHostLink {
public:
    virtual ~IHostLink() = default;
    // Returns one host-framed line, or empty string if no full line is ready.
    // Sentinel handling (e.g. "__LINE_TOO_LONG__") is up to the adapter.
    virtual std::string readLine() = 0;
    // Writes one line to the host (adapter appends newline + flushes).
    virtual void writeLine(const std::string& line) = 0;
};

// LoRa radio (SX1262 on the real board). Models a non-blocking TX/RX state machine
// driven by an interrupt flag (takeIrqFlag) + RadioLib-style start/finish split.
class IRadio {
public:
    virtual ~IRadio() = default;
    // Place the radio into RX mode. True on success.
    virtual bool startReceive() = 0;
    // Start a TX (non-blocking; TX_DONE IRQ will fire on completion). Returns the
    // HW status code (0 = OK, non-zero = error) so the caller can surface the exact
    // RadioLib code in "ERR TX <code>" -- matches the int returned by tickTxComplete.
    virtual int startTransmit(const std::uint8_t* data, std::size_t len) = 0;
    // After TX_DONE IRQ, complete the transmit (RadioLib bookkeeping). True on success.
    virtual bool finishTransmit() = 0;
    // After RX_DONE IRQ, read the received frame (returns empty vector on read error).
    virtual std::vector<std::uint8_t> readReceivedFrame() = 0;
    // The IRQ flag bits since the last clear (RadioLib-defined bitmask).
    virtual std::uint32_t getIrqFlags() = 0;
    // Clears all IRQ flag bits.
    virtual void clearIrqFlags() = 0;
    // Atomic test-and-clear of the volatile IRQ flag set from the radio's ISR.
    // True iff the IRQ pin fired since the last takeIrqFlag() call.
    virtual bool takeIrqFlag() = 0;
};

// ESP-NOW link (only present on DUAL_BAND builds). Nullable in the Modem ctor for
// single-band builds (the orchestration must guard on a !nullptr check before use).
class IEspNow {
public:
    virtual ~IEspNow() = default;
    // Sends a frame to `mac` (or broadcast if mac is the all-FF broadcast addr).
    // Returns true on accepted-for-tx.
    virtual bool send(const std::uint8_t* mac,
                      const std::uint8_t* data, std::size_t len) = 0;
    // Adds a unicast peer (idempotent). Returns true on success or already-exists.
    virtual bool addPeer(const std::uint8_t* mac) = 0;
    // Deletes a unicast peer. Idempotent (no-op if not present).
    virtual void deletePeer(const std::uint8_t* mac) = 0;

    struct RxItem {
        std::uint8_t src[MAC_LEN];
        std::vector<std::uint8_t> data;  // empty iff no item was ready
    };
    // Polls one frame off the ESP-NOW RX queue, or returns an item with data.empty()
    // if the queue is empty. Non-blocking.
    virtual RxItem pollRx() = 0;
};

}  // namespace modem_core
