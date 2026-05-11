// Minimal probe DLL: zero external dependencies (no CRT, no Qt, no CLO SDK).
// Drops a log line in ~/md_mcp_probe.log every time MD loads it, and another
// if MD ever calls the exported Create() factory. Lets us answer:
//   1. Does MD scan its Plugins folder for arbitrary DLLs at startup?
//   2. If yes, does MD invoke the CLO-style Create() entry point?

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

static void probe_log(const char* msg)
{
    char path[MAX_PATH];
    DWORD n = GetEnvironmentVariableA("USERPROFILE", path, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) return;
    lstrcatA(path, "\\md_mcp_probe.log");

    HANDLE h = CreateFileA(path,
        FILE_APPEND_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        NULL,
        OPEN_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    SetFilePointer(h, 0, NULL, FILE_END);

    SYSTEMTIME st;
    GetLocalTime(&st);

    char buf[1280];
    int len = wsprintfA(buf,
        "[%04d-%02d-%02d %02d:%02d:%02d.%03d] %s\r\n",
        st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
        msg);
    DWORD written = 0;
    WriteFile(h, buf, (DWORD)len, &written, NULL);
    CloseHandle(h);
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved)
{
    (void)lpReserved;
    if (reason == DLL_PROCESS_ATTACH) {
        char modPath[MAX_PATH] = "";
        char hostPath[MAX_PATH] = "";
        GetModuleFileNameA(hModule, modPath, MAX_PATH);
        GetModuleFileNameA(NULL,     hostPath, MAX_PATH);
        char msg[2 * MAX_PATH + 128];
        wsprintfA(msg, "DLL_PROCESS_ATTACH  module=%s  host=%s  pid=%lu",
            modPath, hostPath, (unsigned long)GetCurrentProcessId());
        probe_log(msg);
    }
    return TRUE;
}

// CLO-style plugin factory. Logs the call but returns null -- safe because we
// don't want anything else to happen; the host should detect "null plugin" and
// move on, or at worst crash after we have already logged.
extern "C" __declspec(dllexport) void* Create()
{
    probe_log("Create() was called by the host");
    return NULL;
}
