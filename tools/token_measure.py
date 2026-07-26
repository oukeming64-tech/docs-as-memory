#!/usr/bin/env python3
"""token_measure — Docs as Memory token 评测量尺（零依赖）。

唯一量尺：est_tokens = ceil(normalized_utf8_bytes / 4)（specs/TOKEN_EVAL.md §3）。

用法：
  python3 tools/token_measure.py --runner kimi --task T-l0-budget
  python3 tools/token_measure.py --runner kimi --task T-auth-locate
  python3 tools/token_measure.py --runner kimi --task T-affected-auth

每个 run 会：
  1. 计算 fixture 内容哈希（TOKEN_EVAL §8 算法）
  2. 复制 fixture 到隔离临时目录，再跑 doc-memory reindex
  3. 按任务卡的冻结 top_k 执行 scripted_path，统计实际加载的文档字节
  4. 任一 CLI 子命令失败即闭锁，不生成误导性成功报告
  5. 写报告 fixtures/eval/reports/<runner>-<YYYYMMDD>-<task_id>.md
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_MEMORY = os.path.join(REPO_ROOT, "doc_memory.py")
FIXTURE = os.path.join(REPO_ROOT, "fixtures", "demo_project")
TASKS_DIR = os.path.join(REPO_ROOT, "fixtures", "eval", "tasks")
REPORTS_DIR = os.path.join(REPO_ROOT, "fixtures", "eval", "reports")
L0_BUDGET = 1500
RATIO_LIMIT = 0.30


def configure_utf8_stdio() -> None:
    """Keep JSON and diagnostics usable on narrow Windows console locales."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            pass


def est_tokens(nbytes: int) -> int:
    return math.ceil(nbytes / 4)


def normalized_file_bytes(path: str) -> bytes:
    """Read UTF-8 text bytes with CRLF/CR normalized to LF."""
    with open(path, "rb") as f:
        return f.read().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def fixture_hash(fixture: str) -> str:
    """TOKEN_EVAL §8：稳定排序后串联 path + LF-normalized bytes。"""
    shard_root = os.path.join(fixture, "docs", "shards")
    h = hashlib.sha256()
    for dirpath, _d, filenames in sorted(os.walk(shard_root)):
        for fn in sorted(filenames):
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, fixture).replace(os.sep, "/")
            h.update(rel.encode("utf-8"))
            h.update(b"\n")
            h.update(normalized_file_bytes(full))
    return h.hexdigest()


def list_shard_files(fixture: str):
    shard_root = os.path.join(fixture, "docs", "shards")
    out = []
    for dirpath, _d, filenames in os.walk(shard_root):
        for fn in filenames:
            if fn.endswith(".md") and not fn.startswith("_"):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, fixture).replace(os.sep, "/")
                out.append((rel, full))
    return sorted(out)


def parse_task_card(task_id: str) -> dict:
    path = os.path.join(TASKS_DIR, f"{task_id}.md")
    if not os.path.isfile(path):
        sys.exit(f"error: 任务卡不存在: {path}")
    text = open(path, encoding="utf-8").read()
    m = re.search(r"```task\n(.*?)\n```", text, re.S)
    if not m:
        sys.exit(f"error: 任务卡缺 ```task 块: {path}")
    card = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            card[k.strip()] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
        elif re.fullmatch(r"\d+", v):
            card[k.strip()] = int(v)
        else:
            card[k.strip()] = v
    return card


def run_cli(args, fixture, raw_log):
    cmd = [sys.executable, DOC_MEMORY, "--root", fixture] + args
    proc = subprocess.run(cmd, capture_output=True)
    display_command = (
        " ".join(cmd)
        .replace(REPO_ROOT + os.sep, "")
        .replace(fixture, "fixtures/demo_project")
    )
    raw_log.append("$ " + display_command)
    raw_log.append(proc.stdout.decode("utf-8", "replace").rstrip("\n"))
    if proc.stderr:
        raw_log.append("[stderr] " + proc.stderr.decode("utf-8", "replace").rstrip("\n"))
    raw_log.append(f"[exit={proc.returncode}]")
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(
            f"doc-memory 子命令失败（exit={proc.returncode}）: "
            f"{' '.join(args)}{': ' + detail if detail else ''}")
    return proc.stdout


