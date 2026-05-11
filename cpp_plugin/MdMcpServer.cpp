#include "stdafx.h"
#include "MdMcpServer.h"

// CLO API
#include "CLOAPIInterface.h"

// Qt
#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QMetaObject>
#include <QString>
#include <QTextStream>

// WinSock
#include <winsock2.h>
#include <ws2tcpip.h>

namespace
{
void mcpLog(const QString& msg)
{
    static const QString path = QDir::homePath() + "/md_mcp_listener.log";
    QFile f(path);
    if (f.open(QIODevice::Append | QIODevice::Text)) {
        QTextStream ts(&f);
        ts << QDateTime::currentDateTime().toString("[yyyy-MM-dd hh:mm:ss] ")
           << "[cpp] " << msg << "\n";
    }
}

QString stdToQ(const std::string& s) { return QString::fromUtf8(s.data(), int(s.size())); }
std::string qToStd(const QString& s)
{
    QByteArray b = s.toUtf8();
    return std::string(b.constData(), b.size());
}

QByteArray encode(const QJsonValue& id, const QJsonValue& result)
{
    QJsonObject o;
    o["id"] = id;
    o["result"] = result;
    return QJsonDocument(o).toJson(QJsonDocument::Compact) + "\n";
}

QByteArray encodeError(const QJsonValue& id, const QString& error)
{
    QJsonObject o;
    o["id"] = id;
    o["error"] = error;
    return QJsonDocument(o).toJson(QJsonDocument::Compact) + "\n";
}
} // namespace

MdMcpServer::MdMcpServer(QObject* parent) : QObject(parent) {}

MdMcpServer::~MdMcpServer() { stop(); }

void MdMcpServer::start(quint16 port)
{
    if (m_worker.joinable()) return;
    m_stop = false;
    m_worker = std::thread([this, port] { workerLoop(port); });
}

void MdMcpServer::stop()
{
    if (m_stop.exchange(true)) return;
    quint64 s = m_listenSocket.exchange(0);
    if (s != 0) {
        closesocket(static_cast<SOCKET>(s)); // unblock accept()
    }
    // Don't join from the main thread: the worker may be in BlockingQueuedConnection
    // back to us, which would deadlock. The worker is short-lived and exits when
    // m_stop is observed or the listening socket is closed.
    if (m_worker.joinable()) {
        m_worker.detach();
    }
}

void MdMcpServer::workerLoop(quint16 port)
{
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        mcpLog("WSAStartup failed");
        return;
    }

    SOCKET srv = socket(AF_INET, SOCK_STREAM, 0);
    if (srv == INVALID_SOCKET) {
        mcpLog(QString("socket() failed: %1").arg(WSAGetLastError()));
        WSACleanup();
        return;
    }

    int yes = 1;
    setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, reinterpret_cast<const char*>(&yes), sizeof(yes));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);

    if (bind(srv, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        mcpLog(QString("bind 127.0.0.1:%1 failed: %2 -- another listener already running?")
                   .arg(port).arg(WSAGetLastError()));
        closesocket(srv);
        WSACleanup();
        return;
    }
    if (listen(srv, 4) != 0) {
        mcpLog(QString("listen failed: %1").arg(WSAGetLastError()));
        closesocket(srv);
        WSACleanup();
        return;
    }

    // Short accept timeout so we can notice m_stop without waiting for a connection.
    DWORD timeoutMs = 500;
    setsockopt(srv, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&timeoutMs), sizeof(timeoutMs));

    m_listenSocket = static_cast<quint64>(srv);
    mcpLog(QString("listening on 127.0.0.1:%1 (MD GUI stays responsive)").arg(port));

    while (!m_stop) {
        sockaddr_in client_addr{};
        int alen = sizeof(client_addr);
        SOCKET conn = accept(srv, reinterpret_cast<sockaddr*>(&client_addr), &alen);
        if (conn == INVALID_SOCKET) {
            int err = WSAGetLastError();
            if (err == WSAETIMEDOUT || err == WSAEWOULDBLOCK) continue;
            if (m_stop) break;
            mcpLog(QString("accept failed: %1").arg(err));
            break;
        }

        // Read one JSON line.
        QByteArray buf;
        const int max_request = 16 * 1024 * 1024; // 16 MB safety cap
        char tmp[65536];
        while (!buf.contains('\n') && buf.size() < max_request) {
            int n = recv(conn, tmp, sizeof(tmp), 0);
            if (n <= 0) break;
            buf.append(tmp, n);
        }

        if (buf.contains('\n')) {
            QByteArray line = buf.left(buf.indexOf('\n'));
            QByteArray response;
            // Marshal the actual work onto the main thread (where MD's API lives).
            QMetaObject::invokeMethod(this, "handleRequestOnMain",
                Qt::BlockingQueuedConnection,
                Q_RETURN_ARG(QByteArray, response),
                Q_ARG(QByteArray, line));
            int sent = 0;
            const char* p = response.constData();
            int remaining = int(response.size());
            while (remaining > 0) {
                int n = send(conn, p + sent, remaining, 0);
                if (n <= 0) break;
                sent += n;
                remaining -= n;
            }
        }

        closesocket(conn);
    }

    m_listenSocket = 0;
    closesocket(srv);
    WSACleanup();
    mcpLog("listener stopped");
}

