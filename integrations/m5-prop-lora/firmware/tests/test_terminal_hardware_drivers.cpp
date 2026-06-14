#include "../sticks3-terminal/src/drivers/terminal_chain_encoder_driver.h"
#include "../sticks3-terminal/src/drivers/terminal_external_oled.h"
#include "../sticks3-terminal/src/drivers/terminal_fader_driver.h"

#include <array>
#include <iostream>

namespace {

using terminal_chain_encoder_driver::ChainEncoderDriver;
using terminal_chain_encoder_driver::ChainEncoderRawReader;
using terminal_chain_encoder_driver::applyChainKeyButtonLevels;
using terminal_chain_encoder_driver::chainEncoderIdForLane;
using terminal_chain_encoder_driver::classifyChainPress;
using terminal_chain_encoder_driver::makeChainEncoderSample;
using terminal_chain_encoder_driver::makeChainEncoderIncrementSample;
using terminal_control_surface::ControlSnapshot;
using terminal_control_surface::ControlSurface;
using terminal_external_display::makeFrame;
using terminal_external_oled::ExternalOledDriver;
using terminal_external_oled::ExternalOledSink;
using terminal_fader_driver::FaderDriver;
using terminal_fader_driver::FaderRawReader;
using terminal_setup::TerminalSetupState;

class FakeFaderRawReader : public FaderRawReader {
   public:
    bool begin() override {
        began = true;
        return available;
    }

    int readRaw(std::size_t lane) override {
        return lane < terminal_setup::LANE_COUNT ? raw[lane] : terminal_fader_filter::RAW_SAMPLE_MISSING;
    }

    bool available = true;
    bool began = false;
    std::array<int, terminal_setup::LANE_COUNT> raw = {};
};

class FakeChainEncoderRawReader : public ChainEncoderRawReader {
   public:
    bool begin() override {
        began = true;
        return available;
    }

    terminal_encoder_filter::EncoderSample readSample(std::size_t lane) override {
        return lane < terminal_setup::LANE_COUNT
                   ? samples[lane]
                   : terminal_encoder_filter::EncoderSample{};
    }

    bool available = true;
    bool began = false;
    std::array<terminal_encoder_filter::EncoderSample, terminal_setup::LANE_COUNT> samples = {};
};

class FakeExternalOledSink : public ExternalOledSink {
   public:
    bool begin() override {
        ++beginCount;
        began = true;
        return available;
    }

    bool draw(const terminal_external_display::DisplayRenderPlan& plan,
              const terminal_external_display::DisplayFrame& frame) override {
        ++drawCount;
        if (failNextDraw) {
            failNextDraw = false;
            return false;
        }
        drew = true;
        lastPlan = plan;
        lastFrame = frame;
        return true;
    }

    bool available = true;
    bool failNextDraw = false;
    bool began = false;
    bool drew = false;
    int beginCount = 0;
    int drawCount = 0;
    terminal_external_display::DisplayRenderPlan lastPlan = {};
    terminal_external_display::DisplayFrame lastFrame = {};
};

bool faderStubLeavesBrightnessUnchanged() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    FaderDriver faders;
    const bool began = faders.begin();
    snapshot.lanes[0].sliderPercent = 0;
    faders.read(snapshot);
    surface.apply(snapshot, state);
    return began == false &&
           faders.available() == false &&
           state.draftLane(0).brightness == 100 &&
           !state.dirty();
}

bool fakeFaderRawReaderPublishesChangedRawSample() {
    FakeFaderRawReader reader;
    reader.raw[0] = 0;
    FaderDriver faders(reader);
    faders.begin();
    reader.raw[0] = 2048;

    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    faders.read(snapshot);
    surface.apply(snapshot, state);
    return reader.began && faders.available() && state.draftLane(0).brightness == 50;
}

bool faderBeginPrimesCurrentRawWithoutChangingBrightness() {
    FakeFaderRawReader reader;
    reader.raw[0] = 2048;
    FaderDriver faders(reader);
    faders.begin();

    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    faders.read(snapshot);
    surface.apply(snapshot, state);
    return state.draftLane(0).brightness == 100 && !state.dirty();
}

