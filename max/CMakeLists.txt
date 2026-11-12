# SID1 Max external (sid1~). Build: cmake -S max -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build --config Release
cmake_minimum_required(VERSION 3.25)

# Runs on macOS 10.13+ (the user's Monterey included); set before project()
set(CMAKE_OSX_DEPLOYMENT_TARGET "10.13" CACHE STRING "Minimum macOS" FORCE)
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64" CACHE STRING "macOS architectures")

include(FetchContent)
FetchContent_Declare(
  max-sdk-base
  GIT_REPOSITORY https://github.com/Cycling74/max-sdk-base.git
  GIT_TAG c03a2922a2a8ff149165a1e2ea134e9321d6e202
)
FetchContent_MakeAvailable(max-sdk-base)

set(C74_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/externals")
project(SID1 C CXX)
set(AUTHOR_DOMAIN "com.transistorlabs")
set(COPYRIGHT_STRING "GPL-3.0, Transistor Labs / Ticco Ross")
add_subdirectory("sid1~")
