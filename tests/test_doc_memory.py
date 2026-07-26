from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "doc_memory.py"
BUNDLED_CLI = REPO_ROOT / "doc-memory" / "scripts" / "doc_memory.py"
INSTALLER = REPO_ROOT / "doc-memory" / "scripts" / "install_project.py"
SKILL_INSTALLER = REPO_ROOT / "doc-memory" / "scripts" / "install_skill.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DocMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="doc-memory-test-")
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, *arguments, cli=CLI, root=None):
        command = [
            sys.executable,
            str(cli),
            "--root",
            str(root or self.root),
            *arguments,
        ]
        return subprocess.run(
            command, encoding="utf-8", capture_output=True,
            timeout=20, check=False)

    def init(self):
        completed = self.run_cli("init")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed

    def write_shard(self, relative: str, frontmatter: str, body="# Body\n"):
        destination = self.root / "docs" / "shards" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            f"---\n{frontmatter.rstrip()}\n---\n\n{body}",
            encoding="utf-8",
        )
        return destination

    def make_symlink(self, source: Path, destination: Path):
        try:
            os.symlink(str(source), str(destination))
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks are unavailable on this runner: {exc}")

    def test_standalone_init_embeds_template(self):
        standalone = self.root / "doc_memory.py"
        shutil.copyfile(CLI, standalone)
        completed = self.run_cli("init", cli=standalone)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        template = self.root / "docs" / "shards" / "_TEMPLATE.md"
        self.assertTrue(template.is_file())
        self.assertIn("title:", template.read_text(encoding="utf-8"))

    def test_version_is_public_release_version(self):
        completed = subprocess.run(
            [sys.executable, str(CLI), "--version"],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "doc-memory 0.1.0")

    def test_cli_forces_utf8_output_on_narrow_locale(self):
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"
        completed = subprocess.run(
            [sys.executable, str(CLI), "--root", str(self.root), "init"],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
            env=environment,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("reindex 完成", completed.stdout)

    def test_overview_fails_closed_when_index_is_stale(self):
        self.init()
        shard = self.root / "docs" / "shards" / "example-hello.md"
        shard.write_text(
            shard.read_text(encoding="utf-8") + "\nchanged\n",
            encoding="utf-8",
        )
        blocked = self.run_cli("overview")
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("已闭锁", blocked.stderr)
        diagnostic = self.run_cli("overview", "--allow-stale")
        self.assertEqual(diagnostic.returncode, 0, diagnostic.stderr)
        self.assertIn("不可作为当前事实", diagnostic.stderr)

    def test_scalar_title_is_rejected_without_search_crash(self):
        self.init()
        self.write_shard(
            "example-hello.md",
            "title: 123\n"
            "summary: valid\n"
            "keywords: [valid]\n"
            "domain: meta\n",
        )
        reindex = self.run_cli("reindex")
        self.assertEqual(reindex.returncode, 1)
        self.assertIn("title 必须是字符串", reindex.stderr)
        search = self.run_cli("search", "valid")
        self.assertEqual(search.returncode, 1)
        self.assertNotIn("Traceback", search.stderr)

    def test_backslash_path_escape_is_rejected(self):
        self.init()
        self.write_shard(
            "escape.md",
            "title: escape\n"
            "summary: escape\n"
            "keywords: [escape]\n"
            "domain: meta\n"
            "code_paths: ['..\\\\outside.txt']\n",
        )
        backslash = self.run_cli("reindex")
        self.assertEqual(backslash.returncode, 1)
        self.assertIn("escapes root", backslash.stderr)

    def test_symlink_path_escape_is_rejected(self):
        self.init()
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        (outside / "file.txt").write_text("outside", encoding="utf-8")
        self.make_symlink(outside, self.root / "link")
        self.write_shard(
            "symlink.md",
            "title: symlink\n"
            "summary: symlink\n"
            "keywords: [symlink]\n"
            "domain: meta\n"
            "code_paths: [link/file.txt]\n",
        )
        symlink = self.run_cli("reindex")
        self.assertEqual(symlink.returncode, 1)
        self.assertIn("escapes root", symlink.stderr)

    def test_partial_results_require_explicit_override(self):
        self.init()
        broken = self.root / "docs" / "shards" / "broken.md"
        broken.write_text("# no frontmatter\n", encoding="utf-8")
        blocked = self.run_cli("search", "example")
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("读取失败已闭锁", blocked.stderr)
        partial = self.run_cli("search", "example", "--allow-partial")
        self.assertEqual(partial.returncode, 0, partial.stderr)
        self.assertIn("example-hello.md", partial.stdout)
        self.assertIn("结果不完整", partial.stderr)

    def test_duplicate_fields_are_rejected(self):
        self.init()
        self.write_shard(
            "example-hello.md",
            "title: first\n"
            "title: second\n"
            "summary: duplicate\n"
            "keywords: [duplicate]\n"
            "domain: meta\n",
        )
        duplicate = self.run_cli("reindex")
        self.assertEqual(duplicate.returncode, 1)
        self.assertIn("字段重复", duplicate.stderr)

    def test_symlinked_shards_are_rejected(self):
        self.init()
        outside = Path(self.temporary.name) / "outside-shard.md"
        outside.write_text(
            "---\ntitle: outside\nsummary: outside\n"
            "keywords: [outside]\ndomain: meta\n---\n",
            encoding="utf-8",
        )
        (self.root / "docs" / "shards" / "example-hello.md").unlink()
        self.make_symlink(
            outside, self.root / "docs" / "shards" / "linked.md")
        linked = self.run_cli("reindex")
        self.assertEqual(linked.returncode, 2)
        self.assertIn("symlinked shard", linked.stderr)

    def test_managed_docs_symlink_cannot_escape_project(self):
        outside = Path(self.temporary.name) / "external-docs"
        outside.mkdir()
        self.make_symlink(outside, self.root / "docs")
        completed = self.run_cli("init")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("escapes root", completed.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_cold_domains_are_opt_in(self):
        self.init()
        shard = self.root / "docs" / "shards" / "example-hello.md"
        text = shard.read_text(encoding="utf-8").replace(
            "domain: meta", "domain: history")
        shard.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_cli("reindex").returncode, 0)
        default = self.run_cli("search", "example")
        self.assertEqual(default.returncode, 0)
        self.assertEqual(default.stdout, "")
        included = self.run_cli("search", "example", "--include-cold")
        self.assertEqual(included.returncode, 0, included.stderr)
        self.assertIn("example-hello.md", included.stdout)

    def test_l0_dynamically_collapses_to_budget(self):
        shard_root = self.root / "docs" / "shards"
        shard_root.mkdir(parents=True)
        for index in range(220):
            self.write_shard(
                f"bulk/doc-{index:03d}.md",
                f"title: Document {index} with a deliberately long descriptive title\n"
                f"summary: Summary {index} " + ("details " * 12) + "\n"
                f"keywords: [document, item-{index}]\n"
                "domain: bulk\n",
                body=f"# Document {index}\n\nbody\n",
            )
        completed = self.run_cli("reindex")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        index_bytes = (self.root / "docs" / "INDEX.md").read_bytes()
        self.assertLessEqual((len(index_bytes) + 3) // 4, 1500)
        metadata = json.loads(
            (self.root / "docs" / "index.json").read_text(encoding="utf-8"))
        self.assertIn(metadata["l0_mode"], {"compact", "domains", "minimal"})
        self.assertEqual(self.run_cli("validate").returncode, 0)

    def test_migrate_is_dry_run_first_and_preserves_sources(self):
        source = Path(self.temporary.name) / "source-docs"
        source.mkdir()
        first = source / "guide.md"
        second = source / "nested" / "details.md"
        second.parent.mkdir()
        first.write_text(
            "# Guide\n\nThis paragraph contains a unique-migration-probe.\n",
            encoding="utf-8",
        )
        second.write_text("# Details\n\n第二篇说明。\n", encoding="utf-8")
        before = {path: sha256(path) for path in (first, second)}

        dry_run = self.run_cli("migrate", "--source", str(source))
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertIn("DRY-RUN", dry_run.stdout)
        self.assertFalse((self.root / "docs").exists())

        applied = self.run_cli(
            "migrate", "--source", str(source), "--apply")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(before, {path: sha256(path) for path in (first, second)})
        migrated = list((self.root / "docs" / "shards" / "imported").rglob("*.md"))
        self.assertEqual(len(migrated), 2)
        self.assertIn("source_sha256:", migrated[0].read_text(encoding="utf-8"))
        search = self.run_cli("search", "unique-migration-probe")
        self.assertEqual(search.returncode, 0, search.stderr)
        self.assertIn("guide.md", search.stdout)
        self.assertEqual(self.run_cli("validate").returncode, 0)

    def test_migration_destination_collision_blocks_all_writes(self):
        source = Path(self.temporary.name) / "collision-source"
        source.mkdir()
        (source / "a+b.md").write_text("# One\n", encoding="utf-8")
        (source / "a b.md").write_text("# Two\n", encoding="utf-8")
        completed = self.run_cli(
            "migrate", "--source", str(source), "--apply")
        self.assertEqual(completed.returncode, 1)
        self.assertIn("落到同一目标", completed.stderr)
        self.assertFalse((self.root / "docs").exists())

    def test_bundled_cli_matches_development_cli(self):
        self.assertTrue(BUNDLED_CLI.is_file())
        self.assertEqual(CLI.read_bytes(), BUNDLED_CLI.read_bytes())

    def test_project_installer_is_dry_run_and_idempotent(self):
        dry_run = subprocess.run(
            [sys.executable, str(INSTALLER), "--root", str(self.root),
             "--with-agents-snippet"],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertFalse((self.root / "doc_memory.py").exists())

        apply = subprocess.run(
            [sys.executable, str(INSTALLER), "--root", str(self.root),
             "--apply", "--with-agents-snippet", "--init"],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(apply.returncode, 0, apply.stderr)
        agents = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(agents.count("<!-- doc-memory:start -->"), 1)
        self.assertTrue((self.root / "docs" / "shards" / "_TEMPLATE.md").is_file())

        again = subprocess.run(
            [sys.executable, str(INSTALLER), "--root", str(self.root),
             "--apply", "--with-agents-snippet"],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(again.returncode, 0, again.stderr)
        agents_again = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(agents, agents_again)

    def test_skill_installer_is_dry_run_idempotent_and_backed_up(self):
        skills_root = Path(self.temporary.name) / "skills"
        dry_run = subprocess.run(
            [sys.executable, str(SKILL_INSTALLER),
             "--skills-root", str(skills_root)],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        target = skills_root / "doc-memory"
        self.assertFalse(target.exists())

        applied = subprocess.run(
            [sys.executable, str(SKILL_INSTALLER),
             "--skills-root", str(skills_root), "--apply"],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertTrue((target / "SKILL.md").is_file())

        unchanged = subprocess.run(
            [sys.executable, str(SKILL_INSTALLER),
             "--skills-root", str(skills_root), "--apply"],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(unchanged.returncode, 0, unchanged.stderr)
        self.assertIn("无需写入", unchanged.stdout)

        readme = target / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\nlocal change\n",
            encoding="utf-8",
        )
        blocked = subprocess.run(
            [sys.executable, str(SKILL_INSTALLER),
             "--skills-root", str(skills_root), "--apply"],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(blocked.returncode, 1)
        upgraded = subprocess.run(
            [sys.executable, str(SKILL_INSTALLER),
             "--skills-root", str(skills_root), "--apply", "--force"],
            encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
        backups = list(skills_root.glob("doc-memory.backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertIn("local change", (backups[0] / "README.md").read_text(
            encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
