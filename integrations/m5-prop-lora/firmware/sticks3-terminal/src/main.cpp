#include <Arduino.h>
#include <M5Unified.h>
#include <Wire.h>

#include <array>
#include <cstdint>
#include <cstdio>
#include <string>

#include "drivers/terminal_chain_encoder_driver.h"
#include "drivers/terminal_external_oled.h"
#include "drivers/terminal_fader_driver.h"
#include "drivers/terminal_switch_driver.h"
#include "terminal_config.h"
#include "terminal_control_surface.h"
#include "terminal_external_display.h"
#include "terminal_app_logic.h"
#include "terminal_physical_tick.h"
#include "terminal_setup.h"
#include "terminal_switch_dispatch.h"
#include "terminal_switch_pipeline.h"
#include "terminal_switches.h"
#include "terminal_usb_link.h"

#ifndef ARDUINO_USB_MODE
#error "USB setup link requires USB CDC on boot"
#endif

#ifndef ARDUINO_USB_CDC_ON_BOOT
#error "USB setup link requires USB CDC on boot"
#endif

#if ARDUINO_USB_MODE != 1 || ARDUINO_USB_CDC_ON_BOOT != 1
#error "USB setup link requires USB CDC on boot"
#endif

#ifndef TERMINAL_G4_ADC_SMOKE
#define TERMINAL_G4_ADC_SMOKE 0
#endif

#ifndef TERMINAL_EXTERNAL_OLED_DRAW_SMOKE
#define TERMINAL_EXTERNAL_OLED_DRAW_SMOKE 0
#endif

#ifndef TERMINAL_CHAIN_UART_SMOKE
#define TERMINAL_CHAIN_UART_SMOKE 0
#endif

#ifndef TERMINAL_LIVE_DEBUG
#define TERMINAL_LIVE_DEBUG 0
#endif

#if TERMINAL_CHAIN_UART_SMOKE
#include <M5Chain.h>
#endif

#if (TERMINAL_G4_ADC_SMOKE + TERMINAL_EXTERNAL_OLED_DRAW_SMOKE + TERMINAL_CHAIN_UART_SMOKE) > 1
#error "G4 ADC, Chain UART, and external OLED draw smoke are separate hardware tests"
#endif

#if !TERMINAL_G4_ADC_SMOKE && !TERMINAL_EXTERNAL_OLED_DRAW_SMOKE && !TERMINAL_CHAIN_UART_SMOKE

