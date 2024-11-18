"""python -m check_server demo | report | collect"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .parser import DEFAULT_THRESHOLDS, analyze_html, validate_thresholds

ROOT = Path(__file__).resolve().parents[1]


def make_report(source, output, threshold_path=None, demo=False):
    source, output = Path(source), Path(output)
    paths = sorted(source.glob("*.html"))
    if not paths:
        raise ValueError("no HTML reports found")
    thresholds = DEFAULT_THRESHOLDS
    if threshold_path:
        thresholds = json.loads(Path(threshold_path).read_text(encoding="utf-8-sig"))
    validate_thresholds(thresholds)
    results = [analyze_html(path, thresholds) for path in paths]
    aliases = [result["host_alias"].casefold() for result in results]
    if len(aliases) != len(set(aliases)):
        raise ValueError("duplicate report host aliases")
    if demo and not all(result["example"] for result in results):
        raise ValueError("demo only accepts example data")
    manifest_path = source / "collection.json"
    collection = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    failed = [row["host_alias"] for row in collection if row["status"] != "collected"]
    expected = {row["host_alias"] for row in collection if row["status"] == "collected"}
    if expected and expected != {result["host_alias"] for result in results}:
        raise ValueError("collection manifest and HTML reports do not match")
    output.mkdir(parents=True, exist_ok=False)
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_kind": ("synthetic" if all(r["synthetic"] for r in results) else
                        "example" if all(r["example"] for r in results) else "authorized-or-local-input"),
        "thresholds": thresholds,
        "failed_hosts": failed,
        "review_required": True,
        "hosts": results,
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    from .report import build_word, write_bundle
    build_word(results, output / "inspection.docx", failed)
    write_bundle(output, paths, results)
    print(f"Generated {len(results)} host reports; {len(failed)} collection failures. Human review required.")
    return not failed


def main(argv=None):
    parser = argparse.ArgumentParser(description="服务器巡检与报告整理")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="离线使用示例报告生成交付包")
    demo.add_argument("--output", type=Path, default=Path("output/demo"))
    report = sub.add_parser("report", help="解析匿名 HTML 并生成 JSON 和 Word")
    report.add_argument("--input", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--thresholds", type=Path)
    collect = sub.add_parser("collect", help="经授权连接自有或获授权的 Linux 主机")
    collect.add_argument("--inventory", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--known-hosts", type=Path)
    collect.add_argument("--authorized", action="store_true", help="确认已获得目标主机访问和巡检授权")
    args = parser.parse_args(argv)
    if args.command == "collect" and not args.authorized:
        parser.error("collect requires --authorized")
    try:
        if args.command == "demo":
            success = make_report(ROOT / "examples/html", args.output, demo=True)
        elif args.command == "report":
            success = make_report(args.input, args.output, args.thresholds)
        else:
            from .collector import collect_all
            success = collect_all(args.inventory, args.output, ROOT / "scripts/os_check.sh", args.known_hosts)
        return 0 if success else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Do not echo paths, inventory contents or credential-bearing exception text.
        print(f"Operation failed ({type(exc).__name__}). Check input format, access and output-directory uniqueness.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
