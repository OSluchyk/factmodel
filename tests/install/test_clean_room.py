"""Clean-room install (WP4.1): the built wheel alone, in a fresh virtual environment outside the
repository, runs the whole Chinook loop. Nothing is imported from the source tree: the commands
run from a folder outside it, with no PYTHONPATH, and the test checks where `factmodel` and
its shipped files resolve from."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DAY = "2026-10-27"
pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed")


def _run(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    done = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    assert done.returncode == 0, f"{' '.join(args)}\n{done.stdout}\n{done.stderr}"
    return done


def test_wheel_runs_the_chinook_loop_without_the_source_tree(tmp_path: Path) -> None:
    base_env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("PYTHONPATH", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONHOME")
    }
    dist = tmp_path / "dist"
    _run(["uv", "build", "--wheel", "--out-dir", str(dist)], ROOT, base_env)
    (wheel,) = dist.glob("factmodel-*.whl")
    venv = tmp_path / "venv"
    _run(["uv", "venv", str(venv), "--python", "3.12", "--quiet"], tmp_path, base_env)
    python = venv / "bin" / "python"
    _run(
        ["uv", "pip", "install", "--python", str(python), "--quiet", f"{wheel}[sql]"],
        tmp_path,
        base_env,
    )
    env = {
        **base_env,
        "PATH": f"{venv / 'bin'}{os.pathsep}{base_env.get('PATH', '')}",
        "VIRTUAL_ENV": str(venv),
    }
    work = tmp_path / "work"
    model = work / "chinook"
    shutil.copytree(ROOT / "examples" / "chinook", model, ignore=shutil.ignore_patterns("out"))

    where = _run(
        [
            str(python),
            "-c",
            "import json, sys, importlib.resources as ir, factmodel, factmodel.resources as r;"
            "print(json.dumps({'module': factmodel.__file__, 'path': sys.path,"
            " 'vocabulary': ir.files('factmodel').joinpath('VOCABULARY.md').is_file(),"
            " 'profile': str(r.framework_file('profiles'))}))",
        ],
        work,
        env,
    )
    found = json.loads(where.stdout)
    assert str(venv) in found["module"] and str(ROOT) not in found["module"]
    assert str(venv) in found["profile"] and found["vocabulary"] is True
    assert not any(p.startswith(str(ROOT)) for p in found["path"])

    fact = str(venv / "bin" / "fact")
    log = [_run([fact, "--version"], work, env).stdout.strip()]
    for args in (
        ["check", "--root", "chinook"],
        ["project", "--root", "chinook"],
        ["probe", "generate", "--root", "chinook"],
    ):
        log.append(_run([fact, *args], work, env).stdout.strip().splitlines()[-1])
    url = _run(
        [str(python), "chinook/seed/seed.py", "sqlite", str(work / "chinook.db")], work, env
    ).stdout.strip()
    eq_env = {**env, "FACT_DSN_CHINOOK_SQLITE": url}
    eq = _run(
        [
            fact,
            "equivalence",
            "run",
            "--root",
            "chinook",
            "--layer",
            "customer-purchases",
            "--date",
            DAY,
        ],
        work,
        eq_env,
    )
    log.append(eq.stdout.strip())
    out = work / "release"
    log.append(
        _run(
            [
                fact,
                "release",
                "--root",
                "chinook",
                "--out",
                str(out),
                "--version",
                "0.1.0",
                "--date",
                DAY,
            ],
            work,
            env,
        ).stdout.strip()
    )
    log.append(_run([fact, "check", "--release", str(out)], work, env).stdout.strip())
    log.append(
        _run(
            [
                fact,
                "export",
                "--root",
                "chinook",
                "--target",
                "dbt",
                "--layer",
                "customer-purchases",
                "--out",
                str(work / "dbt"),
            ],
            work,
            env,
        ).stdout.strip()
    )
    text = "\n".join(log)
    assert log[0].startswith("fact 0.1.0 (schemas ")
    assert "gate: pass" in log[1]
    assert "customer-purchases: 31 pass, 0 fail, 0 error of 31" in text
    assert "proven" in text and "release 0.1.0:" in text
    assert text.count("gate: pass") >= 2
    assert (work / "dbt" / "customer-purchases.yml").is_file()
    print(text)  # the clean-room log the round report quotes (pytest -s)
