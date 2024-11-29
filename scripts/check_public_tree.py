"""Fail on high-risk tracked file types and non-documentation IPv4 literals."""

import hashlib
import ipaddress
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NETWORKS = tuple(ipaddress.ip_network(value) for value in (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "127.0.0.0/8",
))
SAMPLE_XLSX_SHA256 = "f1ff7c84a001379b3e03c08286131fc55e8de4b9c7eb17e1efd3f6346368c20f"
BLOCKED = {".docx", ".xlsx", ".pptx", ".bin", ".log", ".zip", ".bundle", ".ipynb", ".pem", ".key"}


def main():
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    problems = []
    for name in filter(None, names):
        path = ROOT / name
        if name == "tools/account_list.xlsx":
            if hashlib.sha256(path.read_bytes()).hexdigest() != SAMPLE_XLSX_SHA256:
                problems.append((name, "account sample changed; review before updating its approved hash"))
            continue
        if path.suffix.lower() in BLOCKED or name.endswith(".local.json") or path.name.startswith(".env"):
            problems.append((name, "private or binary artifact"))
            continue
        content = path.read_text(encoding="utf-8")
        # Kernel build versions may contain four numeric components.
        addresses = re.sub(r"(?m)^系统内核版本\s*[:：]\s*[0-9A-Za-z_.+-]+[ \t]*$", "", content)
        for candidate in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", addresses):
            try:
                address = ipaddress.ip_address(candidate)
            except ValueError:
                continue
            if not any(address in network for network in NETWORKS):
                problems.append((name, "non-example address"))
        if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", content):
            problems.append((name, "private key marker"))
    for name, kind in problems:
        print(f"{name}: {kind}")
    print(f"Public-tree check: {len(problems)} issue(s). This is a guardrail, not a complete secret scanner.")
    return bool(problems)


if __name__ == "__main__":
    raise SystemExit(main())
