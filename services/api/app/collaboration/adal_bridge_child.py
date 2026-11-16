"""Inside the networkless child: bridge loopback proxy to the policy Unix socket."""

import select
import socket
import socketserver
import subprocess
import sys
import threading


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as remote:
            remote.connect("/run/egress/proxy.sock")
            while True:
                ready, _, _ = select.select([self.request, remote], [], [], 10)
                if not ready:
                    return
                for source in ready:
                    data = source.recv(65536)
                    if not data:
                        return
                    (remote if source is self.request else self.request).sendall(data)


if __name__ == "__main__":
    with socketserver.ThreadingTCPServer(("127.0.0.1", 39081), Handler) as server:
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            # Raw runtime stderr never enters application logs.
            result = subprocess.run(sys.argv[1:], stderr=subprocess.DEVNULL, check=False)
        finally:
            server.shutdown()
        sys.exit(result.returncode)