// ============== MAIN-THREAD DISPATCH ==============
QByteArray MdMcpServer::handleRequestOnMain(QByteArray requestLine)
{
    QJsonParseError jerr;
    QJsonDocument doc = QJsonDocument::fromJson(requestLine, &jerr);
    if (jerr.error != QJsonParseError::NoError || !doc.isObject()) {
        return encodeError(QJsonValue::Null,
                           QString("bad json: %1").arg(jerr.errorString()));
    }
    const QJsonObject req = doc.object();
    const QJsonValue  id      = req.value("id");
    const QString     method  = req.value("method").toString();
    const QJsonObject params  = req.value("params").toObject();

    using namespace CLOAPI;
    APICommand& cmd = APICommand::getInstance();

    try {
        if (method == "ping") {
            return encode(id, QJsonObject{{"pong", true}});
        }

        if (method == "shutdown") {
            // Kick the worker out of accept() then have it exit cleanly.
            QMetaObject::invokeMethod(this, [this]() { stop(); }, Qt::QueuedConnection);
            return encode(id, QJsonObject{{"bye", true}});
        }

        if (method == "scene_info") {
            auto* uti = cmd.GetUtilityAPI();
            auto* pat = cmd.GetPatternAPI();
            auto* fab = cmd.GetFabricAPI();
            QJsonObject r;
            r["project_name"] = stdToQ(uti->GetProjectName());
            r["project_path"] = stdToQ(uti->GetProjectFilePath());
            r["md_version"]   = QJsonArray{
                int(uti->GetMajorVersion()),
                int(uti->GetMinorVersion()),
                int(uti->GetPatchVersion())};
            r["pattern_count"] = pat->GetPatternCount();
            r["fabric_count"]  = int(fab->GetFabricCount(true));
            QJsonArray styles;
            for (const auto& s : fab->GetFabricStyleNameList()) styles.append(stdToQ(s));
            r["fabric_styles"] = styles;
            return encode(id, r);
        }

        if (method == "list_patterns") {
            auto* pat = cmd.GetPatternAPI();
            const int n = pat->GetPatternCount();
            QJsonArray arr;
            for (int i = 0; i < n; ++i) {
                QJsonObject o;
                o["index"]        = i;
                o["name"]         = stdToQ(pat->GetPatternPieceName(i));
                o["fabric_index"] = pat->GetPatternPieceFabricIndex(i);
                arr.append(o);
            }
            return encode(id, arr);
        }

        if (method == "list_fabrics") {
            auto* fab = cmd.GetFabricAPI();
            const int n = int(fab->GetFabricCount(true));
            QJsonArray arr;
            for (int i = 0; i < n; ++i) {
                arr.append(QJsonObject{{"index", i}, {"name", stdToQ(fab->GetFabricName(i))}});
            }
            QJsonArray styles;
            for (const auto& s : fab->GetFabricStyleNameList()) styles.append(stdToQ(s));
            return encode(id, QJsonObject{{"fabrics", arr}, {"styles", styles}});
        }

        if (method == "assign_fabric") {
            auto* fab = cmd.GetFabricAPI();
            const unsigned int fi = static_cast<unsigned int>(params.value("fabric_index").toInt());
            const unsigned int pi = static_cast<unsigned int>(params.value("pattern_index").toInt());
            const int face        = params.value("face").toInt(2);
            const bool ok = fab->AssignFabricToPattern(fi, pi, face);
            return encode(id, QJsonObject{{"ok", ok}});
        }

        if (method == "import_project") {
            auto* imp = cmd.GetImportAPI();
            const std::string path = qToStd(params.value("path").toString());
            const bool ok = imp->ImportFile(path);
            return encode(id, QJsonObject{
                {"ok", ok}, {"used", "ImportFile"}, {"path", stdToQ(path)}});
        }

        if (method == "export_project") {
            auto* exp = cmd.GetExportAPI();
            const std::string path = qToStd(params.value("path").toString());
            const std::string saved = exp->ExportZPrj(path, false);
            return encode(id, QJsonObject{
                {"ok", !saved.empty()},
                {"used", "ExportZPrj"},
                {"returned", stdToQ(saved)}});
        }

        if (method == "simulate") {
            auto* uti = cmd.GetUtilityAPI();
            const unsigned int steps = static_cast<unsigned int>(params.value("steps").toInt(1));
            const bool ok = uti->Simulate(steps);
            return encode(id, QJsonObject{
                {"ok", ok}, {"returned", ok}, {"steps", int(steps)}});
        }

        if (method == "execute_python" || method == "md_api") {
            return encodeError(id, QString("'%1' is not implemented in the v0.2 C++ plugin yet; "
                                           "fall back to the v0.1 Python listener for arbitrary code "
                                           "or API introspection.").arg(method));
        }

        return encodeError(id, QString("unknown method: %1").arg(method));
    }
    catch (const std::exception& e) {
        return encodeError(id, QString("c++ exception: %1").arg(QString::fromUtf8(e.what())));
    }
    catch (...) {
        return encodeError(id, "unknown c++ exception");
    }
}
