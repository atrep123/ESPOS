cmake_minimum_required(VERSION 3.16.0)
# Validate before IDF discovers/compiles existing generated C. This also
# closes the direct idf.py path, which does not execute SCons extra_scripts.
find_package(Python3 COMPONENTS Interpreter REQUIRED)
execute_process(
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/validate_idf_ui.py" "${CMAKE_CURRENT_SOURCE_DIR}"
    RESULT_VARIABLE ui_validation_result
)
if(NOT ui_validation_result EQUAL 0)
    message(FATAL_ERROR "UI validation/generation failed")
endif()
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(ESPOS)
