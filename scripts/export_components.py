"""Synchronize Platform components to sibling component repositories.

Safety rules:
- `ElevatorAI-Platform` is the integration source of truth.
- Existing sibling `.git` directories are never removed.
- If a sibling Git working tree is dirty, the script refuses to overwrite it.

Usage:
    python scripts/export_components.py --apply
"""

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
MAPPING = {
    "services/vision": "ElevatorAI-Vision",
    "services/agent": "ElevatorAI-Agent",
    "apps/web": "ElevatorAI-Web",
}


def git_is_dirty(path: Path) -> bool:
    if not (path / ".git").exists():
        return False
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(path),
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def clear_worktree(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True)
        return
    for child in path.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def copy_contents(src: Path, dst: Path) -> None:
    clear_worktree(dst)
    for child in src.iterdir():
        target = dst / child.name
        if child.is_dir() and not child.is_symlink():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform the synchronization")
    args = parser.parse_args()

    for src_rel, dst_name in MAPPING.items():
        src = ROOT / src_rel
        dst = PARENT / dst_name
        print("{0} -> {1}".format(src.relative_to(ROOT), dst))
        if not args.apply:
            continue
        if git_is_dirty(dst):
            raise SystemExit("Refusing to overwrite dirty Git working tree: {0}".format(dst))
        copy_contents(src, dst)

    if not args.apply:
        print("Dry run only. Re-run with --apply to synchronize.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
