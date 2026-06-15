#include "../sticks3-terminal/src/terminal_hardware_topology.h"

#include <iostream>

namespace {

namespace topology = terminal_hardware_topology;

bool plannedHardwareHasOneFaderAndOneEncoderPerLane() {
    return topology::CONTROL_LANE_COUNT == 5 &&
           topology::UNIT_FADER_COUNT == topology::CONTROL_LANE_COUNT &&
           topology::CHAIN_ENCODER_COUNT == topology::CONTROL_LANE_COUNT;
}

bool terminalHasStatusOnlySwitchesAndNoRadioModule() {
    return topology::STICKS3_CONTROLLER_COUNT == 1 &&
           topology::MECHANICAL_SWITCH_COUNT == 2 &&
           topology::TERMINAL_HAS_LORA_MODULE == false;
}

bool pahubIsNotAllowedToRouteAnalogFaderReads() {
    return topology::PAHUB_COUNT == 1 &&
           topology::PAHUB_CAN_ROUTE_ANALOG_FADERS == false &&
           topology::PAHUB_CAN_ROUTE_UNIT_FADER_RGB_DATA == false;
}

bool pbhubOwnsFaderAdcAndRgbReflection() {
    return topology::PBHUB_COUNT == 1 &&
           topology::PBHUB_PORT_COUNT == 6 &&
           topology::PBHUB_I2C_ADDRESS == 0x61 &&
           topology::UNIT_FADERS_USE_PBHUB_FOR_ADC_AND_RGB == true &&
           topology::UNIT_FADER_RGB_REFLECTION_ENABLED == true &&
           topology::UNIT_FADER_RGB_CONTROL_DEFERRED_FOR_FIRST_SLICE == false;
}

bool groveAndOledRolesStayExplicitlyUnfinalized() {
    return topology::GROVE2USB_C_ADAPTER_COUNT == 2 &&
           topology::EXTERNAL_OLED_COUNT == 1 &&
           topology::GROVE2USB_ROLE_FINALIZED == false &&
           topology::EXTERNAL_OLED_ROLE_FINALIZED == false;
}

bool laneControlsAreDirectPhysicalControls() {
    return topology::LANE_CONTROLS_ARE_DIRECT_PHYSICAL_CONTROLS == true;
}

bool faderModulesAreAnalogB10kWithSk6812Rgb() {
    return topology::UNIT_FADER_COUNT == topology::CONTROL_LANE_COUNT &&
           topology::UNIT_FADERS_ARE_M5STACK_U123_B10K_SK6812 == true &&
           topology::UNIT_FADER_SLIDER_OUTPUT_IS_ANALOG == true &&
           topology::UNIT_FADER_RGB_OUTPUT_IS_SK6812_DATA == true &&
           topology::UNIT_FADER_RGB_LED_COUNT == 14;
}

bool pbhubFaderSliceKeepsPahubAsBranchSelectorOnly() {
    return topology::STICKS3_HAT2_EXPOSES_TEN_GPIO_LABELS == true &&
           topology::STICKS3_HAT2_G1_TO_G4_SHARE_INTERNAL_FUNCTIONS == true &&
           topology::STICKS3_GROVE_G9_G10_RESERVED_FOR_REMAINING_TOPOLOGY == true &&
           topology::UNIT_FADERS_CAN_USE_FIVE_SAFE_DIRECT_STICKS3_ADC_WITH_REST_UNCHANGED == false &&
           topology::UNIT_FADERS_REQUIRE_EXTERNAL_ADC_OR_VERIFIED_SHARED_PIN == true &&
           topology::UNIT_FADERS_USE_PAHUB_PORTS_FOR_SIGNALS == false &&
           topology::UNIT_FADERS_USE_PBHUB_FOR_ADC_AND_RGB == true &&
           topology::REQUIRED_FADER_ADC_COUNT_FOR_SLIDER_ONLY == 5 &&
           topology::SAFE_DIRECT_ADC_BUDGET_WITH_REST_UNCHANGED == 4;
}

bool g4AdcSmokeAcceptsG4AsSharedFaderAdcCandidate() {
    return topology::STICKS3_G4_ADC_SMOKE_BUILDS_AND_UPLOADS == true &&
           topology::STICKS3_G4_ADC_SMOKE_TRACKS_FADER_RANGE == true &&
           topology::STICKS3_G4_ADC_SMOKE_ACCEPTED_AS_FADER_ADC == true &&
           topology::STICKS3_G4_ADC_SMOKE_DIRECTION_IS_INVERTED == true &&
           topology::UNIT_FADERS_HAVE_VERIFIED_SHARED_PIN_FOR_SLIDER_ONLY == true &&
           topology::STICKS3_G4_ADC_SMOKE_PIN == 4 &&
           topology::STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_MIN == 0 &&
           topology::STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_MAX == 4095 &&
           topology::STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_SPAN == 4095 &&
           topology::STICKS3_G4_ADC_SMOKE_PHYSICAL_BOTTOM_RAW == 4095 &&
           topology::STICKS3_G4_ADC_SMOKE_PHYSICAL_TOP_RAW == 0;
}

bool benchWiringUsesPrimaryPahubAndPbhubPorts() {
    return topology::PRIMARY_PAHUB_PORT_CHAIN_BRANCH == 0 &&
           topology::PRIMARY_PAHUB_PORT_EXTERNAL_DISPLAY == 3 &&
           topology::PRIMARY_PAHUB_PORT_PBHUB == 5 &&
           topology::PBHUB_PORT_POT5 == 0 &&
           topology::PBHUB_PORT_POT4 == 1 &&
           topology::PBHUB_PORT_POT3 == 2 &&
           topology::PBHUB_PORT_POT2 == 3 &&
           topology::PBHUB_PORT_POT1 == 4 &&
           topology::PBHUB_PORT_XIAO_GROVE2USB_C == 5 &&
           topology::PBHUB_PORT5_RESERVED_FOR_XIAO_LINK == true;
}

bool pbhubPort5DoesNotCarrySerial2PropLink() {
    return topology::PBHUB_PORT_XIAO_GROVE2USB_C == 5 &&
           topology::PBHUB_PORT5_RESERVED_FOR_XIAO_LINK == true &&
           topology::PBHUB_PORT5_IS_SERIAL2_UART_ROUTE == false &&
           topology::PROP_LINK_REQUIRES_DIRECT_STICKS3_UART == true;
}

bool chainPhysicalOrderIsLed5ToLed1ThenUploadAndSimFireSwitch() {
    return topology::PHYSICAL_CHAIN_ORDER_IS_LED5_TO_LED1 == true &&
           topology::CHAIN_BRANCH_POSITION_ENCODER_LED5 == 0 &&
           topology::CHAIN_BRANCH_POSITION_ENCODER_LED4 == 1 &&
           topology::CHAIN_BRANCH_POSITION_ENCODER_LED3 == 2 &&
           topology::CHAIN_BRANCH_POSITION_ENCODER_LED2 == 3 &&
           topology::CHAIN_BRANCH_POSITION_ENCODER_LED1 == 4 &&
           topology::CHAIN_BRANCH_POSITION_UPLOAD_SWITCH == 5 &&
           topology::CHAIN_BRANCH_POSITION_SIM_FIRE_SWITCH == 6 &&
           topology::CHAIN_BRANCH_DEVICE_COUNT == 7;
}

bool lastChainSwitchIsSimFire() {
    return topology::LAST_CHAIN_SWITCH_IS_SIM_FIRE == true;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("planned hardware has one fader and one encoder per lane", plannedHardwareHasOneFaderAndOneEncoderPerLane) ? 0 : 1;
    failures += runCase("terminal has status-only switches and no radio module", terminalHasStatusOnlySwitchesAndNoRadioModule) ? 0 : 1;
    failures += runCase("PaHUB is not allowed to route analog fader reads", pahubIsNotAllowedToRouteAnalogFaderReads) ? 0 : 1;
    failures += runCase("PbHUB owns fader ADC and RGB reflection", pbhubOwnsFaderAdcAndRgbReflection) ? 0 : 1;
    failures += runCase("Grove and OLED roles stay explicitly unfinalized", groveAndOledRolesStayExplicitlyUnfinalized) ? 0 : 1;
    failures += runCase("lane controls are direct physical controls", laneControlsAreDirectPhysicalControls) ? 0 : 1;
    failures += runCase("fader modules are analog B10K with SK6812 RGB", faderModulesAreAnalogB10kWithSk6812Rgb) ? 0 : 1;
    failures += runCase("PbHUB fader slice keeps PaHUB as branch selector only", pbhubFaderSliceKeepsPahubAsBranchSelectorOnly) ? 0 : 1;
    failures += runCase("G4 ADC smoke accepts G4 as shared fader ADC candidate", g4AdcSmokeAcceptsG4AsSharedFaderAdcCandidate) ? 0 : 1;
    failures += runCase("bench wiring uses primary PaHUB and PbHUB ports", benchWiringUsesPrimaryPahubAndPbhubPorts) ? 0 : 1;
    failures += runCase("PbHUB port 5 does not carry Serial2 prop-link UART", pbhubPort5DoesNotCarrySerial2PropLink) ? 0 : 1;
    failures += runCase("chain physical order is LED5 to LED1 then upload and sim-fire switch", chainPhysicalOrderIsLed5ToLed1ThenUploadAndSimFireSwitch) ? 0 : 1;
    failures += runCase("last chain switch is sim-fire", lastChainSwitchIsSimFire) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
