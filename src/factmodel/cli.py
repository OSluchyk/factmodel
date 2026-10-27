"""The `fact` command line."""

import json
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from factmodel import __version__, migrate, repo, vocabulary
from factmodel import probes as probes_module
from factmodel import status as status_module
from factmodel import sync as sync_module
from factmodel.adapters import registry
from factmodel.adapters import sql as sql_adapter
from factmodel.adapters.base import AdapterError, dialect_for, today, warehouse_pin, with_date
from factmodel.adapters.export import ExportAdapter
from factmodel.adapters.git import GitAdapter
from factmodel.core import derived
from factmodel.core.drafts import to_facts
from factmodel.equivalence import harness
from factmodel.equivalence.corpus import CorpusError
from factmodel.gate.runner import BLOCKING_STAGES, run_gate
from factmodel.io.yaml_strict import load
from factmodel.model.loader import inspect_model
from factmodel.model.types import Probe, Snapshot, Source
from factmodel.probes import intake as probe_intake_module
from factmodel.probes import script as probe_script

app = typer.Typer(
    name="fact",
    help="Build, check and keep current an evidence-grounded model of a data platform.",
    no_args_is_help=True,
    add_completion=False,
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"fact {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print the version and exit.",
            callback=_print_version,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Build, check and keep current an evidence-grounded model of a data platform."""


RootOption = Annotated[
    Path,
    typer.Option("--root", help="The model repository.", file_okay=False, exists=True),
]


@app.command()
def project(root: RootOption = Path(".")) -> None:
    """Recompute derived values (labels, scope, residue) into generated/."""
    result = inspect_model(root)
    blocking = [issue for issue in result.issues if issue.stage in BLOCKING_STAGES]
    for issue in blocking:
        typer.echo(str(issue), err=True)
    if blocking:
        typer.echo(f"{len(blocking)} issue(s); run fact check for details", err=True)
        raise typer.Exit(1)
    model = result.model
    values = derived.derive_model(model)
    if values is None:
        typer.echo("no profile or model config; see factmodel.yaml", err=True)
        raise typer.Exit(1)
    files = derived.render(values)
    changed = derived.write(model.root, files)
    for path in changed:
        typer.echo(f"wrote {path.relative_to(model.root).as_posix()}")
    if not changed:
        typer.echo("generated/ is up to date")


@app.command()
def check(
    root: RootOption = Path("."),
    stage: Annotated[str | None, typer.Option("--stage", help="Run one stage only.")] = None,
) -> None:
    """Run the gate; exit 0 only when every stage passes."""
    try:
        report = run_gate(root, stage)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from error
    for line in report.lines():
        typer.echo(line)
    if not report.passed:
        raise typer.Exit(1)


@app.command()
def init(
    target: Annotated[Path, typer.Argument(help="Folder for the new model repository.")],
    profile: Annotated[str, typer.Option("--profile", help="Profile ID, for example retail.")],
    model_id: Annotated[str | None, typer.Option("--id", help="Model ID (a slug).")] = None,
    anchor: Annotated[
        str | None,
        typer.Option(
            "--anchor",
            help="Anchor entity ID; default: the profile's subject. Not allowed without one.",
        ),
    ] = None,
) -> None:
    """Create a model repository: config, layout, agent files, CI and generated/."""
    try:
        written = repo.init(target, profile, model_id, anchor)
    except repo.RepoError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(f"created {target} with {len(written)} files (profile {profile})")


source_app = typer.Typer(help="Manage the source registry.", no_args_is_help=True)
app.add_typer(source_app, name="source")


@source_app.command("add")
def source_add(
    source_id: Annotated[str, typer.Option("--id", help="Source ID (a slug).")],
    title: Annotated[str, typer.Option("--title")],
    source_kind: Annotated[str, typer.Option("--kind", help="git, warehouse, api, ...")],
    access_mode: Annotated[str, typer.Option("--access-mode")],
    engine: Annotated[str | None, typer.Option("--engine", help="Warehouse engine.")] = None,
    location: Annotated[str | None, typer.Option("--location")] = None,
    access: Annotated[str | None, typer.Option("--access", help="How access is obtained.")] = None,
    rank: Annotated[int | None, typer.Option("--rank")] = None,
    adapter: Annotated[
        str | None, typer.Option("--adapter", help="Adapter that reads it: export, sql, git, ...")
    ] = None,
    dialect: Annotated[
        str | None, typer.Option("--dialect", help="sqlglot dialect, if the engine has none.")
    ] = None,
    dsn_env: Annotated[
        str | None,
        typer.Option("--dsn-env", help="Environment variable that holds the connection string."),
    ] = None,
    revision: Annotated[str | None, typer.Option("--revision", help="Git revision.")] = None,
    include: Annotated[
        list[str] | None, typer.Option("--include", help="Git path glob; repeat for more.")
    ] = None,
    root: RootOption = Path("."),
) -> None:
    """Register a source: kind, access mode, adapter. Records how to get access, never a secret."""
    fields = {
        "id": source_id,
        "title": title,
        "source_kind": source_kind,
        "access_mode": access_mode,
        "rank": rank,
        "adapter": adapter,
        "engine": engine,
        "dialect": dialect,
        "location": location,
        "dsn_env": dsn_env,
        "revision": revision,
        "include": include or None,
        "access": access,
    }
    try:
        path = repo.add_source(root, fields)
    except repo.RepoError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(f"wrote {path.relative_to(root).as_posix()}")


@app.command("migrate")
def migrate_command(root: RootOption = Path(".")) -> None:
    """Report the model's framework version, the installed schema version, and compatibility."""
    result = migrate.report(root)
    for line in result.lines():
        typer.echo(line)
    if not result.compatible:
        raise typer.Exit(1)


@app.command("status")
def status_command(root: RootOption = Path(".")) -> None:
    """Open findings, open escalations, fired triggers, stale evidence, next actions."""
    for line in status_module.status(root).lines():
        typer.echo(line)


@app.command("adapters")
def adapters_command() -> None:
    """List installed adapters, the engines they read and their default dialects."""
    installed = registry.adapters()
    defaults = vocabulary.text_map("engine_dialect")
    for name in sorted({*installed, *registry.BUILT_IN}):
        adapter = installed.get(name)
        if adapter is None:
            typer.echo(f"{name}  not installed")
            continue
        engines = adapter.engines()
        listed = sorted(defaults) if engines == ["*"] else engines
        dialects = ", ".join(f"{e}={adapter.default_dialect(e)}" for e in listed)
        typer.echo(f"{name}  engines: {', '.join(engines)}  default dialects: {dialects}")


def _source(root: Path, source_id: str) -> Source:
    try:
        return repo.source_of(root, source_id)
    except repo.RepoError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error


@app.command("export-sql")
def export_sql(
    source_id: Annotated[str, typer.Option("--source", help="Source ID.")],
    root: RootOption = Path("."),
) -> None:
    """Print the SQL the owner runs to export a source's metadata (agents read, people run)."""
    source = _source(root, source_id)
    typer.echo(ExportAdapter().export_sql(source))


@app.command("snapshot")
def snapshot_command(
    source_id: Annotated[str, typer.Option("--source", help="Source ID.")],
    from_export: Annotated[
        Path | None, typer.Option("--from-export", help="Folder with exported views.")
    ] = None,
    date: Annotated[str | None, typer.Option("--date", help="Date read, YYYY-MM-DD.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Read a source's metadata through its adapter into sources/snapshots/; set current_pin."""
    source = _source(root, source_id)
    try:
        if from_export is not None:
            snap = ExportAdapter().read(from_export, source)
        else:
            snap = registry.get(source.adapter).snapshot(source, root.resolve())
        if date is not None:
            snap = with_date(snap, date)
        path, changed = repo.write_snapshot(root, snap)
        if snap.pin is not None:
            repo.set_current_pin(root, source.id, snap.pin)
    except (AdapterError, repo.RepoError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    rel = path.relative_to(root).as_posix()
    typer.echo(f"{'wrote' if changed else 'unchanged'} {rel} ({len(snap.objects)} objects)")


@app.command("draft")
def draft_command(
    source_id: Annotated[str, typer.Option("--source", help="Source ID.")],
    snapshot: Annotated[
        Path | None, typer.Option("--snapshot", help="Snapshot file; default: the latest.")
    ] = None,
    root: RootOption = Path("."),
) -> None:
    """Turn a snapshot into entity drafts under drafts/ (never physical/)."""
    _source(root, source_id)
    try:
        path = snapshot or repo.latest_snapshot(root, source_id)
        snap = Snapshot.model_validate(load(path).data)
        drafts = to_facts(snap)
        changed = repo.write_drafts(root, drafts)
    except (ValueError, repo.RepoError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(f"{len(drafts)} drafts, {len(changed)} written")


@app.command("quote")
def quote_command(
    source_id: Annotated[str, typer.Option("--source", help="A git source ID.")],
    path: Annotated[str, typer.Option("--path", help="File path in the repository.")],
    line: Annotated[int, typer.Option("--line", min=1, help="First line to quote.")],
    lines: Annotated[int, typer.Option("--lines", min=1, help="Number of lines.")] = 1,
    root: RootOption = Path("."),
) -> None:
    """Print an evidence record that quotes a text file in a git source, pinned to its version."""
    source = _source(root, source_id)
    try:
        record = GitAdapter().quote(source, root.resolve(), path, line, lines)
    except AdapterError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(repo.dump_yaml({"id": "ev-<name>", **record}).rstrip())


@app.command("sync")
def sync_command(
    source_id: Annotated[str, typer.Option("--source", help="Source ID.")],
    root: RootOption = Path("."),
) -> None:
    """Compare the latest snapshot with the previous one and the model; draft, open, fire."""
    _source(root, source_id)
    try:
        result = sync_module.sync(root.resolve(), source_id)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    counts: dict[str, int] = {}
    for item in result.items:
        counts[item.drift_class] = counts.get(item.drift_class, 0) + 1
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "no drift"
    typer.echo(f"{summary}; {len(result.written)} files written")
    for path in result.written:
        typer.echo(f"  {path.relative_to(root.resolve()).as_posix()}")


probe_app = typer.Typer(help="Generate, render, run and take in data probes.", no_args_is_help=True)
app.add_typer(probe_app, name="probe")


def _dialects(model: Any) -> dict[str, str]:
    out = {}
    for source in model.sources.values():
        try:
            out[source.id] = dialect_for(source.engine, source.dialect)
        except AdapterError:
            continue
    return out


@probe_app.command("generate")
def probe_generate(
    source_id: Annotated[str | None, typer.Option("--source", help="Only this source.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Write probes/<probe-id>.yaml for every fact data can confirm."""
    model = inspect_model(root).model
    entities = {
        k: e for k, e in model.entities.items() if source_id is None or e.source == source_id
    }
    layers = {
        k: layer
        for k, layer in model.layers.items()
        if source_id is None or any(entities.get(e.entity) for e in layer.entities)
    }
    docs, skipped = probes_module.generate(entities, model.sources, _dialects(model), layers=layers)
    changed = 0
    for doc in docs:
        changed += repo.write_text_if_changed(
            root / "probes" / f"{doc['id']}.yaml",
            probes_module.GENERATED_HEADER + "\n" + repo.dump_yaml(doc),
        )
    typer.echo(f"{len(docs)} probes, {changed} written, {len(skipped)} facts skipped")
    for item in skipped:
        typer.echo(f"  skipped {item.fact}: {item.reason}")


def _probes_by_source(model: Any, source_id: str | None) -> dict[str, list[Probe]]:
    grouped: dict[str, list[Probe]] = {}
    for probe in model.probes.values():
        entity = model.entities.get(probe.entity or "")
        owner = entity.source if entity is not None else None
        if owner and (source_id is None or owner == source_id):
            grouped.setdefault(owner, []).append(probe)
    return grouped


@probe_app.command("render")
def probe_render(
    dialect: Annotated[str, typer.Option("--dialect", help="sqlglot dialect, e.g. postgres.")],
    source_id: Annotated[str | None, typer.Option("--source", help="Only this source.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Write probes/scripts/<source>.<dialect>.sh, plain shell the owner reads, then runs."""
    model = inspect_model(root).model
    for owner, probes in sorted(_probes_by_source(model, source_id).items()):
        text, skipped = probe_script.script(owner, dialect, probes)
        path = root / "probes" / "scripts" / f"{owner}.{dialect}.sh"
        repo.write_text_if_changed(path, text)
        path.chmod(0o755)
        note = f", {len(skipped)} not rendered" if skipped else ""
        typer.echo(f"{path.relative_to(root).as_posix()}: {len(probes)} probes{note}")


@probe_app.command("run")
def probe_run(
    source_id: Annotated[str, typer.Option("--source", help="A source with a dsn_env.")],
    environment: Annotated[str, typer.Option("--environment")] = "prod",
    data_quality: Annotated[str, typer.Option("--data-quality")] = "unknown",
    date: Annotated[str | None, typer.Option("--date", help="YYYY-MM-DD.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Run a source's probes through the sql adapter (counts only); write probes/results/."""
    source = _source(root, source_id)
    model = inspect_model(root).model
    try:
        url = sql_adapter.dsn(source)
        dialect = dialect_for(source.engine, source.dialect)
    except AdapterError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    probes = sorted(_probes_by_source(model, source_id).get(source_id, []), key=lambda p: p.id)
    queries = [(p.id, sql) for p in probes if (sql := probes_module.render(p, dialect))]
    day = date or today()
    header = {
        "source": source.id,
        "pin": warehouse_pin(source.engine or dialect, sql_adapter.target_of(source, url), day),
        "environment": environment,
        "data_quality": data_quality,
        "ran_on": day,
    }
    rows = [header, *sql_adapter.measure(url, queries)]
    path = root / "probes" / "results" / f"{source.id}@{day}.jsonl"
    repo.write_text_if_changed(path, "".join(json.dumps(r, sort_keys=False) + "\n" for r in rows))
    failed = sum(1 for r in rows[1:] if "error" in r)
    typer.echo(f"{len(queries)} probes run, {failed} failed: {path.relative_to(root).as_posix()}")


@probe_app.command("intake")
def probe_intake(
    results: Annotated[Path, typer.Argument(help="A results file (JSON lines).")],
    root: RootOption = Path("."),
) -> None:
    """Turn probe results into evidence; cite in-range results, open findings for the rest."""
    try:
        out = probe_intake_module.intake(root.resolve(), results)
    except probe_intake_module.IntakeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(
        f"{len(out.confirmed)} in range, {len(out.out_of_range)} out of range, "
        f"{len(out.failed)} failed, {len(out.rejected)} rejected; {len(out.written)} files written"
    )
    for reason in out.rejected:
        typer.echo(f"  rejected {reason}")


equivalence_app = typer.Typer(
    help="Prove a layer: run its consumer on the corpus and compare with the references.",
    no_args_is_help=True,
)
app.add_typer(equivalence_app, name="equivalence")
LayerOption = Annotated[str, typer.Option("--layer", help="Layer ID.")]


def _layer_source(model: Any, layer_id: str, source_id: str | None) -> Source:
    if source_id is not None:
        source = model.sources.get(source_id)
    else:
        layer = model.layers.get(layer_id)
        entity = model.entities.get(layer.entities[0].entity) if layer else None
        source = model.sources.get(entity.source) if entity is not None else None
    if source is None:
        typer.echo("no source to run on; pass --source", err=True)
        raise typer.Exit(1)
    return cast(Source, source)


@equivalence_app.command("run")
def equivalence_run(
    layer_id: LayerOption,
    corpus: Annotated[Path | None, typer.Option("--corpus", help="Another corpus folder.")] = None,
    source_id: Annotated[
        str | None, typer.Option("--source", help="Source to run on; default: the layer's.")
    ] = None,
    results: Annotated[
        Path | None, typer.Option("--results", help="Output of fact equivalence script.")
    ] = None,
    date: Annotated[str | None, typer.Option("--date", help="YYYY-MM-DD.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Compile every corpus item, compare it with its reference, write the report and last run."""
    model = inspect_model(root).model
    source = _layer_source(model, layer_id, source_id)
    day = date or today()
    try:
        dialect = dialect_for(source.engine, source.dialect)
        if results is not None:
            result = harness.from_results(
                root.resolve(),
                model,
                layer_id,
                results,
                source=source.id,
                dialect=dialect,
                ran_on=day,
            )
        else:
            result = harness.run(
                root.resolve(),
                model,
                layer_id,
                url=sql_adapter.dsn(source),
                source=source.id,
                dialect=dialect,
                ran_on=day,
                corpus=corpus,
            )
    except (AdapterError, harness.EquivalenceError, CorpusError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    harness.write(root.resolve(), result)
    total = result.counts()["all"]
    typer.echo(
        f"{layer_id}: {total['pass']} pass, {total['fail']} fail, {total['error']} error "
        f"of {len(result.items)}"
    )
    if result.regressions:
        typer.echo(f"regressions against the accepted run: {', '.join(result.regressions)}")
        raise typer.Exit(1)


@equivalence_app.command("accept")
def equivalence_accept(layer_id: LayerOption, root: RootOption = Path(".")) -> None:
    """Accept the layer's last run (the owner's act): copy it into equivalence/accepted.json."""
    try:
        changed = harness.accept(root.resolve(), layer_id)
    except harness.EquivalenceError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(f"{layer_id}: {'accepted' if changed else 'already accepted'}")


@equivalence_app.command("script")
def equivalence_script(
    layer_id: LayerOption,
    dialect: Annotated[str, typer.Option("--dialect", help="sqlglot dialect, e.g. postgres.")],
    root: RootOption = Path("."),
) -> None:
    """Write equivalence/scripts/<layer>.<dialect>.sh for an owner-run live comparison."""
    model = inspect_model(root).model
    try:
        text = harness.script(root.resolve(), model, layer_id, dialect)
    except (harness.EquivalenceError, CorpusError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    path = root / "equivalence" / "scripts" / f"{layer_id}.{dialect}.sh"
    repo.write_text_if_changed(path, text)
    path.chmod(0o755)
    typer.echo(path.relative_to(root).as_posix())
