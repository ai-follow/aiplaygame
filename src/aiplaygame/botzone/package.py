from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

PACKAGE_SUBDIRS = {"agents", "botzone", "core"}
EXCLUDED_RELATIVE_FILES = {
    Path("botzone/package.py"),
    Path("core/engine.py"),
    Path("core/evaluation.py"),
}
FORBIDDEN_ARCHIVE_PARTS = {
    ".env",
    ".venv",
    "dist",
    "docs",
    "frontend",
    "models",
    "node_modules",
    "output",
    "replays",
    "screenshots",
    "tests",
}

MAIN_PY = """\
from __future__ import annotations

import json
import sys

from aiplaygame.botzone.adapter import BotzoneAdapter


def main() -> None:
    payload = json.load(sys.stdin)
    adapter = BotzoneAdapter()
    action = adapter.decide_payload(payload)
    print(json.dumps(adapter.format_response(action), ensure_ascii=False))


if __name__ == "__main__":
    main()
"""


def build_botzone_package(
    out_path: Path,
    project_root: Path | None = None,
) -> dict[str, Any]:
    root = (project_root or _default_project_root()).resolve()
    package_root = root / "src" / "aiplaygame"
    if not package_root.exists():
        raise FileNotFoundError(f"Cannot find package source: {package_root}")

    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    archive_names: list[str] = []
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _write_text(archive, "main.py", MAIN_PY, archive_names)
        _write_text(archive, "__main__.py", MAIN_PY, archive_names)
        _write_text(archive, "requirements.txt", "pydantic>=2.7.0\n", archive_names)

        for source in sorted(package_root.rglob("*.py")):
            relative = source.relative_to(package_root)
            if relative in EXCLUDED_RELATIVE_FILES:
                continue
            if relative.parts[0] != "__init__.py" and relative.parts[0] not in PACKAGE_SUBDIRS:
                continue
            archive_name = str(Path("aiplaygame") / relative)
            _assert_safe_archive_name(archive_name)
            archive.write(source, archive_name)
            archive_names.append(archive_name)

        manifest = {
            "name": "aiplaygame-botzone-agent",
            "entrypoint": "main.py",
            "source_dirs": sorted(PACKAGE_SUBDIRS),
            "files": sorted(archive_names),
            "notes": [
                "No livestream keys, frontend assets, local caches, or model weights are included.",
                "The package expects Botzone-compatible Python plus the listed requirements.",
            ],
        }
        _write_text(
            archive,
            "BOTZONE_PACKAGE.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            archive_names,
        )

    return {
        "out_path": str(out_path),
        "file_count": len(archive_names),
        "files": sorted(archive_names),
    }


def _write_text(
    archive: zipfile.ZipFile,
    archive_name: str,
    content: str,
    archive_names: list[str],
) -> None:
    _assert_safe_archive_name(archive_name)
    archive.writestr(archive_name, content)
    archive_names.append(archive_name)


def _assert_safe_archive_name(archive_name: str) -> None:
    parts = set(Path(archive_name).parts)
    forbidden = parts & FORBIDDEN_ARCHIVE_PARTS
    if forbidden:
        raise ValueError(f"Forbidden file in Botzone package: {archive_name}")
    if "stream" in archive_name.lower() or "secret" in archive_name.lower():
        raise ValueError(f"Potential secret-bearing file in Botzone package: {archive_name}")


def _default_project_root() -> Path:
    return Path(__file__).resolve().parents[3]
