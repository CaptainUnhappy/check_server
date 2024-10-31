"""Parse the historical h2/pre report format without treating missing data as healthy."""

import math
import re
from pathlib import Path

from bs4 import BeautifulSoup

DEFAULT_THRESHOLDS = {
    "cpu_percent": 80,
    "memory_percent": 80,
    "disk_percent": 80,
    "established_connections": 1000,
}
MANUAL_ITEMS = (
    "账户与权限", "登录失败记录", "计划任务", "进程明细",
    "服务器时间", "防火墙", "业务可用性",
)


def parse_sections(html):
    soup = BeautifulSoup(html, "html.parser")
    sections = {}
    for heading in soup.find_all("h2"):
        # Do not accidentally consume a later section when this one has no pre.
        following = heading.find_next_sibling()
        if following and following.name == "pre":
            sections[heading.get_text(strip=True)] = following.get_text()
    return sections


def field(text, label):
    match = re.search(r"^" + re.escape(label) + r"\s*[:：]\s*([^\r\n]*)$", text, re.M)
    return match.group(1).strip() if match else None


def number(value, percent=False):
    if value is None:
        return None
    value = value.strip().removesuffix("%").strip()
    try:
        result = float(value)
    except ValueError:
        return None
    if not math.isfinite(result) or result < 0 or (percent and result > 100):
        return None
    if not percent and not result.is_integer():
        return None
    return result


def validate_thresholds(thresholds):
    if set(thresholds) != set(DEFAULT_THRESHOLDS):
        raise ValueError("threshold keys do not match the example configuration")
    for key, value in thresholds.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError("thresholds must be numbers")
        if not math.isfinite(value) or value <= 0:
            raise ValueError("thresholds must be finite and positive")
        if key.endswith("percent") and value > 100:
            raise ValueError("percentage thresholds must be at most 100")
    return thresholds


def disk_usage(text):
    lines = text.splitlines()
    active = False
    values = []
    invalid = False
    for line in lines:
        if "系统磁盘分区存储使用情况" in line:
            active = True
            continue
        if active and (line.startswith("系统") or "inode" in line.lower()):
            break
        if not active or not line.strip() or line.startswith("Filesystem"):
            continue
        # df -Pk and df -Th both end in a percentage and mount point.
        match = re.search(r"\s(\S+)%\s+(/.*)$", line)
        usage = number(match.group(1), percent=True) if match else None
        if usage is None:
            invalid = True
        else:
            values.append(usage)
    return values, invalid


def check(name, value, rule, failed):
    return {
        "item": name,
        "value": value,
        "rule": rule,
        "status": "待复核" if value is None else ("告警" if failed else "通过"),
    }


def analyze_html(path, thresholds=None):
    thresholds = validate_thresholds(dict(DEFAULT_THRESHOLDS if thresholds is None else thresholds))
    path = Path(path)
    sections = parse_sections(path.read_text(encoding="utf-8-sig"))
    info = sections.get("系统信息", "")
    hardware = sections.get("配置信息", "")
    resources = sections.get("系统资源巡检区", "")
    # Original IPs are never used as the report identity fallback.
    alias = field(info, "主机标识")
    if not alias or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", alias):
        raise ValueError("report needs an anonymous host alias in 系统信息 / 主机标识")
    values = {
        "cpu_percent": number(field(resources, "CPU使用率"), percent=True),
        "memory_percent": number(field(hardware, "内存使用率"), percent=True),
        "established_connections": number(field(resources, "系统 established socket数量")),
    }
    labels = {"cpu_percent": "CPU使用率", "memory_percent": "内存使用率",
              "established_connections": "ESTABLISHED连接数"}
    checks = []
    for key, value in values.items():
        limit = thresholds[key]
        unit = "%" if key.endswith("percent") else ""
        checks.append(check(labels[key], value, f"< {limit}{unit}", value is not None and value >= limit))
    disks, invalid = disk_usage(resources)
    disk_limit = thresholds["disk_percent"]
    # A known breach remains an alert even if another disk row is incomplete.
    breached = any(value >= disk_limit for value in disks)
    disk_value = max(disks) if disks and (breached or not invalid) else None
    checks.append(check("磁盘最高占用率", disk_value, f"所有分区 < {disk_limit}%", breached))
    if invalid:
        checks.append(check("磁盘采集完整性", None, "存在无法解析的分区，需复核", False))
    zombies = number(field(resources, "系统当前僵尸进程数"))
    checks.append(check("僵尸进程", zombies, "= 0", zombies is not None and zombies > 0))
    checks.extend(check(item, None, "人工检查并签字", False) for item in MANUAL_ITEMS)
    return {
        "host_alias": alias,
        "collected_at": field(info, "巡检时间"),
        "synthetic": field(info, "数据来源") == "synthetic",
        "checks": checks,
    }
