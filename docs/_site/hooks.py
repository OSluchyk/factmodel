"""MkDocs hook: assemble the documentation site from the repository before every build.

The site is generated, never written by hand: the spec, the decisions (the index in the
navigation, one page per record at `/decisions/D-NNN/`), `docs/`, one page per
skill (from `agent/skills/*/SKILL.md`), a CLI reference generated from the Typer app and a
schema reference generated from `schemas/*.schema.json`. A link to a repository file that is
not a page of the site becomes a link to the file on GitHub, so `mkdocs build --strict` checks
every link between pages.
"""

import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "docs" / "_site" / "pages"
GITHUB = "https://github.com/OSluchyk/factmodel/blob/main/"
LINK = re.compile(r"(\]\()([^)\s]+)(\))")

# One example per command; the build fails when a command has none.
EXAMPLES = {
    "adapters": "fact adapters",
    "check": "fact check --root examples/chinook",
    "draft": "fact draft --root model --source shop-db",
    "equivalence accept": "fact equivalence accept --root examples/qcew --layer employment-wages",
    "equivalence run": "fact equivalence run --root examples/qcew --layer employment-wages",
    "equivalence script": "fact equivalence script --root model --layer sales --dialect postgres",
    "export": "fact export --root examples/qcew --target dbt --layer employment-wages --out out",
    "export-sql": "fact export-sql --root model --source sales-bq",
    "init": "fact init model --profile statistics",
    "lookup": "fact lookup --root examples/qcew --layer employment-wages",
    "migrate": "fact migrate --root examples/chinook",
    "probe generate": "fact probe generate --root examples/qcew --set volatile",
    "probe intake": "fact probe intake --root model probes/results/shop-db@2026-10-27.jsonl",
    "probe render": "fact probe render --root model --dialect duckdb --source shop-db",
    "probe run": "fact probe run --root model --source shop-db --data-quality synthetic",
    "project": "fact project --root examples/chinook",
    "propose joins": (
        "fact propose joins --root model --source shop-db --environment local "
        "--data-quality synthetic"
    ),
    "propose keys": (
        "fact propose keys --root model --source shop-db --environment local "
        "--data-quality synthetic"
    ),
    "quote": "fact quote --root model --source ddl --path ddl/schema.sql --line 12",
    "release": "fact release --root examples/chinook --out release/out --version 0.1.0",
    "snapshot": "fact snapshot --root model --source shop-db",
    "source add": (
        "fact source add --root model --id shop-db --title Shop --kind warehouse "
        "--access-mode agent_read --engine sqlite --adapter sql --dsn-env FACT_DSN_SHOP"
    ),
    "status": "fact status --root examples/chinook",
    "sync": "fact sync --root model --source shop-db",
}


def _site_path(repo: str) -> str | None:
    """The page a repository Markdown file becomes, or None when it is not a page."""
    if repo == "README.md":
        return "index.md"
    if repo == "agent/skills/README.md":
        return "skills/index.md"
    match = re.fullmatch(r"agent/skills/([^/]+)/SKILL\.md", repo)
    if match:
        return f"skills/{match.group(1)}.md"
    match = re.fullmatch(r"decisions/(D-\d{3})-[^/]+\.md", repo)
    if match:
        return f"decisions/{match.group(1)}.md"  # one page per record, at /decisions/D-NNN/
    if repo.startswith(("spec/", "decisions/")) and repo.endswith(".md"):
        return repo
    if repo.startswith("docs/") and repo.endswith(".md") and not repo.startswith("docs/_site/"):
        return repo
    return None


def _rewrite(text: str, repo: str, site: str) -> str:
    def fix(match: re.Match[str]) -> str:
        target = match.group(2)
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            return match.group(0)
        path, _, anchor = target.partition("#")
        resolved = (Path(repo).parent / path).as_posix()
        parts: list[str] = []
        for part in resolved.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part not in ("", "."):
                parts.append(part)
        resolved = "/".join(parts)
        page = _site_path(resolved)
        suffix = f"#{anchor}" if anchor else ""
        if page is not None and (ROOT / resolved).is_file():
            return f"{match.group(1)}{_relative(site, page)}{suffix}{match.group(3)}"
        if (ROOT / resolved).exists():
            return f"{match.group(1)}{GITHUB}{resolved}{suffix}{match.group(3)}"
        return match.group(0)

    return LINK.sub(fix, text)


def _relative(site: str, page: str) -> str:
    here = Path(site).parent.parts
    there = Path(page).parts
    common = 0
    while common < min(len(here), len(there) - 1) and here[common] == there[common]:
        common += 1
    return "/".join([".."] * (len(here) - common) + list(there[common:]))


