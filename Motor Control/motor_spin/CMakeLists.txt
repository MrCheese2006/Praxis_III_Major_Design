# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location
# (note this can come from environment, CMake cache etc)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico_w CACHE STRING "Board type")

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

project(motor_spin C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# Add executable. Default name is the project name, version 0.1

# NOTE: motor_spin.c uses C++ constructs (String class, method calls).
# Rename the file to motor_spin.cpp, or add set_source_files_properties below.
set_source_files_properties(motor_spin.c PROPERTIES LANGUAGE CXX)
add_executable(motor_spin motor_spin.c)

pico_set_program_name(motor_spin "motor_spin")
pico_set_program_version(motor_spin "0.1")

# motor_spin.c uses Serial (mapped to USB CDC on Pico W)
pico_enable_stdio_uart(motor_spin 0)
pico_enable_stdio_usb(motor_spin 1)

# Add the standard include files to the build
target_include_directories(motor_spin PRIVATE
        ${CMAKE_CURRENT_LIST_DIR}
)

# Libraries required by motor_spin.c:
#   pico_stdlib                              — core SDK (GPIO, time, etc.)
#   pico_cyw43_arch_lwip_threadsafe_background — WiFi on Pico W (replaces WiFi.h / HTTPClient.h)
#   pico_lwip_http                           — lwIP HTTP client (replaces HTTPClient.h)
#   hardware_pwm                             — PWM output (replaces analogWrite)
#   hardware_gpio                            — GPIO + interrupt support (attachInterrupt)
#
# NOTE: WiFi.h, HTTPClient.h, and DHT.h are Arduino-framework headers and will not
# resolve under the Pico SDK. motor_spin.c must be ported to use the Pico SDK
# equivalents listed above before this project will compile successfully.
target_link_libraries(motor_spin
        pico_stdlib
        pico_cyw43_arch_lwip_threadsafe_background
        pico_lwip_http
        hardware_pwm
        hardware_gpio
)

pico_add_extra_outputs(motor_spin)

