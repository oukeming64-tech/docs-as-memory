#!/usr/bin/env python3
"""
doc-memory — 文档碎片索引 CLI（零第三方依赖，Python >= 3.9，仅标准库）

命令：init / reindex / search / affected / validate / overview / migrate

实现约定：
- frontmatter 只支持 YAML 子集：`key: 标量`、`key: [a, b]` 行内列表、
  `key:` 后跟 `- item` 块列表、单/双引号、` #` 行尾注释。
- 索引新鲜度用内容哈希（Markdown 换行规范为 LF 后，sha256 串联
  relpath + b'\\n' + normalized_bytes，稳定排序）；不用 mtime。
- search 排序：keyword 精确命中 x3 + title 字面 x2 + summary/body/path 字面 x1，
  平分按路径字典序；大小写不敏感；默认排除 history/cold 冷域并只返回 top-2。
- affected：查询路径与 code_path 任一方是另一方前缀即命中（尾斜杠归一化）。
- 读取类命令遇到损坏碎片默认失败闭锁；显式 --allow-partial 才可降级。
- 退出码：0 成功/仅警告；1 数据/校验错误；2 用法/路径安全错误。
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from datetime import date, datetime


def configure_utf8_stdio() -> None:
    """Keep human-readable output usable on narrow Windows console locales."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            pass


configure_utf8_stdio()

VERSION = "0.1.1"
SCHEMA_VERSION = 2
SHARD_ROOT = os.path.join("docs", "shards")
INDEX_MD = os.path.join("docs", "INDEX.md")
INDEX_JSON = os.path.join("docs", "index.json")
TEMPLATE_NAME = "_TEMPLATE.md"

REQUIRED_FIELDS = ("title", "summary", "keywords", "domain")
RECOMMENDED_FIELDS = ("code_paths", "trust_level")
SUMMARY_LIMIT_CJK = 80
SUMMARY_LIMIT_LATIN = 160
STALE_DAYS = 90
L0_BUDGET = 1500
DEFAULT_SEARCH_LIMIT = 2
COLD_DOMAINS = frozenset({"history", "cold", "archive", "archives"})
DEFAULT_MIGRATE_EXCLUDES = (
    ".git/**",
    "*/.git/**",
    ".hg/**",
    "*/.hg/**",
    ".svn/**",
    "*/.svn/**",
    "node_modules/**",
    "*/node_modules/**",
    "dist/**",
    "*/dist/**",
    "build/**",
    "*/build/**",
    "target/**",
    "*/target/**",
    ".venv/**",
    "*/.venv/**",
    "venv/**",
    "*/venv/**",
    "__pycache__/**",
    "*/__pycache__/**",
    "docs/shards/**",
    "*/docs/shards/**",
)
DEFAULT_IGNORED_DIR_NAMES = frozenset({
    ".git", ".hg", ".svn", "node_modules", "dist", "build", "target",
    ".venv", "venv", "__pycache__",
})
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------

