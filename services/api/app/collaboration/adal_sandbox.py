"""Docker isolation and an allowlisted CONNECT bridge; no TLS interception.

The child has no network interface beyond loopback. A Unix socket exposes only
CONNECT to reviewed public HTTPS hosts. It never receives the backend environment.
"""

import hashlib
import ipaddress
import os
import re
import select
import socket
import socketserver
import threading
from pathlib import Path


def bundle_digest(directory):
    root = Path(directory).resolve(strict=True)
    hasher = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Runtime bundle cannot contain symlinks")
        if path.is_file():
            hasher.update(str(path.relative_to(root)).encode() + b"\0")
            hasher.update(hashlib.sha256(path.read_bytes()).digest())
    return hasher.hexdigest()


def validate_target(target, allowed, resolver=socket.getaddrinfo):
    host, separator, port = target.rpartition(":")
    if separator != ":" or port != "443" or host not in allowed or not re.fullmatch(r"[a-z0-9.-]+", host):
        raise ValueError("Egress target denied")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("Literal addresses are not provider hosts")
    addresses = resolver(host, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Private or unresolved provider address denied")
    return host, 443


def sandbox_command(image, workspace, bundle, auth, bridge_dir, *, name="sueperman-adal"):
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise ValueError("Local image digest required")
    work, code, credentials, bridge = (Path(p).resolve() for p in (workspace, bundle, auth, bridge_dir))
    if any("," in str(p) or "\n" in str(p) for p in [work, code, credentials, bridge]):
        raise ValueError("Unsafe mount path")
    if any(not p.is_dir() for p in [work, code, credentials]):
        raise ValueError("Prepared workspace, runtime bundle and scoped authentication directory required")
    uid, gid = os.getuid(), os.getgid()
    helper = Path(__file__).with_name("adal_bridge_child.py").resolve()
    return [
        "docker",
        "run",
        "--rm",
        "--init",
        "--interactive",
        "--pull=never",
        "--name",
        name,
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--memory=1g",
        "--cpus=1",
        "--user",
        f"{uid}:{gid}",
        "--tmpfs",
        f"/tmp:rw,nosuid,nodev,size=64m,uid={uid},gid={gid}",
        "--tmpfs",
        f"/home/adal:rw,nosuid,nodev,size=16m,uid={uid},gid={gid}",
        "--mount",
        f"type=bind,source={work},target={work}",
        "--mount",
        f"type=bind,source={code},target=/opt/adal,readonly",
        "--mount",
        f"type=bind,source={credentials},target=/home/adal/.adal,readonly",
        "--mount",
        f"type=bind,source={bridge},target=/run/egress,readonly",
        "--mount",
        f"type=bind,source={helper},target=/opt/bridge.py,readonly",
        "--workdir",
        str(work),
        "--env",
        "HOME=/home/adal",
        "--env",
        "HTTPS_PROXY=http://127.0.0.1:39081",
        "--env",
        "HTTP_PROXY=http://127.0.0.1:39081",
        image,
        "python",
        "/opt/bridge.py",
        "/opt/adal/adal",
        "--sdk-runtime",
    ]


def relay(first, second):
    """Bounded idle relay. TLS is established and verified by the original client."""
    while True:
        ready, _, _ = select.select([first, second], [], [], 10)
        if not ready:
            return
        for source in ready:
            data = source.recv(65536)
            if not data:
                return
            (second if source is first else first).sendall(data)


class EgressBridge:
    def __init__(self, path, allowed):
        self.path, self.allowed = Path(path), frozenset(allowed)
        if any(not re.fullmatch(r"[a-z0-9.-]+", h) or "." not in h for h in self.allowed):
            raise ValueError("Exact reviewed hostnames required; no wildcards")

    def __enter__(self):
        allowed = self.allowed

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(5)
                data = b""
                try:
                    while b"\r\n\r\n" not in data and len(data) <= 8192:
                        chunk = self.request.recv(1024)
                        if not chunk:
                            return
                        data += chunk
                    header, suffix = data.split(b"\r\n\r\n", 1)
                    method, target, version = header.split(b"\r\n", 1)[0].decode("ascii").split()
                    if method != "CONNECT" or version != "HTTP/1.1" or suffix:
                        raise ValueError("CONNECT only")
                    host, port = validate_target(target, allowed)
                    # Resolve once more and connect to a checked public address, not an unchecked DNS name.
                    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
                    address = addresses[0]
                    if not ipaddress.ip_address(address[4][0]).is_global:
                        raise ValueError("Private address denied")
                    with socket.socket(address[0], socket.SOCK_STREAM) as remote:
                        remote.settimeout(5)
                        remote.connect(address[4])
                        self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                        relay(self.request, remote)
                except (OSError, ValueError, UnicodeError):
                    try:
                        self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
                    except OSError:
                        pass

        class Server(socketserver.ThreadingUnixStreamServer):
            daemon_threads = True

        self.server = Server(str(self.path), Handler)
        os.chmod(self.path, 0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)
        self.path.unlink(missing_ok=True)
