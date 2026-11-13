cmake_minimum_required(VERSION 3.16)
project(as2w_r270_deploy LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(ONNXRUNTIME_ROOT "" CACHE PATH "Extracted ONNX Runtime package")
if(NOT ONNXRUNTIME_ROOT)
  message(FATAL_ERROR "Set ONNXRUNTIME_ROOT for R270")
endif()
find_package(yaml-cpp REQUIRED)
find_library(ort_library NAMES onnxruntime libonnxruntime.so.1
  PATHS "${ONNXRUNTIME_ROOT}/lib" NO_DEFAULT_PATH REQUIRED)
if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../../../include/isaaclab/algorithms/algorithms.h")
  message(FATAL_ERROR "Copy this AS2-W target into the pinned unitree_cpp_deploy checkout")
endif()

add_library(as2w_r270 r270_controller.cpp)
target_include_directories(as2w_r270 PUBLIC . "${ONNXRUNTIME_ROOT}/include" ../../../include)
target_link_libraries(as2w_r270 PUBLIC "${ort_library}" yaml-cpp)

add_executable(as2w_r270_smoke smoke.cpp)
target_link_libraries(as2w_r270_smoke PRIVATE as2w_r270)
if(BUILD_TESTING)
  add_test(NAME r270-controller-smoke COMMAND as2w_r270_smoke
    "${CMAKE_SOURCE_DIR}/models/r270/deploy.yaml")
endif()

option(AS2W_R270_PUBLISH "Build the gated R270 FSM LowCmd publisher" OFF)
option(AS2W_R270_STAND_TRIAL "Allow only the bounded A-to-fixed-PD stand trial" OFF)
option(AS2W_R270_ZERO_B_TRIAL "Allow only the bounded B zero-speed R270 trial" OFF)
option(AS2W_R270_FULL_MOTION "Allow the supervised low-speed R270 field session" OFF)
if(AS2W_R270_PUBLISH)
  find_package(unitree_sdk2 CONFIG REQUIRED)
  find_package(Threads REQUIRED)
  add_executable(as2w_r270_publish ../common/as2w_publish.cpp)
  target_compile_definitions(as2w_r270_publish PRIVATE AS2W_POLICY_R270=1)
  target_link_libraries(as2w_r270_publish PRIVATE as2w_r270 unitree_sdk2 Threads::Threads)
  if(AS2W_R270_STAND_TRIAL)
    target_compile_definitions(as2w_r270_publish PRIVATE AS2W_ENABLE_POLICY_STAND_TRIAL=1)
  endif()
  if(AS2W_R270_ZERO_B_TRIAL)
    target_compile_definitions(as2w_r270_publish PRIVATE AS2W_ENABLE_POLICY_ZERO_B_TRIAL=1)
  endif()
  if(AS2W_R270_FULL_MOTION)
    target_compile_definitions(as2w_r270_publish PRIVATE AS2W_ENABLE_POLICY_MOTION=1)
  endif()
  if(BUILD_TESTING)
    add_test(NAME r270-startup-frame-audit COMMAND as2w_r270_publish
      "${CMAKE_SOURCE_DIR}/models/r270/deploy.yaml"
      "${CMAKE_SOURCE_DIR}/config/r152_measured.map" --offline-audit)
  endif()
endif()


