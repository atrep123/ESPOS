// Host unit tests for shared/core/safety_logic.h -- the receiver-side fire
// safety decision logic. Pure C++17, no Arduino/ESP/mbedtls. Build & run via
// tools/run_host_tests.ps1 (or any host C++ compiler).
//
// Style mirrors firmware/tests/test_palette.cpp: each case is a bool-returning
// function; main() reports PASS/FAIL and exits non-zero on any failure.

#include "../../shared/core/safety_logic.h"

#include <cstdint>
#include <iostream>

namespace {

using prop_safety::ARM_TTL_MS;
using prop_safety::FireAuthority;
using prop_safety::ReplayDecision;
using prop_safety::ReplayFilter;
using prop_safety::epochFromNonce;
using prop_safety::epochIsNewSession;
using prop_safety::routeValid;

// ---- epoch / session -----------------------------------------------------

bool epochExtractsTopHalf() {
    bool ok = true;
    ok &= epochFromNonce(0xABCD1234DEADBEEFull) == 0xABCD1234u;  // low half ignored
    ok &= epochFromNonce(0x00000001FFFFFFFFull) == 0x00000001u;
    ok &= epochFromNonce(0x0000000000000000ull) == 0x00000000u;
    return ok;
}

bool epochNewSessionSemantics() {
    bool ok = true;
    ok &= epochIsNewSession(5, 5) == false;   // same epoch -> same session
    ok &= epochIsNewSession(5, 6) == true;    // any difference -> new session
    ok &= epochIsNewSession(0, 1) == true;    // no monotonic ordering (no brick)
    ok &= epochIsNewSession(1, 0) == true;    // a fresh (reflashed) Dial is accepted
    return ok;
}

// ---- frame route ---------------------------------------------------------

bool routeAcceptsExactTripleAndRejectsEach() {
    const std::uint8_t K = 1, S = 0x11, D = 0x22;  // expected key/source/dest
    bool ok = true;
    ok &= routeValid(K, S, D, K, S, D) == true;        // exact match
    ok &= routeValid(9, S, D, K, S, D) == false;       // wrong key id
    ok &= routeValid(K, 0x33, D, K, S, D) == false;    // wrong source
    ok &= routeValid(K, S, 0x44, K, S, D) == false;    // wrong destination
    return ok;
}

// ---- fire authority ------------------------------------------------------

bool fireBlockedWhenNeverArmed() {
    FireAuthority fa;
    return fa.fireAllowed(0) == false && fa.fireAllowed(50000) == false;
}

bool armEnablesFireWithinTtl() {
    FireAuthority fa;
    fa.onArm(1000);
    bool ok = true;
    ok &= fa.fireAllowed(1000) == true;                       // immediately
    ok &= fa.fireAllowed(1000 + ARM_TTL_MS - 1) == true;      // last ms of window
    ok &= fa.fireAllowed(1000 + ARM_TTL_MS) == false;         // TTL reached -> SAFE
    ok &= fa.fireAllowed(1000 + ARM_TTL_MS + 1) == false;     // past TTL
    return ok;
}

bool stopLatchesLockout() {
    FireAuthority fa;
    fa.onArm(1000);
    fa.onStop();
    bool ok = true;
    ok &= fa.armed == false;
    ok &= fa.lockout == true;
    ok &= fa.fireAllowed(1001) == false;        // a delayed/stray Fire cannot re-fire
    // ...until a fresh deliberate Arm clears the latch:
    fa.onArm(2000);
    ok &= fa.lockout == false;
    ok &= fa.fireAllowed(2000) == true;
    return ok;
}

bool stopFenceBlocksLowerSequenceNewEpochReplay() {
    FireAuthority fa;
    const std::uint32_t liveEpoch = 0x22222222u;
    const std::uint32_t replayedEpoch = 0x11111111u;

    bool ok = fa.onArmFrame(1000, 999, liveEpoch) == true;
    fa.onStopFrame(1000);
    ok &= fa.armed == false;
    ok &= fa.lockout == true;
    ok &= fa.lockoutSeq == 1000u;

    ok &= fa.onArmFrame(1001, 100, replayedEpoch) == false;
    ok &= fa.armed == false;
    ok &= fa.lockout == true;
    ok &= fa.fireAllowedForFrame(1001, 101, replayedEpoch) == false;

    ok &= fa.onArmFrame(2000, 1001, liveEpoch) == true;
    ok &= fa.lockout == false;
    ok &= fa.fireAllowedForFrame(2001, 1002, liveEpoch) == true;
    return ok;
}

bool fireIsOneShot() {
    FireAuthority fa;
    fa.onArm(1000);
    bool ok = (fa.fireAllowed(1000) == true);
    fa.onFireConsumed();                         // startFire() clears _armed
    ok &= fa.armed == false;
    ok &= fa.fireAllowed(1000) == false;         // a second Fire needs a new Arm
    return ok;
}

bool serviceTtlDropsToSafe() {
    FireAuthority fa;
    fa.onArm(1000);
    fa.serviceTtl(1000 + ARM_TTL_MS - 1);
    bool ok = (fa.armed == true);                // still inside window
    fa.serviceTtl(1000 + ARM_TTL_MS);
    ok &= fa.armed == false;                     // TTL elapsed -> disarmed
    return ok;
}

// The device clock is a uint32 ms counter that wraps every ~49.7 days. The
// signed-delta TTL comparison must keep working across that rollover.
bool ttlSurvivesMillisWraparound() {
    FireAuthority fa;
    const std::uint32_t near = 0xFFFFFF00u;      // ~near the 32-bit ms rollover
    fa.onArm(near);                              // expiry wraps past 2^32
    bool ok = true;
    ok &= fa.fireAllowed(near) == true;                 // armed right after arm
    ok &= fa.fireAllowed(near + 10) == true;            // a few ms later, still armed
    ok &= fa.fireAllowed(near + ARM_TTL_MS - 1) == true;  // last ms (post-wrap now)
    ok &= fa.fireAllowed(near + ARM_TTL_MS) == false;     // TTL reached across wrap
    return ok;
}

// ---- replay / dedup window ----------------------------------------------

bool replayBasicAcceptDupAndBackfill() {
    ReplayFilter rf;
    rf.resetForNewSession(100);
    bool ok = true;
    ok &= rf.classify(101) == ReplayDecision::EXECUTE;    // new high-water
    ok &= rf.windowBase == 101u;
    ok &= rf.classify(101) == ReplayDecision::DROP_DUP;   // exact repeat of base
    ok &= rf.classify(100) == ReplayDecision::DROP_DUP;   // previous base is "seen"
    return ok;
}

bool replayWithinWindowIsAcceptOnceThenDup() {
    ReplayFilter rf;
    rf.resetForNewSession(100);
    bool ok = true;
    ok &= rf.classify(105) == ReplayDecision::EXECUTE;    // jump forward (shift 5)
    ok &= rf.windowBase == 105u;
    ok &= rf.classify(103) == ReplayDecision::EXECUTE;    // older but in window, 1st time
    ok &= rf.classify(103) == ReplayDecision::DROP_DUP;   // same again -> dup
    ok &= rf.classify(104) == ReplayDecision::EXECUTE;    // another in-window backfill
    ok &= rf.classify(104) == ReplayDecision::DROP_DUP;
    ok &= rf.windowBase == 105u;                          // base unchanged by backfill
    return ok;
}

bool replayStaleBoundary() {
    ReplayFilter rf;
    rf.resetForNewSession(1000);
    rf.classify(1100);                                    // base = 1100
    bool ok = true;
    // exactly at the trailing edge (diff == WINDOW_BITS == 32) is still inside
    ok &= rf.classify(1100 - 32) == ReplayDecision::EXECUTE;   // 1068, diff 32
    ok &= rf.classify(1100 - 32) == ReplayDecision::DROP_DUP;  // now seen
    // one past the edge (diff 33) is too old
    ok &= rf.classify(1100 - 33) == ReplayDecision::DROP_STALE;  // 1067
    ok &= rf.windowBase == 1100u;                         // stale/dup never move base
    return ok;
}

bool replayBigJumpForgetsHistory() {
    ReplayFilter rf;
    rf.resetForNewSession(100);
    rf.classify(105);
    bool ok = true;
    // a forward jump larger than the window clears the mask entirely
    ok &= rf.classify(105 + 40) == ReplayDecision::EXECUTE;   // 145, shift 40 > 32
    ok &= rf.windowBase == 145u;
    // sequences just below the new base are "new" again (history was dropped)
    ok &= rf.classify(140) == ReplayDecision::EXECUTE;
    return ok;
}

bool replayNewSessionResetReacceptsLowSequences() {
    ReplayFilter rf;
    rf.resetForNewSession(50000);
    rf.classify(50001);
    // A Dial reboot (new epoch) restarts sequences low; the epoch branch resets
    // the window so the receiver does not treat them as stale.
    rf.resetForNewSession(3);
    bool ok = true;
    ok &= rf.classify(4) == ReplayDecision::EXECUTE;   // low seq accepted post-reset
    ok &= rf.classify(4) == ReplayDecision::DROP_DUP;
    return ok;
}

// ---- review hardening (gaps raised by the independent Opus review) --------

// Defense in depth: after a FIRE is consumed, a replayed copy of the SAME fire
// is blocked by BOTH layers -- the replay window dedups it AND the one-shot arm
// is already cleared. Either layer alone would stop the re-fire.
bool fireConsumedThenReplayedFireDoubleBlocked() {
    FireAuthority fa;
    ReplayFilter rf;
    rf.resetForNewSession(500);
    fa.onArm(1000);
    bool ok = (rf.classify(501) == ReplayDecision::EXECUTE);  // FIRE seq 501
    ok &= fa.fireAllowed(1000) == true;
    fa.onFireConsumed();                                       // one-shot: disarmed
    ok &= rf.classify(501) == ReplayDecision::DROP_DUP;        // layer 1: dedup
    ok &= fa.fireAllowed(1000) == false;                      // layer 2: not armed
    return ok;
}

// Replay window works at the very top of the uint32 sequence range, including
// the windowBase==0 special-case entry.
bool replayNearSequenceMax() {
    ReplayFilter rf;  // fresh -> windowBase == 0
    const std::uint32_t MAX = 0xFFFFFFFFu;
    bool ok = true;
    ok &= rf.classify(MAX) == ReplayDecision::EXECUTE;       // base==0 && seq>0
    ok &= rf.windowBase == MAX;
    ok &= rf.classify(MAX) == ReplayDecision::DROP_DUP;      // exact repeat
    ok &= rf.classify(MAX - 1) == ReplayDecision::EXECUTE;   // in-window backfill
    ok &= rf.classify(MAX - 1) == ReplayDecision::DROP_DUP;
    return ok;
}

// serviceTtl (not just fireAllowed) must also disarm correctly across the
// 49.7-day uint32 millis() rollover.
bool serviceTtlSurvivesMillisWraparound() {
    FireAuthority fa;
    const std::uint32_t near = 0xFFFFFF00u;  // expiry wraps past 2^32
    fa.onArm(near);
    fa.serviceTtl(near + 10);
    bool ok = (fa.armed == true);            // still inside window across wrap
    fa.serviceTtl(near + ARM_TTL_MS);
    ok &= fa.armed == false;                 // TTL elapsed across wrap -> disarmed
    return ok;
}

// Exact-boundary forward jump (shift == RX_REPLAY_WINDOW_BITS == 32): only the
// previous base stays "seen"; its neighbour is treated as new.
bool replayShiftExactlyWindowWidth() {
    ReplayFilter rf;
    rf.resetForNewSession(100);
    bool ok = true;
    ok &= rf.classify(132) == ReplayDecision::EXECUTE;   // shift == 32 exactly
    ok &= rf.windowBase == 132u;
    ok &= rf.classify(100) == ReplayDecision::DROP_DUP;  // old base marked seen
    ok &= rf.classify(101) == ReplayDecision::EXECUTE;   // neighbour was not seen
    return ok;
}

// Re-arming after a TTL expiry installs a FRESH full window with no stale
// expiry carryover; and a STOP makes a later serviceTtl a safe no-op.
bool rearmAfterExpiryResetsFreshWindow() {
    FireAuthority fa;
    fa.onArm(1000);
    fa.serviceTtl(1000 + ARM_TTL_MS);            // expires
    bool ok = (fa.armed == false);
    fa.onArm(20000);                             // fresh arm -> fresh expiry
    ok &= fa.fireAllowed(20000) == true;
    ok &= fa.fireAllowed(20000 + ARM_TTL_MS - 1) == true;  // full fresh window
    ok &= fa.fireAllowed(20000 + ARM_TTL_MS) == false;
    fa.onStop();                                 // latch lockout, disarm
    fa.serviceTtl(20000 + ARM_TTL_MS + 5);       // no-op: already disarmed
    ok &= fa.armed == false;
    ok &= fa.lockout == true;
    return ok;
}

// ---- harness -------------------------------------------------------------

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("epoch extracts top 32 bits", epochExtractsTopHalf) ? 0 : 1;
    failures += runCase("epoch new-session uses != (no brick)", epochNewSessionSemantics) ? 0 : 1;
    failures += runCase("route accepts exact triple, rejects each field", routeAcceptsExactTripleAndRejectsEach) ? 0 : 1;
    failures += runCase("fire blocked when never armed", fireBlockedWhenNeverArmed) ? 0 : 1;
    failures += runCase("arm enables fire within TTL", armEnablesFireWithinTtl) ? 0 : 1;
    failures += runCase("stop latches lockout until re-arm", stopLatchesLockout) ? 0 : 1;
    failures += runCase("STOP fence blocks lower-seq new-epoch replay", stopFenceBlocksLowerSequenceNewEpochReplay) ? 0 : 1;
    failures += runCase("fire is one-shot", fireIsOneShot) ? 0 : 1;
    failures += runCase("serviceTtl drops to SAFE", serviceTtlDropsToSafe) ? 0 : 1;
    failures += runCase("TTL survives millis() wraparound", ttlSurvivesMillisWraparound) ? 0 : 1;
    failures += runCase("replay: accept/dup/backfill", replayBasicAcceptDupAndBackfill) ? 0 : 1;
    failures += runCase("replay: in-window accept-once", replayWithinWindowIsAcceptOnceThenDup) ? 0 : 1;
    failures += runCase("replay: stale boundary (diff 32 vs 33)", replayStaleBoundary) ? 0 : 1;
    failures += runCase("replay: big jump forgets history", replayBigJumpForgetsHistory) ? 0 : 1;
    failures += runCase("replay: new-session reset re-accepts low seq", replayNewSessionResetReacceptsLowSequences) ? 0 : 1;
    failures += runCase("fire consumed + replayed fire double-blocked", fireConsumedThenReplayedFireDoubleBlocked) ? 0 : 1;
    failures += runCase("replay near uint32 sequence max", replayNearSequenceMax) ? 0 : 1;
    failures += runCase("serviceTtl survives millis() wraparound", serviceTtlSurvivesMillisWraparound) ? 0 : 1;
    failures += runCase("replay: shift == window width (32)", replayShiftExactlyWindowWidth) ? 0 : 1;
    failures += runCase("re-arm after expiry resets fresh window", rearmAfterExpiryResetsFreshWindow) ? 0 : 1;
    if (failures == 0) {
        std::cout << "ALL PASS (test_safety_logic)\n";
    } else {
        std::cout << failures << " FAILED (test_safety_logic)\n";
    }
    return failures == 0 ? 0 : 1;
}