namespace {

terminal_setup::TerminalSetupState g_setup;
terminal_control_surface::ControlSurface g_controls;
terminal_fader_driver::ConfiguredFaderDriver g_faders;
terminal_chain_encoder_driver::ConfiguredChainEncoderDriver g_encoders;
terminal_external_oled::ConfiguredExternalOledDriver g_externalOled;
terminal_switch_driver::SwitchDriver g_switchDriver;
terminal_switch_pipeline::SwitchPipeline g_switchPipeline(terminal_config::SWITCH_DEBOUNCE_MS);
static_assert(terminal_config::TERMINAL_LANE_COUNT == terminal_setup::LANE_COUNT,
              "terminal lane config must match setup state");
std::uint32_t g_lastDrawMs = 0;
std::uint32_t g_lastI2cScanMs = 0;
terminal_external_display::DisplayFrame g_externalFrame;
terminal_usb_link::UsbSetupLink g_usbLink(terminal_config::USB_LINE_MAX);

std::uint16_t statusBackground(terminal_setup::Status status) {
    switch (status) {
        case terminal_setup::Status::Uploaded:
            return TFT_DARKGREEN;
        case terminal_setup::Status::Problem:
            return TFT_RED;
        case terminal_setup::Status::Uploading:
            return TFT_ORANGE;
        case terminal_setup::Status::SimFire:
            return TFT_PURPLE;
        case terminal_setup::Status::Dirty:
            return TFT_NAVY;
        case terminal_setup::Status::Ready:
            return TFT_BLACK;
    }
    return TFT_BLACK;
}

void drawStatusPanel() {
    // Secondary status examples: NAHRANO on accepted upload, PROBLEM on rollback.
    M5.Display.fillScreen(statusBackground(g_setup.status()));
    M5.Display.setTextColor(TFT_WHITE, statusBackground(g_setup.status()));
    M5.Display.setTextDatum(top_left);
    M5.Display.setTextSize(2);
    M5.Display.setCursor(6, 8);
    M5.Display.println("TERMINAL");
    M5.Display.setTextSize(3);
    M5.Display.setCursor(6, 36);
    M5.Display.println(g_setup.statusText());

    g_lastDrawMs = millis();
}

bool renderExternalDisplay() {
    const terminal_external_display::DisplayFrame nextFrame =
        terminal_external_display::makeFrame(g_setup);
    if (!g_externalOled.draw(nextFrame)) {
        return false;
    }
    g_externalFrame = nextFrame;
    return true;
}

struct I2cScanResult {
    std::uint8_t found = 0;
    std::uint8_t downstreamFound = 0;
    bool expectedFound = false;
};

I2cScanResult scanI2cBus(TwoWire& bus, const char* prefix, std::uint8_t expectedAddress) {
    I2cScanResult result;
    for (std::uint8_t address = 0x03; address <= 0x77; ++address) {
        bus.beginTransmission(address);
        const std::uint8_t error = bus.endTransmission();
        if (error == 0) {
            ++result.found;
            if (address == expectedAddress) {
                result.expectedFound = true;
            } else {
                ++result.downstreamFound;
            }
            Serial.printf("%s FOUND 0x%02X %s\n",
                          prefix,
                          address,
                          address == expectedAddress ? "MUX" : "DOWNSTREAM");
        }
        delay(2);
    }
    return result;
}

void selectPahubChannel(TwoWire& bus, std::uint8_t muxAddress, std::uint8_t channel) {
    bus.beginTransmission(muxAddress);
    bus.write(static_cast<std::uint8_t>(1U << channel));
    const std::uint8_t error = bus.endTransmission();
    Serial.printf("OLED_I2C_SCAN_PAHUB CHANNEL %u SELECT err=%u\n", channel, error);
}

void deselectPahub(TwoWire& bus, std::uint8_t muxAddress) {
    bus.beginTransmission(muxAddress);
    bus.write(static_cast<std::uint8_t>(0));
    const std::uint8_t error = bus.endTransmission();
    Serial.printf("OLED_I2C_SCAN_PAHUB DESELECT err=%u\n", error);
}

void runOledI2cScanPass(TwoWire& bus, std::uint32_t frequency) {
    bus.setClock(frequency);
    Serial.printf("OLED_I2C_SCAN START sda=%d scl=%d port=%d freq=%u expected=0x%02X\n",
                  terminal_config::EXTERNAL_OLED_SDA_PIN,
                  terminal_config::EXTERNAL_OLED_SCL_PIN,
                  terminal_config::EXTERNAL_OLED_I2C_PORT,
                  frequency,
                  terminal_config::EXTERNAL_OLED_I2C_ADDRESS);

    const I2cScanResult rootScan =
        scanI2cBus(bus, "OLED_I2C_SCAN", terminal_config::EXTERNAL_OLED_I2C_ADDRESS);
    Serial.printf("OLED_I2C_SCAN EXPECTED_FOUND %u\n", rootScan.expectedFound ? 1U : 0U);
    Serial.printf("OLED_I2C_SCAN DONE count=%u downstream=%u expected=0x%02X freq=%u\n",
                  rootScan.found,
                  rootScan.downstreamFound,
                  terminal_config::EXTERNAL_OLED_I2C_ADDRESS,
                  frequency);
    if (terminal_config::I2C_SCAN_PAHUB_CHANNELS && rootScan.expectedFound) {
        Serial.printf("OLED_I2C_SCAN_PAHUB START address=0x%02X ports=%u freq=%u\n",
                      terminal_config::EXTERNAL_OLED_I2C_ADDRESS,
                      terminal_hardware_topology::PAHUB_PORT_COUNT,
                      frequency);
        for (std::uint8_t channel = 0; channel < terminal_hardware_topology::PAHUB_PORT_COUNT; ++channel) {
            char prefix[40] = {};
            snprintf(prefix, sizeof(prefix), "OLED_I2C_SCAN_PAHUB CHANNEL %u", channel);
            selectPahubChannel(bus, terminal_config::EXTERNAL_OLED_I2C_ADDRESS, channel);
            const I2cScanResult channelScan =
                scanI2cBus(bus, prefix, terminal_config::EXTERNAL_OLED_I2C_ADDRESS);
            Serial.printf("OLED_I2C_SCAN_PAHUB CHANNEL %u DONE count=%u downstream=%u\n",
                          channel,
                          channelScan.found,
                          channelScan.downstreamFound);
            if (channelScan.downstreamFound == 0) {
                Serial.printf("OLED_I2C_SCAN_PAHUB CHANNEL %u DOWNSTREAM_EMPTY\n", channel);
            }
        }
        deselectPahub(bus, terminal_config::EXTERNAL_OLED_I2C_ADDRESS);
    }
}

void runOledI2cScanSmoke() {
    if (!terminal_config::EXTERNAL_OLED_I2C_SCAN_SMOKE) {
        return;
    }

    delay(250);
    TwoWire& bus = terminal_config::EXTERNAL_OLED_I2C_PORT == 1 ? Wire1 : Wire;
    bus.begin(terminal_config::EXTERNAL_OLED_SDA_PIN,
              terminal_config::EXTERNAL_OLED_SCL_PIN,
              terminal_config::EXTERNAL_OLED_I2C_FREQ);

    runOledI2cScanPass(bus, terminal_config::EXTERNAL_OLED_I2C_FREQ);
    if (terminal_config::EXTERNAL_OLED_I2C_FREQ != 100000) {
        runOledI2cScanPass(bus, 100000);
    }
    Serial.flush();
}

void pollOledI2cScanSmoke() {
    if (!terminal_config::EXTERNAL_OLED_I2C_SCAN_SMOKE) {
        return;
    }
    if (millis() - g_lastI2cScanMs < 3000) {
        return;
    }
    g_lastI2cScanMs = millis();
    runOledI2cScanSmoke();
}

bool renderExternalDisplayIfChanged() {
    const terminal_external_display::DisplayFrame nextFrame =
        terminal_external_display::makeFrame(g_setup);
    if (nextFrame == g_externalFrame) {
        return false;
    }
    if (!g_externalOled.draw(nextFrame)) {
        return false;
    }
    g_externalFrame = nextFrame;
    return true;
}

void logLiveDebugSnapshot(const terminal_control_surface::ControlSnapshot& snapshot) {
#if TERMINAL_LIVE_DEBUG
    bool hasInput = false;
    for (std::size_t lane = 0; lane < snapshot.lanes.size(); ++lane) {
        const terminal_control_surface::LaneInput& input = snapshot.lanes[lane];
        if (input.sliderPercent != terminal_control_surface::SLIDER_UNCHANGED ||
            input.encoderDelta != 0 ||
            input.encoderPressed ||
            input.effectPressed) {
            hasInput = true;
            break;
        }
    }
    if (!hasInput) {
        return;
    }

    Serial.print("TERMINAL_LIVE_INPUT");
    for (std::size_t lane = 0; lane < snapshot.lanes.size(); ++lane) {
        const terminal_control_surface::LaneInput& input = snapshot.lanes[lane];
        if (input.sliderPercent == terminal_control_surface::SLIDER_UNCHANGED &&
            input.encoderDelta == 0 &&
            !input.encoderPressed &&
            !input.effectPressed) {
            continue;
        }
        Serial.printf(" L%u:s=%d,d=%d,p=%u,e=%u",
                      static_cast<unsigned>(lane + 1U),
                      input.sliderPercent,
                      input.encoderDelta,
                      input.encoderPressed ? 1U : 0U,
                      input.effectPressed ? 1U : 0U);
    }
    Serial.println();
    Serial.flush();
#else
    (void)snapshot;
#endif
}

void drainUsbSetupInput() {
    while (Serial.available() > 0) {
        Serial.read();
    }
}

bool uploadInFlight();

terminal_switches::SwitchSnapshot readSwitches() {
    terminal_switches::SwitchSnapshot snapshot = g_switchDriver.read();
    g_encoders.readSwitches(snapshot);
    return snapshot;
}

void primeSwitches() {
    g_switchPipeline.prime(readSwitches(), millis());
}

void performTerminalAction(const terminal_app_logic::TerminalAction& action) {
    if (action.drainUsbInput) {
        drainUsbSetupInput();
    }
    if (action.sendLine) {
        Serial.println(action.line.c_str());
    }
    if (action.lockFadersToDraft) {
        g_faders.lockToDraft(g_setup);
    }
    if (action.redraw) {
        renderExternalDisplay();
        drawStatusPanel();
    }
}

void primeDirectControls() {
    terminal_control_surface::ControlSnapshot snapshot;
    g_faders.read(snapshot);
    g_controls.primeEdges(snapshot);
}

void requestUpload() {
    if (!terminal_app_logic::canStartUpload(g_setup, g_usbLink)) {
        return;
    }
    drainUsbSetupInput();
    performTerminalAction(
        terminal_app_logic::startUploadAfterUsbDrain(g_setup, g_usbLink, millis(), terminal_config::UPLOAD_ACK_TIMEOUT_MS));
}

void requestSimFire() {
    if (uploadInFlight()) {
        return;
    }
    performTerminalAction(terminal_app_logic::requestSimFire(
        g_setup, g_usbLink, millis(), terminal_config::UPLOAD_ACK_TIMEOUT_MS));
}

void pollSwitches() {
    const terminal_switch_dispatch::SwitchAction action =
        g_switchPipeline.update(readSwitches(), millis(), uploadInFlight());
    switch (action) {
        case terminal_switch_dispatch::SwitchAction::Upload:
            requestUpload();
            return;
        case terminal_switch_dispatch::SwitchAction::SimFire:
            requestSimFire();
            return;
        case terminal_switch_dispatch::SwitchAction::None:
            return;
    }
}

void pollDirectControls() {
    terminal_control_surface::ControlSnapshot snapshot;
    g_faders.read(snapshot);
    g_encoders.read(snapshot);
    g_controls.apply(snapshot, g_setup);
    renderExternalDisplayIfChanged();
}

void pollPhysicalTick() {
    terminal_control_surface::ControlSnapshot snapshot;
    if (!uploadInFlight()) {
        g_faders.read(snapshot);
        g_encoders.read(snapshot);
        logLiveDebugSnapshot(snapshot);
    }
    const std::uint32_t nowMs = millis();
    const terminal_switch_dispatch::SwitchAction action =
        g_switchPipeline.update(readSwitches(), nowMs, uploadInFlight());
    const terminal_physical_tick::PhysicalTickResult result =
        terminal_physical_tick::runPhysicalTick(
            snapshot,
            action,
            g_setup,
            g_controls,
            g_usbLink,
            g_externalFrame,
            nowMs,
            terminal_config::UPLOAD_ACK_TIMEOUT_MS,
            []() { drainUsbSetupInput(); });
    if (result.frameChanged && !result.action.redraw) {
        if (!g_externalOled.draw(result.frame)) {
            g_externalFrame = {};
        }
    }
    performTerminalAction(result.action);
}

bool uploadInFlight() {
    return terminal_app_logic::uploadInFlight(g_setup, g_usbLink);
}

void handleUsbEvent(terminal_usb_link::UploadEvent event) {
    const terminal_app_logic::TerminalAction action =
        terminal_app_logic::handleUploadEvent(g_setup, g_usbLink, event);
    performTerminalAction(action);
    if (action.redraw) {
        primeDirectControls();
    }
}

void pollUsbSetupAcks() {
    while (Serial.available() > 0) {
        const char ch = static_cast<char>(Serial.read());
        handleUsbEvent(g_usbLink.push(ch));
    }
}

void pollUploadTimeout() {
    handleUsbEvent(g_usbLink.pollTimeout(millis()));
}

}  // namespace

