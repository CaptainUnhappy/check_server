import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import zipfile

import paramiko

from check_server.__main__ import main, make_report
from check_server.collector import collect_all, collect_host, execute, read_inventory
from check_server.parser import analyze_html, number, parse_sections, validate_thresholds

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/html"
SAMPLE = FIXTURES / "demo-app-01_20241018.html"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def changed_report(self, old, new):
        path = self.directory / "sample.html"
        path.write_text(SAMPLE.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        return analyze_html(path)

    def result(self, report, label):
        return next(item for item in report["checks"] if item["item"] == label)

    def inventory(self, hosts=None):
        path = self.directory / "hosts.local.json"
        path.write_text(json.dumps({"hosts": hosts or [{
            "alias": "demo-app-01", "host": "192.0.2.10", "username": "inspector",
            "password_env": "TEST_CHECK_PASSWORD",
        }]}), encoding="utf-8")
        return path

    def test_full_reports_generate_delivery(self):
        reports = sorted((ROOT / "examples/html").glob("*.html"))
        self.assertEqual(len(reports), 19)
        aliases = set()
        for path in reports:
            sections = parse_sections(path.read_text(encoding="utf-8"))
            self.assertEqual(set(sections), {"用户安全审计", "登陆失败记录", "系统信息", "配置信息", "系统资源巡检区", "系统安全审计"})
            self.assertGreater(len(sections["系统资源巡检区"].splitlines()), 50)
            result = analyze_html(path)
            self.assertTrue(result["example"])
            self.assertFalse(result["synthetic"])
            aliases.add(result["host_alias"])
            self.assertNotIn("磁盘采集完整性", {c["item"] for c in result["checks"]})
        self.assertEqual(len(aliases), 19)
        output = self.directory / "full-reports"
        with patch("paramiko.SSHClient") as client, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(make_report(ROOT / "examples/html", output, demo=True))
            client.assert_not_called()
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["source_kind"], "example")
        self.assertEqual(len(summary["hosts"]), 19)
        with zipfile.ZipFile(output / "delivery.zip") as bundle:
            self.assertEqual(set(bundle.namelist()), {"inspection.docx", "summary.json"} | {f"html/{alias}.html" for alias in aliases})

    def test_wrapped_disk_device_is_valid(self):
        report = self.changed_report("/dev/demo-root 104857600 36700160 68157440 35% /", "/dev/mapper/vg0-root\n xfs 100G 35G 65G 35% /")
        self.assertEqual(self.result(report, "磁盘最高占用率")["value"], 52)
        self.assertNotIn("磁盘采集完整性", {c["item"] for c in report["checks"]})

    def test_unfinished_wrapped_device_requires_review(self):
        report = self.changed_report("/dev/demo-data 209715200 109051904 100663296 52% /data", "/dev/mapper/vg0-data")
        self.assertEqual(self.result(report, "磁盘最高占用率")["status"], "待复核")
        self.assertEqual(self.result(report, "磁盘采集完整性")["status"], "待复核")

    def test_normal_sample_keeps_manual_review(self):
        report = analyze_html(SAMPLE)
        self.assertEqual(sum(c["status"] == "通过" for c in report["checks"]), 5)
        self.assertEqual(sum(c["status"] == "待复核" for c in report["checks"]), 7)

    def test_exact_threshold_is_alert(self):
        report = self.changed_report("23.5%", "80%")
        self.assertEqual(self.result(report, "CPU使用率")["status"], "告警")

    def test_missing_cpu_is_not_zero(self):
        report = self.changed_report("CPU使用率：23.5%", "CPU使用率：")
        self.assertIsNone(self.result(report, "CPU使用率")["value"])
        self.assertEqual(self.result(report, "CPU使用率")["status"], "待复核")

    def test_no_disk_rows_is_not_healthy(self):
        report = self.changed_report("系统磁盘分区存储使用情况：", "无磁盘字段：")
        self.assertEqual(self.result(report, "磁盘最高占用率")["status"], "待复核")

    def test_invalid_disk_row_does_not_hide_breach(self):
        report = self.changed_report("52% /data", "95% /data\n/dev/demo-other UNKNOWN /other")
        self.assertEqual(self.result(report, "磁盘最高占用率")["status"], "告警")
        self.assertEqual(self.result(report, "磁盘采集完整性")["status"], "待复核")

    def test_missing_pre_does_not_consume_next_section(self):
        sections = parse_sections("<h2>first</h2><h2>second</h2><pre>value</pre>")
        self.assertNotIn("first", sections)
        self.assertEqual(sections["second"], "value")

    def test_invalid_numeric_values(self):
        for value in ("nan", "inf", "-1", "101", "UNKNOWN"):
            with self.subTest(value=value):
                self.assertIsNone(number(value, percent=True))
        self.assertIsNone(number("1.5"))

    def test_alias_required(self):
        with self.assertRaises(ValueError):
            self.changed_report("主机标识：demo-app-01", "主机IP：192.0.2.10")

    def test_threshold_validation(self):
        for thresholds in ({}, {"cpu_percent": 200}):
            with self.assertRaises(ValueError):
                validate_thresholds(thresholds)

    def test_inventory_rejects_plaintext_credentials(self):
        path = self.inventory([{"alias": "demo-a", "host": "192.0.2.10", "username": "inspector", "password": "synthetic-only"}])
        with self.assertRaises(ValueError):
            read_inventory(path)

    def test_inventory_rejects_duplicate_aliases_on_windows(self):
        host = {"alias": "demo-a", "host": "192.0.2.10", "username": "inspector", "password_env": "TEST_CHECK_PASSWORD"}
        with self.assertRaises(ValueError):
            read_inventory(self.inventory([host, dict(host, alias="DEMO-A")]))

    def test_example_inventory_cannot_connect(self):
        with self.assertRaises(ValueError):
            read_inventory(ROOT / "config/hosts.example.json")

    def test_collect_requires_explicit_authorization(self):
        with patch("paramiko.SSHClient") as client, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["collect", "--inventory", "config/hosts.local.json", "--output", "output/test"])
            client.assert_not_called()

    def test_missing_auth_does_not_connect(self):
        host = read_inventory(self.inventory())[0]
        with patch.dict(os.environ, {}, clear=True), patch("paramiko.SSHClient") as client:
            with self.assertRaises(ValueError):
                collect_host(host, self.directory, ROOT / "scripts/os_check.sh")
            client.assert_not_called()

    def test_unknown_host_keys_are_rejected_and_client_closed(self):
        host = read_inventory(self.inventory())[0]
        with patch.dict(os.environ, {"TEST_CHECK_PASSWORD": "synthetic-only"}), patch("paramiko.SSHClient") as constructor:
            client = constructor.return_value
            client.connect.side_effect = paramiko.SSHException("synthetic-error")
            with self.assertRaises(paramiko.SSHException):
                collect_host(host, self.directory, ROOT / "scripts/os_check.sh")
            self.assertIsInstance(client.set_missing_host_key_policy.call_args.args[0], paramiko.RejectPolicy)
            client.close.assert_called_once()

    def test_collection_continues_and_does_not_log_exception_contents(self):
        host = read_inventory(self.inventory())[0]
        inventory = self.inventory([host, dict(host, alias="demo-b")])
        output = self.directory / "collection"
        with patch("check_server.collector.collect_host", side_effect=[RuntimeError("synthetic-private-detail"), output / "demo-b.html"]) as collect:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(collect_all(inventory, output, ROOT / "scripts/os_check.sh"))
            self.assertEqual(collect.call_count, 2)
        content = (output / "collection.json").read_text(encoding="utf-8")
        self.assertNotIn("synthetic-private-detail", content)
        self.assertEqual(json.loads(content)[1]["status"], "collected")

    def test_remote_command_timeout_closes_channel(self):
        ssh = MagicMock()
        stdin, stdout, stderr = MagicMock(), MagicMock(), MagicMock()
        ssh.exec_command.return_value = (stdin, stdout, stderr)
        with self.assertRaises(TimeoutError):
            execute(ssh, "true", timeout=-1)
        stdout.channel.close.assert_called_once()

    def test_offline_delivery_contains_only_expected_members(self):
        output = self.directory / "report"
        with patch("paramiko.SSHClient") as client, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(make_report(FIXTURES, output, demo=True))
            client.assert_not_called()
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["source_kind"], "synthetic")
        self.assertTrue(summary["review_required"])
        self.assertEqual(summary["hosts"][1]["collected_at"], "2024-10-18T09:05:00+08:00")
        with zipfile.ZipFile(output / "delivery.zip") as bundle:
            self.assertEqual(set(bundle.namelist()), {"inspection.docx", "summary.json", "html/demo-app-01.html", "html/demo-db-01.html"})
        with zipfile.ZipFile(output / "inspection.docx") as doc:
            self.assertFalse(any("embeddings" in name or name.startswith("customXml/") for name in doc.namelist()))
            self.assertIn(">check_server<", doc.read("docProps/core.xml").decode())

    def test_failed_host_is_visible_in_json_and_word(self):
        source = self.directory / "source"
        source.mkdir()
        (source / "sample.html").write_bytes(SAMPLE.read_bytes())
        (source / "collection.json").write_text(json.dumps([
            {"host_alias": "demo-app-01", "status": "collected"},
            {"host_alias": "demo-failed", "status": "failed"},
        ]), encoding="utf-8")
        output = self.directory / "report"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(make_report(source, output))
        self.assertEqual(json.loads((output / "summary.json").read_text(encoding="utf-8"))["failed_hosts"], ["demo-failed"])
        with zipfile.ZipFile(output / "inspection.docx") as doc:
            self.assertIn("demo-failed", doc.read("word/document.xml").decode())

    def test_existing_output_cannot_mix_old_results(self):
        with self.assertRaises(FileExistsError):
            make_report(FIXTURES, self.directory, demo=True)


if __name__ == "__main__":
    unittest.main()
