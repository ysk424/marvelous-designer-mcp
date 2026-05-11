cmake_minimum_required(VERSION 3.20)

# Defaults match this dev machine. Override on the command line for portability:
#   cmake -S . -B build -DQTDIR=... -DCLO_SDK=...
if (NOT DEFINED QTDIR)
    set(QTDIR "C:/Qt/6.10.3/msvc2022_64")
endif()
if (NOT DEFINED CLO_SDK)
    set(CLO_SDK "C:/Users/azoo/SDK/CLO_SDK_v2026.0.238/CLO_SDK_v2026.0.238_Win")
endif()
message("QTDIR:   ${QTDIR}")
message("CLO_SDK: ${CLO_SDK}")

set(CMAKE_AUTOMOC ON)
set(CMAKE_INCLUDE_CURRENT_DIR ON)

project(MdMcpPlugin
    DESCRIPTION "Marvelous Designer MCP listener (C++ plugin, non-freezing)"
    VERSION 0.2.0
    LANGUAGES CXX
)

add_library(${PROJECT_NAME} SHARED)

set_target_properties(${PROJECT_NAME} PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

if (MSVC)
    set_target_properties(${PROJECT_NAME} PROPERTIES
        MSVC_RUNTIME_LIBRARY "MultiThreadedDLL"
    )
    target_compile_definitions(${PROJECT_NAME} PRIVATE
        UNICODE
        WIN32
        QT_NO_DEBUG
        NDEBUG
        LIBRARYAPIIMPLEMENTATION_LIB
        CLO_SCENE_LIB_STATIC
    )
endif()

# Sources
target_sources(${PROJECT_NAME} PRIVATE
    dllmain.cpp
    stdafx.cpp
    stdafx.h
    targetver.h
    MdMcpPlugin.cpp
    MdMcpPlugin.h
    MdMcpServer.cpp
    MdMcpServer.h
)

# CLO SDK: headers + import-lib for CLOAPIInterface.dll. At runtime the symbols
# resolve against MD's already-loaded CLOAPIInterface.dll inside the same process.
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CLO_SDK}/CLOAPIInterface
    ${CLO_SDK}/Samples/LibraryWindowImplementation
)
find_library(CLO_API_INTERFACE
    NAMES CLOAPIInterface
    HINTS ${CLO_SDK}/CLOAPIInterface/Lib
    REQUIRED
)

# Qt
set(Qt6_DIR ${QTDIR}/lib/cmake/Qt6)
set(CMAKE_PROGRAM_PATH ${QTDIR}/bin)
find_package(Qt6 6.10 REQUIRED COMPONENTS Core)

target_link_libraries(${PROJECT_NAME} PRIVATE
    Qt6::Core
    ${CLO_API_INTERFACE}
    ws2_32
)

# --- Diagnostic probe DLL ----------------------------------------------------
# No CRT/Qt/CLO deps. Used to determine empirically whether MD loads arbitrary
# DLLs from the Plugins folder at startup, and whether it calls Create().
add_library(MdMcpProbe SHARED probe.cpp)
set_target_properties(MdMcpProbe PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)
if (MSVC)
    set_target_properties(MdMcpProbe PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
    target_compile_definitions(MdMcpProbe PRIVATE UNICODE WIN32 NDEBUG)
    target_link_options(MdMcpProbe PRIVATE /NODEFAULTLIB:libcmt /NODEFAULTLIB:libcpmt)
endif()
target_link_libraries(MdMcpProbe PRIVATE user32 kernel32)
