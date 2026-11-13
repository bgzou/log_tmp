cmake_minimum_required(VERSION 3.16)
project(as2w_getup1199_deploy LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(ONNXRUNTIME_ROOT "" CACHE PATH "Extracted ONNX Runtime package")
if(NOT ONNXRUNTIME_ROOT)
  message(FATAL_ERROR "Set ONNXRUNTIME_ROOT for getup1199")
endif()

find_package(yaml-cpp REQUIRED)
find_library(ort_library NAMES onnxruntime libonnxruntime.so.1
  PATHS "${ONNXRUNTIME_ROOT}/lib" NO_DEFAULT_PATH REQUIRED)

# Recovery deep-side-curriculum model_1199 training contract (staged rise,
# low-support latch handoff, fixed-stand integral, predictive guard, wheel
# position hold) is the runtime of record for this policy. The library is
# always paired with its parity fixture
# (logs/20261113_getup1199_deploy_precheck/getup1199_fixture.txt).
option(AS2W_GETUP1199 "Build the getup1199 controller library" OFF)
option(AS2W_GETUP1199_PUBLISH "Build the gated getup1199 FSM publisher" OFF)
if(AS2W_GETUP1199)
  add_library(as2w_getup1199 getup1199_controller.cpp)
  target_include_directories(as2w_getup1199 PUBLIC . "${ONNXRUNTIME_ROOT}/include" ../../../include)
  target_link_libraries(as2w_getup1199 PUBLIC "${ort_library}" yaml-cpp)
  add_executable(as2w_getup1199_replay getup1199_replay.cpp)
  target_link_libraries(as2w_getup1199_replay PRIVATE as2w_getup1199)
  if(AS2W_GETUP1199_PUBLISH)
    find_package(unitree_sdk2 CONFIG REQUIRED)
    find_package(Threads REQUIRED)
    add_executable(as2w_getup1199_publish ../common/as2w_publish.cpp)
    target_compile_definitions(as2w_getup1199_publish PRIVATE
      AS2W_POLICY_GETUP1199=1 AS2W_ENABLE_GETUP_TRIAL=1)
    target_link_libraries(as2w_getup1199_publish PRIVATE
      as2w_getup1199 unitree_sdk2 Threads::Threads)
    if(BUILD_TESTING)
      add_test(NAME getup1199-startup-audit COMMAND as2w_getup1199_publish
        "${CMAKE_SOURCE_DIR}/models/getup1199/deploy.yaml"
        "${CMAKE_SOURCE_DIR}/config/r152_measured.map" --offline-audit)
    endif()
  endif()
endif()
