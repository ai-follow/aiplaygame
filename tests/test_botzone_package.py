import json
import zipfile

from aiplaygame.botzone.package import build_botzone_package


def test_botzone_package_contains_only_submission_files(tmp_path):
    out_path = tmp_path / "botzone-agent.zip"
    result = build_botzone_package(out_path)
    assert result["file_count"] > 5

    with zipfile.ZipFile(out_path) as archive:
        names = set(archive.namelist())
        assert "main.py" in names
        assert "__main__.py" in names
        assert "BOTZONE_PACKAGE.json" in names
        assert "requirements.txt" in names
        assert "aiplaygame/botzone/adapter.py" in names
        assert "aiplaygame/core/rules.py" in names
        assert "aiplaygame/core/evaluation.py" not in names
        assert "aiplaygame/core/engine.py" not in names
        assert "aiplaygame/botzone/package.py" not in names
        assert not any(name.startswith("frontend/") for name in names)
        assert not any(".env" in name for name in names)
        manifest = json.loads(archive.read("BOTZONE_PACKAGE.json"))
        assert manifest["entrypoint"] == "main.py"
