#!/usr/bin/env python3
"""Install the complete doc-memory skill package with dry-run and backups."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
from datetime import datetime


SKILL_NAME = "doc-memory"


def package_digest(root: str):
    digest = hashlib.sha256()
    count = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            if os.path.islink(os.path.join(dirpath, name)):
                raise ValueError(
                    f"skill package may not contain symlink directories: "
                    f"{os.path.join(dirpath, name)}")
        dirnames[:] = sorted(
            name for name in dirnames
            if name != "__pycache__")
        for filename in sorted(filenames):
            if filename.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(dirpath, filename)
            if os.path.islink(full):
                raise ValueError(f"skill package may not contain symlinks: {full}")
            relative = os.path.relpath(full, root).replace(os.sep, "/")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            with open(full, "rb") as handle:
                digest.update(handle.read())
            count += 1
    return digest.hexdigest(), count


def ignored(_directory, names):
    return {
        name for name in names
        if name == "__pycache__" or name.endswith((".pyc", ".pyo"))
    }


def unique_backup(target: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    base = target + f".backup-{timestamp}"
    candidate = base
    counter = 1
    while os.path.exists(candidate):
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install the complete doc-memory skill. Default is dry-run; "
            "a differing installed copy requires --apply --force and is backed up."
        ))
    parser.add_argument(
        "--skills-root",
        default=os.path.expanduser("~/.codex/skills"),
        help="skills directory (default ~/.codex/skills)",
    )
    parser.add_argument("--apply", action="store_true", help="perform installation")
    parser.add_argument(
        "--force",
        action="store_true",
        help="upgrade a differing installed copy after making a recoverable backup",
    )
    args = parser.parse_args(argv)
    if args.force and not args.apply:
        parser.error("--force requires --apply")

    source = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    skills_root = os.path.realpath(os.path.abspath(os.path.expanduser(args.skills_root)))
    target = os.path.join(skills_root, SKILL_NAME)
    if os.path.exists(skills_root) and not os.path.isdir(skills_root):
        print(f"error: skills root is not a directory: {skills_root}", file=sys.stderr)
        return 1

    if os.path.realpath(target) == source:
        print(f"already installed at {target}")
        return 0
    try:
        source_digest, source_count = package_digest(source)
    except (OSError, ValueError) as exc:
        print(f"error: source package invalid: {exc}", file=sys.stderr)
        return 1

    target_digest = None
    target_count = 0
    if os.path.lexists(target):
        if os.path.islink(target) or not os.path.isdir(target):
            print(f"error: target must be a real directory: {target}", file=sys.stderr)
            return 1
        try:
            target_digest, target_count = package_digest(target)
        except (OSError, ValueError) as exc:
            print(f"error: installed package invalid: {exc}", file=sys.stderr)
            return 1

    same = target_digest == source_digest
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"skill install {mode}: {target}")
    print(f"  source: files={source_count} sha256={source_digest}")
    if target_digest:
        print(f"  target: files={target_count} sha256={target_digest}")
    else:
        print("  target: absent")
    if same:
        print("技能包已是当前版本，无需写入。")
        return 0
    if target_digest and not args.force:
        print(
            "error: installed package differs; inspect the checksums, then use "
            "--apply --force to upgrade with backup",
            file=sys.stderr,
        )
        return 1
    if not args.apply:
        print("未写入。确认后加 --apply。")
        return 0

    os.makedirs(skills_root, exist_ok=True)
    staging_root = tempfile.mkdtemp(prefix=".doc-memory-install-", dir=skills_root)
    staging_target = os.path.join(staging_root, SKILL_NAME)
    backup = None
    try:
        shutil.copytree(source, staging_target, ignore=ignored)
        staged_digest, staged_count = package_digest(staging_target)
        if (staged_digest, staged_count) != (source_digest, source_count):
            print("error: staged package checksum mismatch", file=sys.stderr)
            return 1
        if target_digest:
            backup = unique_backup(target)
            os.replace(target, backup)
            print(f"backup: {backup}")
        try:
            os.replace(staging_target, target)
        except OSError:
            if backup and not os.path.exists(target) and os.path.exists(backup):
                os.replace(backup, target)
            raise
    except OSError as exc:
        print(f"error: installation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    print(f"installed: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
