#!/usr/bin/env python3
"""Sync or verify the third-party skills declared in upstreams.json."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "upstreams.json"
README = ROOT / "README.md"
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
REQUIRED = {
    "name",
    "repository",
    "ref",
    "source",
    "destination",
    "license",
    "license_name",
    "commit",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def safe_relative(value: str, field: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        fail(f"Invalid {field}: {value!r}")
    return path


def load_sources() -> list[dict[str, str]]:
    try:
        sources = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Cannot read {CONFIG.name}: {error}")
    if not isinstance(sources, list):
        fail(f"{CONFIG.name} must contain a JSON array")

    names: set[str] = set()
    destinations: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != REQUIRED:
            fail(f"Each upstream must contain exactly: {', '.join(sorted(REQUIRED))}")
        if any(not isinstance(source[key], str) for key in REQUIRED):
            fail("Every upstream value must be a string")
        name = source["name"]
        if not NAME_RE.fullmatch(name):
            fail(f"Invalid skill name: {name!r}")
        destination = safe_relative(source["destination"], "destination")
        safe_relative(source["source"], "source")
        safe_relative(source["license"], "license")
        if destination.parts[0] != "skills" or destination.name != name:
            fail(f"Destination must be skills/{name}")
        if not source["repository"].startswith("https://github.com/"):
            fail(f"Only HTTPS GitHub repositories are supported: {source['repository']!r}")
        if name in names or source["destination"] in destinations:
            fail(f"Duplicate upstream name or destination: {name}")
        names.add(name)
        destinations.add(source["destination"])
    return sources


def run(*command: str, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        details = getattr(error, "stderr", "").strip()
        fail(f"Command failed: {' '.join(command)}{': ' + details if details else ''}")
    return result.stdout.strip()


def reject_symlinks(path: Path) -> None:
    for item in (path, *path.rglob("*")):
        if item.is_symlink():
            fail(f"Upstream symlinks are not allowed: {item}")


def frontmatter_name(skill_file: Path) -> str:
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        fail(f"Missing YAML frontmatter: {skill_file}")
    frontmatter = text[4:].split("\n---\n", 1)[0]
    name = re.search(r"(?m)^name:\s*['\"]?([^'\"\n]+)['\"]?\s*$", frontmatter)
    description = re.search(r"(?m)^description:\s*(\S.*)$", frontmatter)
    if not name or not description:
        fail(f"Frontmatter must contain name and description: {skill_file}")
    return name.group(1).strip()


def checkout(repository: str, target: str, directory: Path) -> str:
    run("git", "init", "--quiet", str(directory))
    run("git", "remote", "add", "origin", repository, cwd=directory)
    run("git", "fetch", "--quiet", "--depth", "1", "origin", target, cwd=directory)
    run("git", "checkout", "--quiet", "--detach", "FETCH_HEAD", cwd=directory)
    return run("git", "rev-parse", "HEAD", cwd=directory)


def catalog(sources: list[dict[str, str]]) -> str:
    rows = [
        "<!-- upstreams:start -->",
        "| Skill | 来源 / Source | 固定提交 / Pinned commit | License |",
        "| --- | --- | --- | --- |",
    ]
    for source in sources:
        repository = source["repository"].removesuffix(".git")
        source_url = f"{repository}/tree/{source['ref']}/{source['source']}"
        commit = source["commit"]
        rows.append(
            f"| `{source['name']}` | [{repository.removeprefix('https://github.com/')}]({source_url}) "
            f"| [`{commit[:12]}`]({repository}/commit/{commit}) | {source['license_name']} |"
        )
    rows.append("<!-- upstreams:end -->")
    return "\n".join(rows)


def update_catalog(sources: list[dict[str, str]], check: bool) -> bool:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(r"<!-- upstreams:start -->.*?<!-- upstreams:end -->", re.DOTALL)
    if not pattern.search(text):
        fail(f"Missing upstream catalog markers in {README.name}")
    updated = pattern.sub(catalog(sources), text, count=1)
    if updated == text:
        return False
    if check:
        fail(f"Upstream catalog is stale in {README.name}")
    temporary = README.with_suffix(".md.tmp")
    temporary.write_text(updated, encoding="utf-8")
    os.replace(temporary, README)
    return True


def prepare(source: dict[str, str], target: str, temporary: Path) -> tuple[Path, str]:
    checkout_dir = temporary / "checkout"
    checkout_dir.mkdir()
    commit = checkout(source["repository"], target, checkout_dir)
    source_dir = checkout_dir.joinpath(*PurePosixPath(source["source"]).parts)
    license_file = checkout_dir.joinpath(*PurePosixPath(source["license"]).parts)
    if not source_dir.is_dir() or not (source_dir / "SKILL.md").is_file():
        fail(f"Missing upstream SKILL.md: {source['source']}")
    if not license_file.is_file():
        fail(f"Missing upstream license: {source['license']}")
    reject_symlinks(source_dir)
    reject_symlinks(license_file)
    if frontmatter_name(source_dir / "SKILL.md") != source["name"]:
        fail(f"Upstream name does not match {source['name']}")

    expected = temporary / "expected"
    shutil.copytree(source_dir, expected)
    return expected, commit


def snapshot(path: Path) -> dict[str, tuple[bytes, bool]]:
    if not path.is_dir() or path.is_symlink():
        return {}
    reject_symlinks(path)
    return {
        item.relative_to(path).as_posix(): (
            item.read_bytes(),
            bool(item.stat().st_mode & stat.S_IXUSR),
        )
        for item in path.rglob("*")
        if item.is_file()
    }


def replace_directory(expected: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    backup = destination.with_name(f".{destination.name}.backup")
    shutil.rmtree(staged)
    shutil.copytree(expected, staged)
    if backup.exists():
        fail(f"Refusing to overwrite stale backup: {backup}")
    try:
        if destination.exists():
            destination.rename(backup)
        staged.rename(destination)
    except BaseException:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    else:
        shutil.rmtree(backup, ignore_errors=True)
    finally:
        shutil.rmtree(staged, ignore_errors=True)


def validate_inventory() -> None:
    names: set[str] = set()
    skills_dir = ROOT / "skills"
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.exists() else []:
        name = frontmatter_name(skill_file)
        if name != skill_file.parent.name:
            fail(f"Folder and frontmatter name differ: {skill_file}")
        if name in names:
            fail(f"Duplicate skill name: {name}")
        names.add(name)


def write_config(sources: list[dict[str, str]]) -> None:
    content = json.dumps(sources, indent=2, ensure_ascii=False) + "\n"
    temporary = CONFIG.with_suffix(".json.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, CONFIG)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify pinned mirrors without modifying files")
    args = parser.parse_args()
    sources = load_sources()
    changed = False

    for source in sources:
        target = source["commit"] if args.check else source["ref"]
        if not target:
            fail(f"No pinned commit for {source['name']}; run the sync first")
        with tempfile.TemporaryDirectory(prefix="skills-sync-") as directory:
            expected, commit = prepare(source, target, Path(directory))
            destination = ROOT.joinpath(*PurePosixPath(source["destination"]).parts)
            if snapshot(expected) == snapshot(destination):
                print(f"- {source['name']}: `{source['commit'] or commit}` (unchanged)")
                continue
            if args.check:
                fail(f"Mirror differs from pinned commit for {source['name']}")
            old_commit = source["commit"] or "new"
            replace_directory(expected, destination)
            source["commit"] = commit
            changed = True
            print(f"- {source['name']}: `{old_commit}` -> `{commit}`")

    if changed:
        write_config(sources)
    update_catalog(sources, args.check)
    validate_inventory()


if __name__ == "__main__":
    main()
