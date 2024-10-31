import unittest
from pathlib import Path
from check_server.parser import analyze_html

ROOT = Path(__file__).resolve().parents[1]

class ParserTests(unittest.TestCase):
    def test_normal_sample_preserves_manual_review(self):
        report = analyze_html(ROOT / 'examples/html/demo-app-01_20241018.html')
        self.assertEqual(sum(c['status'] == '通过' for c in report['checks']), 5)
        self.assertEqual(sum(c['status'] == '待复核' for c in report['checks']), 7)

    def test_threshold_boundary_is_warning(self):
        report = analyze_html(ROOT / 'examples/html/demo-db-01_20241018.html')
        cpu = next(c for c in report['checks'] if c['item'] == 'CPU使用率')
        self.assertEqual(cpu['status'], '告警')

    def test_missing_connection_count_requires_review(self):
        report = analyze_html(ROOT / 'examples/html/demo-db-01_20241018.html')
        connection = next(c for c in report['checks'] if c['item'] == 'ESTABLISHED连接数')
        self.assertIsNone(connection['value'])
        self.assertEqual(connection['status'], '待复核')
