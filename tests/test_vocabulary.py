import pytest

from factmodel import vocabulary

EXPECTED_BLOCKS = {
    "file_kind",
    "evidence_status",
    "representative",
    "source_kind",
    "access_mode",
    "entity_class",
    "entity_status",
    "subject_scope",
    "scope_basis",
    "mechanism",
    "cardinality",
    "service_kind",
    "derived_value",
}


@pytest.fixture(scope="module")
def blocks() -> dict[str, list[str]]:
    return vocabulary.parse_blocks(vocabulary.vocabulary_text())


def test_every_block_parses(blocks: dict[str, list[str]]) -> None:
    assert blocks
    assert all(values for values in blocks.values())


def test_expected_blocks_present(blocks: dict[str, list[str]]) -> None:
    assert blocks.keys() >= EXPECTED_BLOCKS


def test_no_problems(blocks: dict[str, list[str]]) -> None:
    assert vocabulary.validate(blocks) == []


def test_every_block_is_found() -> None:
    # A block whose opening line drifts from the pattern would be skipped silently.
    text = vocabulary.vocabulary_text()
    assert text.count("```yaml vocabulary:") == len(vocabulary.parse_blocks(text))


def test_load_returns_tuples() -> None:
    loaded = vocabulary.load()
    assert loaded["evidence_status"] == ("confirmed", "inferred", "unresolved", "retracted")
    assert loaded["representative"] == ("true", "false", "unknown")


def test_duplicate_block_name_fails() -> None:
    text = "```yaml vocabulary:a\n- x\n```\n\n```yaml vocabulary:a\n- y\n```\n"
    with pytest.raises(vocabulary.VocabularyError, match="duplicate vocabulary block"):
        vocabulary.parse_blocks(text)


def test_non_list_block_fails() -> None:
    with pytest.raises(vocabulary.VocabularyError, match="list of strings"):
        vocabulary.parse_blocks("```yaml vocabulary:a\nkey: value\n```\n")


def test_unquoted_boolean_fails() -> None:
    with pytest.raises(vocabulary.VocabularyError, match="list of strings"):
        vocabulary.parse_blocks("```yaml vocabulary:a\n- true\n```\n")


@pytest.mark.parametrize(
    ("blocks", "problem"),
    [
        ({"a": ["x", "x"]}, "a: duplicate value: x"),
        ({"a": ["Bad"]}, "a: value is not a slug: 'Bad'"),
        ({"a": ["-x"]}, "a: value is not a slug: '-x'"),
        ({"a": ["x" * 65]}, "a: value is not a slug"),
        ({"Bad": ["x"]}, "block name is not a slug: Bad"),
    ],
)
def test_validate_reports(blocks: dict[str, list[str]], problem: str) -> None:
    problems = vocabulary.validate(blocks)
    assert any(p.startswith(problem) for p in problems), problems
