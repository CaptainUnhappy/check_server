"""Authorized SSH collection. No connection is made by the offline demo."""

import json
import os
from pathlib import Path
import re
import shlex
import time

import paramiko

ALIAS = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")
REMOTE_DIR = re.compile(r"/tmp/check-server\.[A-Za-z0-9]{8}")
MAX_REPORT_BYTES = 2 * 1024 * 1024


def read_inventory(path):
    path = Path(path)
    if not path.name.endswith(".local.json"):
        raise ValueError("use an ignored *.local.json inventory")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    hosts = data.get("hosts")
    if not isinstance(hosts, list) or not hosts:
        raise ValueError("hosts must be a nonempty list")
    aliases = set()
    allowed = {"alias", "host", "port", "username", "key_filename_env", "password_env"}
    for host in hosts:
        if not isinstance(host, dict) or set(host) - allowed:
            raise ValueError("inventory contains unsupported fields; use environment references")
        alias = host.get("alias", "")
        if not isinstance(alias, str) or not ALIAS.fullmatch(alias) or alias.casefold() in aliases:
            raise ValueError("host aliases must be valid and unique")
        aliases.add(alias.casefold())
        for key in ("host", "username"):
            if not isinstance(host.get(key), str) or not host[key].strip():
                raise ValueError("host and username are required")
        port = host.get("port", 22)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("SSH port must be an integer from 1 to 65535")
        auth = [key for key in ("key_filename_env", "password_env") if host.get(key)]
        if len(auth) != 1 or not isinstance(host[auth[0]], str):
            raise ValueError("select exactly one environment-based authentication method")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", host[auth[0]]):
            raise ValueError("invalid environment variable name")
    return hosts


def execute(ssh, command, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    stdin.close()
    channel = stdout.channel
    chunks = []
    size = 0
    deadline = time.monotonic() + timeout
    try:
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError("remote command timeout")
            if channel.recv_ready():
                part = channel.recv(65536)
                size += len(part)
                chunks.append(part)
            if channel.recv_stderr_ready():
                size += len(channel.recv_stderr(65536))
            if size > MAX_REPORT_BYTES:
                raise ValueError("remote output exceeds limit")
            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                break
            time.sleep(0.01)
        if channel.recv_exit_status() != 0:
            raise RuntimeError("remote command failed")
        return b"".join(chunks).decode("utf-8").strip()
    finally:
        stdout.close()
        stderr.close()
        channel.close()


def collect_host(host, output, script, known_hosts=None):
    auth_key = "key_filename_env" if host.get("key_filename_env") else "password_env"
    secret = os.environ.get(host[auth_key])
    if not secret:
        raise ValueError("required authentication environment variable is missing")
    auth = {"key_filename" if auth_key == "key_filename_env" else "password": secret}
    ssh = paramiko.SSHClient()
    remote = None
    sftp = None
    try:
        ssh.load_system_host_keys()
        if known_hosts:
            ssh.load_host_keys(str(known_hosts))
        ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        ssh.connect(host["host"], port=host.get("port", 22), username=host["username"],
                    timeout=10, auth_timeout=10, banner_timeout=10,
                    allow_agent=False, look_for_keys=False, **auth)
        candidate = execute(ssh, "umask 077; mktemp -d /tmp/check-server.XXXXXXXX")
        if not REMOTE_DIR.fullmatch(candidate):
            raise ValueError("unexpected remote temporary directory")
        remote = candidate
        sftp = ssh.open_sftp()
        sftp.get_channel().settimeout(30)
        remote_script, remote_report = remote + "/inspect.sh", remote + "/report.html"
        sftp.put(str(script), remote_script)
        sftp.chmod(remote_script, 0o700)
        command = "/bin/bash " + " ".join(shlex.quote(arg) for arg in (remote_script, host["alias"], remote_report))
        execute(ssh, command)
        if sftp.stat(remote_report).st_size > MAX_REPORT_BYTES:
            raise ValueError("remote report exceeds limit")
        target = Path(output) / (host["alias"] + ".html")
        partial = target.with_suffix(".part")
        try:
            sftp.get(remote_report, str(partial))
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
        return target
    finally:
        if sftp:
            # Delete only the exact files created in this invocation's random directory.
            if remote:
                for name in ("inspect.sh", "report.html"):
                    try:
                        sftp.remove(remote + "/" + name)
                    except OSError:
                        pass
                try:
                    sftp.rmdir(remote)
                except OSError:
                    pass
            sftp.close()
        ssh.close()


def collect_all(inventory, output, script, known_hosts=None):
    hosts = read_inventory(inventory)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = []
    for host in hosts:
        row = {"host_alias": host["alias"]}
        try:
            collect_host(host, output, script, known_hosts)
            row["status"] = "collected"
        except Exception as exc:
            # Exception text may contain IPs, usernames or key paths: do not log it.
            row.update(status="failed", error_type=type(exc).__name__)
        manifest.append(row)
        print(row["host_alias"] + ": " + row["status"])
    (output / "collection.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return all(row["status"] == "collected" for row in manifest)
