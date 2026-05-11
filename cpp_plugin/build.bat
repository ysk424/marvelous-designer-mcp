@echo off
setlocal ENABLEDELAYEDEXPANSION

rem Build the MD MCP C++ plugin. Run from the cpp_plugin directory or from anywhere.
rem Override QTDIR / CLO_SDK on the command line if your install paths differ.

set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
set "CMAKE=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"

if not exist "%VCVARS%" (
    echo [build] vcvars64.bat not found at: %VCVARS%
    echo Edit build.bat or install VS2022 ^(Community^) with the Desktop C++ workload.
    exit /b 1
)
if not exist "%CMAKE%" (
    echo [build] cmake not found at: %CMAKE%
    echo Install VS2022's C++ CMake tools, or set CMAKE to a standalone cmake.exe.
    exit /b 1
)

call "%VCVARS%" || exit /b 1

pushd "%~dp0"

if "%QTDIR%"=="" set "QTDIR=C:/Qt/6.10.3/msvc2022_64"
if "%CLO_SDK%"=="" set "CLO_SDK=C:/Users/azoo/SDK/CLO_SDK_v2026.0.238/CLO_SDK_v2026.0.238_Win"

echo [build] QTDIR=%QTDIR%
echo [build] CLO_SDK=%CLO_SDK%

"%CMAKE%" -S . -B build -G "Visual Studio 17 2022" -A x64 ^
    -DQTDIR="%QTDIR%" -DCLO_SDK="%CLO_SDK%" || (popd & exit /b 1)

"%CMAKE%" --build build --config Release -j || (popd & exit /b 1)

echo.
echo [build] OK. Output: %CD%\build\Release\MdMcpPlugin.dll
popd
endlocal
