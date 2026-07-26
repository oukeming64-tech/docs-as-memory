#!/usr/bin/env python3
"""Install the bundled Docs as Memory engine into one project, safely and idempotently."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Optional


START_MARKER = "<!-- doc-memory:start -->"
END_MARKER = "<!-- doc-memory:end -->"


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            pass


configure_utf8_stdio()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: str, data: bytes, mode: Optional[int] = None) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".doc-memory-", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def project_path(root: str, relative: str) -> str:
    normalized = relative.replace("\\", "/")
    if os.path.isabs(relative) or ".." in normalized.split("/"):
        raise ValueError(f"path must stay inside project root: {relative}")
    target = os.path.realpath(os.path.join(root, relative))
    try:
        contained = os.path.commonpath((root, target)) == root
    except ValueError:
        contained = False
    if not contained:
        raise ValueError(f"path escapes project root: {relative}")
    return target


def unique_backup(target: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    base = target + f".doc-memory.bak-{timestamp}"
    candidate = base
    counter = 1
    while os.path.exists(candidate):
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def merge_marked_section(existing: str, snippet: str) -> str:
    block = f"{START_MARKER}\n{snippet.rstrip()}\n{END_MARKER}"
    start_count = existing.count(START_MARKER)
    end_count = existing.count(END_MARKER)
    if start_count != end_count or start_count > 1:
        raise ValueError("AGENTS markers are missing or duplicated; repair them before install")
    if start_count == 1:
        start = existing.index(START_MARKER)
        end = existing.index(END_MARKER, start) + len(END_MARKER)
        return existing[:start] + block + existing[end:]
    if existing and not existing.endswith("\n"):
        existing += "\n"
    separator = "\n" if existing else ""
    return existing + separator + block + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install doc_memory.py into a project. Default is dry-run; "
            "existing files are never replaced without --force."
        ))
    parser.add_argument("--root", required=True, help="target project root")
    parser.add_argument("--apply", action="store_true", help="perform planned writes")
    parser.add_argument("--force", action="store_true",
                        help="replace a different existing doc_memory.py")
    parser.add_argument("--with-agents-snippet", action="store_true",
                        help="idempotently add/update a marked AGENTS section")
    parser.add_argument("--agents-file", default="AGENTS.md",
                        help="project-relative agent instructions file")
    parser.add_argument("--init", action="store_true",
                        help="after install, run doc_memory.py init (requires --apply)")
    args = parser.parse_args(argv)

    if args.force and not args.apply:
        parser.error("--force requires --apply")
    if args.init and not args.apply:
        parser.error("--init requires --apply")

    root = os.path.realpath(os.path.abspath(args.root))
    if not os.path.isdir(root):
        parser.error(f"project root does not exist: {root}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    bundled_cli = os.path.join(script_dir, "doc_memory.py")
    snippet_file = os.path.join(
        os.path.dirname(script_dir), "templates", "AGENTS_SNIPPET.md")
    if not os.path.isfile(bundled_cli):
        print(f"error: bundled engine missing: {bundled_cli}", file=sys.stderr)
        return 1

    try:
        with open(bundled_cli, "rb") as handle:
            cli_data = handle.read()
    except OSError as exc:
        print(f"error: bundled engine unreadable: {exc}", file=sys.stderr)
        return 1
    cli_target = project_path(root, "doc_memory.py")
    existing_cli = None
    if os.path.exists(cli_target):
        if not os.path.isfile(cli_target):
            print(f"error: target is not a regular file: {cli_target}", file=sys.stderr)
            return 1
        try:
            with open(cli_target, "rb") as handle:
                existing_cli = handle.read()
        except OSError as exc:
            print(f"error: cannot read existing CLI: {exc}", file=sys.stderr)
            return 1
    cli_changed = existing_cli != cli_data
    if existing_cli is not None and cli_changed and not args.force:
        print(
            "error: project doc_memory.py differs; dry-run with checksums shown below, "
            "then use --apply --force only if replacement is intended",
            file=sys.stderr,
        )
        print(f"current sha256={digest(existing_cli)}", file=sys.stderr)
        print(f"bundled sha256={digest(cli_data)}", file=sys.stderr)
        return 1

    agents_target = None
    agents_existing = ""
    agents_merged = ""
    if args.with_agents_snippet:
        if not os.path.isfile(snippet_file):
            print(f"error: snippet missing: {snippet_file}", file=sys.stderr)
            return 1
        agents_target = project_path(root, args.agents_file)
        if os.path.exists(agents_target):
            if not os.path.isfile(agents_target):
                print(f"error: AGENTS target is not a file: {agents_target}", file=sys.stderr)
                return 1
            try:
                with open(agents_target, "r", encoding="utf-8") as handle:
                    agents_existing = handle.read()
            except (OSError, UnicodeDecodeError) as exc:
                print(f"error: cannot read AGENTS as UTF-8: {exc}", file=sys.stderr)
                return 1
        try:
            with open(snippet_file, "r", encoding="utf-8") as handle:
                snippet = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"error: cannot read bundled AGENTS snippet: {exc}", file=sys.stderr)
            return 1
        try:
            agents_merged = merge_marked_section(agents_existing, snippet)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"install {mode}: root={root}")
    print(
        f"  doc_memory.py: {'update' if cli_changed else 'unchanged'} "
        f"sha256={digest(cli_data)[:12]}…")
    if agents_target:
        state = "update" if agents_merged != agents_existing else "unchanged"
        print(f"  {os.path.relpath(agents_target, root)}: {state}")
    if not args.apply:
        print("未写入。确认后加 --apply；不同的现有 CLI 还需要显式 --force。")
        return 0

    if cli_changed:
        atomic_write(cli_target, cli_data, mode=0o755)
        print("written: doc_memory.py")
    if agents_target and agents_merged != agents_existing:
        if agents_existing:
            backup = unique_backup(agents_target)
            atomic_write(backup, agents_existing.encode("utf-8"))
            print(f"backup: {os.path.basename(backup)}")
        atomic_write(agents_target, agents_merged.encode("utf-8"))
        print(f"written: {os.path.relpath(agents_target, root)}")
    if args.init:
        completed = subprocess.run(
            [sys.executable, cli_target, "--root", root, "init"],
            check=False,
        )
        if completed.returncode:
            return completed.returncode
    print("安装完成。建议下一步运行：python3 doc_memory.py validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