void setup() {
    auto cfg = M5.config();
    M5.begin(cfg);
    M5.Display.setRotation(1);
    M5.Display.setBrightness(160);
    Serial.begin(terminal_config::USB_SETUP_BAUD);
    runOledI2cScanSmoke();
    g_lastI2cScanMs = millis();
    const bool fadersAvailable = g_faders.begin();
    const bool encodersAvailable = g_encoders.begin();
    const bool externalOledAvailable = g_externalOled.begin();
    g_switchDriver.begin();
#if TERMINAL_LIVE_DEBUG
    Serial.printf("TERMINAL_LIVE_DEBUG START faders=%u chain=%u oled=%u switch_pins=%d,%d\n",
                  fadersAvailable ? 1U : 0U,
                  encodersAvailable ? 1U : 0U,
                  externalOledAvailable ? 1U : 0U,
                  terminal_config::UPLOAD_SWITCH_PIN,
                  terminal_config::SIM_FIRE_SWITCH_PIN);
    Serial.flush();
#endif
    primeSwitches();
    primeDirectControls();
    renderExternalDisplay();
    drawStatusPanel();
}

void loop() {
    M5.update();
    pollPhysicalTick();
    pollUploadTimeout();
    pollUsbSetupAcks();
    pollOledI2cScanSmoke();
    if (millis() - g_lastDrawMs > terminal_config::STATUS_REDRAW_MS) {
        renderExternalDisplayIfChanged();
        drawStatusPanel();
    }
    delay(5);
}

#elif TERMINAL_CHAIN_UART_SMOKE

