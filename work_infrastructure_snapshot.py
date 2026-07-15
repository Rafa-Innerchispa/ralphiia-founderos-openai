#!/usr/bin/env python3
"""Collect a secret-free, read-only infrastructure snapshot for RalphiIA."""

from __future__ import annotations

import json
import platform
import re
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
        return (result.stdout or result.stderr).strip()
    except Exception:
        return ""


def version(command: list[str]) -> str | None:
    value = run(command)
    return value.splitlines()[0][:120] if value else None


def classify_bind(address: str) -> str:
    if address.startswith("127.") or address == "::1":
        return "loopback"
    if address.startswith("100.") or address.startswith("fd7a:"):
        return "tailscale"
    if address in {"0.0.0.0", "*", "[::]"} or address.startswith("192.168."):
        return "lan_or_all"
    return "other"


def listeners() -> list[dict[str, str | int]]:
    output = run(["ss", "-lntH"])
    rows: list[dict[str, str | int]] = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        local = fields[3]
        address, _, port = local.rpartition(":")
        if not port.isdigit():
            continue
        address = address.strip("[]") or "*"
        rows.append({"address": address, "port": int(port), "scope": classify_bind(address)})
    return sorted(rows, key=lambda row: (int(row["port"]), str(row["address"])))


def services() -> list[str]:
    output = run(["systemctl", "list-units", "--type=service", "--state=running", "--no-legend"])
    names = []
    for line in output.splitlines():
        name = line.split(None, 1)[0] if line.split(None, 1) else ""
        if name.endswith(".service"):
            names.append(name)
    return sorted(set(names))


def snapshot() -> dict[str, object]:
    tailscale = run(["tailscale", "ip", "-4"])
    ips = run(["hostname", "-I"]).split()
    return {
        "schema_version": "infrastructure.snapshot.v1",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "os": platform.platform(),
        "architecture": platform.machine(),
        "user": run(["id", "-un"]),
        "lan_ips": [ip for ip in ips if re.match(r"^192\\.168\\.", ip)],
        "tailscale_ipv4": tailscale if re.match(r"^100\\.", tailscale) else None,
        "tools": {
            "codex": version(["codex", "--version"]),
            "node": version(["node", "--version"]),
            "npm": version(["npm", "--version"]),
            "python": version(["python3", "--version"]),
            "git": version(["git", "--version"]),
            "tmux": version(["tmux", "-V"]),
        },
        "listeners": listeners(),
        "running_services": services(),
        "secret_policy": "No credentials, tokens, keys, environment values or process arguments are collected.",
    }


def main() -> None:
    print(json.dumps(snapshot(), ensure_ascii=True, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
