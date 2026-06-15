#include "../sticks3-terminal/src/drivers/terminal_fader_rgb.h"
#include "../sticks3-terminal/src/drivers/terminal_fader_driver.h"
#include "../sticks3-terminal/src/drivers/terminal_pbhub_client.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>

namespace {

using terminal_pbhub_client::PbHubBus;
using terminal_pbhub_client::PbHubClient;

class FakePbHubBus : public PbHubBus {
   public:
    bool write(std::uint8_t address,
               std::uint8_t reg,
               const std::uint8_t* data,
               std::size_t length) override {
        ++writeCount;
        lastWriteAddress = address;
        lastWriteReg = reg;
        lastWriteLength = length;
        lastWrite.fill(0);
        for (std::size_t i = 0; i < length && i < lastWrite.size(); ++i) {
            lastWrite[i] = data[i];
        }
        return writeOk;
    }

    bool read(std::uint8_t address,
              std::uint8_t reg,
              std::uint8_t* data,
              std::size_t length) override {
        ++readCount;
        lastReadAddress = address;
        lastReadReg = reg;
        lastReadLength = length;
        if (!readOk) {
            return false;
        }
        for (std::size_t i = 0; i < length && i < readData.size(); ++i) {
            data[i] = readData[i];
        }
        return true;
    }

    bool writeOk = true;
    bool readOk = true;
    std::uint8_t lastWriteAddress = 0;
    std::uint8_t lastWriteReg = 0;
    std::size_t lastWriteLength = 0;
    std::array<std::uint8_t, 8> lastWrite = {};
    std::uint8_t lastReadAddress = 0;
    std::uint8_t lastReadReg = 0;
    std::size_t lastReadLength = 0;
    std::array<std::uint8_t, 8> readData = {};
    int writeCount = 0;
    int readCount = 0;
};

bool pbhubAnalogReadUsesOfficialLittleEndianRegisterShape() {
    FakePbHubBus bus;
    bus.readData[0] = 0x34;
    bus.readData[1] = 0x12;
    PbHubClient client(bus, 0x61);
    std::uint16_t raw = 0;

    return client.readAnalog(2, raw) &&
           raw == 0x1234 &&
           bus.readCount == 1 &&
           bus.lastReadAddress == 0x61 &&
           bus.lastReadReg == 0x66 &&
           bus.lastReadLength == 2;
}

bool pbhubFillLedColorUsesOfficialRegisterShape() {
    FakePbHubBus bus;
    PbHubClient client(bus, 0x61);

    return client.fillLedColor(4, 0, 14, 0x10, 0x20, 0x30) &&
           bus.writeCount == 1 &&
           bus.lastWriteAddress == 0x61 &&
           bus.lastWriteReg == 0x8A &&
           bus.lastWriteLength == 7 &&
           bus.lastWrite[0] == 0 &&
           bus.lastWrite[1] == 0 &&
           bus.lastWrite[2] == 14 &&
           bus.lastWrite[3] == 0 &&
           bus.lastWrite[4] == 0x10 &&
           bus.lastWrite[5] == 0x20 &&
           bus.lastWrite[6] == 0x30;
}

bool pbhubFaderRawReaderMapsLogicalLanesToPot1ThroughPot5Ports() {
    FakePbHubBus bus;
    PbHubClient client(bus, 0x61);
    terminal_fader_driver::PbHubFaderRawReader reader(client);

    if (!reader.begin()) {
        return false;
    }
    bus.readData[0] = 0xCD;
    bus.readData[1] = 0xAB;
    const int lane1Raw = reader.readRaw(0);
    const std::uint8_t lane1Reg = bus.lastReadReg;
    const int raw = reader.readRaw(4);

    return lane1Raw == 0xABCD &&
           lane1Reg == 0x86 &&
           raw == 0xABCD &&
           bus.lastReadReg == 0x46;
}

bool pbhubRgbSinkMirrorsColorBrightnessAndEffectMarker() {
    FakePbHubBus bus;
    PbHubClient client(bus, 0x61);
    terminal_fader_rgb::PbHubFaderRgbSink sink(client);
    terminal_setup::TerminalSetupState state;
    state.rotateHue(0, terminal_setup::ENCODER_DEGREES_PER_PALETTE_STEP);
    state.setBrightness(0, 50);
    state.setEffectLed(0, true);

    if (!sink.begin()) {
        return false;
    }
    const bool drawn = sink.draw(state);

    return drawn &&
           bus.writeCount >= 7 &&
           bus.lastWriteAddress == 0x61 &&
           bus.lastWriteReg == 0x89 &&
           bus.lastWriteLength == 5 &&
           bus.lastWrite[0] == 0 &&
           bus.lastWrite[1] == 0 &&
           bus.lastWrite[2] == 0x18 &&
           bus.lastWrite[3] == 0x18 &&
           bus.lastWrite[4] == 0x18;
}

bool pbhubRgbSinkRecoversAfterTransientWriteFailure() {
    FakePbHubBus bus;
    PbHubClient client(bus, 0x61);
    terminal_fader_rgb::PbHubFaderRgbSink sink(client);
    terminal_setup::TerminalSetupState state;

    if (!sink.begin()) {
        return false;
    }

    bus.writeOk = false;
    const bool failedDraw = sink.draw(state);
    const int writesAfterFailure = bus.writeCount;

    bus.writeOk = true;
    const bool recoveredDraw = sink.draw(state);

    return !failedDraw &&
           recoveredDraw &&
           bus.writeCount > writesAfterFailure;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("PbHUB analog read uses official little-endian register shape",
                        pbhubAnalogReadUsesOfficialLittleEndianRegisterShape) ? 0 : 1;
    failures += runCase("PbHUB fill LED color uses official register shape",
                        pbhubFillLedColorUsesOfficialRegisterShape) ? 0 : 1;
    failures += runCase("PbHUB fader raw reader maps logical lanes to Pot1 through Pot5 ports",
                        pbhubFaderRawReaderMapsLogicalLanesToPot1ThroughPot5Ports) ? 0 : 1;
    failures += runCase("PbHUB RGB sink mirrors color brightness and effect marker",
                        pbhubRgbSinkMirrorsColorBrightnessAndEffectMarker) ? 0 : 1;
    failures += runCase("PbHUB RGB sink recovers after transient write failure",
                        pbhubRgbSinkRecoversAfterTransientWriteFailure) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
