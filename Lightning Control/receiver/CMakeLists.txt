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

project(receiver C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# NOTE: receiver.c currently uses Arduino-style APIs (RH_ASK, WiFi, HTTPClient).
# These do not exist in the Pico SDK. The file must be rewritten using Pico SDK
# equivalents before it will compile. The libraries linked below are the correct
# Pico SDK replacements for each Arduino dependency:
#   Arduino WiFi.h       → pico_cyw43_arch_lwip_threadsafe_background
#   Arduino HTTPClient.h → lwIP HTTP (pico_lwip_http) or raw lwIP TCP
#   Arduino SPI.h        → hardware_spi
#   RH_ASK               → no SDK equivalent; needs custom GPIO bit-bang implementation
#
# Also note: receiver.c uses C++ (classes, String, etc.) — rename to receiver.cpp
# and update the add_executable line accordingly once the code is ported.

add_executable(receiver receiver.c)

pico_set_program_name(receiver "receiver")
pico_set_program_version(receiver "0.1")

# Enable USB stdio so Serial output is visible over USB (used for debug prints)
pico_enable_stdio_uart(receiver 0)
pico_enable_stdio_usb(receiver 1)

# Add the standard library to the build
target_link_libraries(receiver
        pico_stdlib)

# Add the standard include files to the build
target_include_directories(receiver PRIVATE
        ${CMAKE_CURRENT_LIST_DIR}
)

# Pico SDK equivalents of the Arduino libraries used in receiver.c
target_link_libraries(receiver
        hardware_spi                                 # replaces Arduino SPI.h
        pico_cyw43_arch_lwip_threadsafe_background   # replaces Arduino WiFi.h (Pico W CYW43 + lwIP)
        pico_lwip_http                               # replaces Arduino HTTPClient.h (lwIP HTTP)
)

pico_add_extra_outputs(receiver)

