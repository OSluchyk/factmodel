"""Gate stage `generated-fresh`: generated/ differs from a fresh `fact project`."""

from factmodel.gate.runner import GateContext
from factmodel.model.loader import LoadIssue

STAGE = "generated-fresh"
HINT = "run fact project and commit generated/"


def run(ctx: GateContext) -> list[LoadIssue] | None:
    if ctx.generated is None:
        return None
    folder = ctx.root / "generated"
    issues = []
    for name, text in sorted(ctx.generated.items()):
        path = folder / name
        if not path.is_file():
            message = f"generated/{name} is missing"
        elif path.read_text(encoding="utf-8") != text:
            message = f"generated/{name} differs from a fresh fact project"
        else:
            continue
        issues.append(ctx.issue(STAGE, "stale", f"generated/{name}", [], message, HINT))
    if folder.is_dir():
        for path in sorted(folder.glob("*.tsv")):
            if path.name not in ctx.generated:
                message = f"generated/{path.name} is not produced by fact project"
                hint = "delete the file; generated/ holds only fact project output"
                issues.append(
                    ctx.issue(STAGE, "unexpected", f"generated/{path.name}", [], message, hint)
                )
    return issues
