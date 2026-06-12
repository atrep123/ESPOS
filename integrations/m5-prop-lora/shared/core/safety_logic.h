#pragma once

// ---------------------------------------------------------------------------
// prop_safety -- canonical receiver-side SAFETY decision logic.
//
// This header is the single, host-testable source of truth for the pure
// decision predicates that gate firing on the DinMeter receiver:
//   * session (epoch) detection            -- when to reset the replay window
//   * frame route validation               -- key / source / destination
//   * replay / dedup sliding window         -- accept / drop-dup / drop-stale
//   * fire authority state machine          -- ARM / STOP / TTL / one-shot FIRE
//
// It is deliberately FREE of any Arduino / ESP-IDF / mbedtls dependency so it
// compiles with a bare host C++17 compiler and can be unit-tested off-target
// (see firmware/tests/test_safety_logic.cpp). Crypto (HMAC frame auth) lives
// in shared/protocol/prop_protocol.h and is intentionally NOT duplicated here:
// authenticity is verified before any of these predicates run.
//
// IMPORTANT (lockstep contract): until the firmware is refactored to call into
// this module, the logic below MUST remain a byte-for-byte mirror of
// firmware/din-rx/src/prop_rx.cpp. The references below point at the verified
// firmware source so the two can be diffed:
//   - epochFromNonce / epoch != _lastEpoch ....... prop_rx.cpp ~1187-1198
//   - ReplayFilter::classify (classifyReplay) ..... prop_rx.cpp ~1099-1131
//   - FireAuthority onArm/onStop/fireAllowed ...... prop_rx.cpp ~1255-1311
//   - FireAuthority::serviceTtl (serviceArmTtl) ... prop_rx.cpp ~1664-1670
//   - ARM_TTL_MS / RX_REPLAY_WINDOW_BITS .......... prop_rx.cpp 2441 / 45
// ---------------------------------------------------------------------------

#include <cstdint>

namespace prop_safety {

// ARM has a safety TTL backstop: if no FIRE arrives within this window the
// receiver silently returns to SAFE (mirrors prop_rx.cpp ARM_TTL_MS = 12000,
// ~2 missed 5 s heartbeats). 32-bit ms; wraparound handled by signed compare.
constexpr std::uint32_t ARM_TTL_MS = 12000;

// Width (in sequence numbers) of the replay/dedup sliding window behind the
// high-water base (mirrors prop_rx.cpp RX_REPLAY_WINDOW_BITS = 32).
constexpr std::uint32_t RX_REPLAY_WINDOW_BITS = 32;

// --- session / epoch ------------------------------------------------------
// The Dial encodes a per-boot RANDOM 32-bit epoch in the TOP 32 bits of the
// frame nonce (Option A). ANY different epoch means a fresh Dial session, so
// the receiver resets its dedup window. '!=' semantics (no monotonic ordering)
// guarantee an erased/reflashed Dial can never be permanently rejected.
inline std::uint32_t epochFromNonce(std::uint64_t nonce)
{
    return static_cast<std::uint32_t>(nonce >> 32);
}

inline bool epochIsNewSession(std::uint32_t incomingEpoch, std::uint32_t lastEpoch)
{
    return incomingEpoch != lastEpoch;
}

// --- frame route ----------------------------------------------------------
// First safety gate: a frame must carry the shared key id and be addressed
// from the expected peer to us (mirrors validateFrameRoute in prop_rx.cpp).
// Device-specific expected values are passed in so this stays target-agnostic.
inline bool routeValid(std::uint8_t keyId, std::uint8_t source, std::uint8_t destination,
                       std::uint8_t expectedKeyId, std::uint8_t expectedSource,
                       std::uint8_t expectedDestination)
{
    return keyId == expectedKeyId && source == expectedSource &&
           destination == expectedDestination;
}

// --- replay / dedup window ------------------------------------------------
enum class ReplayDecision : std::uint8_t {
    EXECUTE,     // first time we have seen this sequence -> act on it
    DROP_DUP,    // already seen (redundant burst copy) -> ignore silently
    DROP_STALE,  // older than the trailing window -> reject
};

// Sliding-window replay filter. `windowBase` is the highest accepted sequence;
// `windowMask` records which of the RX_REPLAY_WINDOW_BITS sequences immediately
// below the base have already been seen (bit (n-1) == base-n).
struct ReplayFilter {
    std::uint32_t windowBase = 0;
    std::uint32_t windowMask = 0;

    // Reset on a new session: the first frame of the session defines the base
    // (mirrors the epoch branch in prop_rx.cpp ~1190-1192).
    void resetForNewSession(std::uint32_t sequence)
    {
        windowBase = sequence;
        windowMask = 0;
    }