def shard_paths_from_output(stdout: bytes) -> list:
    """从 search/affected 输出中提取命中的 shard 路径。"""
    paths = []
    for line in stdout.decode("utf-8", "replace").splitlines():
        m = re.match(r"^(docs/shards/\S+\.md)\s*\|", line.strip())
        if m:
            paths.append(m.group(1))
    return paths


def _measure_on_fixture(task_id: str, runner: str, fixture: str) -> dict:
    card = parse_task_card(task_id)
    raw_log = []
    loaded = []          # [(label, rel_path_or_None, bytes)]  实际进入上下文的文档字节
    fh = fixture_hash(fixture)
    fixture_id = f"demo_project@{fh[:16]}"

    # step 0: reindex（保证 INDEX 新鲜）
    run_cli(["reindex"], fixture, raw_log)

    # baseline：全部碎片完整文件（TOKEN_EVAL §4.1）
    baseline_bytes = 0
    baseline_mode = card.get("baseline_mode", "all_shards")
    if baseline_mode == "all_shards":
        for _rel, full in list_shard_files(fixture):
            baseline_bytes += len(normalized_file_bytes(full))

    index_md = os.path.join(fixture, "docs", "INDEX.md")

    if task_id == "T-l0-budget":
        data = normalized_file_bytes(index_md)
        loaded.append(("L0 INDEX.md", "docs/INDEX.md", len(data)))
        atlas_bytes = len(data)
        probe_ok = est_tokens(atlas_bytes) <= L0_BUDGET
        probe_answer = "BUDGET_OK" if probe_ok else f"OVER_BUDGET({est_tokens(atlas_bytes)})"

    elif task_id == "T-auth-locate":
        data = normalized_file_bytes(index_md)
        loaded.append(("L0 INDEX.md", "docs/INDEX.md", len(data)))
        atlas_bytes = len(data)
        out = run_cli(
            ["search", card["query"], "--limit", str(int(card["top_k"]))],
            fixture,
            raw_log,
        )
        loaded.append(("search stdout", None, len(out)))
        atlas_bytes += len(out)
        hits = shard_paths_from_output(out)[: int(card["top_k"])]
        body_all = ""
        for rel in hits:
            b = normalized_file_bytes(os.path.join(fixture, rel))
            loaded.append(("shard", rel, len(b)))
            atlas_bytes += len(b)
            body_all += b.decode("utf-8", "replace")
        probe_ok = card["probe_expected"] in body_all
        probe_answer = (f"在已加载碎片中找到 {card['probe_expected']}"
                        if probe_ok else f"未找到 {card['probe_expected']}")

    elif task_id == "T-affected-auth":
        out = run_cli(["affected", card["affected_path"]], fixture, raw_log)
        loaded.append(("affected stdout", None, len(out)))
        atlas_bytes = len(out)
        hits = shard_paths_from_output(out)
        if int(card.get("top_k", 0)) > 0:
            hits = hits[: int(card["top_k"])]
        body_all = ""
        for rel in hits:
            b = normalized_file_bytes(os.path.join(fixture, rel))
            loaded.append(("shard", rel, len(b)))
            atlas_bytes += len(b)
            body_all += b.decode("utf-8", "replace")
        probe_ok = card["probe_expected"] in hits or card["probe_expected"] in body_all
        probe_answer = (f"affected 命中 {card['probe_expected']}"
                        if probe_ok else f"未命中 {card['probe_expected']}")
    else:
        sys.exit(f"error: 未知任务 {task_id}")

    ratio = (est_tokens(atlas_bytes) / est_tokens(baseline_bytes)) if baseline_bytes else None
    verdicts = []
    if task_id == "T-l0-budget":
        verdicts.append(f"AC-5 量尺：est_tokens={est_tokens(atlas_bytes)} ≤ {L0_BUDGET} → "
                        + ("PASS" if probe_ok else "FAIL"))
    if ratio is not None and task_id == "T-auth-locate":
        verdicts.append(f"AC-1 量尺：ratio={ratio:.4f} ≤ {RATIO_LIMIT} → "
                        + ("PASS" if ratio <= RATIO_LIMIT else "FAIL"))
    verdicts.append("探针：" + ("PASS" if probe_ok else "FAIL"))

    return {
        "card": card, "fixture_id": fixture_id, "fixture_hash": fh,
        "baseline_bytes": baseline_bytes, "atlas_bytes": atlas_bytes,
        "ratio": ratio, "loaded": loaded, "raw_log": raw_log,
        "probe_ok": probe_ok, "probe_answer": probe_answer,
        "verdicts": verdicts, "runner": runner, "task_id": task_id,
    }


