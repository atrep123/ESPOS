#include "../dualkey-tx/src/dualkey_tx_logic.h"

#include <iostream>

namespace {

using dualkey_tx::ButtonLevel;
using dualkey_tx::DualKeyTxLogic;
using dualkey_tx::EventKind;

bool key1PressPublishesBlueSetAfterDebounce() {
    DualKeyTxLogic logic(20);
    auto cold = logic.update(0, ButtonLevel{false, false});
    auto bounce = logic.update(5, ButtonLevel{true, false});
    auto edge = logic.update(25, ButtonLevel{true, false});
    auto held = logic.update(80, ButtonLevel{true, false});
    return cold.kind == EventKind::None &&
           bounce.kind == EventKind::None &&
           edge.kind == EventKind::BlueSet &&
           edge.value == 1 &&
           edge.eventId == 1 &&
           held.kind == EventKind::None;
}

bool key1SecondPressPublishesBlueOff() {
    DualKeyTxLogic logic(20);
    logic.update(0, ButtonLevel{true, false});
    auto on = logic.update(25, ButtonLevel{true, false});
    logic.update(50, ButtonLevel{false, false});
    logic.update(75, ButtonLevel{false, false});
    logic.update(100, ButtonLevel{true, false});
    auto off = logic.update(125, ButtonLevel{true, false});
    return on.kind == EventKind::BlueSet &&
           on.value == 1 &&
           off.kind == EventKind::BlueSet &&
           off.value == 0 &&
           off.eventId == 2;
}

bool key2PressPublishesOneShotBarrelEffect() {
    DualKeyTxLogic logic(15);
    logic.update(0, ButtonLevel{false, true});
    auto edge = logic.update(16, ButtonLevel{false, true});
    auto held = logic.update(80, ButtonLevel{false, true});
    return edge.kind == EventKind::BarrelEffect &&
           edge.value == 0 &&
           edge.eventId == 1 &&
           held.kind == EventKind::None;
}

bool simultaneousEdgesPreferBlueThenBarrelOnNextTick() {
    DualKeyTxLogic logic(10);
    logic.update(0, ButtonLevel{true, true});
    auto first = logic.update(11, ButtonLevel{true, true});
    auto second = logic.update(12, ButtonLevel{true, true});
    return first.kind == EventKind::BlueSet &&
           first.value == 1 &&
           second.kind == EventKind::BarrelEffect &&
           second.eventId == 2;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("key1 press publishes blue set after debounce",
                        key1PressPublishesBlueSetAfterDebounce) ? 0 : 1;
    failures += runCase("key1 second press publishes blue off",
                        key1SecondPressPublishesBlueOff) ? 0 : 1;
    failures += runCase("key2 press publishes one-shot barrel effect",
                        key2PressPublishesOneShotBarrelEffect) ? 0 : 1;
    failures += runCase("simultaneous edges prefer blue then barrel on next tick",
                        simultaneousEdgesPreferBlueThenBarrelOnNextTick) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}

