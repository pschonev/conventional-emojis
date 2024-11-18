import pytest

from conventional_emojis.constants import (
    BREAKING,
    COMMIT_MESSAGE_TEMPLATE,
    COMMIT_TYPES,
)
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


@pytest.fixture
def basic_toml() -> str:
    return """[types]
feat = "🔥"
fix = "🙌"
docs = "📖"
chore = "🏡"

[scopes]
api = "🔌"
ui = "🎨"

[combos.feat]
api = "🚀"

[combos.chore]
"lint.*|typecheck.*" = "☝️🤓"
"catch|except.*|error.*" = "🥅"

[config]
breaking_emoji = "🍌"
commit_message_template = "{breaking_emoji}{type_emoji}{scope_emoji} {conventional_prefix} {description}\\n\\n{body}"
"""


@pytest.fixture
def basic_config(basic_toml: str) -> ConventionalEmojisConfig:
    return ConventionalEmojisConfig.from_toml(basic_toml)


##### Load Configuration #####
class TestConfigLoading:
    def test_config_loading_base_values(self, basic_config: ConventionalEmojisConfig):
        """Test that basic configuration values are loaded correctly."""
        assert basic_config.types == {
            "feat": "🔥",
            "fix": "🙌",
            "docs": "📖",
            "chore": "🏡",
            "style": "💄",
            "refactor": "♻️",
            "perf": "⚡️",
            "test": "✅",
            "build": "🏗️",
            "ci": "👷",
            "config": "🔧",
            "wip": "🚧",
        }
        assert basic_config.config.breaking_emoji == "🍌"
        assert (
            basic_config.config.commit_message_template
            == "{breaking_emoji}{type_emoji}{scope_emoji} {conventional_prefix} {description}\n\n{body}"
        )

    def test_config_loading_scopes(self, basic_config: ConventionalEmojisConfig):
        """Test that scopes are loaded correctly (with types as scopes)."""
        assert basic_config.scopes == {
            "api": "🔌",
            "ui": "🎨",
            "feat": "🔥",
            "fix": "🙌",
            "docs": "📖",
            "chore": "🏡",
            "style": "💄",
            "refactor": "♻️",
            "perf": "⚡️",
            "test": "✅",
            "build": "🏗️",
            "ci": "👷",
            "config": "🔧",
            "wip": "🚧",
        }

    def test_disallow_types_as_scopes(self, basic_toml: str):
        """Test that types cannot be used as scopes."""
        config_without_types_as_scopes = ConventionalEmojisConfig.from_toml(
            basic_toml,
            allow_types_as_scopes=False,
        )
        assert config_without_types_as_scopes.scopes == {
            "api": "🔌",
            "ui": "🎨",
        }

    def test_config_loading_combos(self, basic_config: ConventionalEmojisConfig):
        """Test that combo patterns are loaded correctly."""
        assert basic_config.combos == {
            "feat": {"api": "🚀"},
            "chore": {"lint.*|typecheck.*": "☝️🤓", "catch|except.*|error.*": "🥅"},
        }

    def test_empty_config(self):
        """Test configuration with empty TOML content."""
        config = ConventionalEmojisConfig.from_toml("")
        assert config.types == COMMIT_TYPES
        assert config.scopes is None
        assert config.combos is None
        assert config.config.breaking_emoji == BREAKING
        assert config.config.commit_message_template == COMMIT_MESSAGE_TEMPLATE

    def test_template_override(self):
        """Test that template override works correctly."""
        custom_template = "{breaking_emoji}{conventional_prefix}{type_emoji}{scope_emoji} {description}\n{body}"
        config = ConventionalEmojisConfig.from_toml(
            "",
            template_override=custom_template,
        )
        assert config.config.commit_message_template == custom_template


##### Extract Commit Details #####


