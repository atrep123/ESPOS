# This file was automatically generated for projects
# without default 'CMakeLists.txt' file.

FILE(GLOB_RECURSE app_sources ${CMAKE_SOURCE_DIR}/src/*.*)

idf_component_register(SRCS ${app_sources})

# The input can change without a CMake reconfigure; validate every build.
add_custom_target(espos_validate_ui
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/validate_idf_ui.py" "${CMAKE_SOURCE_DIR}"
    VERBATIM
)
add_dependencies(${COMPONENT_LIB} espos_validate_ui)
