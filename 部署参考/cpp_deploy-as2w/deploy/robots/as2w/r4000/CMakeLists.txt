cmake_minimum_required(VERSION 3.16)
project(as2w_r4000_deploy LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(ONNXRUNTIME_ROOT "" CACHE PATH "Extracted ONNX Runtime package")
if(NOT ONNXRUNTIME_ROOT)
  message(FATAL_ERROR "Set ONNXRUNTIME_ROOT for R4000")
endif()

find_package(yaml-cpp REQUIRED)
find_library(ort_library NAMES onnxruntime libonnxruntime.so.1
  PATHS "${ONNXRUNTIME_ROOT}/lib" NO_DEFAULT_PATH REQUIRED)

# The rolling-4000 training contract (5 Hz leg filter, 0.9 rad/s slew,
# pure_turn_common_scale=0) is the runtime of record for this policy; the
# library below is therefore only built as the bounded joystick candidate
# and is always paired with its parity fixture.
option(AS2W_R4000_JOYSTICK_CANDIDATE "Build bounded R4000 joystick trial candidate" OFF)
option(AS2W_R4000_PUBLISH "Build the gated R4000 FSM publisher" OFF)
if(AS2W_R4000_JOYSTICK_CANDIDATE)
  add_library(as2w_r4000_joystick r4000_controller.cpp)
  target_compile_definitions(as2w_r4000_joystick PRIVATE AS2W_R4000_JOYSTICK_CANDIDATE=1)
  target_include_directories(as2w_r4000_joystick PUBLIC . "${ONNXRUNTIME_ROOT}/include" ../../../include)
  target_link_libraries(as2w_r4000_joystick PUBLIC "${ort_library}" yaml-cpp)
  add_executable(as2w_r4000_joystick_replay r4000_replay.cpp)
  target_compile_definitions(as2w_r4000_joystick_replay PRIVATE AS2W_R4000_JOYSTICK_CANDIDATE=1)
  target_link_libraries(as2w_r4000_joystick_replay PRIVATE as2w_r4000_joystick)
  if(AS2W_R4000_PUBLISH)
    find_package(unitree_sdk2 CONFIG REQUIRED)
    find_package(Threads REQUIRED)
    add_executable(as2w_r4000_joystick_publish ../common/as2w_publish.cpp)
    target_compile_definitions(as2w_r4000_joystick_publish PRIVATE
      AS2W_POLICY_R4000=1 AS2W_R4000_JOYSTICK_CANDIDATE=1
      AS2W_ENABLE_POLICY_ZERO_B_TRIAL=1)
    target_link_libraries(as2w_r4000_joystick_publish PRIVATE
      as2w_r4000_joystick unitree_sdk2 Threads::Threads)
    if(BUILD_TESTING)
      add_test(NAME r4000-joystick-startup-audit COMMAND as2w_r4000_joystick_publish
        "${CMAKE_SOURCE_DIR}/models/r4000/deploy.yaml"
        "${CMAKE_SOURCE_DIR}/config/r152_measured.map" --offline-audit)
    endif()
  endif()
endif()
