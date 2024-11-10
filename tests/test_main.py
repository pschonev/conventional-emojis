# test_conventional_emojis.py

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from conventional_emojis.exceptions import (
    InvalidCommitTemplateError,
    NoConventionalCommitTypeFoundError,
    NonConventionalCommitError,
    UndefinedScopeError,
)
from conventional_emojis.main import (
    CommitMessageDetails,
    ConventionalEmojisConfig,
    Emojis,
    extract_commit_details,
    get_emojis,
    process_commit_message,
    update_commit_message,
)

VALID_CONFIG_TOML = """
[types]
feat = "✨"
fix = "🐛"
docs = "📚"

[scopes]
api = "🔌"
ui = "🎨"

[combos]
feat.api = "🚀"
"""


@pytest.fixture
def basic_config():
    return ConventionalEmojisConfig(
        types={"feat": "✨", "fix": "🐛", "docs": "📚"},
        scopes={"api": "🔌", "ui": "🎨"},
        breaking_emoji="💥",
        commit_message_template="{breaking_emoji}{type_emoji}{scope_emoji} {conventional_prefix} {description}\n\n{body}",
    )


def test_extract_valid_commit_details():
    commit_message = "feat(api): add new endpoint\n\nThis adds a new API endpoint"
    details = extract_commit_details(commit_message)
    assert details.commit_type == "feat"
    assert details.scope == "api"
    assert details.description == "add new endpoint"
    assert details.body == "This adds a new API endpoint"
    assert not details.breaking


def test_extract_breaking_commit_details():
    commit_message = "feat(api)!: breaking change\n\nThis is breaking"
    details = extract_commit_details(commit_message)
    assert details.breaking
    assert details.commit_type == "feat"
    assert details.scope == "api"


def test_extract_invalid_commit_format():
    with pytest.raises(NonConventionalCommitError):
        extract_commit_details("invalid commit message")


def test_get_emojis_basic(basic_config):
    details = CommitMessageDetails(
        conventional_prefix="feat(api)",
        description="test",
        body="",
        commit_type="feat",
        scope="api",
        breaking=False,
    )
    emojis = get_emojis(details, basic_config)
    assert emojis.type_emoji == "✨"
    assert emojis.scope_emoji == "🔌"
    assert emojis.breaking_emoji == ""


def test_get_emojis_breaking(basic_config):
    details = CommitMessageDetails(
        conventional_prefix="feat(api)!",
        description="test",
        body="",
        commit_type="feat",
        scope="api",
        breaking=True,
    )
    emojis = get_emojis(details, basic_config)
    assert emojis.breaking_emoji == "💥"


def test_get_emojis_invalid_type(basic_config):
    details = CommitMessageDetails(
        conventional_prefix="invalid(api)",
        description="test",
        body="",
        commit_type="invalid",
        scope="api",
        breaking=False,
    )
    with pytest.raises(NoConventionalCommitTypeFoundError):
        get_emojis(details, basic_config)


def test_config_loading():
    with patch("pathlib.Path.open", mock_open(read_data=VALID_CONFIG_TOML)):
        with patch("pathlib.Path.exists", return_value=True):
            config = ConventionalEmojisConfig.from_toml(
                config_file=Path("dummy.toml"),
                allow_types_as_scopes=True,
            )
            assert config.types["feat"] == "✨"
            assert config.scopes["api"] == "🔌"


def test_update_commit_message():
    details = CommitMessageDetails(
        conventional_prefix="feat(api)",
        description="test",
        body="test body",
        commit_type="feat",
        scope="api",
        breaking=False,
    )
    emojis = Emojis(type_emoji="✨", scope_emoji="🔌", breaking_emoji="")
    template = "{breaking_emoji}{type_emoji}{scope_emoji} {conventional_prefix}: {description}\n\n{body}"
    result = update_commit_message(details, emojis, template)
    assert result == "✨🔌 feat(api): test\n\ntest body"


def test_update_commit_message_invalid_template():
    details = CommitMessageDetails(
        conventional_prefix="feat(api)",
        description="test",
        body="",
        commit_type="feat",
        scope="api",
        breaking=False,
    )
    emojis = Emojis(type_emoji="✨", scope_emoji="🔌", breaking_emoji="")
    with pytest.raises(InvalidCommitTemplateError):
        update_commit_message(details, emojis, "{invalid}")


# Test End-to-End Processing
def test_process_commit_message(basic_config):
    commit_message = "feat(api): add endpoint\n\nDetails here"
    result = process_commit_message(commit_message, basic_config)
    assert "✨🔌 feat(api): add endpoint\n\nDetails here" == result


# Test Scope Pattern Enforcement
def test_enforce_scope_patterns(basic_config):
    details = CommitMessageDetails(
        conventional_prefix="feat(invalid)",
        description="test",
        body="",
        commit_type="feat",
        scope="invalid",
        breaking=False,
    )
    with pytest.raises(UndefinedScopeError):
        get_emojis(details, basic_config, enforce_scope_patterns=True)