bool faderLockToDraftSuppressesMismatchUntilPickup() {
    FakeFaderRawReader reader;
    reader.raw[0] = 3686;
    FaderDriver faders(reader);
    faders.begin();

    TerminalSetupState state;
    state.setBrightness(0, 20);
    faders.lockToDraft(state);

    ControlSurface surface;
    ControlSnapshot mismatch;
    faders.read(mismatch);
    surface.apply(mismatch, state);
    if (state.draftLane(0).brightness != 20) {
        return false;
    }

    reader.raw[0] = 819;
    ControlSnapshot pickup;
    faders.read(pickup);
    surface.apply(pickup, state);
    if (state.draftLane(0).brightness != 20) {
        return false;
    }

    reader.raw[0] = 942;
    ControlSnapshot moved;
    faders.read(moved);
    surface.apply(moved, state);
    return state.draftLane(0).brightness == 23;
}

bool chainEncoderStubLeavesColorOnAndEffectStateUnchanged() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    ChainEncoderDriver encoders;
    snapshot.lanes[1].encoderDelta = 45;
    snapshot.lanes[1].encoderPressed = true;
    snapshot.lanes[1].effectPressed = true;
    encoders.read(snapshot);
    surface.apply(snapshot, state);
    return state.draftLane(1).hue == 365 &&
           state.draftLane(1).on == true &&
           state.draftLane(1).effect == false &&
           !state.dirty();
}

bool fakeChainEncoderRawReaderPublishesMovementAndButtons() {
    FakeChainEncoderRawReader reader;
    reader.samples[0] = terminal_encoder_filter::EncoderSample{10, false, false};
    ChainEncoderDriver encoders(reader);
    encoders.begin();
    reader.samples[0] = terminal_encoder_filter::EncoderSample{13, true, true};

    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    encoders.read(snapshot);
    surface.apply(snapshot, state);
    return reader.began &&
           encoders.available() &&
           state.draftLane(0).hue == 363 &&
           state.draftLane(0).on == true &&
           state.draftLane(0).effect == true;
}

bool chainEncoderBeginPrimesCurrentPositionWithoutPublishingDelta() {
    FakeChainEncoderRawReader reader;
    reader.samples[0] = terminal_encoder_filter::EncoderSample{8, false, false};
    ChainEncoderDriver encoders(reader);
    encoders.begin();

    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    encoders.read(snapshot);
    surface.apply(snapshot, state);
    return state.draftLane(0).hue == 360 &&
           state.draftLane(0).on == true &&
           state.draftLane(0).effect == false &&
           !state.dirty();
}

bool chainEncoderDriverPreservesSliderInput() {
    FakeChainEncoderRawReader reader;
    reader.samples[2] = terminal_encoder_filter::EncoderSample{5, false, false};
    ChainEncoderDriver encoders(reader);
    encoders.begin();
    reader.samples[2] = terminal_encoder_filter::EncoderSample{6, false, false};

    ControlSnapshot snapshot;
    snapshot.lanes[2].sliderPercent = 33;
    encoders.read(snapshot);
    return snapshot.lanes[2].sliderPercent == 33 &&
           snapshot.lanes[2].encoderDelta == 6;
}

bool chainEncoderSinglePressClassifiesAsEffectToggle() {
    const auto press = classifyChainPress(true, false);
    return !press.encoderPressed && press.effectPressed;
}

bool chainEncoderLongPressAlsoClassifiesAsEffectToggle() {
    const auto press = classifyChainPress(true, true);
    return !press.encoderPressed && press.effectPressed;
}

bool chainEncoderSampleFactoryKeepsPressEdgesExclusive() {
    const auto sample = makeChainEncoderSample(17, true, true);
    return sample.position == 17 &&
           !sample.encoderPressed &&
           sample.effectPressed;
}