def normalize_markdown_bytes(data: bytes) -> bytes:
    """Normalize text line endings so committed indexes are cross-platform."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def est_tokens(data: bytes) -> int:
    """唯一量尺：est_tokens = ceil(normalized_utf8_bytes / 4)。"""
    return math.ceil(len(normalize_markdown_bytes(data)) / 4)


def eprint(*args):
    print(*args, file=sys.stderr)


def resolve_root(root_arg: str) -> str:
    root = os.path.realpath(os.path.abspath(root_arg))
    if not os.path.isdir(root):
        eprint(f"error: root 不存在或不是目录: {root}")
        sys.exit(2)
    return root


def safe_relpath(path: str, root: str) -> str:
    """拒绝绝对路径、.. 与符号链接逃逸；返回规范化相对路径。"""
    if "\x00" in path:
        raise ValueError("path contains NUL")
    normalized = path.replace("\\", "/")
    if os.path.isabs(path) or normalized.startswith("/"):
        raise ValueError(f"path must be relative to root: {path}")
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if ".." in parts:
        raise ValueError(f"path escapes root: {path}")
    joined = os.path.realpath(os.path.join(root, path))
    try:
        contained = os.path.commonpath((root, joined)) == root
    except ValueError:
        contained = False
    if not contained:
        raise ValueError(f"path escapes root: {path}")
    rel = os.path.relpath(joined, root)
    return rel.replace(os.sep, "/")


def norm_code_path(p: str) -> str:
    """归一化 code_path / 查询路径：posix 分隔、去 ./ 前缀、目录统一带尾斜杠。"""
    p = p.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    p = p.rstrip("/") if p != "/" else p
    return p


def checked_code_path(p: str, root: str, require_exists: bool = True) -> str:
    """校验仓内相对路径并返回 POSIX 风格；在归一化后再次做 containment。"""
    normalized = norm_code_path(p)
    if not normalized or normalized == ".":
        raise ValueError(f"empty repository-relative path: {p!r}")
    rel = safe_relpath(normalized, root)
    full = os.path.realpath(os.path.join(root, rel))
    if require_exists and not os.path.exists(full):
        raise ValueError(f"path does not exist: {p}")
    return rel


def is_cold_entry(entry) -> bool:
    domain = str(entry.get("domain") or "").lower()
    if domain in COLD_DOMAINS:
        return True
    parts = set(str(entry.get("path") or "").lower().split("/"))
    return bool(parts.intersection(COLD_DOMAINS))


def guard_managed_paths(root: str) -> None:
    """确保 Docs as Memory 的固定读写位置没有通过符号链接逃出项目根。"""
    for relative in (SHARD_ROOT, INDEX_MD, INDEX_JSON):
        safe_relpath(relative, root)


# ---------------------------------------------------------------------------
# frontmatter 解析（YAML 子集）
# ---------------------------------------------------------------------------

class FrontmatterError(Exception):
    pass


def _strip_comment(line: str) -> str:
    """去掉不在引号内的 ` #` 行尾注释。"""
    out = []
    in_s, in_d = False, False
    for i, ch in enumerate(line):
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d:
            if i == 0 or line[i - 1] in (" ", "\t"):
                break
        out.append(ch)
    return "".join(out).rstrip()


def _parse_scalar(raw: str):
    raw = _strip_comment(raw).strip()
    if raw and raw[0] in ("'", '"') and (
            len(raw) < 2 or raw[-1] != raw[0]):
        raise FrontmatterError(f"标量引号未闭合: {raw!r}")
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        return raw[1:-1]
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    if raw == "":
        return None
    return raw


def _parse_flow_list(raw: str):
    raw = _strip_comment(raw).strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        raise FrontmatterError(f"不是合法行内列表: {raw!r}")
    inner = raw[1:-1].strip()
    if not inner:
        return []
    items, buf, in_s, in_d = [], [], False, False
    for ch in inner:
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        if ch == "," and not in_s and not in_d:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if in_s or in_d:
        raise FrontmatterError(f"行内列表引号未闭合: {raw!r}")
    items.append("".join(buf))
    return [_parse_scalar(x) for x in items]


def parse_frontmatter(text: str):
    """解析 YAML 子集 frontmatter。返回 (meta: dict, body: str)。"""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("缺少 frontmatter 起始 '---'")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise FrontmatterError("缺少 frontmatter 结束 '---'")

    meta = {}
    i = 1
    while i < end:
        raw_line = lines[i]
        if not raw_line.strip():
            i += 1
            continue
        if raw_line[0] in (" ", "\t"):
            raise FrontmatterError(f"顶层字段不允许缩进: {raw_line!r}")
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:(.*)$", raw_line)
        if not m:
            raise FrontmatterError(f"无法解析的行（仅支持 YAML 子集）: {raw_line!r}")
        key, rest = m.group(1), m.group(2).strip()
        if key in meta:
            raise FrontmatterError(f"字段重复: {key}")
        if rest == "":
            # 可能是块列表
            items = []
            j = i + 1
            while j < end:
                lm = re.match(r"^\s+-\s+(.*)$", lines[j])
                if lm:
                    items.append(_parse_scalar(lm.group(1)))
                    j += 1
                elif not lines[j].strip():
                    j += 1
                else:
                    break
            if items:
                meta[key] = items
                i = j
                continue
            meta[key] = None
            i += 1
            continue
        if rest.startswith("["):
            meta[key] = _parse_flow_list(rest)
        else:
            meta[key] = _parse_scalar(rest)
        i += 1

    body = "\n".join(lines[end + 1:])
    return meta, body


# ---------------------------------------------------------------------------
# 碎片扫描与校验
# ---------------------------------------------------------------------------

def iter_shard_files(root: str):
    shard_root = os.path.join(root, SHARD_ROOT)
    if not os.path.isdir(shard_root):
        return []
    real_shard_root = os.path.realpath(shard_root)
    if os.path.commonpath((root, real_shard_root)) != root:
        raise ValueError(f"{SHARD_ROOT} escapes root through a symlink")
    out = []
    for dirpath, dirnames, filenames in os.walk(shard_root, followlinks=False):
        dirnames[:] = sorted(
            dirname for dirname in dirnames
            if not os.path.islink(os.path.join(dirpath, dirname)))
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            if fn.startswith("_"):
                continue  # _TEMPLATE.md 等下划线文件不索引
            full = os.path.join(dirpath, fn)
            if os.path.islink(full):
                raise ValueError(f"symlinked shard is not allowed: {full}")
            real = os.path.realpath(full)
            if os.path.commonpath((real_shard_root, real)) != real_shard_root:
                raise ValueError(f"shard escapes {SHARD_ROOT}: {full}")
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out.append((rel, full))
    out.sort()
    return out


def shards_hash(root: str) -> str:
    """Cross-platform hash over paths and LF-normalized Markdown bytes."""
    h = hashlib.sha256()
    for rel, full in iter_shard_files(root):
        h.update(rel.encode("utf-8"))
        h.update(b"\n")
        with open(full, "rb") as f:
            h.update(normalize_markdown_bytes(f.read()))
    return h.hexdigest()


def check_shard(meta, rel, root):
    """对单个碎片做字段校验，返回 (errors, warns)。"""
    errors, warns = [], []

    for f in REQUIRED_FIELDS:
        if meta.get(f) in (None, "", []):
            errors.append(f"{rel}: 缺必填字段 {f}")
    for f in RECOMMENDED_FIELDS:
        if f not in meta or meta.get(f) is None or meta.get(f) == "":
            if not (f == "code_paths"
                    and meta.get("migration_status") == "needs-review"):
                warns.append(f"{rel}: 缺建议字段 {f}")

    for field in ("title", "summary", "domain"):
        value = meta.get(field)
        if value not in (None, "") and not isinstance(value, str):
            errors.append(f"{rel}: {field} 必须是字符串，得到 {value!r}")

    summary = meta.get("summary")
    if isinstance(summary, str):
        cjk = sum(1 for ch in summary if ord(ch) > 0x2E7F)
        latin = len(summary) - cjk
        if cjk > SUMMARY_LIMIT_CJK or latin > SUMMARY_LIMIT_LATIN:
            warns.append(f"{rel}: summary 超软上限（CJK≤{SUMMARY_LIMIT_CJK}/Latin≤{SUMMARY_LIMIT_LATIN}）")

    kw = meta.get("keywords")
    if kw is not None and not isinstance(kw, list):
        errors.append(f"{rel}: keywords 必须是列表")
    elif isinstance(kw, list):
        for item in kw:
            if not isinstance(item, str):
                errors.append(f"{rel}: keywords 项必须是字符串: {item!r}")

    domain = meta.get("domain")
    if isinstance(domain, str) and domain and not SLUG_RE.match(domain):
        warns.append(f"{rel}: domain 建议 slug 形式（小写字母/数字/-/_）: {domain!r}")

    tl = meta.get("trust_level")
    if tl is not None and not (type(tl) is int and 1 <= tl <= 4):
        errors.append(f"{rel}: trust_level 必须是 1-4 的整数，得到 {tl!r}")

    migration_status = meta.get("migration_status")
    if migration_status is not None and migration_status not in (
            "needs-review", "reviewed"):
        errors.append(
            f"{rel}: migration_status 只能是 needs-review 或 reviewed")

    va = meta.get("verified_at")
    if va is not None:
        if not (isinstance(va, str) and DATE_RE.match(va)):
            errors.append(f"{rel}: verified_at 必须是 YYYY-MM-DD 字符串（建议加引号）")
        else:
            try:
                d = date.fromisoformat(va)
                if (date.today() - d).days > STALE_DAYS:
                    warns.append(f"{rel}: verified_at={va} 已超 {STALE_DAYS} 天，请复核")
            except ValueError:
                errors.append(f"{rel}: verified_at 不是合法日期: {va!r}")

    cps = meta.get("code_paths")
    if cps is not None:
        if not isinstance(cps, list):
            errors.append(f"{rel}: code_paths 必须是列表")
        else:
            for cp in cps:
                if not isinstance(cp, str):
                    errors.append(f"{rel}: code_paths 项必须是字符串: {cp!r}")
                    continue
                try:
                    checked_code_path(cp, root, require_exists=True)
                except ValueError as exc:
                    errors.append(f"{rel}: code_paths 非法: {exc}")
    return errors, warns


def load_shards(root: str, strict: bool = False):
    """扫描并解析全部碎片。返回 (entries, errors, warns)。

    entries: [{path, title, summary, keywords, domain, code_paths,
               trust_level, verified_at, est_tokens}]
    """
    entries, errors, warns = [], [], []
    migration_review_count = 0
    for rel, full in iter_shard_files(root):
        try:
            with open(full, "rb") as file_handle:
                raw_data = file_handle.read()
            normalized_data = normalize_markdown_bytes(raw_data)
            text = normalized_data.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"{rel}: 非 UTF-8 编码")
            continue
        except OSError as exc:
            errors.append(f"{rel}: 无法读取: {exc}")
            continue
        try:
            meta, body = parse_frontmatter(text)
        except FrontmatterError as e:
            errors.append(f"{rel}: frontmatter 解析失败: {e}")
            continue
        errs, wrns = check_shard(meta, rel, root)
        errors.extend(errs)
        warns.extend(wrns)
        if errs and strict:
            continue
        if meta.get("migration_status") == "needs-review":
            migration_review_count += 1
        nbytes = len(normalized_data)
        keywords = meta.get("keywords")
        code_paths = meta.get("code_paths")
        entries.append({
            "path": rel,
            "title": meta.get("title") if isinstance(meta.get("title"), str) else "",
            "summary": meta.get("summary") if isinstance(meta.get("summary"), str) else "",
            "keywords": list(keywords) if isinstance(keywords, list)
                        and all(isinstance(k, str) for k in keywords) else [],
            "domain": meta.get("domain") if isinstance(meta.get("domain"), str) else "",
            "code_paths": [norm_code_path(c) for c in code_paths]
                          if isinstance(code_paths, list)
                          and all(isinstance(c, str) for c in code_paths) else [],
            "trust_level": meta.get("trust_level"),
            "verified_at": meta.get("verified_at"),
            "migration_status": meta.get("migration_status"),
            "est_tokens": math.ceil(nbytes / 4),
            "_body_text": body,
        })
    entries.sort(key=lambda e: e["path"])
    if migration_review_count:
        warns.append(
            f"{migration_review_count} 个迁移 shard 标记为 needs-review；"
            "请人工整理 keywords/code_paths 后改为 reviewed")
    return entries, errors, warns


# ---------------------------------------------------------------------------
# 索引生成（原子写）
# ---------------------------------------------------------------------------

def atomic_write(path: str, data: bytes):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".doc-memory-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as file_handle:
            file_handle.write(data)
            file_handle.flush()
            os.fsync(file_handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _index_header(entries, shash: str, mode: str, cold_count: int):
    domain_count = len({e["domain"] for e in entries})
    return [
        "# Docs as Memory L0 Index",
        "",
        "<!-- generated by `python3 doc_memory.py reindex`; do not edit manually.",
        f"     shards_hash: {shash}",
        f"     l0_mode: {mode} -->",
        "",
        (f"Shards: {len(entries)} | Domains: {domain_count} | "
         f"Cold: {cold_count} | Mode: {mode}"),
        "",
        ("用法：`search <关键词>` / `affected <代码路径>` 后只读 1–2 片；"
         "冷域默认折叠且不检索，需要时显式加 `--include-cold`。"),
        "",
    ]


def _render_index_mode(entries, shash: str, mode: str) -> str:
    hot = [e for e in entries if not is_cold_entry(e)]
    cold = [e for e in entries if is_cold_entry(e)]
    by_domain = {}
    for entry in hot:
        by_domain.setdefault(entry["domain"], []).append(entry)

    lines = _index_header(entries, shash, mode, len(cold))
    if mode in ("full", "compact"):
        for domain in sorted(by_domain):
            group = by_domain[domain]
            lines.append(f"## {domain} ({len(group)})")
            lines.append("")
            for entry in group:
                if mode == "full":
                    lines.append(
                        f"- {entry['title']} — {entry['summary']} — ({entry['path']})")
                else:
                    lines.append(f"- {entry['title']} — ({entry['path']})")
            lines.append("")
    elif mode == "domains":
        all_domains = {}
        for entry in entries:
            key = entry["domain"] or "(unset)"
            counts = all_domains.setdefault(key, {"hot": 0, "cold": 0})
            counts["cold" if is_cold_entry(entry) else "hot"] += 1
        lines.extend(["## Domain map", ""])
        for domain in sorted(all_domains):
            counts = all_domains[domain]
            lines.append(
                f"- {domain}: hot={counts['hot']}, cold={counts['cold']}")
        lines.append("")

    if cold:
        cold_domains = {}
        for entry in cold:
            cold_domains[entry["domain"]] = cold_domains.get(entry["domain"], 0) + 1
        summary = ", ".join(
            f"{domain or '(unset)'}={count}"
            for domain, count in sorted(cold_domains.items()))
        lines.extend([
            "## Cold domains (collapsed)",
            "",
            f"- {summary}",
            "",
        ])
    return "\n".join(lines)


def render_index_md(entries, shash: str):
    """动态选择 L0 详细度，硬保证 est_tokens ≤ L0_BUDGET。"""
    for mode in ("full", "compact", "domains"):
        rendered = _render_index_mode(entries, shash, mode)
        if est_tokens(rendered.encode("utf-8")) <= L0_BUDGET:
            return rendered, mode

    # 极端仓库：连 domain 列表也放不下时，只保留可操作的总览。
    cold_count = sum(1 for entry in entries if is_cold_entry(entry))
    lines = _index_header(entries, shash, "minimal", cold_count)
    lines.extend([
        "## Map",
        "",
        "- 仓库过大，L0 仅保留统计；请直接使用 `search` 或 `affected`。",
        "",
    ])
    rendered = "\n".join(lines)
    if est_tokens(rendered.encode("utf-8")) > L0_BUDGET:
        raise RuntimeError("internal error: minimal L0 exceeds token budget")
    return rendered, "minimal"


def build_index(entries, shash: str, l0_mode: str) -> dict:
    by_keyword = {}
    by_code_path = {}
    domains = {}
    for e in entries:
        for kw in e["keywords"]:
            by_keyword.setdefault(kw.lower(), []).append(e["path"])
        for cp in e["code_paths"]:
            by_code_path.setdefault(cp, []).append(e["path"])
        domains.setdefault(e["domain"], {})
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "shard_root": SHARD_ROOT.replace(os.sep, "/"),
        "shards_hash": shash,
        "l0_mode": l0_mode,
        "l0_budget_est_tokens": L0_BUDGET,
        "cold_shard_count": sum(1 for e in entries if is_cold_entry(e)),
        "shards": [{k: v for k, v in e.items()
                    if k != "est_tokens" and not k.startswith("_")}
                   for e in entries],
        "by_keyword": {k: sorted(v) for k, v in sorted(by_keyword.items())},
        "by_code_path": {k: sorted(v) for k, v in sorted(by_code_path.items())},
        "domains": domains,
    }


def cmd_reindex(args) -> int:
    root = resolve_root(args.root)
    guard_managed_paths(root)
    if not os.path.isdir(os.path.join(root, SHARD_ROOT)):
        eprint(f"error: {SHARD_ROOT}/ 不存在，请先 `python3 doc_memory.py init`")
        return 1
    entries, errors, warns = load_shards(root)
    for w in warns:
        eprint(f"warn: {w}")
    if errors:
        for e in errors:
            eprint(f"error: {e}")
        eprint("error: 存在非法碎片，索引未更新；请先修复或 `validate` 查看")
        return 1
    shash = shards_hash(root)
    index_md, l0_mode = render_index_md(entries, shash)
    index = build_index(entries, shash, l0_mode)
    atomic_write(os.path.join(root, INDEX_JSON),
                 (json.dumps(index, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    atomic_write(os.path.join(root, INDEX_MD), index_md.encode("utf-8"))
    imd_bytes = index_md.encode("utf-8")
    print(f"reindex 完成：{len(entries)} 碎片，{len(index['domains'])} 个 domain")
    print(f"  {INDEX_MD}  est_tokens={est_tokens(imd_bytes)} "
          f"(normalized_utf8_bytes={len(normalize_markdown_bytes(imd_bytes))}, "
          f"mode={l0_mode}, 预算≤{L0_BUDGET})")
    print(f"  {INDEX_JSON} shards_hash={shash[:12]}…")
    return 0


# ---------------------------------------------------------------------------
# search / affected
# ---------------------------------------------------------------------------

def apply_filters(entries, globs, include_cold=False):
    """按 glob 排除碎片路径（FR-DM-8 冷域约定，如 docs/history/**）。

    注意：fnmatch 的 * 可跨 / 匹配，故 "docs/history/*" 与 "docs/history/**"
    都会排除嵌套文件；可用 domain 前缀（如 "docs/shards/history/*"）做冷域隔离。
    """
    return [
        entry for entry in entries
        if (include_cold or not is_cold_entry(entry))
        and not any(fnmatch.fnmatch(entry["path"], glob) for glob in globs)
    ]


def score_entry(e, terms):
    """keyword 精确 x3 + keyword 子串/title x2 + summary/body/path x1。"""
    score = 0
    kws = [k.lower() for k in e["keywords"]]
    title = e["title"].lower()
    summary = e["summary"].lower()
    body = e.get("_body_text", "").lower()
    path = e["path"].lower()
    for t in terms:
        tl = t.lower()
        if tl in kws:
            score += 3
        elif any(tl in k for k in kws):
            score += 2
        if tl in title:
            score += 2
        if tl in summary:
            score += 1
        if tl in body:
            score += 1
        if tl in path:
            score += 1
    return score


def _handle_read_errors(errors, allow_partial: bool) -> bool:
    """打印读取错误；返回是否允许继续。"""
    if not errors:
        return True
    for error in errors:
        eprint(f"error: {error}")
    if not allow_partial:
        eprint("error: 读取失败已闭锁；修复后重试，或显式加 --allow-partial 降级")
        return False
    eprint("warn: --allow-partial 已启用；结果不完整，不可据此宣称验收通过")
    return True


def cmd_search(args) -> int:
    root = resolve_root(args.root)
    guard_managed_paths(root)
    terms = args.query.split()
    if not terms:
        eprint("error: query 不能为空")
        return 2
    if args.limit < 0:
        eprint("error: --limit 不能为负数")
        return 2
    entries, errors, _warns = load_shards(root, strict=True)
    if not _handle_read_errors(errors, args.allow_partial):
        return 1
    entries = apply_filters(entries, args.exclude_glob, args.include_cold)
    scored = [(score_entry(e, terms), e) for e in entries]
    hits = [e for s, e in sorted(scored, key=lambda x: (-x[0], x[1]["path"])) if s > 0]
    if args.limit:
        hits = hits[: args.limit]
    if args.json:
        print(json.dumps({
            "query": args.query,
            "partial": bool(errors),
            "results": [{
                "path": e["path"], "title": e["title"], "summary": e["summary"],
                "score": score_entry(e, terms), "est_tokens": e["est_tokens"],
            } for e in hits],
        }, ensure_ascii=False, indent=2))
    else:
        for e in hits:
            print(f"{e['path']} | {e['title']} | {e['summary']} | "
                  f"est_tokens={e['est_tokens']} score={score_entry(e, terms)}")
        if not hits:
            eprint("（无命中；可换关键词，注意 keywords 中英文都试试）")
    return 0


def cmd_affected(args) -> int:
    root = resolve_root(args.root)
    guard_managed_paths(root)
    try:
        q = checked_code_path(args.path, root, require_exists=False)
    except ValueError as exc:
        eprint(f"error: 查询路径非法: {exc}")
        return 2
    entries, errors, _warns = load_shards(root, strict=True)
    if not _handle_read_errors(errors, args.allow_partial):
        return 1
    entries = apply_filters(entries, args.exclude_glob, args.include_cold)
    hits = []
    for e in entries:
        for cp in e["code_paths"]:
            if cp and (q.startswith(cp + "/") or cp.startswith(q + "/") or q == cp):
                hits.append(e)
                break
    hits.sort(key=lambda e: e["path"])
    if args.json:
        print(json.dumps({
            "query_path": q,
            "partial": bool(errors),
            "results": [{
                "path": e["path"], "title": e["title"], "summary": e["summary"],
                "code_paths": e["code_paths"], "est_tokens": e["est_tokens"],
            } for e in hits],
        }, ensure_ascii=False, indent=2))
    else:
        for e in hits:
            print(f"{e['path']} | {e['title']} | {e['summary']} | "
                  f"est_tokens={e['est_tokens']} code_paths={','.join(e['code_paths'])}")
        if not hits:
            eprint(f"（无碎片声明 code_paths 覆盖 {q}）")
    return 0


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

def index_freshness_errors(root: str):
    """校验两个索引是否存在、可读，并与当前 shard 内容哈希一致。"""
    errors = []
    idx_json_path = os.path.join(root, INDEX_JSON)
    idx_md_path = os.path.join(root, INDEX_MD)
    current_hash = shards_hash(root)
    idx = None
    if not os.path.isfile(idx_json_path):
        errors.append(f"{INDEX_JSON} 不存在，请运行 reindex")
    else:
        try:
            with open(idx_json_path, "r", encoding="utf-8") as f:
                idx = json.load(f)
            if not isinstance(idx, dict):
                errors.append(f"{INDEX_JSON} 顶层必须是对象，请 reindex")
                idx = None
            stored = idx.get("shards_hash") if idx else None
            if idx and idx.get("schema_version") != SCHEMA_VERSION:
                errors.append(f"{INDEX_JSON} schema_version 不符（期望 {SCHEMA_VERSION}），请 reindex")
            if stored != current_hash:
                errors.append(f"索引已过期：碎片内容 hash 与 {INDEX_JSON} 不一致，请 reindex")
        except (json.JSONDecodeError, OSError) as e:
            errors.append(f"{INDEX_JSON} 损坏: {e}")
    if not os.path.isfile(idx_md_path):
        errors.append(f"{INDEX_MD} 不存在，请运行 reindex")
    else:
        try:
            with open(idx_md_path, "r", encoding="utf-8") as f:
                head = f.read(4096)
            if f"shards_hash: {current_hash}" not in head:
                errors.append(f"{INDEX_MD} 与当前碎片不一致，请 reindex")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{INDEX_MD} 损坏: {exc}")
    return errors, idx


def cmd_validate(args) -> int:
    root = resolve_root(args.root)
    guard_managed_paths(root)
    errors, warns = [], []

    if not os.path.isdir(os.path.join(root, SHARD_ROOT)):
        errors.append(f"{SHARD_ROOT}/ 不存在（先 init）")
    entries, ferrs, fwrns = load_shards(root)
    errors.extend(ferrs)
    warns.extend(fwrns)
    fresh_errors, idx = index_freshness_errors(root)
    errors.extend(fresh_errors)

    idx_md_path = os.path.join(root, INDEX_MD)
    if os.path.isfile(idx_md_path):
        try:
            with open(idx_md_path, "rb") as file_handle:
                l0_tokens = est_tokens(file_handle.read())
            if l0_tokens > L0_BUDGET:
                errors.append(
                    f"{INDEX_MD} 超 L0 预算：est_tokens={l0_tokens} > {L0_BUDGET}")
        except OSError as exc:
            errors.append(f"{INDEX_MD} 无法读取: {exc}")
    if idx is not None and idx.get("l0_budget_est_tokens") not in (None, L0_BUDGET):
        warns.append(
            f"{INDEX_JSON} 记录的 L0 预算与当前工具不同，请 reindex")

    for w in warns:
        print(f"warn: {w}")
    for e in errors:
        print(f"error: {e}")
    n = len(entries)
    if errors:
        print(f"validate: {len(errors)} error(s), {len(warns)} warn(s)，扫描碎片 {n} 个 → 未通过")
        return 1
    print(f"validate: 0 error, {len(warns)} warn(s)，扫描碎片 {n} 个 → 通过")
    return 0


# ---------------------------------------------------------------------------
# overview
# ---------------------------------------------------------------------------

def cmd_overview(args) -> int:
    root = resolve_root(args.root)
    guard_managed_paths(root)
    idx_md_path = os.path.join(root, INDEX_MD)
    entries, parse_errors, _warns = load_shards(root, strict=True)
    fresh_errors, idx = index_freshness_errors(root)
    errors = parse_errors + fresh_errors
    if errors and not args.allow_stale:
        for error in errors:
            eprint(f"error: {error}")
        eprint("error: overview 已闭锁；先运行 reindex/validate，或显式加 --allow-stale")
        return 1
    if errors:
        for error in errors:
            eprint(f"warn: {error}")
        eprint("warn: --allow-stale 已启用；以下总览不可作为当前事实依据")
    if args.json:
        by_domain = {}
        for e in entries:
            by_domain.setdefault(e["domain"], 0)
            by_domain[e["domain"]] += 1
        imd_bytes = b""
        if os.path.isfile(idx_md_path):
            try:
                with open(idx_md_path, "rb") as f:
                    imd_bytes = f.read()
            except OSError as exc:
                eprint(f"error: {INDEX_MD} 无法读取: {exc}")
                return 1
        print(json.dumps({
            "shard_count": len(entries),
            "domains": by_domain,
            "index_md_est_tokens": est_tokens(imd_bytes) if imd_bytes else None,
            "l0_mode": idx.get("l0_mode") if idx else None,
            "errors": errors,
            "stale_allowed": bool(errors and args.allow_stale),
        }, ensure_ascii=False, indent=2))
        return 0
    if not os.path.isfile(idx_md_path):
        eprint(f"error: {INDEX_MD} 不存在，请先 reindex")
        return 1
    try:
        with open(idx_md_path, "r", encoding="utf-8") as f:
            sys.stdout.write(f.read())
    except (OSError, UnicodeDecodeError) as exc:
        eprint(f"error: {INDEX_MD} 无法读取: {exc}")
        return 1
    return 0


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

EMBEDDED_SHARD_TEMPLATE = """---
title:                    # 必填，短标题
summary:                  # 必填，≤80 中文字，供 L0 索引展示
keywords: []              # 必填，中英都写；检索主依赖
domain:                   # 必填，slug，如 backend / frontend / product / ops
code_paths: []            # 建议，仓内相对路径，禁止绝对路径、.. 与符号链接逃逸
trust_level: 4            # 建议，1=实现真相 2=API契约 3=测试 4=叙述文档
verified_at: "YYYY-MM-DD" # 可选，超 90 天 validate 会 warn（注意加引号）
---

# 标题

一事一碎片，正文建议 ≤150 行。改完必须 `python3 doc_memory.py reindex`。
"""

EXAMPLE_SHARD = """---
title: 示例碎片：项目简介
summary: 这是 doc-memory init 生成的示例碎片，展示 frontmatter 写法，可直接删除。
keywords: [example, doc-memory, 示例]
domain: meta
code_paths: []
trust_level: 4
---

# 示例碎片

- 一事一碎片，正文建议 ≤150 行。
- frontmatter 必填：title / summary / keywords / domain。
- 改完碎片后必须运行：`python3 doc_memory.py reindex`。
"""


def cmd_init(args) -> int:
    root = resolve_root(args.root)
    guard_managed_paths(root)
    shard_dir = os.path.join(root, SHARD_ROOT)
    os.makedirs(shard_dir, exist_ok=True)

    tpl_src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "templates", "shard._TEMPLATE.md")
    tpl_dst = os.path.join(shard_dir, TEMPLATE_NAME)
    if not os.path.exists(tpl_dst):
        content = EMBEDDED_SHARD_TEMPLATE
        if os.path.isfile(tpl_src):
            with open(tpl_src, "r", encoding="utf-8") as f:
                content = f.read()
        atomic_write(tpl_dst, content.encode("utf-8"))
        print(f"created: {SHARD_ROOT}/{TEMPLATE_NAME}")

    example = os.path.join(shard_dir, "example-hello.md")
    if not os.path.exists(example):
        atomic_write(example, EXAMPLE_SHARD.encode("utf-8"))
        print(f"created: {SHARD_ROOT}/example-hello.md")

    rc = cmd_reindex(args)
    if rc == 0:
        print("init 完成。下一步：运行 validate；已有文档可先用 migrate --dry-run 预演。")
    return rc


# ---------------------------------------------------------------------------
# migrate（只读源文档，向 docs/shards 写派生副本）
# ---------------------------------------------------------------------------

def _portable_component(value: str, fallback: str = "document") -> str:
    value = value.strip().replace(" ", "-")
    value = re.sub(r"[^0-9A-Za-z\u3400-\u9fff._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-_.")
    if not value:
        value = fallback
    if value.startswith("_"):
        value = "doc-" + value.lstrip("_")
    return value


def _migration_files(source: str, globs, max_files: int):
    """列出 UTF-8 Markdown 候选；不跟随目录符号链接。"""
    if os.path.isfile(source):
        paths = [source] if source.lower().endswith(".md") else []
        source_root = os.path.dirname(source)
    else:
        source_root = source
        paths = []
        for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
            dirnames[:] = sorted(
                dirname for dirname in dirnames
                if dirname not in DEFAULT_IGNORED_DIR_NAMES
                and not os.path.islink(os.path.join(dirpath, dirname)))
            for filename in sorted(filenames):
                if filename.lower().endswith(".md"):
                    paths.append(os.path.join(dirpath, filename))

    selected = []
    all_globs = tuple(DEFAULT_MIGRATE_EXCLUDES) + tuple(globs)
    for full in sorted(paths):
        real = os.path.realpath(full)
        try:
            contained = os.path.commonpath((source_root, real)) == source_root
        except ValueError:
            contained = False
        if not contained:
            continue
        rel = os.path.relpath(real, source_root).replace(os.sep, "/")
        if any(fnmatch.fnmatch(rel, pattern) for pattern in all_globs):
            continue
        selected.append((rel, real))
    if max_files and len(selected) > max_files:
        raise ValueError(
            f"migration matched {len(selected)} files, over --max-files={max_files}")
    return source_root, selected


def _shorten_generated_text(value: str, limit: int) -> str:
    value = value.replace("\r", " ").replace("\n", " ").strip()
    if len(value) <= limit:
        return value
    shortened = value[:limit - 1].rstrip()
    if " " in shortened and sum(ch.isascii() for ch in shortened) > len(shortened) / 2:
        shortened = shortened.rsplit(" ", 1)[0] or shortened
    return shortened.rstrip(".,;:，。；：") + "…"


def _extract_title_summary(text: str, fallback: str):
    lines = text.splitlines()
    in_frontmatter = bool(lines and lines[0].strip() == "---")
    title = ""
    paragraph = []
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if in_frontmatter:
            if index > 0 and stripped == "---":
                in_frontmatter = False
            continue
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*$", stripped)
        if heading and not title:
            title = heading.group(1).strip()
            continue
        if not stripped or stripped.startswith(("#", "<!--", "```", "---")):
            if paragraph:
                break
            continue
        cleaned = re.sub(r"[`*_>\[\]()]", "", stripped)
        if cleaned:
            paragraph.append(cleaned)
        if len(" ".join(paragraph)) >= 100:
            break
    title = (title or fallback).replace('"', "'").strip()
    summary = " ".join(paragraph).replace('"', "'").strip()
    if not summary:
        summary = f"由 {fallback} 迁移生成的只读副本，元数据待人工复核。"
    return (
        _shorten_generated_text(title, 120),
        _shorten_generated_text(summary, 72),
    )


def _migration_keywords(title: str, rel: str):
    raw = re.findall(r"[A-Za-z0-9_-]{2,}|[\u3400-\u9fff]{2,8}", f"{title} {rel}")
    out = []
    for item in raw:
        cleaned = item.lower().strip("._-,").replace(",", "-")
        if cleaned and cleaned not in out:
            out.append(cleaned)
        if len(out) == 8:
            break
    return out or ["imported", "待整理"]


def _migration_destination(root: str, source_root: str, rel: str):
    source_label = _portable_component(os.path.basename(source_root), "source")
    pieces = rel.split("/")
    clean_dirs = [_portable_component(piece, "dir") for piece in pieces[:-1]]
    stem = _portable_component(os.path.splitext(pieces[-1])[0], "document")
    relative_destination = os.path.join(
        SHARD_ROOT, "imported", source_label, *clean_dirs, stem + ".md")
    safe_relpath(relative_destination, root)
    return relative_destination.replace(os.sep, "/")


def _render_migrated_shard(text: str, source_label: str, title: str,
                           summary: str, keywords, domain: str, digest: str):
    keyword_text = ", ".join(
        f'"{item.replace(chr(34), chr(39))}"' for item in keywords)
    safe_source = source_label.replace('"', "'").replace("\r", " ").replace("\n", " ")
    return (
        "---\n"
        f'title: "{title}"\n'
        f'summary: "{summary}"\n'
        f"keywords: [{keyword_text}]\n"
        f"domain: {domain}\n"
        "code_paths: []\n"
        "trust_level: 4\n"
        "migration_status: needs-review\n"
        f'source_path: "{safe_source}"\n'
        f'source_sha256: "{digest}"\n'
        f'migrated_at: "{date.today().isoformat()}"\n'
        "---\n\n"
        "<!-- Docs as Memory migrated copy. Source file is unchanged; "
        "metadata and code_paths require human review. -->\n\n"
        + text.rstrip() + "\n"
    )


def cmd_migrate(args) -> int:
    root = resolve_root(args.root)
    guard_managed_paths(root)
    if args.max_files < 0:
        eprint("error: --max-files 不能为负数")
        return 2
    if args.json and args.apply:
        eprint("error: --json 当前只用于 dry-run 清单；apply 请使用普通输出")
        return 2
    source = os.path.realpath(os.path.abspath(args.source))
    if not os.path.exists(source):
        eprint(f"error: source 不存在: {source}")
        return 2
    if not (os.path.isfile(source) or os.path.isdir(source)):
        eprint(f"error: source 必须是文件或目录: {source}")
        return 2
    if not SLUG_RE.match(args.domain):
        eprint(f"error: --domain 必须是 slug: {args.domain!r}")
        return 2
    if os.path.isdir(os.path.join(root, SHARD_ROOT)):
        _entries, existing_errors, _warns = load_shards(root)
        if existing_errors:
            for error in existing_errors:
                eprint(f"error: {error}")
            eprint("error: 现有 shards 未通过预检；未写入任何迁移文件")
            return 1

    try:
        source_root, files = _migration_files(
            source, args.exclude_glob, args.max_files)
    except ValueError as exc:
        eprint(f"error: {exc}")
        return 2
    if not files:
        eprint("error: 没有匹配到可迁移的 .md 文件")
        return 1

    plans, errors = [], []
    for rel, full in files:
        try:
            with open(full, "r", encoding="utf-8") as file_handle:
                text = file_handle.read()
            with open(full, "rb") as file_handle:
                digest = hashlib.sha256(file_handle.read()).hexdigest()
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: 无法作为 UTF-8 Markdown 读取: {exc}")
            continue
        destination = _migration_destination(root, source_root, rel)
        title, summary = _extract_title_summary(
            text, os.path.splitext(os.path.basename(rel))[0])
        content = _render_migrated_shard(
            text,
            f"{os.path.basename(source_root)}/{rel}",
            title,
            summary,
            _migration_keywords(title, rel),
            args.domain,
            digest,
        )
        full_destination = os.path.join(root, destination)
        plans.append({
            "source": full,
            "source_rel": rel,
            "destination": destination,
            "full_destination": full_destination,
            "content": content,
            "exists": os.path.exists(full_destination),
            "source_sha256": digest,
        })

    destinations = {}
    for plan in plans:
        destinations.setdefault(plan["destination"], []).append(plan["source_rel"])
    for destination, source_paths in destinations.items():
        if len(source_paths) > 1:
            errors.append(
                f"多个源文件清洗后落到同一目标 {destination}: "
                + ", ".join(source_paths))

    if errors:
        for error in errors:
            eprint(f"error: {error}")
        eprint("error: 预检未通过，未写入任何文件")
        return 1
    conflicts = [plan for plan in plans if plan["exists"]]
    if args.apply and conflicts and not args.force:
        for plan in conflicts:
            eprint(f"error: 目标已存在: {plan['destination']}")
        eprint("error: 未写入任何文件；如确认覆盖派生副本，显式加 --force")
        return 1

    if args.json:
        print(json.dumps({
            "mode": "apply" if args.apply else "dry-run",
            "source": source,
            "count": len(plans),
            "conflicts": len(conflicts),
            "files": [{
                "source": plan["source_rel"],
                "destination": plan["destination"],
                "exists": plan["exists"],
                "source_sha256": plan["source_sha256"],
            } for plan in plans],
        }, ensure_ascii=False, indent=2))
    else:
        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"migrate {mode}: {len(plans)} file(s), conflicts={len(conflicts)}")
        for plan in plans:
            suffix = " [exists]" if plan["exists"] else ""
            print(f"  {plan['source_rel']} -> {plan['destination']}{suffix}")

    if not args.apply:
        print("未写入。确认清单后加 --apply；源文件在任何模式下都不会修改。")
        return 0

    for plan in plans:
        os.makedirs(os.path.dirname(plan["full_destination"]), exist_ok=True)
        atomic_write(plan["full_destination"], plan["content"].encode("utf-8"))
    print(f"已写入 {len(plans)} 个派生 shard；源文件未修改。正在重建索引…")
    return cmd_reindex(args)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="doc-memory",
        description="文档碎片索引 CLI（零依赖）。先 L0 索引，再按需下钻碎片。")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    p.add_argument("--root", default=".", help="项目根（默认当前目录）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="建 docs/shards、模板、示例碎片并生成索引")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("reindex", help="扫描碎片，原子写 INDEX.md + index.json")
    sp.set_defaults(func=cmd_reindex)

    sp = sub.add_parser(
        "search", help="keywords 优先 + title/summary/body/path 字面检索")
    sp.add_argument("query")
    sp.add_argument("--json", action="store_true")
    sp.add_argument(
        "--limit", type=int, default=DEFAULT_SEARCH_LIMIT,
        help=f"最多输出 N 条（默认 {DEFAULT_SEARCH_LIMIT}；0=不限）")
    sp.add_argument("--include-cold", action="store_true",
                    help="包含 domain/path 为 history/cold/archive 的冷域")
    sp.add_argument("--allow-partial", action="store_true",
                    help="损坏碎片存在时仍返回不完整结果（不可用于验收）")
    sp.add_argument("--exclude-glob", action="append", default=[],
                    metavar="GLOB", help="排除路径匹配的碎片（可多次），如 'docs/history/**'")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("affected", help="按代码路径反查受影响碎片")
    sp.add_argument("path")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--include-cold", action="store_true",
                    help="包含 domain/path 为 history/cold/archive 的冷域")
    sp.add_argument("--allow-partial", action="store_true",
                    help="损坏碎片存在时仍返回不完整结果（不可用于验收）")
    sp.add_argument("--exclude-glob", action="append", default=[],
                    metavar="GLOB", help="排除路径匹配的碎片（可多次），如 'docs/history/**'")
    sp.set_defaults(func=cmd_affected)

    sp = sub.add_parser("validate", help="frontmatter/路径/索引新鲜度/verified_at 体检")
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("overview", help="打印 L0 INDEX.md（--json 输出统计）")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--allow-stale", action="store_true",
                    help="显式读取过期 L0（仅诊断，不可作为当前事实依据）")
    sp.set_defaults(func=cmd_overview)

    sp = sub.add_parser(
        "migrate",
        help="把现有 Markdown 复制为派生 shards；默认 dry-run，永不修改源文件")
    sp.add_argument("--source", required=True, help="源 .md 文件或目录（可在项目外）")
    mode = sp.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="只显示计划（默认）")
    mode.add_argument("--apply", action="store_true",
                      help="确认后写入 docs/shards/imported 并 reindex")
    sp.add_argument("--force", action="store_true",
                    help="仅配合 --apply，覆盖已存在的派生 shard")
    sp.add_argument("--domain", default="imported",
                    help="生成 shard 的 domain slug（默认 imported）")
    sp.add_argument("--exclude-glob", action="append", default=[],
                    metavar="GLOB", help="额外排除源目录中的相对路径 glob（可多次）")
    sp.add_argument("--max-files", type=int, default=500,
                    help="安全上限（默认 500；0=不限）")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_migrate)

    args = p.parse_args(argv)
    if getattr(args, "force", False) and not getattr(args, "apply", False):
        p.error("--force 只能与 migrate --apply 一起使用")
    try:
        return args.func(args)
    except ValueError as e:
        eprint(f"error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
