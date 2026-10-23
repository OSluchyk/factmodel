# Plumbline

Plumbline is a framework that lets AI agents build, check and keep current a semantic model of any data platform. Every fact in a model carries its evidence - a source, a pin and a status - and every derived value is computed by code, never typed by hand. One physical layer describes what exists; semantic layers on top serve one use case each and are proven by the consumer that uses them.

**Status: pre-alpha.** The repository holds the specification, the core vocabulary and an empty Python package. Nothing is usable yet.

- [Specification](spec/SPEC.md)
- [Vocabulary](spec/VOCABULARY.md)
- [Implementation plan](spec/IMPLEMENTATION_PLAN.md)
- [Decision records](decisions/README.md)

## Development

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest -q
uv run plb --version
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full set of checks.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
