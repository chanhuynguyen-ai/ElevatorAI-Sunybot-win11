from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "apps/web/src/App.jsx",
    ROOT / "services/vision/src/elevator_vision/api.py",
    ROOT / "services/agent/src/elevator_agent/app.py",
    ROOT / "services/gateway/src/elevator_gateway/app.py",
    ROOT / "infrastructure/postgres/init.sql",
    ROOT / "docker-compose.yml",
]
FORBIDDEN_DIRS = {"node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "elevator_env38"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".engine", ".so"}
FORBIDDEN_NAMES = {".env"}
MODEL_SUFFIXES = {".pt", ".onnx"}


def tracked_paths():
    if (ROOT / ".git").exists():
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
        )
        return [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]
    return [path.relative_to(ROOT) for path in ROOT.rglob("*") if path.is_file()]


def is_forbidden(path: Path) -> bool:
    if any(part in FORBIDDEN_DIRS for part in path.parts):
        return True
    if path.name in FORBIDDEN_NAMES:
        return True
    if path.suffix in FORBIDDEN_SUFFIXES or path.suffix in MODEL_SUFFIXES:
        return True
    return False


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.exists()]
    if missing:
        print("MISSING:", *missing, sep="\n- ")
        return 1

    bad = [path for path in tracked_paths() if is_forbidden(path)]
    if bad:
        print("Repository hygiene check failed; forbidden tracked paths:")
        for path in bad[:50]:
            print("-", path)
        return 2

    print("repository structure: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