def measure(task_id: str, runner: str) -> dict:
    """Run against an isolated fixture copy so evaluation never dirties source files."""
    with tempfile.TemporaryDirectory(prefix="docs-as-memory-eval-") as temp_root:
        fixture = os.path.join(temp_root, "demo_project")
        shutil.copytree(FIXTURE, fixture)
        return _measure_on_fixture(task_id, runner, fixture)


def render_report(r: dict) -> str:
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    lines = [
        "# Token eval report",
        "",
        f"- runner: {r['runner']}",
        f"- date: {now}",
        f"- fixture_id: {r['fixture_id']}",
        f"- task_id: {r['task_id']}",
        "- method: normalized_utf8_bytes/4",
        "- mode: scripted_path",
        "",
        "## Absolute numbers",
        f"- baseline_normalized_utf8_bytes: {r['baseline_bytes']}",
        f"- baseline_est_tokens: {est_tokens(r['baseline_bytes']) if r['baseline_bytes'] else 'n/a'}",
        f"- atlas_normalized_utf8_bytes: {r['atlas_bytes']}",
        f"- atlas_est_tokens: {est_tokens(r['atlas_bytes'])}",
        f"- ratio: {format(r['ratio'], '.4f') if r['ratio'] is not None else 'n/a (T-l0-budget 无 baseline)'}",
        "",
        "## Loaded paths (ordered)",
    ]
    for i, (label, rel, n) in enumerate(r["loaded"], 1):
        name = rel if rel else f"({label})"
        lines.append(
            f"{i}. {name} — normalized_utf8_bytes={n}, est_tokens={est_tokens(n)}")
    lines += [
        "",
        "## CLI raw",
        "```",
        *r["raw_log"],
        "```",
        "",
        "## Probe",
        f"- question: {r['card'].get('probe_question', '')}",
        f"- answer: {r['probe_answer']}",
        f"- pass: {'true' if r['probe_ok'] else 'false'}",
        "",
        "## Verdicts (本端量尺结果；AC 是否通过须等双端对比)",
        *[f"- {v}" for v in r["verdicts"]],
        "",
        "## Notes",
        "- 本报告由 tools/token_measure.py 生成；raw 输出见上。",
        "- 双端一致性检查（|K-G|/max ≤ 0.10）见 SUMMARY.md，由后跑完的一方合并。",
        "",
    ]
    return "\n".join(lines)


def display_report_path(path: str) -> str:
    """Prefer repo-relative output, with a cross-volume-safe absolute fallback."""
    absolute = os.path.abspath(path)
    try:
        if os.path.commonpath([absolute, REPO_ROOT]) == REPO_ROOT:
            return os.path.relpath(absolute, REPO_ROOT).replace(os.sep, "/")
    except ValueError:
        pass
    return absolute


def main():
    configure_utf8_stdio()
    p = argparse.ArgumentParser(
        description="Docs as Memory token 量尺（method=normalized_utf8_bytes/4）")
    p.add_argument(
        "--runner",
        required=True,
        choices=["kimi", "grok", "codex"],
        help="kimi/grok 用于正式双端验收；codex 仅用于工程回归",
    )
    p.add_argument("--task", required=True)
    p.add_argument("--out", default=REPORTS_DIR)
    args = p.parse_args()

    try:
        r = measure(args.task, args.runner)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    report = render_report(r)
    os.makedirs(args.out, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    fname = f"{args.runner}-{date_str}-{args.task}.md"
    fpath = os.path.join(args.out, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(report)

    print(json.dumps({
        "report": display_report_path(fpath),
        "fixture_id": r["fixture_id"],
        "baseline_est_tokens": est_tokens(r["baseline_bytes"]) if r["baseline_bytes"] else None,
        "atlas_est_tokens": est_tokens(r["atlas_bytes"]),
        "ratio": r["ratio"],
        "probe_pass": r["probe_ok"],
        "verdicts": r["verdicts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
