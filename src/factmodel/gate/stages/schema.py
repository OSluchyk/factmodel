"""Gate stage `schema`: issues the loader reports for this stage."""

from factmodel.gate.runner import GateContext
from factmodel.model.loader import LoadIssue


def run(ctx: GateContext) -> list[LoadIssue]:
    return ctx.result.stage("schema")