def _copy(repo: str) -> None:
    site = _site_path(repo)
    assert site is not None
    text = (ROOT / repo).read_text(encoding="utf-8")
    target = SITE / site
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_rewrite(text, repo, site), encoding="utf-8")


def cli_reference() -> str:
    import typer

    from factmodel.cli import app

    lines = [
        "# CLI reference",
        "",
        "Generated from the `fact` command line; every command, every option, one example.",
        "",
    ]
    seen: list[str] = []

    def walk(group: Any, prefix: list[str]) -> None:
        for name in sorted(group.commands):
            command = group.commands[name]
            path = [*prefix, name]
            if getattr(command, "commands", None):
                walk(command, path)
                continue
            key = " ".join(path)
            seen.append(key)
            if key not in EXAMPLES:
                raise ValueError(f"the CLI reference has no example for `fact {key}`")
            lines.extend([f"## fact {key}", "", (command.help or "").strip(), ""])
            params = command.params
            options = [p for p in params if p.param_type_name == "option" and p.name != "help"]
            arguments = [p for p in params if p.param_type_name == "argument"]
            if arguments or options:
                lines.extend(["| Parameter | Default | Help |", "| --- | --- | --- |"])
                for arg in arguments:
                    lines.append(f"| `{arg.name.upper()}` (argument) | required | |")
                for opt in options:
                    flags = ", ".join(f"`{o}`" for o in opt.opts)
                    default = (
                        "required"
                        if opt.required
                        else (f"`{opt.default}`" if opt.default not in (None, False) else "-")
                    )
                    help_text = (opt.help or "").replace("|", "\\|")
                    lines.append(f"| {flags} | {default} | {help_text} |")
                lines.append("")
            lines.extend(["Example:", "", "```bash", EXAMPLES[key], "```", ""])

    walk(typer.main.get_command(app), [])
    extra = sorted(set(EXAMPLES) - set(seen))
    if extra:
        raise ValueError(f"examples for commands that do not exist: {extra}")
    return "\n".join(lines)


def _type(spec: dict[str, Any]) -> str:
    if "$ref" in spec:
        return spec["$ref"].rsplit("/", 1)[-1]
    if "enum" in spec:
        values = spec["enum"]
        shown = ", ".join(f"`{v}`" for v in values[:8])
        return f"one of {shown}" + (", ..." if len(values) > 8 else "")
    if "const" in spec:
        return f"`{spec['const']}`"
    if "oneOf" in spec:
        return " or ".join(_type(s) for s in spec["oneOf"])
    kind = spec.get("type", "")
    if kind == "array" and isinstance(spec.get("items"), dict):
        return f"list of {_type(spec['items'])}"
    return str(kind) if kind else "object"


def schema_pages() -> dict[str, str]:
    pages = {}
    index = [
        "# Schema reference",
        "",
        "Generated from `schemas/*.schema.json`: one page per file kind.",
        "",
    ]
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        kind = path.name.removesuffix(".schema.json")
        required = set(schema.get("required", []))
        lines = [
            f"# {schema.get('title', kind)} (`{kind}`)",
            "",
            schema.get("description", ""),
            "",
            f"Schema id: `{schema.get('$id', '')}`",
            "",
            "| Key | Type | Required | Description |",
            "| --- | --- | --- | --- |",
        ]
        for key, spec in schema.get("properties", {}).items():
            spec = spec if isinstance(spec, dict) else {}
            description = str(spec.get("description", "")).replace("\n", " ").replace("|", "\\|")
            lines.append(
                f"| `{key}` | {_type(spec)} | {'yes' if key in required else ''} | {description} |"
            )
        pages[f"reference/schemas/{kind}.md"] = "\n".join(lines) + "\n"
        index.append(f"- [{schema.get('title', kind)}]({kind}.md)")
    pages["reference/schemas/index.md"] = "\n".join(index) + "\n"
    return pages


def assemble() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    (SITE / ".gitkeep").write_text("", encoding="utf-8")
    sources = ["README.md", "agent/skills/README.md"]
    sources += [
        p.relative_to(ROOT).as_posix()
        for p in sorted((ROOT / "agent" / "skills").glob("*/SKILL.md"))
    ]
    for folder in ("spec", "decisions", "docs"):
        sources += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / folder).rglob("*.md"))]
    for repo in sources:
        if _site_path(repo) is not None:
            _copy(repo)
    (SITE / "reference").mkdir(exist_ok=True)
    (SITE / "reference" / "cli.md").write_text(cli_reference(), encoding="utf-8")
    for name, text in schema_pages().items():
        target = SITE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def on_pre_build(config: Any) -> None:
    assemble()
