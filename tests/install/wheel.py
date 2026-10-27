"""The built wheel installed alone in a fresh virtual environment outside the repository
(WP4.1), shared by the clean-room test and the tutorial test so the wheel is built once."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
needs_uv = pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed")


@dataclass(frozen=True)
class Installed:
    venv: Path
    env: dict[str, str]  # PATH starts with the venv; no PYTHONPATH, no project environment

    @property
    def python(self) -> Path:
        return self.venv / "bin" / "python"

    @property
    def fact(self) -> str:
        return str(self.venv / "bin" / "fact")


def run(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    done = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    assert done.returncode == 0, f"{' '.join(args)}\n{done.stdout}\n{done.stderr}"
    return done


def install(folder: Path) -> Installed:
    base_env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("PYTHONPATH", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONHOME")
        and not k.startswith("FACT_")
    }
    dist = folder / "dist"
    run(["uv", "build", "--wheel", "--out-dir", str(dist)], ROOT, base_env)
    (wheel,) = dist.glob("factmodel-*.whl")
    venv = folder / "venv"
    run(["uv", "venv", str(venv), "--python", "3.12", "--quiet"], folder, base_env)
    python = venv / "bin" / "python"
    pip = ["uv", "pip", "install", "--python", str(python), "--quiet"]
    run([*pip, f"{wheel}[sql]"], folder, base_env)
    env = {
        **base_env,
        "PATH": f"{venv / 'bin'}{os.pathsep}{base_env.get('PATH', '')}",
        "VIRTUAL_ENV": str(venv),
    }
    return Installed(venv, env)
