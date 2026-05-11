#pragma once

#include <QObject>
#include <QByteArray>
#include <atomic>
#include <thread>

// Lives on MD's main (Qt) thread. A worker thread runs the WinSock accept loop
// and marshals each request back to this object via Qt::BlockingQueuedConnection
// so CLO API calls happen on the main thread.
class MdMcpServer : public QObject
{
    Q_OBJECT
public:
    explicit MdMcpServer(QObject* parent = nullptr);
    ~MdMcpServer() override;

    void start(quint16 port);
    void stop();

    // Invoked from the worker thread on the main thread via BlockingQueuedConnection.
    Q_INVOKABLE QByteArray handleRequestOnMain(QByteArray requestLine);

private:
    void workerLoop(quint16 port);

    std::thread       m_worker;
    std::atomic<bool> m_stop{false};
    // Stored as 64-bit so SOCKET (uintptr_t) round-trips on Win64 without pulling in <winsock2.h> here.
    std::atomic<quint64> m_listenSocket{0};
};
