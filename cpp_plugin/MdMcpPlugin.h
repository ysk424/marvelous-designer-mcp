#pragma once

#ifdef LIBRARYAPIIMPLEMENTATION_LIB
#define CLO_PLUGIN_SPECIFIER __declspec(dllexport)
#else
#define CLO_PLUGIN_SPECIFIER __declspec(dllimport)
#endif

// SDK's interface header pulls in <QWidget>; CMake adds Samples/LibraryWindowImplementation
// to the include path so this resolves.
#include "LibraryWindowInterface.h"

#include <memory>

class MdMcpServer;

namespace CLOAPI
{
// Our plugin pretends to be a LibraryWindow plugin so we get the DoFunctionStartUp()
// hook on MD's main thread at startup; we don't actually implement any library UI.
class CLO_PLUGIN_SPECIFIER MdMcpPlugin : public LibraryWindowInterface
{
public:
    MdMcpPlugin();
    ~MdMcpPlugin() override;

    // Disable every library-UI / sign-in / PLM feature -- we just want the startup hook.
    bool   EnableCustomUI() override       { return false; }
    bool   IsDefaultTab() override         { return false; }
    bool   IsSigninEnabled() override      { return false; }
    bool   IsPLMSettingsEnabled() override { return false; }

    // Generic plugin hooks (the actually useful part).
    bool        IsPluginEnabled() override { return true; }
    void        DoFunctionStartUp() override;
    const char* GetActionName() override   { return nullptr; }  // no menu action
    int         GetPositionIndexToAddAction() override { return -1; }

private:
    std::unique_ptr<MdMcpServer> m_server;
};
} // namespace CLOAPI

extern "C" CLO_PLUGIN_SPECIFIER CLOAPI::LibraryWindowInterface* Create();