bool chainEncoderSampleFactoryPreservesButtonsWhenPositionMissing() {
    const auto sample = makeChainEncoderSample(
        terminal_encoder_filter::ENCODER_POSITION_MISSING,
        true,
        false);
    return sample.position == terminal_encoder_filter::ENCODER_POSITION_MISSING &&
           !sample.encoderPressed &&
           sample.effectPressed;
}

bool chainEncoderIncrementSampleFactoryPreservesMovementAndButtons() {
    const auto sample = makeChainEncoderIncrementSample(2, true, false);
    return sample.position == terminal_encoder_filter::ENCODER_POSITION_MISSING &&
           sample.hasIncrement &&
           sample.increment == 2 &&
           !sample.encoderPressed &&
           sample.effectPressed;
}

bool chainEncoderDisabledBusReportsUnavailable() {
    ChainEncoderDriver encoders;
    return encoders.begin() == false && encoders.available() == false;
}

bool chainEncoderIdsMapPhysicalLed5ToLogicalLed1() {
    return chainEncoderIdForLane(0) == 5 &&
           chainEncoderIdForLane(1) == 4 &&
           chainEncoderIdForLane(2) == 3 &&
           chainEncoderIdForLane(3) == 2 &&
           chainEncoderIdForLane(4) == 1 &&
           chainEncoderIdForLane(terminal_setup::LANE_COUNT) == 0;
}

bool chainKeyLevelsMapUploadAndLastSwitchToActions() {
    terminal_switches::SwitchSnapshot snapshot;
    applyChainKeyButtonLevels(true, false, snapshot);
    if (!snapshot.uploadPressed || snapshot.simFirePressed) {
        return false;
    }
    applyChainKeyButtonLevels(false, true, snapshot);
    return snapshot.uploadPressed && snapshot.simFirePressed;
}

bool externalOledStubRejectsDisplayFrameWithoutIoCache() {
    TerminalSetupState state;
    state.setBrightness(0, 80);
    const auto frame = makeFrame(state);
    ExternalOledDriver display;
    const bool began = display.begin();
    const bool drew = display.draw(frame);
    return began == false &&
           drew == false &&
           display.available() == false &&
           display.lastFrame().rows[0] != frame.rows[0];
}

bool fakeExternalOledSinkReceivesRenderPlanAndFrame() {
    TerminalSetupState state;
    state.rotateHue(0, 42);
    const auto frame = makeFrame(state);
    FakeExternalOledSink sink;
    ExternalOledDriver display(sink);
    const bool began = display.begin();
    const bool drew = display.draw(frame);
    return began &&
           drew &&
           display.available() &&
           sink.began &&
           sink.drew &&
           sink.lastPlan.widthPx == terminal_external_display::OLED_WIDTH_PX &&
           sink.lastPlan.rows[4].rowBox.yPx == 50 &&
           sink.lastPlan.rows[4].effectBox.xPx == 104 &&
           sink.lastFrame == frame &&
           display.lastFrame() == frame;
}

bool unchangedExternalOledFrameSkipsIoDraw() {
    TerminalSetupState state;
    state.rotateHue(0, 42);
    const auto frame = makeFrame(state);
    FakeExternalOledSink sink;
    ExternalOledDriver display(sink);
    const bool began = display.begin();
    const bool firstDraw = display.draw(frame);
    const bool secondDraw = display.draw(frame);
    return began &&
           firstDraw &&
           secondDraw &&
           display.available() &&
           sink.drawCount == 1 &&
           sink.lastFrame == frame &&
           display.lastFrame() == frame;
}

bool unavailableExternalOledSinkDoesNotCacheFrameWithoutIoDraw() {
    TerminalSetupState state;
    const auto frame = makeFrame(state);
    FakeExternalOledSink sink;
    sink.available = false;
    ExternalOledDriver display(sink);
    const bool began = display.begin();
    const bool drew = display.draw(frame);
    return !began &&
           !drew &&
           !display.available() &&
           sink.began &&
           !sink.drew &&
           display.lastFrame() != frame;
}