class TestExtractCommitDetails:
    def test_extract_valid_commit_details(self):
        commit_message = "feat(api): add new endpoint\n\nThis adds a new API endpoint"
        details = extract_commit_details(commit_message)
        assert details.commit_type == "feat"
        assert details.scope == "api"
        assert details.description == "add new endpoint"
        assert details.body == "This adds a new API endpoint"
        assert not details.breaking

    def test_extract_breaking_commit_details(self):
        commit_message = "feat(api)!: breaking change\n\nThis is breaking"
        details = extract_commit_details(commit_message)
        assert details.breaking
        assert details.commit_type == "feat"
        assert details.scope == "api"

    def test_extract_invalid_commit_format(self):
        with pytest.raises(NonConventionalCommitError):
            extract_commit_details("invalid commit message")


###### Get Emojis #######


class TestGetEmojis:
    @pytest.mark.parametrize(
        (
            "commit_type",
            "scope",
            "breaking",
            "expected_type_emoji",
            "expected_scope_emoji",
            "expected_breaking_emoji",
        ),
        [
            (
                "chore",
                "typechecking",
                False,
                "☝️🤓",
                "",
                "",
            ),  # Matches lint.*|typecheck.* pattern
            (
                "chore",
                "catch",
                False,
                "🥅",
                "",
                "",
            ),  # Matches catch|except.*|error pattern
            (
                "chore",
                "error_handling",
                False,
                "🥅",
                "",
                "",
            ),  # Matches catch|except.*|error pattern
            ("feat", "api", False, "🚀", "", ""),  # Direct match in feat combos
            ("feat", "ui", False, "🔥", "🎨", ""),  # Direct match in scopes
            (
                "chore",
                "other",
                False,
                "🏡",
                "",
                "",
            ),  # Falls back to type emoji when no combo match
            (
                "feat",
                "ui",
                True,
                "🔥",
                "🎨",
                "🍌",
            ),  # Test breaking change with scope emoji
        ],
    )
    def test_emoji_resolution(
        self,
        basic_config: ConventionalEmojisConfig,
        commit_type: str,
        scope: str,
        breaking: bool,
        expected_type_emoji: str,
        expected_scope_emoji: str,
        expected_breaking_emoji: str,
    ):
        """Test that emoji resolution works correctly for different combinations."""
        details = CommitMessageDetails(
            conventional_prefix=f"{commit_type}({scope})",
            description="Test commit",
            body="",
            commit_type=commit_type,
            scope=scope,
            breaking=breaking,
        )
        emojis = get_emojis(details, basic_config)
        assert emojis.type_emoji == expected_type_emoji
        assert emojis.scope_emoji == expected_scope_emoji
        assert emojis.breaking_emoji == expected_breaking_emoji

    def test_breaking_changes(self, basic_config: ConventionalEmojisConfig):
        """Test that breaking changes are handled correctly."""
        details = CommitMessageDetails(
            conventional_prefix="feat(api)!",
            description="Breaking API change",
            body="",
            commit_type="feat",
            scope="api",
            breaking=True,
        )
        emojis = get_emojis(details, basic_config)
        assert emojis.breaking_emoji == "🍌"
        assert emojis.type_emoji == "🚀"  # Should still get combo emoji

    def test_get_emojis_invalid_type(self, basic_config):
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

    # Test Scope Pattern Enforcement
    def test_enforce_scope_patterns(self, basic_config):
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


##### Update Commit Message #####


class TestUpdateCommitMessage:
    def test_update_commit_message(self):
        details = CommitMessageDetails(
            conventional_prefix="feat(api)",
            description="test",
            body="test body",
            commit_type="feat",
            scope="api",
            breaking=False,
        )
        emojis = Emojis(type_emoji="🔥", scope_emoji="🔌", breaking_emoji="")
        template = "{breaking_emoji}{type_emoji}{scope_emoji} {conventional_prefix}: {description}\n\n{body}"
        result = update_commit_message(details, emojis, template)
        assert result == "🔥🔌 feat(api): test\n\ntest body"

    def test_update_commit_message_invalid_template(self):
        details = CommitMessageDetails(
            conventional_prefix="feat(api)",
            description="test",
            body="",
            commit_type="feat",
            scope="api",
            breaking=False,
        )
        emojis = Emojis(type_emoji="🔥", scope_emoji="🔌", breaking_emoji="")
        with pytest.raises(InvalidCommitTemplateError):
            update_commit_message(details, emojis, "{invalid}")