    // EXACT mirror of prop_rx.cpp classifyReplay (~1099-1131). Do not "tidy".
    ReplayDecision classify(std::uint32_t sequence)
    {
        if ((windowBase == 0 && sequence > 0) || sequence > windowBase) {
            const std::uint32_t shift = sequence - windowBase;
            if (shift > RX_REPLAY_WINDOW_BITS) {
                windowMask = 0;
            } else {
                const std::uint32_t acceptedBaseBit = static_cast<std::uint32_t>(1) << (shift - 1);
                if (shift == RX_REPLAY_WINDOW_BITS) {
                    windowMask = acceptedBaseBit;
                } else {
                    windowMask = (windowMask << shift) | acceptedBaseBit;
                }
            }
            windowBase = sequence;
            return ReplayDecision::EXECUTE;
        }

        if (sequence == windowBase) {
            return ReplayDecision::DROP_DUP;
        }

        const std::uint32_t diff = windowBase - sequence;
        if (diff > RX_REPLAY_WINDOW_BITS) {
            return ReplayDecision::DROP_STALE;
        }

        const std::uint32_t seenBit = static_cast<std::uint32_t>(1) << (diff - 1);
        if ((windowMask & seenBit) != 0) {
            return ReplayDecision::DROP_DUP;
        }

        windowMask |= seenBit;
        return ReplayDecision::EXECUTE;
    }
};

// --- fire authority (ARM / STOP / TTL / one-shot FIRE) ---------------------
// The receiver is the fire authority (Sprint A 0.1/0.2). FIRE is rejected
// unless the receiver is locally ARMED, not STOP-latched, and the ARM has not
// timed out. Mirrors the Arm/Fire/Stop handlers + serviceArmTtl in prop_rx.cpp.
struct FireAuthority {
    bool armed = false;            // set ONLY by an Arm frame (never by Preview)
    std::uint32_t armStartMs = 0;  // ms timestamp of the latching Arm; basis for the TTL
    std::uint32_t armExpiryMs = 0; // absolute ms deadline (= armStartMs + ARM_TTL_MS)
    std::uint32_t armEpoch = 0;    // epoch of the ARM currently authorising one FIRE
    std::uint32_t armSeq = 0;      // FIRE must post-date this ARM sequence
    bool lockout = false;          // latched by STOP until the next deliberate Arm
    std::uint32_t lockoutSeq = 0;  // sequence of the STOP fence; lower replay cannot clear it

    void clearArm()
    {
        armed = false;
        armExpiryMs = 0;
        armEpoch = 0;
        armSeq = 0;
    }

    void acceptArm(std::uint32_t nowMs, std::uint32_t sequence, std::uint32_t epoch)
    {
        armed = true;
        armStartMs = nowMs;
        armExpiryMs = nowMs + ARM_TTL_MS;
        armEpoch = epoch;
        armSeq = sequence;
        lockout = false;
    }

    // Legacy pure state helper: arm with a fresh TTL and clear any prior STOP latch.
    void onArm(std::uint32_t nowMs)
    {
        acceptArm(nowMs, 0, 0);
    }

    // Frame-aware ARM gate: a STOP lockout may only be cleared by an ARM whose
    // sequence post-dates the STOP fence, regardless of epoch.
    bool onArmFrame(std::uint32_t nowMs, std::uint32_t sequence, std::uint32_t epoch)
    {
        if (lockout && sequence <= lockoutSeq) {
            return false;
        }
        acceptArm(nowMs, sequence, epoch);
        return true;
    }

    // STOP frame: disarm and LATCH a lockout so a delayed/stray Fire afterwards
    // cannot re-fire until a fresh Arm (~1304-1306).
    void onStop()
    {
        clearArm();
        lockout = true;
    }

    // Frame-aware STOP records a monotonic sequence fence. Epoch changes must not
    // lower this fence because epochs are random, not freshness proof.
    void onStopFrame(std::uint32_t sequence)
    {
        clearArm();
        if (!lockout || sequence > lockoutSeq) {
            lockoutSeq = sequence;
        }
        lockout = true;
    }

    // FIRE is one-shot: startFire() clears _armed in firmware (~1292). Call this
    // when a Fire is accepted so the next Fire needs a new Arm.
    void onFireConsumed()
    {
        clearArm();
    }

    // Bounded elapsed-since-arm so the predicate is self-sufficient even if serviceTtl is
    // not called for a long time. Unsigned (nowMs - armStartMs) only mis-reads as "not
    // expired" after a full ~49.7-day uint32 wrap (vs ~24.85 days for a signed delta on the
    // absolute expiry), and an over-old ARM resolves to expired = fail-safe. Only meaningful
    // while armed (armStartMs is the most recent Arm).
    bool ttlExpired(std::uint32_t nowMs) const
    {
        return (nowMs - armStartMs) >= ARM_TTL_MS;
    }

    // Background service: drop ARM back to SAFE once the TTL elapses (~1664-1670).
    void serviceTtl(std::uint32_t nowMs)
    {
        if (armed && ttlExpired(nowMs)) {
            clearArm();
        }
    }

    // THE safety gate. A Fire may execute only if armed, not locked out, and the
    // ARM is still fresh. Exact negation of the reject condition in prop_rx.cpp
    // (~1270-1271): reject if (!armed || lockout || (int32)(now-expiry) >= 0).
    bool fireAllowed(std::uint32_t nowMs) const
    {
        return armed && !lockout && !ttlExpired(nowMs);
    }

    bool fireAllowedForFrame(std::uint32_t nowMs, std::uint32_t sequence,
                             std::uint32_t epoch) const
    {
        return fireAllowed(nowMs) && epoch == armEpoch && sequence > armSeq &&
               sequence > lockoutSeq;
    }
};

}  // namespace prop_safety
