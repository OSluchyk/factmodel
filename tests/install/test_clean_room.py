"""Clean-room install (WP4.1): the built wheel alone, in a fresh virtual environment outside the
repository, runs the whole Chinook loop. Nothing is imported from the source tree: the commands
run from a folder outside it, with no PYTHONPATH, and the test checks where `factmodel` and
its shipped files resolve from."""

import json
import shutil
from pathlib import Path

from tests.install.wheel import ROOT, Installed, needs_uv, run

DAY = "2026-10-27"
pytestmark = needs_uv


def test_wheel_runs_the_chinook_loop_without_the_source_tree(
    installed: Installed, tmp_path: Path
) -> None:
    venv, env, python = installed.venv, installed.env, installed.python
    work = tmp_path / "work"
    model = work / "chinook"
    shutil.copytree(ROOT / "examples" / "chinook", model, ignore=shutil.ignore_patterns("out"))

    where = run(
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

    fact = installed.fact
    log = [run([fact, "--version"], work, env).stdout.strip()]
    for args in (
        ["check", "--root", "chinook"],
        ["project", "--root", "chinook"],
        ["probe", "generate", "--root", "chinook"],
    ):
        log.append(run([fact, *args], work, env).stdout.strip().splitlines()[-1])
    url = run(
        [str(python), "chinook/seed/seed.py", "sqlite", str(work / "chinook.db")], work, env
    ).stdout.strip()
    eq_env = {**env, "FACT_DSN_CHINOOK_SQLITE": url}
    eq = run(
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
        run(
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
    log.append(run([fact, "check", "--release", str(out)], work, env).stdout.strip())
    log.append(
        run(
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