bool failedExternalOledDrawIsRetriedInsteadOfCached() {
    TerminalSetupState state;
    state.setBrightness(0, 80);
    const auto frame = makeFrame(state);
    FakeExternalOledSink sink;
    sink.failNextDraw = true;
    ExternalOledDriver display(sink);
    const bool began = display.begin();
    const bool firstDraw = display.draw(frame);
    const bool secondDraw = display.draw(frame);
    return began &&
           !firstDraw &&
           secondDraw &&
           sink.beginCount >= 2 &&
           sink.drawCount == 2 &&
           display.lastFrame() == frame;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("fader stub leaves brightness unchanged", faderStubLeavesBrightnessUnchanged) ? 0 : 1;
    failures += runCase("fake fader raw reader publishes changed raw sample", fakeFaderRawReaderPublishesChangedRawSample) ? 0 : 1;
    failures += runCase("fader begin primes current raw without changing brightness", faderBeginPrimesCurrentRawWithoutChangingBrightness) ? 0 : 1;
    failures += runCase("fader lock to draft suppresses mismatch until pickup", faderLockToDraftSuppressesMismatchUntilPickup) ? 0 : 1;
    failures += runCase("chain encoder stub leaves color on and effect state unchanged",
                        chainEncoderStubLeavesColorOnAndEffectStateUnchanged) ? 0 : 1;
    failures += runCase("fake chain encoder raw reader publishes movement and buttons", fakeChainEncoderRawReaderPublishesMovementAndButtons) ? 0 : 1;
    failures += runCase("chain encoder begin primes current position without publishing delta", chainEncoderBeginPrimesCurrentPositionWithoutPublishingDelta) ? 0 : 1;
    failures += runCase("chain encoder driver preserves slider input", chainEncoderDriverPreservesSliderInput) ? 0 : 1;
    failures += runCase("chain encoder single press classifies as effect toggle",
                        chainEncoderSinglePressClassifiesAsEffectToggle) ? 0 : 1;
    failures += runCase("chain encoder long press also classifies as effect toggle",
                        chainEncoderLongPressAlsoClassifiesAsEffectToggle) ? 0 : 1;
    failures += runCase("chain encoder sample factory keeps press edges exclusive", chainEncoderSampleFactoryKeepsPressEdgesExclusive) ? 0 : 1;
    failures += runCase("chain encoder sample factory preserves buttons when position missing", chainEncoderSampleFactoryPreservesButtonsWhenPositionMissing) ? 0 : 1;
    failures += runCase("chain encoder increment sample factory preserves movement and buttons", chainEncoderIncrementSampleFactoryPreservesMovementAndButtons) ? 0 : 1;
    failures += runCase("chain encoder IDs map physical LED5 to logical LED1", chainEncoderIdsMapPhysicalLed5ToLogicalLed1) ? 0 : 1;
    failures += runCase("chain key levels map upload and last switch to actions",
                        chainKeyLevelsMapUploadAndLastSwitchToActions) ? 0 : 1;
    failures += runCase("chain encoder disabled bus reports unavailable", chainEncoderDisabledBusReportsUnavailable) ? 0 : 1;
    failures += runCase("external OLED stub rejects display frame without IO cache", externalOledStubRejectsDisplayFrameWithoutIoCache) ? 0 : 1;
    failures += runCase("fake external OLED sink receives render plan and frame", fakeExternalOledSinkReceivesRenderPlanAndFrame) ? 0 : 1;
    failures += runCase("unchanged external OLED frame skips IO draw", unchangedExternalOledFrameSkipsIoDraw) ? 0 : 1;
    failures += runCase("unavailable external OLED sink does not cache frame without IO draw", unavailableExternalOledSinkDoesNotCacheFrameWithoutIoDraw) ? 0 : 1;
    failures += runCase("failed external OLED draw is retried instead of cached", failedExternalOledDrawIsRetriedInsteadOfCached) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
