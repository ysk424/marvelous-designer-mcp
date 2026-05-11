#include "stdafx.h"
#include "MdMcpPlugin.h"
#include "MdMcpServer.h"

namespace CLOAPI
{
MdMcpPlugin::MdMcpPlugin() = default;
MdMcpPlugin::~MdMcpPlugin() = default;

void MdMcpPlugin::DoFunctionStartUp()
{
    if (m_server) return;
    m_server.reset(new MdMcpServer());
    m_server->start(7421);
}
} // namespace CLOAPI

extern "C" CLO_PLUGIN_SPECIFIER CLOAPI::LibraryWindowInterface* Create()
{
    return new CLOAPI::MdMcpPlugin();
}
