cmake_minimum_required(VERSION 3.16)
project(as2w_r1199_deploy LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(ONNXRUNTIME_ROOT "" CACHE PATH "Extracted ONNX Runtime package")
if(NOT ONNXRUNTIME_ROOT)
  message(FATAL_ERROR "Set ONNXRUNTIME_ROOT for R1199")
endif()

find_package(yaml-cpp REQUIRED)
find_library(ort_library NAMES onnxruntime libonnxruntime.so.1
  PATHS "${ONNXRUNTIME_ROOT}/lib" NO_DEFAULT_PATH REQUIRED)
add_library(as2w_r1199 r1199_controller.cpp)
target_include_directories(as2w_r1199 PUBLIC . "${ONNXRUNTIME_ROOT}/include" ../../../include)
target_link_libraries(as2w_r1199 PUBLIC "${ort_library}" yaml-cpp)

add_executable(as2w_r1199_replay r1199_replay.cpp)
target_link_libraries(as2w_r1199_replay PRIVATE as2w_r1199)

# Isolated forward candidate; the validated zero-B library and binary are
# not rebuilt with motion enabled. This target is for offline parity first.
option(AS2W_R1199_FORWARD_CANDIDATE "Build bounded forward trial candidate" OFF)
if(AS2W_R1199_FORWARD_CANDIDATE)
  add_library(as2w_r1199_forward r1199_controller.cpp)
  target_compile_definitions(as2w_r1199_forward PRIVATE AS2W_R1199_FORWARD_CANDIDATE=1)
  target_include_directories(as2w_r1199_forward PUBLIC . "${ONNXRUNTIME_ROOT}/include" ../../../include)
  target_link_libraries(as2w_r1199_forward PUBLIC "${ort_library}" yaml-cpp)
  add_executable(as2w_r1199_forward_replay r1199_replay.cpp)
  target_compile_definitions(as2w_r1199_forward_replay PRIVATE AS2W_R1199_FORWARD_CANDIDATE=1)
  target_link_libraries(as2w_r1199_forward_replay PRIVATE as2w_r1199_forward)
  if(AS2W_R1199_PUBLISH)
    find_package(unitree_sdk2 CONFIG REQUIRED)
    find_package(Threads REQUIRED)
    add_executable(as2w_r1199_forward_publish ../r214/r214_publish.cpp)
    target_compile_definitions(as2w_r1199_forward_publish PRIVATE
      AS2W_POLICY_R1199=1 AS2W_R1199_FORWARD_CANDIDATE=1
      AS2W_ENABLE_POLICY_ZERO_B_TRIAL=1)
    target_link_libraries(as2w_r1199_forward_publish PRIVATE
      as2w_r1199_forward unitree_sdk2 Threads::Threads)
    if(BUILD_TESTING)
      add_test(NAME r1199-forward-startup-audit COMMAND as2w_r1199_forward_publish
        "${CMAKE_SOURCE_DIR}/models/r1199/deploy.yaml"
        "${CMAKE_SOURCE_DIR}/config/r152_measured.map" --offline-audit)
    endif()
  endif()
endif()

# B is compile-time limited to one forced-zero, 2 s policy hold. No full
# motion target or launcher is provided for this candidate.
option(AS2W_R1199_PUBLISH "Build the gated R1199 FSM publisher" OFF)
option(AS2W_R1199_ZERO_B_TRIAL "Allow one bounded R1199 zero-B cycle" OFF)
if(AS2W_R1199_PUBLISH)
  find_package(unitree_sdk2 CONFIG REQUIRED)
  find_package(Threads REQUIRED)
  add_executable(as2w_r1199_publish ../r214/r214_publish.cpp)
  target_compile_definitions(as2w_r1199_publish PRIVATE AS2W_POLICY_R1199=1)
  target_link_libraries(as2w_r1199_publish PRIVATE as2w_r1199 unitree_sdk2 Threads::Threads)
  if(AS2W_R1199_ZERO_B_TRIAL)
    target_compile_definitions(as2w_r1199_publish PRIVATE AS2W_ENABLE_POLICY_ZERO_B_TRIAL=1)
  endif()
  if(BUILD_TESTING)
    add_test(NAME r1199-startup-frame-audit COMMAND as2w_r1199_publish
      "${CMAKE_SOURCE_DIR}/models/r1199/deploy.yaml"
      "${CMAKE_SOURCE_DIR}/config/r152_measured.map" --offline-audit)
  endif()
endif()

# Separate, bounded joystick candidate. It never changes the already-tested
# zero-B or automatic forward binaries and cannot be invoked as free motion.
option(AS2W_R1199_JOYSTICK_CANDIDATE "Build bounded joystick trial candidate" OFF)
option(AS2W_R1199_TRAINING_CONTRACT "Match R1199 model_1199 training stand-bias AND parking runtime (offline candidate)" OFF)
if(AS2W_R1199_TRAINING_CONTRACT AND NOT AS2W_R1199_JOYSTICK_CANDIDATE)
  message(FATAL_ERROR "TRAINING_CONTRACT requires JOYSTICK_CANDIDATE")
endif()
if(AS2W_R1199_JOYSTICK_CANDIDATE)
  add_library(as2w_r1199_joystick r1199_controller.cpp)
  target_compile_definitions(as2w_r1199_joystick PRIVATE AS2W_R1199_JOYSTICK_CANDIDATE=1)
  if(AS2W_R1199_TRAINING_CONTRACT)
    target_compile_definitions(as2w_r1199_joystick PRIVATE AS2W_R1199_TRAINING_CONTRACT=1)
  endif()
  target_include_directories(as2w_r1199_joystick PUBLIC . "${ONNXRUNTIME_ROOT}/include" ../../../include)
  target_link_libraries(as2w_r1199_joystick PUBLIC "${ort_library}" yaml-cpp)
  add_executable(as2w_r1199_joystick_replay r1199_replay.cpp)
  target_compile_definitions(as2w_r1199_joystick_replay PRIVATE AS2W_R1199_JOYSTICK_CANDIDATE=1)
  target_link_libraries(as2w_r1199_joystick_replay PRIVATE as2w_r1199_joystick)
  if(AS2W_R1199_PUBLISH)
    find_package(unitree_sdk2 CONFIG REQUIRED)
    find_package(Threads REQUIRED)
    add_executable(as2w_r1199_joystick_publish ../r214/r214_publish.cpp)
    target_compile_definitions(as2w_r1199_joystick_publish PRIVATE
      AS2W_POLICY_R1199=1 AS2W_R1199_JOYSTICK_CANDIDATE=1
      AS2W_ENABLE_POLICY_ZERO_B_TRIAL=1)
    target_link_libraries(as2w_r1199_joystick_publish PRIVATE
      as2w_r1199_joystick unitree_sdk2 Threads::Threads)
    if(BUILD_TESTING)
      add_test(NAME r1199-joystick-startup-audit COMMAND as2w_r1199_joystick_publish
        "${CMAKE_SOURCE_DIR}/models/r1199/deploy.yaml"
        "${CMAKE_SOURCE_DIR}/config/r152_measured.map" --offline-audit)
    endif()
  endif()
endif()