namespace {

constexpr std::array<std::uint8_t, 5> CHAIN_SMOKE_ENCODER_IDS = {1, 2, 3, 4, 5};
constexpr std::array<std::uint8_t, 2> CHAIN_SMOKE_KEY_IDS = {6, 7};
constexpr std::uint32_t CHAIN_SMOKE_POLL_MS = 100;
constexpr std::uint32_t CHAIN_SMOKE_HEARTBEAT_POLLS = 10;
constexpr std::uint32_t CHAIN_SMOKE_QUERY_TIMEOUT_MS = 20;

Chain g_chain;
std::uint32_t g_lastChainPollMs = 0;
std::uint32_t g_chainPollCount = 0;
bool g_chainConnected = false;
std::array<std::int16_t, CHAIN_SMOKE_ENCODER_IDS.size()> g_lastEncoderValue = {};
std::array<std::int16_t, CHAIN_SMOKE_ENCODER_IDS.size()> g_lastEncoderInc = {};
std::array<std::uint8_t, CHAIN_SMOKE_ENCODER_IDS.size()> g_lastEncoderButton = {};
std::array<std::uint8_t, CHAIN_SMOKE_KEY_IDS.size()> g_lastKeyButton = {};
std::array<bool, CHAIN_SMOKE_ENCODER_IDS.size()> g_encoderSeen = {};
std::array<bool, CHAIN_SMOKE_KEY_IDS.size()> g_keySeen = {};

const char* deviceTypeName(chain_device_type_t type) {
    switch (type) {
        case CHAIN_ENCODER_TYPE_CODE:
            return "ENCODER";
        case CHAIN_KEY_TYPE_CODE:
            return "KEY";
        case UNIT_CHAIN_BUS_TYPE_CODE:
            return "UNIT_CHAIN_BUS";
        default:
            return "OTHER";
    }
}

const char* pressName(chain_button_press_type_t pressType) {
    switch (pressType) {
        case CHAIN_BUTTON_PRESS_SINGLE:
            return "single";
        case CHAIN_BUTTON_PRESS_DOUBLE:
            return "double";
        case CHAIN_BUTTON_PRESS_LONG:
            return "long";
    }
    return "unknown";
}

bool selectChainPahubChannel() {
    if (!terminal_config::CHAIN_UART_SELECT_PAHUB) {
        Serial.println("CHAIN_UART_SMOKE SELECT_PAHUB skipped");
        return true;
    }

    Wire.begin(
        terminal_config::CHAIN_PAHUB_SDA_PIN,
        terminal_config::CHAIN_PAHUB_SCL_PIN,
        100000);
    Wire.beginTransmission(static_cast<std::uint8_t>(terminal_config::CHAIN_PAHUB_ADDRESS));
    Wire.write(static_cast<std::uint8_t>(1U << terminal_config::CHAIN_PAHUB_CHANNEL));
    const std::uint8_t error = Wire.endTransmission();
    Serial.printf("CHAIN_UART_SMOKE SELECT_PAHUB address=0x%02X channel=%d err=%u sda=%d scl=%d\n",
                  terminal_config::CHAIN_PAHUB_ADDRESS,
                  terminal_config::CHAIN_PAHUB_CHANNEL,
                  error,
                  terminal_config::CHAIN_PAHUB_SDA_PIN,
                  terminal_config::CHAIN_PAHUB_SCL_PIN);
    Wire.end();
    delay(10);
    return error == 0;
}

bool beginChainAndProbe(int rxPin, int txPin, bool swapped) {
    if (swapped) {
        Serial.printf("CHAIN_UART_SMOKE TRY_SWAPPED rx=%d tx=%d\n", rxPin, txPin);
    }
    Serial1.end();
    delay(10);
    g_chain.begin(
        &Serial1,
        terminal_config::CHAIN_BAUD,
        rxPin,
        txPin);
    const bool connected = g_chain.isDeviceConnected(3, 50);
    if (swapped) {
        Serial.println(connected ? "CHAIN_UART_SMOKE CONNECTED_SWAPPED" : "CHAIN_UART_SMOKE NO_DEVICE_SWAPPED");
    } else {
        Serial.println(connected ? "CHAIN_UART_SMOKE CONNECTED" : "CHAIN_UART_SMOKE NO_DEVICE");
    }
    return connected;
}

void printDeviceSummary() {
    std::uint16_t deviceCount = 0;
    const chain_status_t countStatus =
        g_chain.getDeviceNum(&deviceCount, 100);
    Serial.printf("CHAIN_UART_SMOKE DEVICE_COUNT status=%d count=%u\n",
                  static_cast<int>(countStatus),
                  deviceCount);
    if (countStatus != CHAIN_OK || deviceCount == 0) {
        return;
    }

    static device_info_t deviceStorage[16] = {};
    device_list_t devices = {
        deviceCount > 16 ? static_cast<std::uint16_t>(16) : deviceCount,
        deviceStorage};
    const bool listOk = g_chain.getDeviceList(&devices, 200);
    Serial.printf("CHAIN_UART_SMOKE DEVICE_LIST ok=%u count=%u\n",
                  listOk ? 1U : 0U,
                  devices.count);
    if (!listOk) {
        return;
    }
    for (std::uint16_t index = 0; index < devices.count; ++index) {
        Serial.printf("CHAIN_UART_SMOKE DEVICE index=%u id=%u type=%u name=%s\n",
                      index,
                      devices.devices[index].id,
                      static_cast<unsigned>(devices.devices[index].device_type),
                      deviceTypeName(devices.devices[index].device_type));
    }
}

void configureChainControls() {
    for (std::uint8_t id : CHAIN_SMOKE_ENCODER_IDS) {
        std::uint8_t directOperation = 0;
        const chain_status_t directStatus =
            g_chain.setEncoderABDirect(id, ENCODER_AB, &directOperation, CHAIN_SAVE_FLASH_DISABLE, 20);
        encoder_ab_t direct = ENCODER_AB;
        const chain_status_t directReadStatus =
            g_chain.getEncoderABDirect(id, &direct, 20);
        std::uint8_t resetOperation = 0;
        const chain_status_t resetStatus =
            g_chain.resetEncoderIncValue(id, &resetOperation, 20);
        std::uint8_t triggerOperation = 0;
        const chain_status_t triggerStatus =
            g_chain.setEncoderButtonTriggerInterval(
                id,
                BUTTON_DOUBLE_CLICK_TIME_200MS,
                BUTTON_LONG_PRESS_TIME_3S,
                &triggerOperation,
                20);
        std::uint8_t modeOperation = 0;
        const chain_status_t modeStatus =
            g_chain.setEncoderButtonMode(id, CHAIN_BUTTON_REPORT_MODE, &modeOperation, 20);
        Serial.printf("CHAIN_UART_SMOKE CONFIG_ENC id=%u direct_status=%d direct_op=%u direct_read_status=%d direct=%d reset_inc_status=%d reset_inc_op=%u trigger_status=%d trigger_op=%u mode_status=%d mode_op=%u\n",
                      id,
                      static_cast<int>(directStatus),
                      directOperation,
                      static_cast<int>(directReadStatus),
                      static_cast<int>(direct),
                      static_cast<int>(resetStatus),
                      resetOperation,
                      static_cast<int>(triggerStatus),
                      triggerOperation,
                      static_cast<int>(modeStatus),
                      modeOperation);
    }

    for (std::uint8_t id : CHAIN_SMOKE_KEY_IDS) {
        std::uint8_t triggerOperation = 0;
        const chain_status_t triggerStatus =
            g_chain.setKeyButtonTriggerInterval(
                id,
                BUTTON_DOUBLE_CLICK_TIME_200MS,
                BUTTON_LONG_PRESS_TIME_3S,
                &triggerOperation,
                20);
        std::uint8_t modeOperation = 0;
        const chain_status_t modeStatus =
            g_chain.setKeyButtonMode(id, CHAIN_BUTTON_REPORT_MODE, &modeOperation, 20);
        Serial.printf("CHAIN_UART_SMOKE CONFIG_KEY id=%u trigger_status=%d trigger_op=%u mode_status=%d mode_op=%u\n",
                      id,
                      static_cast<int>(triggerStatus),
                      triggerOperation,
                      static_cast<int>(modeStatus),
                      modeOperation);
    }
}

std::size_t encoderIndexForId(std::uint8_t id) {
    for (std::size_t index = 0; index < CHAIN_SMOKE_ENCODER_IDS.size(); ++index) {
        if (CHAIN_SMOKE_ENCODER_IDS[index] == id) {
            return index;
        }
    }
    return CHAIN_SMOKE_ENCODER_IDS.size();
}

std::size_t keyIndexForId(std::uint8_t id) {
    for (std::size_t index = 0; index < CHAIN_SMOKE_KEY_IDS.size(); ++index) {
        if (CHAIN_SMOKE_KEY_IDS[index] == id) {
            return index;
        }
    }
    return CHAIN_SMOKE_KEY_IDS.size();
}

bool pollChainEncoder(std::uint8_t id, bool heartbeat) {
    std::int16_t value = 0;
    const chain_status_t valueStatus =
        g_chain.getEncoderValue(id, &value, CHAIN_SMOKE_QUERY_TIMEOUT_MS);
    std::int16_t increment = 0;
    const chain_status_t incrementStatus =
        g_chain.getEncoderIncValue(id, &increment, CHAIN_SMOKE_QUERY_TIMEOUT_MS);
    std::uint8_t button = 0;
    const chain_status_t buttonStatus =
        g_chain.getEncoderButtonStatus(id, &button, CHAIN_SMOKE_QUERY_TIMEOUT_MS);
    const std::size_t index = encoderIndexForId(id);
    const bool known = index < g_encoderSeen.size();
    const bool changed = known &&
                         (!g_encoderSeen[index] ||
                          g_lastEncoderValue[index] != value ||
                          g_lastEncoderInc[index] != increment ||
                          g_lastEncoderButton[index] != button);
    if (heartbeat || changed || valueStatus != CHAIN_OK || incrementStatus != CHAIN_OK || buttonStatus != CHAIN_OK) {
        Serial.printf("CHAIN_UART_SMOKE %s id=%u value_status=%d value=%d inc_status=%d inc=%d button_status=%d button=%u\n",
                  changed ? "ENC_CHANGE" : "ENC",
                  id,
                  static_cast<int>(valueStatus),
                  value,
                  static_cast<int>(incrementStatus),
                  increment,
                  static_cast<int>(buttonStatus),
                  button);
    }
    if (known) {
        g_encoderSeen[index] = true;
        g_lastEncoderValue[index] = value;
        g_lastEncoderInc[index] = increment;
        g_lastEncoderButton[index] = button;
    }

    chain_button_press_type_t pressType = CHAIN_BUTTON_PRESS_SINGLE;
    while (g_chain.getEncoderButtonPressStatus(id, &pressType)) {
        Serial.printf("CHAIN_UART_SMOKE ENC_PRESS id=%u type=%s raw=%d\n",
                      id,
                      pressName(pressType),
                      static_cast<int>(pressType));
    }
    return changed;
}

bool pollChainKey(std::uint8_t id, bool heartbeat) {
    std::uint8_t button = 0;
    const chain_status_t buttonStatus =
        g_chain.getKeyButtonStatus(id, &button, CHAIN_SMOKE_QUERY_TIMEOUT_MS);
    const std::size_t index = keyIndexForId(id);
    const bool known = index < g_keySeen.size();
    const bool changed = known && (!g_keySeen[index] || g_lastKeyButton[index] != button);
    if (heartbeat || changed || buttonStatus != CHAIN_OK) {
        Serial.printf("CHAIN_UART_SMOKE %s id=%u button_status=%d button=%u\n",
                  changed ? "KEY_CHANGE" : "KEY",
                  id,
                  static_cast<int>(buttonStatus),
                  button);
    }
    if (known) {
        g_keySeen[index] = true;
        g_lastKeyButton[index] = button;
    }

    chain_button_press_type_t pressType = CHAIN_BUTTON_PRESS_SINGLE;
    while (g_chain.getKeyButtonPressStatus(id, &pressType)) {
        Serial.printf("CHAIN_UART_SMOKE KEY_PRESS id=%u type=%s raw=%d\n",
                      id,
                      pressName(pressType),
                      static_cast<int>(pressType));
    }
    return changed;
}

void pollChain() {
    ++g_chainPollCount;
    const bool heartbeat = g_chainPollCount == 1 ||
                           (g_chainPollCount % CHAIN_SMOKE_HEARTBEAT_POLLS) == 0;
    bool changed = false;
    if (heartbeat) {
        Serial.printf("CHAIN_UART_SMOKE POLL count=%lu connected=%u\n",
                      static_cast<unsigned long>(g_chainPollCount),
                      g_chainConnected ? 1U : 0U);
    }
    for (std::uint8_t id : CHAIN_SMOKE_ENCODER_IDS) {
        changed = pollChainEncoder(id, heartbeat) || changed;
    }
    for (std::uint8_t id : CHAIN_SMOKE_KEY_IDS) {
        changed = pollChainKey(id, heartbeat) || changed;
    }
    if (changed && !heartbeat) {
        Serial.printf("CHAIN_UART_SMOKE POLL_CHANGE count=%lu\n",
                      static_cast<unsigned long>(g_chainPollCount));
    }
    Serial.flush();
}

}  // namespace

