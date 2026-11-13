cmake_minimum_required(VERSION 3.16)
project(as2w_r284_deploy LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(ONNXRUNTIME_ROOT "" CACHE PATH "Extracted ONNX Runtime package")
if(NOT ONNXRUNTIME_ROOT)
  message(FATAL_ERROR "Set ONNXRUNTIME_ROOT for R284")
endif()
find_package(yaml-cpp REQUIRED)
find_library(ort_library NAMES onnxruntime libonnxruntime.so.1
  PATHS "${ONNXRUNTIME_ROOT}/lib" NO_DEFAULT_PATH REQUIRED)

add_library(as2w_r284 r284_controller.cpp)
target_include_directories(as2w_r284 PUBLIC . "${ONNXRUNTIME_ROOT}/include" ../../../include)
target_link_libraries(as2w_r284 PUBLIC "${ort_library}" yaml-cpp)

add_executable(as2w_r284_smoke smoke.cpp)
target_link_libraries(as2w_r284_smoke PRIVATE as2w_r284)
if(BUILD_TESTING)
  add_test(NAME r284-controller-smoke COMMAND as2w_r284_smoke
    "${CMAKE_SOURCE_DIR}/models/r284/deploy.yaml")
endif()

option(AS2W_R284_PUBLISH "Build the gated R284 FSM LowCmd publisher" OFF)
option(AS2W_R284_ZERO_B_TRIAL "Allow only the bounded B zero-speed R284 trial" OFF)
if(AS2W_R284_PUBLISH)
  find_package(unitree_sdk2 CONFIG REQUIRED)
  find_package(Threads REQUIRED)
  add_executable(as2w_r284_publish ../common/as2w_publish.cpp)
  target_compile_definitions(as2w_r284_publish PRIVATE AS2W_POLICY_R284=1)
  target_link_libraries(as2w_r284_publish PRIVATE as2w_r284 unitree_sdk2 Threads::Threads)
  if(AS2W_R284_ZERO_B_TRIAL)
    target_compile_definitions(as2w_r284_publish PRIVATE AS2W_ENABLE_POLICY_ZERO_B_TRIAL=1)
  endif()
  if(BUILD_TESTING)
    add_test(NAME r284-startup-frame-audit COMMAND as2w_r284_publish
      "${CMAKE_SOURCE_DIR}/models/r284/deploy.yaml"
      "${CMAKE_SOURCE_DIR}/config/r152_measured.map" --offline-audit)
  endif()
endif()