##### Full Messages #####


class TestFullMessageFormatting:
    def test_full_message_formatting(self, basic_config: ConventionalEmojisConfig):
        """Test complete message formatting with all components."""
        details = CommitMessageDetails(
            conventional_prefix="feat(api)!",
            description="Add new endpoint",
            body="This is a breaking change",
            commit_type="feat",
            scope="api",
            breaking=True,
        )
        emojis = get_emojis(details, basic_config)
        result = update_commit_message(
            details,
            emojis,
            basic_config.config.commit_message_template,
        )
        expected = "🍌🚀 feat(api)! Add new endpoint\n\nThis is a breaking change"
        assert result == expected

    # Test End-to-End Processing
    def test_process_commit_message(self, basic_config):
        commit_message = "chore(linting): add endpoint\n\nDetails here"
        result = process_commit_message(commit_message, basic_config)
        assert result == "☝️🤓 chore(linting): add endpoint\n\nDetails here"


##### Commit Message Edge Cases #####


class TestCommitMessageEdgeCases:
    def test_empty_commit_message(self, basic_config):
        """Test that an error is raised for an empty commit message."""
        with pytest.raises(NonConventionalCommitError):
            process_commit_message("", basic_config)

    def test_invalid_commit_message(self, basic_config):
        """Test that an error is raised for an invalid commit message."""
        with pytest.raises(NonConventionalCommitError):
            process_commit_message("invalid message", basic_config)

    def test_commit_with_no_scope(self, basic_config):
        """Test that a commit message with no scope is processed correctly."""
        result = process_commit_message("feat: add new feature", basic_config)
        assert result == "🔥 feat: add new feature"

    def test_commit_with_invalid_type(self, basic_config):
        """Test that an error is raised for a commit message with an invalid type."""
        with pytest.raises(NoConventionalCommitTypeFoundError):
            process_commit_message("invalid(scope): add new feature", basic_config)

    def test_commit_without_description(self, basic_config):
        """Test that a commit message without a description is processed correctly."""
        result = process_commit_message("feat(api):", basic_config)
        assert result == "🚀 feat(api):"


##### Templates #####


class TestCustomTemplates:
    def test_commit_with_custom_template(self, basic_toml: str):
        """Test that a custom commit message template is used."""
        custom_template = "{breaking_emoji} {conventional_prefix} {type_emoji}{scope_emoji} {description}\n{body}"
        config = ConventionalEmojisConfig.from_toml(
            basic_toml,
            template_override=custom_template,
        )
        result = process_commit_message("feat(ui)!: add new feature", config)
        assert result == "🍌 feat(ui)!: 🔥🎨 add new feature"

    def test_template_with_no_emojis(self, basic_toml: str):
        """Test that a template with no emojis is used correctly."""
        custom_template = "{conventional_prefix} {description}\n{body}"
        config = ConventionalEmojisConfig.from_toml(
            basic_toml,
            template_override=custom_template,
        )
        result = process_commit_message("feat(ui): add new feature", config)
        assert result == "feat(ui): add new feature"

    def test_template_without_breaking_emoji(self, basic_toml: str):
        """Test that a template without a breaking emoji is used correctly."""
        custom_template = (
            "{type_emoji}{scope_emoji} {conventional_prefix} {description}\n{body}"
        )
        config = ConventionalEmojisConfig.from_toml(
            basic_toml,
            template_override=custom_template,
        )
        result = process_commit_message("feat(ui)!: add new feature", config)
        assert result == "🔥🎨 feat(ui)!: add new feature"

    def test_template_with_typo(self, basic_toml: str):
        """Test that an error is raised for an invalid template with a typo (prefix -> prefiz)."""
        custom_template = (
            "{type_emoji}{scope_emoji} {conventional_prefiz} {description}\n{body}"
        )
        config = ConventionalEmojisConfig.from_toml(
            basic_toml,
            template_override=custom_template,
        )
        with pytest.raises(InvalidCommitTemplateError):
            process_commit_message("feat(ui): add new feature", config)
