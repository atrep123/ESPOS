
# For more information about build system see
# https://docs.espressif.com/projects/esp-idf/en/latest/api-guides/build-system.html
# The following five lines of boilerplate have to be in your project's
# CMakeLists in this exact order for cmake to work correctly
cmake_minimum_required(VERSION 3.16)

if(DEFINED ENV{PROP_RELEASE_BUILD_FLAGS} AND NOT "$ENV{PROP_RELEASE_BUILD_FLAGS}" STREQUAL "")
    separate_arguments(_prop_release_build_flags NATIVE_COMMAND "$ENV{PROP_RELEASE_BUILD_FLAGS}")
    add_compile_options(${_prop_release_build_flags})
    message(STATUS "Applied PROP_RELEASE_BUILD_FLAGS release guard defines")
endif()



# -------------------------------------------------------------------------
# Global define
# -------------------------------------------------------------------------

# Enable factory test
add_definitions(-DENABLE_FACTORY_TEST)

# WiFi test setting
add_definitions(-DFACTORY_TEST_WIFI_SSID="?")
add_definitions(-DFACTORY_TEST_WIFI_PASSWORD="?")
# add_definitions(-DFACTORY_TEST_WIFI_SSID="?")
# add_definitions(-DFACTORY_TEST_WIFI_PASSWORD="?")


# Font setting
add_definitions(-DGUI_FONT_CN_BIG=&fonts::efontCN_24)
# add_definitions(-DGUI_FONT_CN_SMALL=&fonts::efontCN_16)
add_definitions(-DGUI_FONT_CN_SMALL=&fonts::efontCN_16_b)

# -------------------------------------------------------------------------



# -------------------------------------------------------------------------
# Regenerate the Dial theme header from the shared single source
# (tools/m5_theme.json) at configure time, so ui_theme_dial_generated.h stays
# in sync with the M5 design system. See tools/gen_firmware_theme.py.
# -------------------------------------------------------------------------
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
    execute_process(
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../../tools/gen_firmware_theme.py
        RESULT_VARIABLE _gen_theme_rc)
    if(NOT _gen_theme_rc EQUAL 0)
        message(WARNING "gen_firmware_theme.py failed (rc=${_gen_theme_rc}); using existing header")
    endif()
endif()

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(stamp_ring_factory_test)
