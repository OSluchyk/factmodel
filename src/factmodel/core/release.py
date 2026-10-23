"""Release partition (spec/ALGORITHMS.md, algorithm 3). Pure; the release command is WP3.4."""

from collections.abc import Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase

from factmodel.model.types import ReleaseAllowlist


@dataclass(frozen=True)
class ReleaseInput:
    path: str
    kind: str | None
    keys: tuple[str, ...]


@dataclass(frozen=True, order=True)
class Disposition:
    path: str
    disposition: str
    keep: tuple[str, ...] = ()


@dataclass(frozen=True, order=True)
class Failure:
    path: str
    reason: str
    key: str | None = None


@dataclass(frozen=True)
class ReleasePlan:
    files: tuple[Disposition, ...]
    failures: tuple[Failure, ...]


def glob_match(pattern: str, path: str) -> bool:
    """``*`` matches inside one path segment; ``**`` matches any number of segments."""

    def walk(pat: list[str], parts: list[str]) -> bool:
        if not pat:
            return not parts
        if pat[0] == "**":
            return any(walk(pat[1:], parts[i:]) for i in range(len(parts) + 1))
        return bool(parts) and fnmatchcase(parts[0], pat[0]) and walk(pat[1:], parts[1:])

    return walk(pattern.split("/"), path.split("/"))


def partition(allowlist: ReleaseAllowlist, files: Sequence[ReleaseInput]) -> ReleasePlan:
    dispositions: list[Disposition] = []
    failures: list[Failure] = []
    keys = allowlist.keys or {}
    for item in sorted(files, key=lambda f: f.path):
        rule = next((r for r in allowlist.files if glob_match(r.pattern, item.path)), None)
        if rule is None:
            failures.append(Failure(item.path, "unmatched"))
            continue
        if rule.disposition != "project":
            dispositions.append(Disposition(item.path, rule.disposition))
            continue
        key_list = keys.get(item.kind) if item.kind else None
        if key_list is None:
            failures.append(Failure(item.path, "no_key_list"))
            continue
        declared = {*key_list.keep, *(key_list.drop or ())}
        undeclared = [key for key in item.keys if key not in declared]
        if undeclared:
            failures.extend(Failure(item.path, "undeclared_key", key) for key in undeclared)
            continue
        kept = tuple(key for key in item.keys if key in key_list.keep)
        dispositions.append(Disposition(item.path, "project", kept))
    return ReleasePlan(tuple(dispositions), tuple(failures))
