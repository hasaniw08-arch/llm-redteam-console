"""Local network adapter info including DHCP status (Windows)."""

from __future__ import annotations

import re
import socket
import subprocess
from dataclasses import dataclass, field
from typing import List


@dataclass
class AdapterInfo:
    name: str
    ipv4: str = ""
    subnet: str = ""
    gateway: str = ""
    dhcp_enabled: str = ""
    dhcp_server: str = ""
    mac: str = ""


@dataclass
class NetworkSnapshot:
    hostname: str = ""
    public_ip: str = ""
    internet_ok: bool = False
    adapters: List[AdapterInfo] = field(default_factory=list)
    summary_lines: List[str] = field(default_factory=list)


def _run_ipconfig() -> str:
    try:
        result = subprocess.run(
            ["ipconfig", "/all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.stdout or result.stderr or ""
    except Exception as exc:
        return f"ipconfig failed: {exc}"


def _parse_ipconfig(text: str) -> List[AdapterInfo]:
    adapters: List[AdapterInfo] = []
    blocks = re.split(r"(?=\r?\n[^\s].*:)", text)
    for block in blocks:
        header = re.search(r"^(.+?):\s*$", block.strip(), re.MULTILINE)
        if not header:
            continue
        name = header.group(1).strip()
        lower = name.lower()
        if "adapter" not in lower:
            continue
        if "disconnected" in block.lower() and "media disconnected" in block.lower():
            continue

        def find(pattern: str) -> str:
            m = re.search(pattern, block, re.IGNORECASE)
            return m.group(1).strip() if m else ""

        ipv4 = find(r"IPv4 Address[^:]*:\s*([\d\.]+)")
        if not ipv4:
            continue

        adapters.append(
            AdapterInfo(
                name=name,
                ipv4=ipv4,
                subnet=find(r"Subnet Mask[^:]*:\s*([\d\.]+)"),
                gateway=find(r"Default Gateway[^:]*:\s*([\d\.]+)"),
                dhcp_enabled=find(r"DHCP Enabled[^:]*:\s*(Yes|No)"),
                dhcp_server=find(r"DHCP Server[^:]*:\s*([\d\.]+)"),
                mac=find(r"Physical Address[^:]*:\s*([\w\-]+)"),
            )
        )
    return adapters


def _check_internet(timeout: float = 3.0) -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False


def _public_ip(timeout: float = 4.0) -> str:
    for host in ("api.ipify.org", "ifconfig.me"):
        try:
            with socket.create_connection((host, 80), timeout=timeout):
                pass
            req = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n".encode()
            with socket.create_connection((host, 80), timeout=timeout) as sock:
                sock.sendall(req)
                data = sock.recv(512).decode(errors="replace")
            body = data.split("\r\n\r\n", 1)[-1].strip()
            if body and len(body) < 64:
                return body
        except OSError:
            continue
    return "Unavailable"


def collect_network_info() -> NetworkSnapshot:
    snap = NetworkSnapshot()
    snap.hostname = socket.gethostname()
    snap.internet_ok = _check_internet()
    if snap.internet_ok:
        snap.public_ip = _public_ip()

    raw = _run_ipconfig()
    snap.adapters = _parse_ipconfig(raw)

    snap.summary_lines.append(f"Host: {snap.hostname}")
    snap.summary_lines.append(f"Internet: {'Connected (DHCP/LAN)' if snap.internet_ok else 'Offline'}")
    if snap.public_ip and snap.public_ip != "Unavailable":
        snap.summary_lines.append(f"Public IP: {snap.public_ip}")

    for ad in snap.adapters:
        snap.summary_lines.append("")
        snap.summary_lines.append(f"Adapter: {ad.name}")
        snap.summary_lines.append(f"  LAN IPv4: {ad.ipv4}")
        if ad.subnet:
            snap.summary_lines.append(f"  Subnet:   {ad.subnet}")
        if ad.gateway:
            snap.summary_lines.append(f"  Gateway:  {ad.gateway}")
        snap.summary_lines.append(f"  DHCP:     {ad.dhcp_enabled or 'Unknown'}")
        if ad.dhcp_server:
            snap.summary_lines.append(f"  DHCP Srv: {ad.dhcp_server}")
        if ad.mac:
            snap.summary_lines.append(f"  MAC:      {ad.mac}")

    if not snap.adapters:
        snap.summary_lines.append("")
        snap.summary_lines.append("No active LAN adapters found.")

    return snap
