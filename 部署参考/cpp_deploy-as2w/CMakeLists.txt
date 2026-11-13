cmake_minimum_required(VERSION 3.16)
project(cpp_deploy_as2w LANGUAGES CXX)

add_library(as2w_policy src/policy.cpp)
target_compile_features(as2w_policy PUBLIC cxx_std_17)
target_include_directories(as2w_policy PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/src")
if(MSVC)
  target_compile_options(as2w_policy PRIVATE /W4)
else()
  target_compile_options(as2w_policy PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(as2w_deploy src/main.cpp)
target_link_libraries(as2w_deploy PRIVATE as2w_policy)

add_executable(as2w_bench src/benchmark.cpp)
target_link_libraries(as2w_bench PRIVATE as2w_policy)

include(CTest)
if(BUILD_TESTING)
  foreach(name recovery-r09 recovery-r12 recovery-r13 stairs-r14 stairs-r17-2000 stairs-r17-3000)
    add_test(NAME ${name} COMMAND as2w_deploy verify
      "${CMAKE_CURRENT_SOURCE_DIR}/models/${name}.bin"
      "${CMAKE_CURRENT_SOURCE_DIR}/models/${name}.fixture")
  endforeach()
  add_executable(as2w_controller_test src/controller_test.cpp)
  target_link_libraries(as2w_controller_test PRIVATE as2w_policy)
  add_test(NAME controller COMMAND as2w_controller_test
    "${CMAKE_CURRENT_SOURCE_DIR}/models/recovery-r12.bin"
    "${CMAKE_CURRENT_SOURCE_DIR}/models/stairs-r17-3000.bin")
endif()

option(AS2W_WITH_SDK2 "Build AS2 SDK2 read-only and high-level diagnostic tool" OFF)
if(AS2W_WITH_SDK2)
  find_package(unitree_sdk2 CONFIG REQUIRED)
  find_package(Threads REQUIRED)
  add_executable(as2w_sdk2 deploy/robots/as2w/src/diagnostics.cpp)
  target_link_libraries(as2w_sdk2 PRIVATE as2w_policy unitree_sdk2 Threads::Threads)
  if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    add_executable(as2w_sport_gamepad deploy/robots/as2w/src/sport_gamepad.cpp)
    target_link_libraries(as2w_sport_gamepad PRIVATE unitree_sdk2 Threads::Threads)
    target_compile_features(as2w_sport_gamepad PRIVATE cxx_std_17)
  endif()
endif()

option(AS2W_R41 "Build the R41 ONNX stairs controller (needs -DONNXRUNTIME_ROOT and yaml-cpp)" OFF)
if(AS2W_R41)
  add_subdirectory(deploy/robots/as2w/r41)
endif()

option(AS2W_R152 "Build the R152 ONNX stairs controller (needs -DONNXRUNTIME_ROOT and yaml-cpp)" OFF)
if(AS2W_R152)
  add_subdirectory(deploy/robots/as2w/r152)
endif()

option(AS2W_R214 "Build the R214 ONNX stairs controller (read-only targets)" OFF)
if(AS2W_R214)
  add_subdirectory(deploy/robots/as2w/r214)
endif()

option(AS2W_R249 "Build the R249 flat low-speed ONNX controller" OFF)
if(AS2W_R249)
  add_subdirectory(deploy/robots/as2w/r249)
endif()

option(AS2W_R270 "Build the R270 history ONNX controller" OFF)
if(AS2W_R270)
  add_subdirectory(deploy/robots/as2w/r270)
endif()

option(AS2W_R284 "Build the R284 zero-wheel-memory ONNX controller" OFF)
if(AS2W_R284)
  add_subdirectory(deploy/robots/as2w/r284)
endif()

option(AS2W_R1199 "Build the R1199 zero-command candidate controller" OFF)
if(AS2W_R1199)
  add_subdirectory(deploy/robots/as2w/r1199)
endif()

option(AS2W_R4000 "Build the R4000 rolling-4000 candidate controller" OFF)
if(AS2W_R4000)
  add_subdirectory(deploy/robots/as2w/r4000)
endif()

option(AS2W_GETUP1199 "Build the getup1199 recovery deep-side candidate controller" OFF)
if(AS2W_GETUP1199)
  add_subdirectory(deploy/robots/as2w/getup1199)
endif()