void setup() {
    Serial.begin(terminal_config::USB_SETUP_BAUD);
    const std::uint32_t startMs = millis();
    while (!Serial && millis() - startMs < 3000) {
        delay(10);
    }

    auto cfg = M5.config();
    M5.begin(cfg);
    M5.Display.setRotation(1);
    M5.Display.fillScreen(TFT_BLACK);
    M5.Display.setTextColor(TFT_WHITE, TFT_BLACK);
    M5.Display.setTextSize(2);
    M5.Display.setCursor(4, 8);
    M5.Display.println("CHAIN UART");
    M5.Display.setCursor(4, 34);
    M5.Display.println("SMOKE");

    Serial.printf("CHAIN_UART_SMOKE START rx=%d tx=%d baud=%d expected_encoders=5 expected_keys=2\n",
                  terminal_config::CHAIN_RX_PIN,
                  terminal_config::CHAIN_TX_PIN,
                  terminal_config::CHAIN_BAUD);
    const bool pahubSelected = selectChainPahubChannel();
    if (!pahubSelected) {
        Serial.println("CHAIN_UART_SMOKE ERROR pahub_select_failed");
    }
    g_chainConnected =
        beginChainAndProbe(terminal_config::CHAIN_RX_PIN, terminal_config::CHAIN_TX_PIN, false);
    if (!g_chainConnected) {
        g_chainConnected =
            beginChainAndProbe(terminal_config::CHAIN_TX_PIN, terminal_config::CHAIN_RX_PIN, true);
    }
    printDeviceSummary();
    if (g_chainConnected) {
        configureChainControls();
    }
    pollChain();
    g_lastChainPollMs = millis();
}

