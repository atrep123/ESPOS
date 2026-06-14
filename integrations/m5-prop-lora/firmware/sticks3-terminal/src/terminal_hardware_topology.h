#pragma once

#include <cstdint>

namespace terminal_hardware_topology {

constexpr std::uint8_t STICKS3_CONTROLLER_COUNT = 1;
constexpr std::uint8_t CONTROL_LANE_COUNT = 5;
constexpr std::uint8_t UNIT_FADER_COUNT = CONTROL_LANE_COUNT;
constexpr std::uint8_t CHAIN_ENCODER_COUNT = CONTROL_LANE_COUNT;
constexpr std::uint8_t MECHANICAL_SWITCH_COUNT = 2;
constexpr std::uint8_t GROVE2USB_C_ADAPTER_COUNT = 2;
constexpr std::uint8_t PAHUB_COUNT = 2;
constexpr std::uint8_t EXTERNAL_OLED_COUNT = 1;
constexpr std::uint8_t UNIT_FADER_RGB_LED_COUNT = 14;

constexpr std::uint8_t PAHUB_PORT_COUNT = 6;
constexpr std::uint8_t PRIMARY_PAHUB_PORT_CHAIN_BRANCH = 0;
constexpr std::uint8_t PRIMARY_PAHUB_PORT_POT5 = 1;
constexpr std::uint8_t PRIMARY_PAHUB_PORT_POT4 = 2;
constexpr std::uint8_t PRIMARY_PAHUB_PORT_EXTERNAL_DISPLAY = 3;
constexpr std::uint8_t PRIMARY_PAHUB_PORT_SECONDARY_PAHUB = 5;

constexpr std::uint8_t SECONDARY_PAHUB_PORT_POT3 = 2;
constexpr std::uint8_t SECONDARY_PAHUB_PORT_POT2 = 3;
constexpr std::uint8_t SECONDARY_PAHUB_PORT_POT1 = 4;

constexpr std::uint8_t CHAIN_BRANCH_POSITION_ENCODER_LED5 = 0;
constexpr std::uint8_t CHAIN_BRANCH_POSITION_ENCODER_LED4 = 1;
constexpr std::uint8_t CHAIN_BRANCH_POSITION_ENCODER_LED3 = 2;
constexpr std::uint8_t CHAIN_BRANCH_POSITION_ENCODER_LED2 = 3;
constexpr std::uint8_t CHAIN_BRANCH_POSITION_ENCODER_LED1 = 4;
constexpr std::uint8_t CHAIN_BRANCH_POSITION_UPLOAD_SWITCH = 5;
constexpr std::uint8_t CHAIN_BRANCH_POSITION_SIM_FIRE_SWITCH = 6;
constexpr std::uint8_t CHAIN_BRANCH_DEVICE_COUNT = 7;

constexpr bool TERMINAL_HAS_LORA_MODULE = false;
constexpr bool UNIT_FADERS_ARE_M5STACK_U123_B10K_SK6812 = true;
constexpr bool UNIT_FADER_SLIDER_OUTPUT_IS_ANALOG = true;
constexpr bool UNIT_FADER_RGB_OUTPUT_IS_SK6812_DATA = true;
constexpr bool UNIT_FADER_RGB_CONTROL_DEFERRED_FOR_FIRST_SLICE = true;
constexpr bool STICKS3_HAT2_EXPOSES_TEN_GPIO_LABELS = true;
constexpr bool STICKS3_HAT2_G1_TO_G4_SHARE_INTERNAL_FUNCTIONS = true;
constexpr bool STICKS3_GROVE_G9_G10_RESERVED_FOR_REMAINING_TOPOLOGY = true;
constexpr bool STICKS3_G4_ADC_SMOKE_BUILDS_AND_UPLOADS = true;
constexpr bool STICKS3_G4_ADC_SMOKE_TRACKS_FADER_RANGE = true;
constexpr bool STICKS3_G4_ADC_SMOKE_ACCEPTED_AS_FADER_ADC = true;
constexpr bool STICKS3_G4_ADC_SMOKE_DIRECTION_IS_INVERTED = true;
constexpr bool UNIT_FADERS_HAVE_VERIFIED_SHARED_PIN_FOR_SLIDER_ONLY = true;
constexpr bool UNIT_FADERS_CAN_USE_FIVE_SAFE_DIRECT_STICKS3_ADC_WITH_REST_UNCHANGED = false;
constexpr bool UNIT_FADERS_REQUIRE_EXTERNAL_ADC_OR_VERIFIED_SHARED_PIN = true;
constexpr bool UNIT_FADERS_USE_PAHUB_PORTS_FOR_SIGNALS = false;
constexpr bool PAHUB_CAN_ROUTE_ANALOG_FADERS = false;
constexpr bool PAHUB_CAN_ROUTE_UNIT_FADER_RGB_DATA = false;
constexpr bool GROVE2USB_ROLE_FINALIZED = false;
constexpr bool EXTERNAL_OLED_ROLE_FINALIZED = false;
constexpr bool LANE_CONTROLS_ARE_DIRECT_PHYSICAL_CONTROLS = true;
constexpr bool PHYSICAL_CHAIN_ORDER_IS_LED5_TO_LED1 = true;
constexpr bool LAST_CHAIN_SWITCH_IS_SIM_FIRE = true;

constexpr std::uint8_t REQUIRED_FADER_ADC_COUNT_FOR_SLIDER_ONLY = 5;
constexpr std::uint8_t SAFE_DIRECT_ADC_BUDGET_WITH_REST_UNCHANGED = 4;
constexpr std::uint8_t STICKS3_G4_ADC_SMOKE_PIN = 4;
constexpr std::uint16_t STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_MIN = 0;
constexpr std::uint16_t STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_MAX = 4095;
constexpr std::uint16_t STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_SPAN = 4095;
constexpr std::uint16_t STICKS3_G4_ADC_SMOKE_PHYSICAL_BOTTOM_RAW = 4095;
constexpr std::uint16_t STICKS3_G4_ADC_SMOKE_PHYSICAL_TOP_RAW = 0;

static_assert(STICKS3_CONTROLLER_COUNT == 1, "Terminal has exactly one M5StickS3 controller");
static_assert(UNIT_FADER_COUNT == CONTROL_LANE_COUNT,
              "Terminal needs one Unit Fader per controlled LED lane");
static_assert(CHAIN_ENCODER_COUNT == CONTROL_LANE_COUNT,
              "Terminal needs one Chain Encoder per controlled LED lane");
static_assert(MECHANICAL_SWITCH_COUNT == 2,
              "Terminal uses exactly upload and sim-fire mechanical switches");
static_assert(!TERMINAL_HAS_LORA_MODULE, "Terminal must remain radio-free");
static_assert(UNIT_FADERS_ARE_M5STACK_U123_B10K_SK6812,
              "Terminal Pot1..Pot5 are M5Stack Unit Fader U123/B10K/SK6812 modules");
static_assert(UNIT_FADER_SLIDER_OUTPUT_IS_ANALOG,
              "Unit Fader slider position needs a direct ADC/backplane path");
static_assert(UNIT_FADER_RGB_OUTPUT_IS_SK6812_DATA,
              "Unit Fader RGB LEDs need a digital SK6812 data path");
static_assert(UNIT_FADER_RGB_CONTROL_DEFERRED_FOR_FIRST_SLICE,
              "First Terminal fader slice reads sliders only and defers fader RGB LEDs");
static_assert(STICKS3_HAT2_EXPOSES_TEN_GPIO_LABELS,
              "StickS3 Hat2 exposes ten GPIO labels, but not all are clean fader ADC signals");
static_assert(STICKS3_HAT2_G1_TO_G4_SHARE_INTERNAL_FUNCTIONS,
              "StickS3 G1-G4 share internal PMIC/speaker/IMU functions and need explicit bench qualification");
static_assert(STICKS3_GROVE_G9_G10_RESERVED_FOR_REMAINING_TOPOLOGY,
              "StickS3 Grove G9/G10 stays reserved for the remaining Terminal topology");
static_assert(STICKS3_G4_ADC_SMOKE_BUILDS_AND_UPLOADS,
              "G4 ADC smoke must remain reproducible while evaluating shared-pin fallback");
static_assert(STICKS3_G4_ADC_SMOKE_TRACKS_FADER_RANGE,
              "Bench smoke observed G4 tracking fader movement across the ADC range");
static_assert(STICKS3_G4_ADC_SMOKE_ACCEPTED_AS_FADER_ADC,
              "G4 is accepted as the verified shared-pin fallback for the fifth slider ADC");
static_assert(STICKS3_G4_ADC_SMOKE_DIRECTION_IS_INVERTED,
              "G4 fader smoke direction is inverted: physical bottom is high raw");
static_assert(UNIT_FADERS_HAVE_VERIFIED_SHARED_PIN_FOR_SLIDER_ONLY,
              "The slider-only first slice now has one verified shared StickS3 ADC candidate");
static_assert(!UNIT_FADERS_CAN_USE_FIVE_SAFE_DIRECT_STICKS3_ADC_WITH_REST_UNCHANGED,
              "Five safe direct ADC fader channels do not fit on bare StickS3 while Grove/remaining topology stays");
static_assert(UNIT_FADERS_REQUIRE_EXTERNAL_ADC_OR_VERIFIED_SHARED_PIN,
              "Slider-only fader slice needs external ADC/mux or one explicitly verified shared StickS3 pin");
static_assert(!UNIT_FADERS_USE_PAHUB_PORTS_FOR_SIGNALS,
              "Unit Faders must not use PaHUB ports as their signal path");
static_assert(!PAHUB_CAN_ROUTE_ANALOG_FADERS,
              "PaHUB must not be treated as an analog fader router");
static_assert(!PAHUB_CAN_ROUTE_UNIT_FADER_RGB_DATA,
              "PaHUB must not be treated as a Unit Fader SK6812 data router");
static_assert(PRIMARY_PAHUB_PORT_CHAIN_BRANCH < PAHUB_PORT_COUNT,
              "Primary PaHUB chain branch port must be a valid mux channel");
static_assert(PRIMARY_PAHUB_PORT_POT5 < PAHUB_PORT_COUNT,
              "Primary PaHUB Pot5 port must be a valid mux channel");
static_assert(PRIMARY_PAHUB_PORT_POT4 < PAHUB_PORT_COUNT,
              "Primary PaHUB Pot4 port must be a valid mux channel");
static_assert(PRIMARY_PAHUB_PORT_EXTERNAL_DISPLAY < PAHUB_PORT_COUNT,
              "Primary PaHUB display port must be a valid mux channel");
static_assert(PRIMARY_PAHUB_PORT_SECONDARY_PAHUB < PAHUB_PORT_COUNT,
              "Primary PaHUB secondary hub port must be a valid mux channel");
static_assert(SECONDARY_PAHUB_PORT_POT3 < PAHUB_PORT_COUNT,
              "Secondary PaHUB Pot3 port must be a valid mux channel");
static_assert(SECONDARY_PAHUB_PORT_POT2 < PAHUB_PORT_COUNT,
              "Secondary PaHUB Pot2 port must be a valid mux channel");
static_assert(SECONDARY_PAHUB_PORT_POT1 < PAHUB_PORT_COUNT,
              "Secondary PaHUB Pot1 port must be a valid mux channel");
static_assert(CHAIN_BRANCH_POSITION_ENCODER_LED1 + 1 == CHAIN_ENCODER_COUNT,
              "The encoder branch contains five LED encoders before switches");
static_assert(CHAIN_BRANCH_DEVICE_COUNT == CHAIN_ENCODER_COUNT + MECHANICAL_SWITCH_COUNT,
              "The chain branch contains five encoders plus two switches");
static_assert(REQUIRED_FADER_ADC_COUNT_FOR_SLIDER_ONLY == CONTROL_LANE_COUNT,
              "Slider-only first slice still needs one ADC channel per Unit Fader");
static_assert(SAFE_DIRECT_ADC_BUDGET_WITH_REST_UNCHANGED <
                  REQUIRED_FADER_ADC_COUNT_FOR_SLIDER_ONLY,
              "Bare StickS3 does not have five clean direct ADC channels while Grove/remaining topology stays");
static_assert(STICKS3_G4_ADC_SMOKE_PIN == 4,
              "The shared-pin smoke is specifically the StickS3 G4 / IMU_INT candidate");
static_assert(STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_MIN == 0 &&
                  STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_MAX == 4095 &&
                  STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_SPAN == 4095,
              "The recorded G4 smoke must preserve the observed full-range ADC evidence");
static_assert(STICKS3_G4_ADC_SMOKE_PHYSICAL_BOTTOM_RAW == 4095 &&
                  STICKS3_G4_ADC_SMOKE_PHYSICAL_TOP_RAW == 0,
              "The recorded G4 smoke must preserve the observed inverted physical direction");

}  // namespace terminal_hardware_topology
