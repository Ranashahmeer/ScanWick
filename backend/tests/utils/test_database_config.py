import os
import subprocess
import sys
from pathlib import Path

from app.config import Settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_dev_mode_defaults_to_false_without_env(monkeypatch):
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.delenv("dev_mode", raising=False)

    settings = Settings(_env_file=None)

    assert settings.dev_mode is False


def test_database_import_fails_without_database_url_outside_dev(tmp_path):
    env = _isolated_env()

    result = subprocess.run(
        [sys.executable, "-c", "import app.database"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "DATABASE_URL is not set" in result.stderr
    assert "local SQLite database in production" in result.stderr


def test_database_import_uses_database_url_with_sql_echo_disabled_in_prod(tmp_path):
    env = _isolated_env()
    env["DATABASE_URL"] = "postgresql://user:pass@db.example.com:5432/scanwick"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.database; "
            "print(app.database.database_url); "
            "print(app.database.engine.echo)",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "postgresql+psycopg://user:pass@db.example.com:5432/scanwick" in result.stdout
    assert result.stdout.rstrip().endswith("False")


def _isolated_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("DEV_MODE", "dev_mode", "DATABASE_URL", "database_url"):
        env.pop(key, None)
    env["PYTHONPATH"] = str(BACKEND_ROOT)
    return env