void loop() {
    M5.update();
    if (millis() - g_lastChainPollMs >= CHAIN_SMOKE_POLL_MS) {
        g_lastChainPollMs = millis();
        pollChain();
    }
    delay(5);
}

#elif TERMINAL_EXTERNAL_OLED_DRAW_SMOKE

namespace {

constexpr std::uint8_t OLED_DRAW_WIDTH = 128;
constexpr std::uint8_t OLED_DRAW_PAGES = 8;
constexpr std::uint8_t OLED_DRAW_CHUNK = 16;

std::uint32_t g_lastOledDrawMs = 0;
std::uint32_t g_oledDrawCount = 0;
bool g_oledAllOnBootShown = false;

bool writeI2cBytes(std::uint8_t address, const std::uint8_t* data, std::size_t size) {
    Wire.beginTransmission(address);
    Wire.write(data, size);
    return Wire.endTransmission() == 0;
}

bool sendOledCommands(const std::uint8_t* commands, std::size_t size) {
    constexpr std::uint8_t CONTROL_COMMAND = 0x00;
    std::uint8_t packet[OLED_DRAW_CHUNK + 1] = {CONTROL_COMMAND};
    std::size_t offset = 0;
    while (offset < size) {
        const std::size_t chunk = size - offset > OLED_DRAW_CHUNK ? OLED_DRAW_CHUNK : size - offset;
        for (std::size_t i = 0; i < chunk; ++i) {
            packet[i + 1] = commands[offset + i];
        }
        if (!writeI2cBytes(static_cast<std::uint8_t>(terminal_config::EXTERNAL_OLED_I2C_ADDRESS), packet, chunk + 1)) {
            return false;
        }
        offset += chunk;
    }
    return true;
}

bool sendOledData(const std::uint8_t* data, std::size_t size) {
    constexpr std::uint8_t CONTROL_DATA = 0x40;
    std::uint8_t packet[OLED_DRAW_CHUNK + 1] = {CONTROL_DATA};
    std::size_t offset = 0;
    while (offset < size) {
        const std::size_t chunk = size - offset > OLED_DRAW_CHUNK ? OLED_DRAW_CHUNK : size - offset;
        for (std::size_t i = 0; i < chunk; ++i) {
            packet[i + 1] = data[offset + i];
        }
        if (!writeI2cBytes(static_cast<std::uint8_t>(terminal_config::EXTERNAL_OLED_I2C_ADDRESS), packet, chunk + 1)) {
            return false;
        }
        offset += chunk;
    }
    return true;
}

std::uint8_t selectOledPahubChannel() {
    Wire.beginTransmission(static_cast<std::uint8_t>(terminal_config::EXTERNAL_OLED_PAHUB_ADDRESS));
    Wire.write(static_cast<std::uint8_t>(1U << terminal_config::EXTERNAL_OLED_PAHUB_CHANNEL));
    const std::uint8_t error = Wire.endTransmission();
    Serial.printf("OLED_DRAW_SMOKE SELECT_PAHUB address=0x%02X channel=%u err=%u\n",
                  terminal_config::EXTERNAL_OLED_PAHUB_ADDRESS,
                  terminal_config::EXTERNAL_OLED_PAHUB_CHANNEL,
                  error);
    return error;
}

const std::array<std::uint8_t, 5>& glyphFor(char ch) {
    static const std::array<std::uint8_t, 5> space{0x00, 0x00, 0x00, 0x00, 0x00};
    static const std::array<std::uint8_t, 5> digit0{0x3E, 0x51, 0x49, 0x45, 0x3E};
    static const std::array<std::uint8_t, 5> digit2{0x42, 0x61, 0x51, 0x49, 0x46};
    static const std::array<std::uint8_t, 5> digit3{0x21, 0x41, 0x45, 0x4B, 0x31};
    static const std::array<std::uint8_t, 5> a{0x7E, 0x11, 0x11, 0x11, 0x7E};
    static const std::array<std::uint8_t, 5> c{0x3E, 0x41, 0x41, 0x41, 0x22};
    static const std::array<std::uint8_t, 5> d{0x7F, 0x41, 0x41, 0x22, 0x1C};
    static const std::array<std::uint8_t, 5> e{0x7F, 0x49, 0x49, 0x49, 0x41};
    static const std::array<std::uint8_t, 5> g{0x3E, 0x41, 0x49, 0x49, 0x7A};
    static const std::array<std::uint8_t, 5> i{0x00, 0x41, 0x7F, 0x41, 0x00};
    static const std::array<std::uint8_t, 5> k{0x7F, 0x08, 0x14, 0x22, 0x41};
    static const std::array<std::uint8_t, 5> l{0x7F, 0x40, 0x40, 0x40, 0x40};
    static const std::array<std::uint8_t, 5> m{0x7F, 0x02, 0x0C, 0x02, 0x7F};
    static const std::array<std::uint8_t, 5> n{0x7F, 0x04, 0x08, 0x10, 0x7F};
    static const std::array<std::uint8_t, 5> o{0x3E, 0x41, 0x41, 0x41, 0x3E};
    static const std::array<std::uint8_t, 5> p{0x7F, 0x09, 0x09, 0x09, 0x06};
    static const std::array<std::uint8_t, 5> r{0x7F, 0x09, 0x19, 0x29, 0x46};
    static const std::array<std::uint8_t, 5> s{0x46, 0x49, 0x49, 0x49, 0x31};
    static const std::array<std::uint8_t, 5> t{0x01, 0x01, 0x7F, 0x01, 0x01};
    static const std::array<std::uint8_t, 5> v{0x1F, 0x20, 0x40, 0x20, 0x1F};
    static const std::array<std::uint8_t, 5> x{0x63, 0x14, 0x08, 0x14, 0x63};
    switch (ch) {
        case '0':
            return digit0;
        case '2':
            return digit2;
        case '3':
            return digit3;
        case 'A':
            return a;
        case 'C':
            return c;
        case 'D':
            return d;
        case 'E':
            return e;
        case 'G':
            return g;
        case 'I':
            return i;
        case 'K':
            return k;
        case 'L':
            return l;
        case 'M':
            return m;
        case 'N':
            return n;
        case 'O':
            return o;
        case 'P':
            return p;
        case 'R':
            return r;
        case 'S':
            return s;
        case 'T':
            return t;
        case 'V':
            return v;
        case 'X':
            return x;
        default:
            return space;
    }
}

void drawTextIntoPage(std::array<std::uint8_t, OLED_DRAW_WIDTH>& page, const char* text) {
    std::size_t column = 0;
    for (const char* cursor = text; *cursor != '\0' && column + 6 < page.size(); ++cursor) {
        const std::array<std::uint8_t, 5>& glyph = glyphFor(*cursor);
        for (std::uint8_t i = 0; i < glyph.size(); ++i) {
            page[column++] = glyph[i];
        }
        page[column++] = 0x00;
    }
}

bool writeOledPage(std::uint8_t oledPage, const char* text) {
    const std::uint8_t setPage[] = {
        0x21,
        0x00,
        0x7F,
        0x22,
        oledPage,
        oledPage,
    };
    if (!sendOledCommands(setPage, sizeof(setPage))) {
        return false;
    }
    std::array<std::uint8_t, OLED_DRAW_WIDTH> page = {};
    drawTextIntoPage(page, text);
    return sendOledData(page.data(), page.size());
}

bool clearOled() {
    for (std::uint8_t page = 0; page < OLED_DRAW_PAGES; ++page) {
        if (!writeOledPage(page, "")) {
            return false;
        }
    }
    return true;
}

bool initOledSsd1309Laskakit() {
    // LaskaKit 2.42" 128x64 I2C OLED is specified as SSD1309.
    // This mirrors the local LovyanGFX SSD1306/SSD1309 init style, then raises
    // contrast for a bench-visible white smoke frame.
    const std::uint8_t init[] = {
        0xAE,        // display off
        0xD5, 0x80,  // clock
        0xA8, 0x3F,  // multiplex 64
        0xD3, 0x00,  // display offset
        0x40,        // start line
        0x20, 0x00,  // horizontal addressing
        0xA1,        // segment remap: rotate bench panel 180 degrees
        0xC8,        // COM scan direction: rotate bench panel 180 degrees
        0xDB, 0x10,  // VCOMH
        0xA4,        // resume RAM display
        0x2E,        // deactivate scroll
        0x8D, 0x14,  // charge pump
        0xDA, 0x12,  // COM pins
        0x81, 0xFF,  // max contrast for smoke visibility
        0xD9, 0x11,  // precharge
        0xA6,        // normal display
        0xAF,        // display on
    };
    return sendOledCommands(init, sizeof(init));
}

bool setOledAllPixelsOn(bool enabled) {
    const std::uint8_t commands[] = {
        static_cast<std::uint8_t>(enabled ? 0xA5 : 0xA4),
        0xAF,
    };
    return sendOledCommands(commands, sizeof(commands));
}

bool drawOledSmokeFrame() {
    return clearOled() &&
           writeOledPage(0, "TERMINAL") &&
           writeOledPage(2, "OLED 0X3C") &&
           writeOledPage(4, "PORT 3 OK") &&
           writeOledPage(6, "SDA SCL OK");
}

void runExternalOledDrawSmoke(bool showAllOnBoot) {
    Serial.printf("OLED_DRAW_SMOKE START sda=%d scl=%d freq=%d address=0x%02X mux=0x%02X channel=%u SSD1306 SSD1309\n",
                  terminal_config::EXTERNAL_OLED_SDA_PIN,
                  terminal_config::EXTERNAL_OLED_SCL_PIN,
                  terminal_config::EXTERNAL_OLED_I2C_FREQ,
                  terminal_config::EXTERNAL_OLED_I2C_ADDRESS,
                  terminal_config::EXTERNAL_OLED_PAHUB_ADDRESS,
                  terminal_config::EXTERNAL_OLED_PAHUB_CHANNEL);
    Wire.begin(terminal_config::EXTERNAL_OLED_SDA_PIN,
               terminal_config::EXTERNAL_OLED_SCL_PIN,
               terminal_config::EXTERNAL_OLED_I2C_FREQ);
    if (selectOledPahubChannel() != 0) {
        Serial.println("OLED_DRAW_SMOKE ERROR mux_select");
        return;
    }
    if (!initOledSsd1309Laskakit()) {
        Serial.println("OLED_DRAW_SMOKE ERROR init");
        return;
    }
    if (showAllOnBoot) {
        if (!setOledAllPixelsOn(true)) {
            Serial.println("OLED_DRAW_SMOKE ERROR all_on");
            return;
        }
        Serial.printf("OLED_DRAW_SMOKE ALL_ON_BOOT address=0x%02X channel=%u\n",
                      terminal_config::EXTERNAL_OLED_I2C_ADDRESS,
                      terminal_config::EXTERNAL_OLED_PAHUB_CHANNEL);
        Serial.flush();
        delay(300);
        if (!setOledAllPixelsOn(false)) {
            Serial.println("OLED_DRAW_SMOKE ERROR all_off");
            return;
        }
    }
    if (!drawOledSmokeFrame()) {
        Serial.println("OLED_DRAW_SMOKE ERROR draw");
        return;
    }
    Serial.printf("OLED_DRAW_SMOKE STABLE_TEXT address=0x%02X channel=%u\n",
                  terminal_config::EXTERNAL_OLED_I2C_ADDRESS,
                  terminal_config::EXTERNAL_OLED_PAHUB_CHANNEL);
    Serial.printf("OLED_DRAW_SMOKE DRAWN address=0x%02X channel=%u count=%lu\n",
                  terminal_config::EXTERNAL_OLED_I2C_ADDRESS,
                  terminal_config::EXTERNAL_OLED_PAHUB_CHANNEL,
                  static_cast<unsigned long>(g_oledDrawCount));
    Serial.flush();
}

}  // namespace

