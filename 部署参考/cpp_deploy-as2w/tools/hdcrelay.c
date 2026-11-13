/* hdcrelay: CPRO 宿主上的微型 TCP 中继。
 * 该设备固件的 hdcd TCP 监听只接受 lo 接口进入的连接，外部 WiFi/以太网 SYN 被静默丢弃。
 * 本工具在指定 IP 上监听普通端口，把数据原样转发到 127.0.0.1:8710，使
 * `hdc tconn <IP>:<LISTEN_PORT>` 可以走无线链路。用法：
 *   hdcrelay LISTEN_IP LISTEN_PORT TARGET_IP TARGET_PORT
 * 自行 daemon 化；日志写 /data/local/tmp/as2w_field/hdcrelay.log。
 * 在 CPRO Ubuntu chroot 内静态编译后，拷贝到 /data/local/tmp/as2w_field/ 原生运行。
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define LOG_PATH "/data/local/tmp/as2w_field/hdcrelay.log"

static FILE *g_log;

static void logline(const char *fmt, ...)
{
    if (!g_log) return;
    char ts[32];
    time_t t = time(NULL);
    struct tm tmv;
    localtime_r(&t, &tmv);
    strftime(ts, sizeof ts, "%Y-%m-%d %H:%M:%S", &tmv);
    va_list ap;
    va_start(ap, fmt);
    fprintf(g_log, "[%s pid=%d] ", ts, (int)getpid());
    vfprintf(g_log, fmt, ap);
    fputc('\n', g_log);
    fflush(g_log);
    va_end(ap);
}

static int make_conn(const char *ip, int port)
{
    struct sockaddr_in a;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_port = htons((unsigned short)port);
    if (inet_pton(AF_INET, ip, &a.sin_addr) != 1) return -1;
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) return -1;
    if (connect(s, (struct sockaddr *)&a, sizeof a) < 0) { close(s); return -1; }
    return s;
}

static void set_nodelay(int s)
{
    int one = 1;
    setsockopt(s, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one);
}

static void fwd(int from, int to, int *eof_from, int *eof_other)
{
    char buf[65536];
    ssize_t n = recv(from, buf, sizeof buf, 0);
    if (n <= 0) {
        *eof_from = 1;
        shutdown(to, SHUT_WR);
        return;
    }
    ssize_t off = 0;
    while (off < n) {
        ssize_t m = send(to, buf + off, (size_t)(n - off), MSG_NOSIGNAL);
        if (m <= 0) { *eof_other = 1; shutdown(from, SHUT_WR); return; }
        off += m;
    }
}

static void pump(int c, int b)
{
    int eof_c = 0, eof_b = 0;
    while (!(eof_c && eof_b)) {
        fd_set rs;
        FD_ZERO(&rs);
        if (!eof_c) FD_SET(c, &rs);
        if (!eof_b) FD_SET(b, &rs);
        int mx = (c > b ? c : b) + 1;
        int r = select(mx, &rs, NULL, NULL, NULL);
        if (r < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (!eof_c && FD_ISSET(c, &rs)) fwd(c, b, &eof_c, &eof_b);
        if (!eof_b && FD_ISSET(b, &rs)) fwd(b, c, &eof_b, &eof_c);
    }
}

int main(int argc, char **argv)
{
    if (argc != 5) {
        fprintf(stderr, "usage: %s LISTEN_IP LISTEN_PORT TARGET_IP TARGET_PORT\n", argv[0]);
        return 2;
    }
    const char *lip = argv[1];
    int lport = atoi(argv[2]);
    const char *tip = argv[3];
    int tport = atoi(argv[4]);
    if (lport <= 0 || lport > 65535 || tport <= 0 || tport > 65535) {
        fprintf(stderr, "invalid port\n");
        return 2;
    }

    pid_t p = fork();
    if (p < 0) { perror("fork"); return 1; }
    if (p > 0) return 0;
    setsid();
    chdir("/");

    g_log = fopen(LOG_PATH, "a");
    int dn = open("/dev/null", O_RDWR);
    if (dn >= 0) { dup2(dn, 0); dup2(dn, 1); dup2(dn, 2); if (dn > 2) close(dn); }

    signal(SIGCHLD, SIG_IGN);
    signal(SIGPIPE, SIG_IGN);

    int ls = socket(AF_INET, SOCK_STREAM, 0);
    if (ls < 0) { logline("socket failed: %s", strerror(errno)); return 1; }
    int one = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);

    struct sockaddr_in la;
    memset(&la, 0, sizeof la);
    la.sin_family = AF_INET;
    la.sin_port = htons((unsigned short)lport);
    if (inet_pton(AF_INET, lip, &la.sin_addr) != 1) {
        logline("bad listen ip %s", lip);
        return 1;
    }
    if (bind(ls, (struct sockaddr *)&la, sizeof la) < 0) {
        logline("bind %s:%d failed: %s (already running?)", lip, lport, strerror(errno));
        return 1;
    }
    if (listen(ls, 16) < 0) {
        logline("listen failed: %s", strerror(errno));
        return 1;
    }
    logline("hdcrelay up: %s:%d -> %s:%d", lip, lport, tip, tport);

    for (;;) {
        struct sockaddr_in ca;
        socklen_t cl = sizeof ca;
        int c = accept(ls, (struct sockaddr *)&ca, &cl);
        if (c < 0) {
            if (errno == EINTR) continue;
            logline("accept failed: %s", strerror(errno));
            sleep(1);
            continue;
        }
        char peer[64];
        snprintf(peer, sizeof peer, "%s:%u", inet_ntoa(ca.sin_addr), (unsigned)ntohs(ca.sin_port));
        pid_t cp = fork();
        if (cp < 0) {
            logline("fork failed: %s", strerror(errno));
            close(c);
            continue;
        }
        if (cp == 0) {
            close(ls);
            int b = make_conn(tip, tport);
            if (b < 0) {
                logline("conn %s: backend %s:%d unreachable (%s)", peer, tip, tport, strerror(errno));
                close(c);
                _exit(1);
            }
            set_nodelay(c);
            set_nodelay(b);
            logline("conn %s open", peer);
            pump(c, b);
            close(c);
            close(b);
            logline("conn %s closed", peer);
            _exit(0);
        }
        close(c);
    }
}