void setup() {
    auto cfg = M5.config();
    M5.begin(cfg);
    M5.Display.setRotation(1);
    M5.Display.fillScreen(TFT_BLACK);
    M5.Display.setTextColor(TFT_WHITE, TFT_BLACK);
    M5.Display.setTextSize(2);
    M5.Display.setCursor(4, 8);
    M5.Display.println("OLED DRAW");
    M5.Display.setCursor(4, 34);
    M5.Display.println("SMOKE");
    Serial.begin(terminal_config::USB_SETUP_BAUD);
    delay(250);
    runExternalOledDrawSmoke(true);
    g_oledAllOnBootShown = true;
    g_lastOledDrawMs = millis();
}

void loop() {
    M5.update();
    if (millis() - g_lastOledDrawMs >= 10000) {
        g_lastOledDrawMs = millis();
        ++g_oledDrawCount;
        Serial.printf("OLED_DRAW_SMOKE HEARTBEAT stable count=%lu\n",
                      static_cast<unsigned long>(g_oledDrawCount));
        Serial.flush();
    }
    delay(5);
}

#else

namespace {

constexpr int G4_ADC_SMOKE_PIN = 4;
constexpr int G4_ADC_SMOKE_SAMPLES = 32;
constexpr int G4_ADC_SMOKE_DELAY_MS = 2;

std::uint32_t g_lastSmokePrintMs = 0;
std::uint32_t g_smokePrintCount = 0;

struct AdcWindow {
    int minValue;
    int maxValue;
    long sum;
};

AdcWindow sampleG4() {
    AdcWindow window{4095, 0, 0};
    for (int i = 0; i < G4_ADC_SMOKE_SAMPLES; ++i) {
        const int raw = analogRead(G4_ADC_SMOKE_PIN);
        if (raw < window.minValue) {
            window.minValue = raw;
        }
        if (raw > window.maxValue) {
            window.maxValue = raw;
        }
        window.sum += raw;
        delay(G4_ADC_SMOKE_DELAY_MS);
    }
    return window;
}

void printWindow(const char* label, const AdcWindow& window) {
    Serial.printf("G4_ADC_SMOKE %s pin=%d min=%d max=%d avg=%ld span=%d\n",
                  label,
                  G4_ADC_SMOKE_PIN,
                  window.minValue,
                  window.maxValue,
                  window.sum / G4_ADC_SMOKE_SAMPLES,
                  window.maxValue - window.minValue);
    Serial.flush();
}

}  // namespace

void setup() {
    Serial.begin(115200);
    const std::uint32_t startMs = millis();
    while (!Serial && millis() - startMs < 3000) {
        delay(10);
    }

    Serial.println("G4_ADC_SMOKE START pin=4 phase=before_m5_begin");
    analogReadResolution(12);
    pinMode(G4_ADC_SMOKE_PIN, INPUT);
    printWindow("before_m5_begin", sampleG4());

    auto cfg = M5.config();
    M5.begin(cfg);
    M5.Display.setRotation(1);
    M5.Display.fillScreen(TFT_BLACK);
    M5.Display.setTextColor(TFT_WHITE, TFT_BLACK);
    M5.Display.setTextSize(2);
    M5.Display.setCursor(4, 8);
    M5.Display.println("G4 ADC");
    M5.Display.setCursor(4, 34);
    M5.Display.println("SMOKE");

    analogReadResolution(12);
    pinMode(G4_ADC_SMOKE_PIN, INPUT);
    Serial.println("G4_ADC_SMOKE phase=after_m5_begin");
    printWindow("after_m5_begin", sampleG4());
    g_lastSmokePrintMs = millis();
}

void loop() {
    M5.update();
    if (millis() - g_lastSmokePrintMs >= 500) {
        g_lastSmokePrintMs = millis();
        ++g_smokePrintCount;
        printWindow("loop", sampleG4());
        if (g_smokePrintCount % 10 == 0) {
            Serial.println("G4_ADC_SMOKE HEARTBEAT");
            Serial.flush();
        }
    }
    delay(5);
}

#endif
